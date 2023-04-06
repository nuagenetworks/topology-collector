#!/usr/bin/python
#  Copyright 2018 NOKIA
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
import binascii
import ctypes
import fcntl
import json
import os
import re
import select
import socket
import struct
import sys

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: lldp
short_description: Given an interface list, returns ToR port information
and VF PCI info in JSON
options:
  interfaces:
    description:
      - List of network interfaces to query
    required: true
  ovs_bridges:
    description:
      - Dict with interface to bridge mappings
    required: true
  lldp_timeout:
    default: 30
    description:
      - Max time to wait for LLDP packet to arrive
'''

EXAMPLES = '''
- topology:
    interfaces: [eth0]
'''


ANY_ETHERTYPE = 0x0003
IFF_PROMISC = 0x100
SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914

# TLV types
LLDP_TLV_PORT_ID = 2
LLDP_TLV_SYS_NAME = 5
LLDP_TLV_SYS_DESCRIPTION = 6
LLDP_TLV_MGMT_ADDRESS = 8

SOL_SOCKET = 1
SO_ATTACH_FILTER = 26


class ifreq(ctypes.Structure):
    """Class for setting flags on a socket."""
    _fields_ = [("ifr_ifrn", ctypes.c_char * 16),
                ("ifr_flags", ctypes.c_short)]


class bpf_insn(ctypes.Structure):
    """"The BPF instruction data structure"""
    _fields_ = [("code", ctypes.c_ushort),
                ("jt", ctypes.c_ubyte),
                ("jf", ctypes.c_ubyte),
                ("k", ctypes.c_uint32)]


class bpf_program(ctypes.Structure):
    """"Structure for BIOCSETF"""
    _fields_ = [("bf_len", ctypes.c_uint),
                ("bf_insns", ctypes.POINTER(bpf_insn))]


# Shamelessly copied/modified from
# ironic-python-agent
class RawPromiscuousSockets(object):
    def __init__(self, interface_names, protocol, module):
        """Initialize context manager.

        :param interface_names: a list of interface names to bind to
        :param protocol: the protocol to listen for
        :returns: A list of tuple of (interface_name, bound_socket), or [] if
                  there is an exception binding or putting the sockets in
                  promiscuous mode
        """
        if not interface_names:
            raise ValueError('interface_names must be a non-empty list of '
                             'network interface names to bind to.')
        self.protocol = protocol
        self.module = module
        self.ovs_bridges = module.params['ovs_bridges']

        # A 4-tuple of (interface_name, socket, ifreq object, sink)
        self.interfaces = [(name, self._get_socket(),
                            ifreq(), self._get_iface_sink(name))
                           for name in interface_names]

    def __enter__(self):
        for interface_name, sock, ifr, sink in self.interfaces:
            iface = sink or interface_name
            try:
                self.module.log('Interface {} entering promiscuous '
                                'mode to capture '.format(iface))
                ifr.ifr_ifrn = iface.encode()
                # Get current flags
                fcntl.ioctl(sock.fileno(), SIOCGIFFLAGS, ifr)  # G for Get
                # bitwise or the flags with promiscuous mode, set the new flags
                ifr.ifr_flags |= IFF_PROMISC
                fcntl.ioctl(sock.fileno(), SIOCSIFFLAGS, ifr)  # S for Set
                # Bind the socket so it can be used
                self.module.log('Binding interface {} for protocol '
                                '{}'.format(iface,
                                            self.protocol))
                sock.bind((iface, self.protocol))

                # Attach kernel packet filter for lldp protocol
                bpf = self._get_bpf_filter()
                sock.setsockopt(SOL_SOCKET, SO_ATTACH_FILTER, bpf)

            except Exception:
                self.module.log('Failed to open all RawPromiscuousSockets, '
                                'attempting to close any opened sockets.')
                self.__exit__(*sys.exc_info())
                raise

        # No need to return each interfaces ifreq.
        return [(sock[0], sock[1]) for sock in self.interfaces]

    def __exit__(self, exception_type, exception_val, trace):
        for name, sock, ifr, sink in self.interfaces:
            # bitwise or with the opposite of promiscuous mode to remove
            ifr.ifr_flags &= ~IFF_PROMISC
            try:
                fcntl.ioctl(sock.fileno(), SIOCSIFFLAGS, ifr)
                sock.close()
                if sink:
                    bridge = self.ovs_bridges.get(name)
                    self._clean_lldp_config(sink,
                                            bridge.get('bridge'))
            except Exception:
                self.module.log('Failed to close raw socket for interface '
                                '{}'.format(sink or name))

    def _get_socket(self):
        return socket.socket(socket.AF_PACKET, socket.SOCK_RAW, self.protocol)

    def _get_bpf_filter(self):
        """ Kernel packet filter for lldp proto.

        Unfortunately instantiation of the class with lldp proto
        does not work for interfaces under OVS bridge.
        Black magic using kernel BPF filter follows

        /sbin/tcpdump -i <itf> -ddd -s 1600 \
            'ether proto 0x88cc and ether dst 01:80:c2:00:00:0e'
        """
        filter = ['8\n', '40 0 0 12\n', '21 0 5 35020\n', '32 0 0 2\n',
                  '21 0 3 3254779918\n', '40 0 0 0\n', '21 0 1 384\n',
                  '6 0 0 1600\n', '6 0 0 0\n']

        # Allocate BPF instructions
        size = int(filter[0])
        bpf_insn_a = bpf_insn * size
        bip = bpf_insn_a()
        # Fill the BPF instruction structures with the byte code
        filter = filter[1:]
        i = 0
        for line in filter:
            values = [int(v) for v in line.split()]
            bip[i].code = ctypes.c_ushort(values[0])
            bip[i].jt = ctypes.c_ubyte(values[1])
            bip[i].jf = ctypes.c_ubyte(values[2])
            bip[i].k = ctypes.c_uint(values[3])
            i += 1
        # Create the BPF program
        return bpf_program(size, bip)

    def _get_iface_sink(self, interface):
        sink = None
        bridge = self.ovs_bridges.get(interface)
        try:
            if bridge and bridge['type'] == 'dpdk':
                sink = self._prepare_itf_for_lldp(interface,
                                                  bridge['bridge'])
        except Exception:
            self.module.log('failed to create sink for interface {}'.format(
                interface))
        finally:
            return sink

    def _prepare_itf_for_lldp(self, interface, bridge):
        if not bridge:
            return None
        # Setup a lldp sink port and ovs flow
        sink = 'lldp.' + interface
        params = {
            'vsctl': self.module.get_bin_path("ovs-vsctl", True),
            'ofctl': self.module.get_bin_path("ovs-ofctl", True),
            'ip': self.module.get_bin_path("ip", True),
            'br': bridge,
            'ovsif': sink
        }
        # Setup a lldp sink port
        cmd = ("%(vsctl)s --may-exist add-port %(br)s %(ovsif)s -- "
               "set interface %(ovsif)s type=internal" % params)
        self.module.run_command(cmd, check_rc=True)
        # add flow to lldp port
        cmd = ("%(ofctl)s dump-ports-desc %(br)s" % params)
        _, out, _ = self.module.run_command(cmd, check_rc=True)
        # in port
        b = re.search(r'\s+(\d+)\({0}\):'.format(interface), out)
        params['in'] = b.group(1) if b else None
        # out port
        b = re.search(r'\s+(\d+)\({0}\):'.format(sink), out)
        params['out'] = b.group(1) if b else None

        cmd = ("%(ofctl)s add-flow %(br)s in_port=%(in)s,"
               "dl_dst=01:80:c2:00:00:0e,dl_type=0x88cc,"
               "actions=output:%(out)s" %
               params)
        self.module.run_command(cmd, check_rc=True)

        cmd = ("%(ip)s link set up dev %(ovsif)s" % params)
        self.module.run_command(cmd, check_rc=True)

        return sink

    def _clean_lldp_config(self, sink, bridge):
        params = {
            'vsctl': self.module.get_bin_path("ovs-vsctl", True),
            'ofctl': self.module.get_bin_path("ovs-ofctl", True),
            'br': bridge,
            'ovsif': sink
        }
        command = ("%(ofctl)s del-flows %(br)s "
                   "dl_dst=01:80:c2:00:00:0e" % params)
        self.module.run_command(command, check_rc=True)
        cmd = ("%(vsctl)s del-port %(br)s %(ovsif)s" % params)
        self.module.run_command(cmd, check_rc=True)


def get_lldp_info(interface_names, module):
    """Get LLDP info from the switch(es).

    Listens on either a single or all interfaces for LLDP packets, then
    parses them. If no LLDP packets are received before lldp_timeout,
    returns a dictionary in the form {'interface': [],...}.

    :param interface_names: The interface to listen for packets on. If
                           None, will listen on each interface.
    :return: A dictionary in the form
             {'interface': [(lldp_type, lldp_data)],...}
    """
    with RawPromiscuousSockets(interface_names,
                               ANY_ETHERTYPE, module) as interfaces:
        try:
            return _get_lldp_info(interfaces, module)
        except Exception as e:
            module.log('Error while getting LLDP info: %s', str(e))
            raise


def _parse_tlv(buff):
    """Iterate over a buffer and generate structured TLV data.

    :param buff: An ethernet packet with the header trimmed off (first
                 14 bytes)
    """
    lldp_info = []
    while len(buff) >= 2:
        # TLV structure: type (7 bits), length (9 bits), val (0-511 bytes)
        tlvhdr = struct.unpack('!H', buff[:2])[0]
        tlvtype = (tlvhdr & 0xfe00) >> 9
        tlvlen = (tlvhdr & 0x01ff)
        tlvdata = buff[2:tlvlen + 2]
        buff = buff[tlvlen + 2:]
        lldp_info.append((tlvtype,
                          binascii.hexlify(tlvdata).decode()))
    return lldp_info


def _receive_lldp_packets(sock):
    """Receive LLDP packets and process them.

    :param sock: A bound socket
    :return: A list of tuples in the form (lldp_type, lldp_data)
    """
    pkt, sa_ll = sock.recvfrom(1600)
    # Filter outgoing packets
    if sa_ll[2] == socket.PACKET_OUTGOING:
        return []
    # Filter invalid packets
    if not pkt or len(pkt) < 14:
        return []
    # Skip header (dst MAC, src MAC, ethertype)
    pkt = pkt[14:]
    return _parse_tlv(pkt)


def _get_lldp_info(interfaces, module):
    """Wait for packets on each socket, parse the received LLDP packets."""
    module.log('Getting LLDP info for interfaces {}'.format(interfaces))

    lldp_info = {}
    if not interfaces:
        return {}

    while interfaces:
        module.log('Waiting on LLDP info for interfaces: {}, '
                   'timeout: {}'.format(interfaces,
                                        module.params['lldp_timeout']))

        socks = [interface[1] for interface in interfaces]
        # rlist is a list of sockets ready for reading
        rlist, _, _ = select.select(
            socks, [], [], module.params['lldp_timeout'])

        if not rlist:
            # Empty read list means timeout on all interfaces
            module.log('LLDP timed out, remaining interfaces: {}'.format(
                interfaces))
            break

        for s in rlist:
            # rlist is a list of sockets ready for reading
            rlist, _, _ = select.select(
                socks, [], [], module.params['lldp_timeout'])
        if not rlist:
            # Empty read list means timeout on all interfaces
            module.log('LLDP timed out, remaining interfaces: {}'.format(
                interfaces))
            break

        for s in rlist:
            # Find interface name matching socket ready for read
            # Create a copy of interfaces to avoid deleting while iterating.
            for index, interface in enumerate(list(interfaces)):
                if s == interface[1]:
                    try:
                        lldp_info[interface[0]] = _receive_lldp_packets(s)
                    except socket.error:
                        module.log('Socket for network interface {} said '
                                   'that it was ready to read we were '
                                   'unable to read from the socket while '
                                   'trying to get LLDP packet. Skipping '
                                   'this network interface.'.format(
                                       interface[0]))
                        del interfaces[index]
                    else:
                        # Remove interface from the list, if pkt is not
                        # outgoing/short
                        if lldp_info[interface[0]]:
                            module.log(
                                'Found LLDP info for interface: {}'.format(
                                    interface[0]))
                            del interfaces[index]

    # Add any interfaces that didn't get a packet as empty lists
    for name, _sock in interfaces:
        lldp_info[name] = []

    return lldp_info


def get_vf_devices(dev_name):
    VF_DEVICE_PATH = "/sys/class/net/%s/device"
    VIRTFN_FORMAT = r"^virtfn(?P<vf_index>\d+)"
    VIRTFN_REG_EX = re.compile(VIRTFN_FORMAT)

    devices = {
        "name": dev_name,
        "vf_info": []
    }

    dev_path = VF_DEVICE_PATH % dev_name
    if os.path.isdir(dev_path):
        file_list = os.listdir(dev_path)
        for file_name in file_list:
            pattern_match = VIRTFN_REG_EX.match(file_name)
            if pattern_match:
                vf_name = pattern_match.group(0)
                file_path = os.path.join(dev_path, file_name)
                if os.path.islink(file_path):
                    file_link = os.readlink(file_path)
                    pci_slot = os.path.basename(file_link)
                    entry = {
                        'device-name': vf_name,
                        'pci-id': pci_slot,
                    }
                    devices['vf_info'].append(entry)
    return devices


def main():
    arg_spec = dict(
        interfaces=dict(type='list', required=True),
        ovs_bridges=dict(type='dict', required=True),
        lldp_timeout=dict(type='int', required=False, default=30),
    )

    module = AnsibleModule(argument_spec=arg_spec)

    interfaces = module.params['interfaces']

    lldpinfo = get_lldp_info(interfaces, module)
    itfinfo = dict()
    for interface in interfaces:
        vfinfo = get_vf_devices(interface)
        itfinfo[interface] = {
            'lldp': lldpinfo.get(interface),
            'vfinfo': vfinfo
        }
    module.exit_json(interfaces=interfaces,
                     stdout=json.dumps(itfinfo, indent=4),
                     changed=True)


if __name__ == '__main__':
    main()
