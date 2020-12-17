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
import datetime
import json
import re

from ansible.module_utils.basic import AnsibleModule
from abc import abstractmethod
import construct
from construct import core
import functools
import netaddr

DOCUMENTATION = '''
---
module: topology
short_description: Decodes lldp tlvs and produces
json report with interface to TOR switch port mapping
options:
  system_name:
    description:
      - The system name or IP address of the compute node
        being processed
    required: true
  interfaces:
    description:
      - Dict with lldp and VF information per interface
    required: true
  ovs_bridges:
    description:
      - Dict of interface to bridge mappings
    required: false
'''

EXAMPLES = '''
- topoloy:
    system_name: 192.168.1.1
    interfaces: [eth0]
    ovs_bridges: {'eth0': { 'bridge':'br-ex', 'type': 'internal'} }
'''


""" Link Layer Discovery Protocol TLVs """

# TLV types we are interested in
LLDP_TLV_END_LLDPPDU = 0
LLDP_TLV_PORT_ID = 2
LLDP_TLV_SYS_NAME = 5
LLDP_TLV_SYS_DESCRIPTION = 6
LLDP_TLV_MGMT_ADDRESS = 8


def bytes_to_int(obj):
    """Convert bytes to an integer

    :param: obj - array of bytes
    """
    return functools.reduce(lambda x, y: x << 8 | y, obj)


def mapping_for_enum(mapping):
    """Return tuple used for keys as a dict

    :param: mapping - dict with tuple as keys
    """
    return dict(mapping.keys())


def mapping_for_switch(mapping):
    """Return dict from values

     :param: mapping - dict with tuple as keys
     """
    return {key[0]: value for key, value in mapping.items()}


IPv4Address = core.ExprAdapter(
    core.Byte[4],
    encoder=lambda obj, ctx: netaddr.IPAddress(obj).words,
    decoder=lambda obj, ctx: str(netaddr.IPAddress(bytes_to_int(obj)))
)

IPv6Address = core.ExprAdapter(
    core.Byte[16],
    encoder=lambda obj, ctx: netaddr.IPAddress(obj).words,
    decoder=lambda obj, ctx: str(netaddr.IPAddress(bytes_to_int(obj)))
)

MACAddress = core.ExprAdapter(
    core.Byte[6],
    encoder=lambda obj, ctx: netaddr.EUI(obj).words,
    decoder=lambda obj, ctx: str(netaddr.EUI(bytes_to_int(obj),
                                 dialect=netaddr.mac_unix_expanded))
)

IANA_ADDRESS_FAMILY_ID_MAPPING = {
    ('ipv4', 1): IPv4Address,
    ('ipv6', 2): IPv6Address,
    ('mac', 6): MACAddress,
}

IANAAddress = core.Embedded(core.Struct(
    'family' / core.Enum(core.Int8ub, **mapping_for_enum(
        IANA_ADDRESS_FAMILY_ID_MAPPING)),
    'value' / core.Switch(construct.this.family, mapping_for_switch(
        IANA_ADDRESS_FAMILY_ID_MAPPING))))

# Note that 'GreedyString()' is used in cases where string len is not defined
CHASSIS_ID_MAPPING = {
    ('entPhysAlias_c', 1): core.Struct('value' / core.GreedyString("utf8")),
    ('ifAlias', 2): core.Struct('value' / core.GreedyString("utf8")),
    ('entPhysAlias_p', 3): core.Struct('value' / core.GreedyString("utf8")),
    ('mac_address', 4): core.Struct('value' / MACAddress),
    ('IANA_address', 5): IANAAddress,
    ('ifName', 6): core.Struct('value' / core.GreedyString("utf8")),
    ('local', 7): core.Struct('value' / core.GreedyString("utf8"))
}

#
# Basic Management Set TLV field definitions
#

# Chassis ID value is based on the subtype
ChassisId = core.Struct(
    'subtype' / core.Enum(core.Byte, **mapping_for_enum(
        CHASSIS_ID_MAPPING)),
    'value' /
    core.Embedded(core.Switch(construct.this.subtype,
                              mapping_for_switch(CHASSIS_ID_MAPPING)))
)

PORT_ID_MAPPING = {
    ('ifAlias', 1): core.Struct('value' / core.GreedyString("utf8")),
    ('entPhysicalAlias', 2): core.Struct('value' / core.GreedyString("utf8")),
    ('mac_address', 3): core.Struct('value' / MACAddress),
    ('IANA_address', 4): IANAAddress,
    ('ifName', 5): core.Struct('value' / core.GreedyString("utf8")),
    ('local', 7): core.Struct('value' / core.GreedyString("utf8"))
}

# Port ID value is based on the subtype
PortId = core.Struct(
    'subtype' / core.Enum(core.Byte, **mapping_for_enum(
        PORT_ID_MAPPING)),
    'value' /
    core.Embedded(core.Switch(construct.this.subtype,
                              mapping_for_switch(PORT_ID_MAPPING)))
)

PortDesc = core.Struct('value' / core.GreedyString("utf8"))

SysName = core.Struct('value' / core.GreedyString("utf8"))

SysDesc = core.Struct('value' / core.GreedyString("utf8"))

MgmtAddress = core.Struct(
    'len' / core.Int8ub,
    'family' / core.Enum(core.Int8ub, **mapping_for_enum(
        IANA_ADDRESS_FAMILY_ID_MAPPING)),
    'address' / core.Switch(construct.this.family, mapping_for_switch(
        IANA_ADDRESS_FAMILY_ID_MAPPING))
)


class LLDPBaseException(Exception):
    message = "An unknown exception occurred."

    def __init__(self, **kwargs):
        try:
            super(LLDPBaseException, self).__init__(self.message % kwargs)
            self.msg = self.message % kwargs
        except Exception:
            # at least get the core message out if something happened
            super(LLDPBaseException, self).__init__(self.message)

    def __str__(self):
        return self.msg


class TlvNotFound(LLDPBaseException):
    message = 'Required %(tlv)s TLV not found in lldp: %(lldp)s.'


class SwitchTypeNotSupported(LLDPBaseException):
    message = ('Could not find any supported switch type '
               'in System Description TLV: %(tlv)s')


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
    def generate_json(self, interface, lldpinfo, vfinfo, ovsapi=None):
        pass

    def validate_lldp(self, lldpout):
        neighborname = neighborip = neighborport = None

        for tlv_type, tlv_data in lldpout:
            try:
                data = bytearray(binascii.a2b_hex(tlv_data))
            except TypeError:
                # invalid data, not in hex, skipping
                continue
            if tlv_type == LLDP_TLV_SYS_NAME:
                neighborname = SysName.parse(data).value
            elif tlv_type == LLDP_TLV_MGMT_ADDRESS:
                addr = MgmtAddress.parse(data)
                if addr.family == 'ipv4':
                    neighborip = addr.address
            elif tlv_type == LLDP_TLV_PORT_ID:
                neighborport = PortId.parse(data).value
        if not neighborip:
            raise TlvNotFound(tlv='Management address (ipv4)',
                              lldp=lldpout)
        if not neighborport:
            raise TlvNotFound(tlv='Port ID',
                              lldp=lldpout)
        return neighborname, neighborip, neighborport

    @staticmethod
    def create_system_json(vfinfo, neighborname, neighborip,
                           neighborport, bridge=None):
        res = vfinfo
        entry = {
            'neighbor-system-name': neighborname,
            'neighbor-system-mgmt-ip': neighborip,
            'neighbor-system-port': neighborport,
            'ovs-bridge': bridge
        }
        res.update(entry)
        return res


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

    def generate_json(self, interface, lldpinfo, vfinfo, bridge=None):
        neighborname, neighborip, neighborport = self.validate_lldp(lldpinfo)
        neighborport = self.convert_ifindex_to_ifname(neighborport)

        return self.create_system_json(vfinfo, neighborname,
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

    def generate_json(self, interface, lldpinfo, vfinfo, bridge=None):
        neighborname, neighborip, neighborport = self.validate_lldp(lldpinfo)
        # just get the port number
        neighborport = self.retrieve_port_number(neighborport)
        return self.create_system_json(vfinfo, neighborname,
                                       neighborip, neighborport, bridge)


def get_switch(lldp_packet):
    switch = None
    sdtlv = next((tlv for tlv in lldp_packet if
                 tlv[0] == LLDP_TLV_SYS_DESCRIPTION), None)
    if not sdtlv:
        raise TlvNotFound(tlv='System description',
                          lldp=lldp_packet)
    data = bytearray(binascii.a2b_hex(sdtlv[1]))
    sysdesc = SysDesc.parse(data).value
    if 'Nokia' in sysdesc:
        switch = NokiaSwitch()
    else:
        cisco = re.search(r"NX-OS|NCS-55", sysdesc)
        if cisco:
            switch = CiscoSwitch(cisco.group(0))
    if not switch:
        raise SwitchTypeNotSupported(tlv=sysdesc)
    return switch


def main():
    arg_spec = dict(
        system_name=dict(required=True),
        interfaces=dict(type='dict', required=True),
        ovs_bridges=dict(type='dict', required=False)
    )

    module = AnsibleModule(argument_spec=arg_spec)

    system_name = module.params['system_name']
    interfaces = module.params['interfaces']
    ovs_bridges = module.params['ovs_bridges']

    startd = datetime.datetime.now()

    # Determining the switch type from the LLDP output itself
    # get_switch() method will raise LLDPBaseException in case
    # - no System Description TLV in lldp packet
    # - System Description TLV does not contain any recognized
    #   switch type patterns
    itf_list = []
    for interface, data in interfaces.items():
        try:
            switch = get_switch(data['lldp'])
            ovs_bridge = ovs_bridges.get(interface)
            itf_list.append(switch.generate_json(
                interface,
                data.get('lldp'),
                data.get('vfinfo'),
                ovs_bridge.get('bridge') if ovs_bridge else None))
        except LLDPBaseException as e:
            module.fail_json(msg="Failed to process LLDP data "
                                 "for interface: %s" % interface,
                             stdout=None,
                             stderr=str(e))

    module.exit_json(system_name=system_name,
                     interfaces=interfaces,
                     stdout=json.dumps(itf_list, indent=4),
                     start=str(startd),
                     end=str(datetime.datetime.now()),
                     delta=str(datetime.datetime.now() - startd),
                     changed=True)


if __name__ == '__main__':
    main()
