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
import datetime
import os
import re
import time

from ansible.module_utils.basic import AnsibleModule
from abc import abstractmethod

DOCUMENTATION = '''
---
module: topology
short_description: Given an interface, returns VSG ToR port
and VF PCI info in JSON
options:
  system_name:
    description:
      - The system name or IP address of the compute node
        being processed
    required: true
  interface:
    description:
      - The network interface to interrogate
    required: true
  ovs_bridge:
    description:
      - OVS bridge this interface belongs to
    required: false
  host:
    default: '127.0.0.1'
    description:
      - OVS Manager address
  port:
    default: '6640'
    description:
      - OVS Manager port
  advanced_mode:
    default: False
    description:
      - Execution mode of LLDP collection.
        advanced_mode will trigger creation of LLDP sink port
        under ovs_bridge and will install a specific LLDP flow from
        interface to sink port created
'''

EXAMPLES = '''
- topoloy: system_name=192.168.1.1 interface=eth0
- topoloy: system_name=cas-cs2-011 interface=eno4
'''


class Switch(object):

    def __init__(self, name):
        self.name = name

    # generate_json() is a function that takes two input strings of
    # specific syntax and creates a JSON string from specific portions
    # of those outputs. The input strings are generated from two specific
    # commands. As such, this function is tightly comupled to the outputs
    # of those commands. The first command is lldptool. The second is ls.
    # The exact syntax of these commands is shown in the main() function
    # in this file. If the outputs or commands change, the code in this
    # function must change with them.

    @abstractmethod
    def generate_json(self, interface, lldpout, lsout, ovsapi=None):
        pass

    def validate_lldp(self, lldpout):
        LLDPSYSTEMNAME = "System Name TLV"
        SYSTEMNAME_RE = LLDPSYSTEMNAME + r"\s+(\S+)\s+"
        LLDPSYSTEMIP = "Management Address TLV"
        SYSTEMIP_RE = LLDPSYSTEMIP + r"\s+\S+:\s+(\S+)\s+"
        LLDPSYSTEMPORT = "Port ID TLV"
        SYSTEMPORT_RE = LLDPSYSTEMPORT + r"\s+\S+:\s+(\S+)\s+"

        raise_error = False

        neighborname = "None"
        neighborip = "None"
        neighborport = "None"

        # Now add neighbor information
        scratch = re.search(SYSTEMNAME_RE, lldpout)
        if scratch:
            neighborname = scratch.group(1)
        else:
            raise_error = True

        scratch = re.search(SYSTEMIP_RE, lldpout)
        if scratch:
            neighborip = scratch.group(1)
        else:
            raise_error = True

        scratch = re.search(SYSTEMPORT_RE, lldpout)
        if scratch:
            neighborport = scratch.group(1)
        else:
            raise_error = True

        if raise_error:
            raise Exception(neighborname, neighborip, neighborport)

        return neighborname, neighborip, neighborport

    @staticmethod
    def create_vfs_json(interface, lsout):
        # Insert the interface name into the JSON object.
        vfs_info = "\n \"name\": \"%s\"" % interface

        # Insert VF port info
        vf_info = ",\n \"vf_info\": ["
        lines = lsout.split('\n')
        found_first_match = False
        for line in lines:
            if re.search(" virt", line) and "->" in line:
                fmt = ",\n { \"device-name\": \"%s\""
                vf_parts = line.split("->")
                vif_info = vf_parts[0].split()[-1]
                pci_id = vf_parts[-1].split('/')
                if (vf_info and re.search(
                        "virt", vif_info) and pci_id and len(pci_id) >= 2):
                    if not found_first_match:
                        found_first_match = True
                        fmt = "\n { \"device-name\": \"%s\""
                    vf_info += fmt % vif_info
                    vf_info += ", \"pci-id\": \"%s\" }" % pci_id[-1]
        vf_info += "]"
        vfs_info += vf_info
        return vfs_info

    @staticmethod
    def create_system_json(parsed, neighborname, neighborip,
                           neighborport, bridge=None):

        NEIGHBORNAME = "neighbor-system-name"
        NEIGHBORIP = "neighbor-system-mgmt-ip"
        NEIGHBORPORT = "neighbor-system-port"
        OVSBRIDGE = 'ovs-bridge'

        parsed += ",\n \"%s\": \"%s\"" % (NEIGHBORNAME, neighborname)
        parsed += ",\n \"%s\": \"%s\"" % (NEIGHBORIP, neighborip)
        parsed += ",\n \"%s\": \"%s\"" % (NEIGHBORPORT, neighborport)
        if bridge:
            parsed += ",\n \"%s\": \"%s\"" % (OVSBRIDGE, bridge)
        else:
            parsed += ",\n \"%s\": null" % OVSBRIDGE

        return "{ %s }" % parsed


class NokiaSwitch(Switch):
    def __init__(self):
        super(NokiaSwitch, self).__init__('nokia')

    # convert_ifindex_to_ifname() is a function that converts the ifindex
    # we get from the Port ID TLV output of lldptool into the ifname
    # of the form x/y/z
    # The following schemes are supported:
    # 32 bit unsigned integer
    # Scheme B
    # None-connector 0110|Zero(5)|Slot(5)|MDA(4)|0|Zero(2)|Port(8)|Zero(3)
    # Connector 0110|Zero(5)|Slot(5)|MDA(4)|1|Zero(1)|Conn(6)|ConnPort(6)
    # Scheme C
    # None-connector 000|Slot(4)|Port-Hi(2)|MDA(2)|Port-Lo(6)|0|Zero(14)
    # Connector 000|Slot(4)|Zero(2)|MDA(2)|Conn(6)|1|Zero(8)|ConnPort(6)
    # Scheme D
    # None-connector 0x4D|isChannel(1)|0|slot(3)|mda(4)|0|0|Zero(5)|Port(8)
    # Connector 0x4D|isChannel(1)|0|slot(3)|mda(4)|0|1|0|Conn(6)|ConnPort(6)

    def convert_ifindex_to_ifname(self, ifindex):
        if not ifindex.isdigit():
            return 'None'

        ifindex = int(ifindex)
        scheme, connector = self._get_scheme_decode_format(ifindex)
        # Scheme B
        if scheme == 3:
            slot = (ifindex >> 18) & 0x1f
            mda = (ifindex >> 14) & 0x0f
            if connector:
                return "%s/%s/c%s/%s" % (
                    slot, mda,
                    (ifindex >> 6) & 0x3f,
                    ifindex & 0x3f)
            else:
                return "%s/%s/%s" % (
                    slot, mda,
                    (ifindex >> 3) & 0xff)
        # Scheme C
        elif scheme == 0:
            slot = ifindex >> 25
            mda = (ifindex >> 21) & 0x03
            if connector:
                return "%s/%s/c%s/%s" % (
                    slot, mda,
                    (ifindex >> 15) & 0x3f,
                    ifindex & 0x3f)
            else:
                return "%s/%s/%s" % (
                    slot, mda,
                    (ifindex >> 15) & 0x3f | (ifindex >> 17) & 0xc0)
        # Scheme D
        elif scheme == 2:
            slot = (ifindex >> 19) & 0x07
            mda = (ifindex >> 15) & 0x0f
            if connector:
                return "%s/%s/c%s/%s" % (
                    slot, mda,
                    (ifindex >> 6) & 0x3f,
                    ifindex & 0x3f)
            else:
                return "%s/%s/%s" % (
                    slot, mda,
                    ifindex & 0xff)
        else:
            return 'None'

    @staticmethod
    def _get_scheme_decode_format(ifindex):
        scheme = ifindex >> 29
        # Connector Bit - Masks 16384 (Scheme C) & 8192 (Scheme B,D)
        connector = ifindex & 16384 if not scheme else ifindex & 8192
        return scheme, connector

    def generate_json(self, interface, lldpout, lsout, bridge=None):
        vfs_info = self.create_vfs_json(interface, lsout)

        neighborname, neighborip, neighborport = self.validate_lldp(lldpout)
        neighborport = self.convert_ifindex_to_ifname(neighborport)

        return self.create_system_json(vfs_info, neighborname,
                                       neighborip, neighborport, bridge)


class CiscoSwitch(Switch):

    def __init__(self, switch_type):
        super(CiscoSwitch, self).__init__('cisco')
        self.switch_type = switch_type

    def retrieve_port_number(self, neighborport):
        scratch = re.search(r'(\w+)([0-9]+(/[0-9]+)*)', str(neighborport))
        if not scratch:
            return "None"
        if 'NX-OS' in self.switch_type:
            return str(scratch.group(1)[0:3].lower() + scratch.group(2))
        elif 'NCS' in self.switch_type:
            return neighborport
        else:
            return "None"

    def generate_json(self, interface, lldpout, lsout, bridge=None):
        vfs_info = self.create_vfs_json(interface, lsout)

        neighborname, neighborip, neighborport = self.validate_lldp(lldpout)
        # just get the port number
        neighborport = self.retrieve_port_number(neighborport)
        return self.create_system_json(vfs_info, neighborname,
                                       neighborip, neighborport, bridge)


def prepare_itf_for_lldp(ovsdbapi, interface, bridge, module):
    if not bridge:
        return interface
    try:
        from ovsdbapp.schema.open_vswitch import commands as cmd
        from ovsdbapp.backend.ovs_idl import command
    except ImportError:
        module.fail_json(msg="ovsdbapp module is required")

    # Setup a lldp sink port and ovs flow
    sink = 'lldp.' + interface
    with ovsdbapi.transaction(check_error=True) as txn:
        # Add the internal bridge port
        c = cmd.AddPortCommand(ovsdbapi, bridge, sink, may_exist=True)
        txn.add(c)

        c = command.DbSetCommand(ovsdbapi, 'Interface', sink,
                                 ('type', 'internal'))
        txn.add(c)

    # setup itf
    params = {
        'prefix': "sudo " if os.getlogin() != "root" else "",
        'ofctl': module.get_bin_path("ovs-ofctl", True),
        'ip': module.get_bin_path("ip", True),
        'lldptool': module.get_bin_path("lldptool", True),
        'systemctl': module.get_bin_path("systemctl", True),
        'br': bridge,
        'if': interface,
        'ovsif': sink
    }

    # add flow to lldp port
    cmd = ("%(prefix)s %(ofctl)s dump-ports %(br)s %(if)s" % params)
    rc, out, err = module.run_command(cmd, check_rc=True)
    b = re.search(r"\s+port\s+(\d+)", out)
    params['in'] = b.group(1) if b else None

    cmd = ("%(prefix)s %(ofctl)s dump-ports %(br)s %(ovsif)s" % params)
    rc, out, err = module.run_command(cmd, check_rc=True)
    b = re.search(r"\s+port\s+(\d+)", out)
    params['out'] = b.group(1) if b else None

    cmd = ("%(prefix)s %(ofctl)s add-flow %(br)s in_port=%(in)s,"
           "dl_dst=01:80:c2:00:00:0e,dl_type=0x88cc,actions=output:%(out)s" %
           params)
    module.run_command(cmd, check_rc=True)

    commands = list()
    commands.append("%(prefix)s %(ip)s link set up dev %(ovsif)s" % params)
    commands.append("%(prefix)s %(lldptool)s set-lldp -g nb "
                    "-i %(ovsif)s adminStatus=rx" %
                    params)
    commands.append("%(prefix)s %(systemctl)s restart lldpad" % params)

    for c in commands:
        module.run_command(c, check_rc=True)

    return sink


def clean_lldp_config(ovsdbapi, interface, bridge, module):
    if not bridge:
        return
    pname = 'lldp.' + interface
    params = {
        'prefix': "sudo " if os.getlogin() != "root" else "",
        'lldptool': module.get_bin_path("lldptool", True),
        'ofctl': module.get_bin_path("ovs-ofctl", True),
        'ovsif': pname,
        'br': bridge,
    }
    command = ("%(prefix)s %(lldptool)s set-lldp -i %(ovsif)s "
               "adminStatus=disabled" % params)
    module.run_command(command, check_rc=True)
    command = ("%(prefix)s %(ofctl)s del-flows %(br)s "
               "dl_dst=01:80:c2:00:00:0e" % params)
    module.run_command(command, check_rc=True)
    ovsdbapi.del_port(pname, bridge).execute(check_error=True)


def get_ovsdb_client(module):
    try:
        from ovsdbapp.backend.ovs_idl import connection
        from ovsdbapp.schema.open_vswitch import impl_idl
    except ImportError:
        module.fail_json(msg="ovsdbapp module is required")

    endpoint = ("tcp:%(host)s:%(port)s" % module.params)
    client = None
    try:
        idl = connection.OvsdbIdl.from_server(endpoint, 'Open_vSwitch')
        connection = connection.Connection(idl=idl, timeout=3)
        client = impl_idl.OvsdbIdl(connection)
    except Exception as e:
        module.fail_json(msg=("could not connect to openvswitch. "
                              "error: %s") % str(e))
    return client


def get_switch(lldp_packet):
    switch = None
    LLDPSYSTEMDESC = "System Description TLV"
    SYSTEMDESC_RE = LLDPSYSTEMDESC + r"\s([\S\s]+?)(?=TLV)"
    sdtlv = re.search(SYSTEMDESC_RE, lldp_packet)
    if sdtlv:
        sysdesc = sdtlv.group(0)
        if 'Nokia' in sysdesc:
            switch = NokiaSwitch()
        else:
            cisco = re.search(r"NX-OS|NCS-55", sysdesc)
            if cisco:
                switch = CiscoSwitch(cisco.group(0))
    return switch


def main():
    arg_spec = dict(
        system_name=dict(required=True),
        interface=dict(required=True),
        ovs_bridge=dict(required=False),
        host=dict(type='str', required=False, default='127.0.0.1'),
        port=dict(type='str', required=False, default='6640'),
        advanced_mode=dict(type='bool', required=False, default=False),
        lldp_poll_delay=dict(type='int', required=False, default=30)
    )

    module = AnsibleModule(argument_spec=arg_spec)

    system_name = module.params['system_name']
    interface = module.params['interface']
    ovs_bridge = module.params['ovs_bridge']
    advanced_mode = module.params['advanced_mode']
    lldp_poll_delay = module.params['lldp_poll_delay']

    LLDPTOOL = module.get_bin_path('lldptool', True)
    LS = module.get_bin_path('ls', True)

    startd = datetime.datetime.now()
    prefix = "sudo " if os.getlogin() != "root" else ""
    itf = interface
    if advanced_mode:
        ovsdb_client = get_ovsdb_client(module)
        itf = prepare_itf_for_lldp(ovsdb_client, interface, ovs_bridge, module)
        time.sleep(lldp_poll_delay)

    lldpcmd = prefix + "%s -t -n -i %s" % (LLDPTOOL, itf)

    lldprc, lldpout, lldperr = module.run_command(lldpcmd)
    module.log("cmd: {} cmdout: {}".format(lldpcmd, lldpout))
    if lldperr is None:
        lldperr = ''
    if lldpout is None:
        lldpout = ''
    if lldprc != 0:
        lldpout = ''

    # Determining the switch type from the LLDP output itself
    # get_switch() method will return None in case
    # - no System Description TLV in lldp packet
    # - System Description TLV does not contain any recognized
    #   switch type patterns
    switch = get_switch(lldpout)
    if not switch:
        if advanced_mode:
            clean_lldp_config(ovsdb_client, interface, ovs_bridge, module)
        module.exit_json(msg="No System Description TLV received on interface",
                         stdout=None)

    lscmd = "%s -la --time-style long-iso /sys/class/net/%s/device/" % (
        LS, interface)
    lsrc, lsout, lserr = module.run_command(lscmd)

    if lserr is None:
        lserr = ''

    if lsout is None:
        lsout = ''

    if lldprc != 0:
        lldpout = ''

    json_entry = None
    try:
        json_entry = switch.generate_json(interface,
                                          lldpout,
                                          lsout,
                                          ovs_bridge)
    except Exception as e:
        module.fail_json(msg="One of the neighbor information is not "
                             "present in LLDP Output System Name: %s, "
                             "Interface: %s Neighbor Info: %s" % (system_name,
                                                                  interface,
                                                                  e.args),
                         stdout=json_entry)
    finally:
        if advanced_mode:
            clean_lldp_config(ovsdb_client, interface, ovs_bridge, module)

    module.exit_json(lldpcmd=lldpcmd,
                     lscmd=lscmd,
                     system_name=system_name,
                     interface=interface,
                     stdout=json_entry,
                     stderr=lldperr,
                     lldpout=lldpout,
                     lldperr=lldperr,
                     lsout=lsout,
                     lsrc=lsrc,
                     lldprc=lldprc,
                     start=str(startd),
                     end=str(datetime.datetime.now()),
                     delta=str(datetime.datetime.now() - startd),
                     changed=True)


if __name__ == '__main__':
    main()
