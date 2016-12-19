#!/usr/bin/python

import datetime
import re
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import b

# Copyright 2016 Nokia
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

DOCUMENTATION = '''
---
module: topology
short_description: Given an interface, returns a JSON string with VSG ToR port mapping and VF PCI info
options:
  system_name:
    description:
      - The system name or IP address of the compute node being processed
    required: true
  interface:
    description:
      - The network interface to interrogate
    required: true
'''

EXAMPLES = '''
- topoloy: system_name=192.168.1.1 interfaace=eth0
- topoloy: system_name=cas-cs2-011 interfaace=eno4
'''

# generate_json() is a function that takes two input strings of specific syntax and
# creates a JSON string from specific portions of those outputs. The input strings
# are generated from two specific commands. As such, this function is tightly comupled
# to the outputs of those commands. The first command is lldptool. The second is ls.
# The exact syntax of these commands is shown in the main() function in this file.
# If the outputs or commands change, the code in this function must change with them.


def generate_json(interface, lldpout, lsout):

    LLDPSYSTEMNAME = "System Name TLV"
    NEIGHBORNAME = "neighbor-system-name"
    LLDPSYSTEMIP = "Management Address TLV"
    NEIGHBORIP = "neighbor-system-mgmt-ip"
    LLDPSYSTEMPORT = "Port Description TLV"
    NEIGHBORPORT = "neighbor-system-port"

    # Insert the interface name into the JSON object.
    parsed = "\n \"name\": \"%s\"" % interface

    # Insert VF port info
    vf_info = ",\n \"vf_info\": ["
    lines = lsout.split('\n')
    found_first_match = False
    for line in lines:
        if re.search(" virt", line):
            fmt = ",\n { \"device-name\": \"%s\""
            vf_parts = line.split(' ')
            if len(vf_parts) >= 17:
                if not found_first_match:
                    found_first_match = True
                    fmt = "\n { \"device-name\": \"%s\""
                vf_info += fmt % vf_parts[16]
            if len(vf_parts) >= 19:
                pci_id_parts = vf_parts[18].split('/')
                if len(pci_id_parts) >= 2:
                    vf_info += ", \"pci-id\": \"%s\" }" % pci_id_parts[1]
    vf_info += "]"
    parsed += vf_info

    # Now add neighbor information
    scratch = lldpout.replace('\n\t', '\t').strip()
    neighborname = "None"
    neighborip = "None"
    neighborport = "None"
    for line in scratch.split('\n'):
        if re.search( LLDPSYSTEMNAME, line):
            sys_name_tlv_parts = line.split('\t')
            if len(sys_name_tlv_parts) >= 2:
                neighborname = sys_name_tlv_parts[1]
        elif re.search( LLDPSYSTEMIP, line):
            mgmt_addr_tlv_parts = line.split('\t')
            if len(mgmt_addr_tlv_parts) >= 2:
                mgmt_addr_parts = mgmt_addr_tlv_parts[1].split(' ')
                if len(mgmt_addr_parts) >= 2:
                    neighborip = mgmt_addr_parts[1]
        elif re.search( LLDPSYSTEMPORT, line):
            port_desc_tlv_parts = line.split('\t')
            if len(port_desc_tlv_parts) >= 2:
                port_desc_parts = port_desc_tlv_parts[1].split('connection')
                if len(port_desc_parts) >= 2:
                    neighbor_port_parts = port_desc_parts[0].split(' ')
                    if len(neighbor_port_parts) >= 2:
                        neighborport = neighbor_port_parts[1]
    parsed += ",\n \"%s\": \"%s\"" % ( NEIGHBORNAME, neighborname)
    parsed += ",\n \"%s\": \"%s\"" % ( NEIGHBORIP, neighborip)
    parsed += ",\n \"%s\": \"%s\" " % ( NEIGHBORPORT, neighborport)
    return "{ %s }" % parsed


def main():
    arg_spec = dict(
        system_name=dict(required=True),
        interface=dict(required=True)
    )

    module = AnsibleModule(argument_spec=arg_spec)

    system_name = module.params['system_name']
    interface = module.params['interface']

    LLDPTOOL = module.get_bin_path('lldptool', True)
    LS = module.get_bin_path('ls', True)

    startd = datetime.datetime.now()

    lldpcmd = "%s -t -n -i %s" % (LLDPTOOL, interface)
    lldprc, lldpout, lldperr = module.run_command(lldpcmd, check_rc=True)

    if lldperr is None:
        lldperr = b('')

    if lldpout is None:
        lldpout = b('')

    if lldprc != 0:
        module.fail_json(msg="lldptool command failed",
                         lldprc=lldprc,
                         lldpcmd=lldpcmd,
                         system_name=system_name,
                         interface=interface,
                         stdout=lldpout,
                         stderr=lldperr,
                         start=str(startd),
                         end=str(datetime.datetime.now()),
                         delta=str(datetime.datetime.now()-startd),
                         changed=False)

    lscmd = "%s -la /sys/class/net/%s/device/" % (LS, interface)
    lsrc, lsout, lserr = module.run_command(lscmd, check_rc=True)

    if lserr is None:
        lserr = b('')

    if lsout is None:
        lsout = b('')

    if lsrc != 0:
        module.fail_json(msg="ls command failed",
                         lsrc=lsrc,
                         lscmd=lscmd,
                         system_name=system_name,
                         interface=interface,
                         stdout=lsout,
                         stderr=lserr,
                         lldpout=lldpout,
                         lldperr=lldperr,
                         start=str(startd),
                         end=str(datetime.datetime.now()),
                         delta=str(datetime.datetime.now()-startd),
                         changed=False)

    module.exit_json(lldpcmd=lldpcmd,
                     lscmd=lscmd,
                     system_name=system_name,
                     interface=interface,
                     stdout=generate_json(interface, lldpout, lsout),
                     stderr=lldperr,
                     lldpout=lldpout,
                     lldperr=lldperr,
                     lsout=lsout,
                     lsrc=lsrc,
                     lldprc=lldprc,
                     start=str(startd),
                     end=str(datetime.datetime.now()),
                     delta=str(datetime.datetime.now()-startd),
                     changed=True)

if __name__ == '__main__':
    main()
