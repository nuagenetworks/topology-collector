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
module: lldp_neighbor_tlv
short_description: Given an interface, returns a JSON representation of the neighbor's LLDP TLV
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
# Verify the state of program "ntpd-status" state.
- lldpneighbortlv: system_name= 192.168.1.1 interfaace=eth0
'''

# convert_lldptool_output_to_json is a function that takes an output string from a
# specific run of lldptool and converts it to JSON. The specific form of the lldptool
# command is 'lldptool -t -n -i <interface>'. That is the form used to gather the
# interface's neighbor TLV. The code, below, is tied very tightly to the exact
# format of the command output. If that output changes, this function must change.


def convert_lldptool_output_to_json(interface, lldpout, lsout):

    LLDPSYSTEMNAME = "System Name TLV"
    NEIGHBORNAME = "neighbor-system-name"
    LLDPSYSTEMIP = "Management Address TLV"
    NEIGHBORIP = "neighbor-system-mgmt-ip"
    LLDPSYSTEMPORT = "Port Description TLV"
    NEIGHBORPORT = "neighbor-system-port"

    # Insert the interface name into the JSON object.
    parsed = "\"name\": \"%s\"" % interface

    # Insert VF port info
    # TODO: Gotta fix this code
    # vf_info = ", \"vf_info\": ["
    # for line in lsout.split('n'):
        # line_split = line.split('/')
        # if len(line_split) == 8:
            # vf_info += "{ \"device-name\": \"%s\", \"pci-id\": \"%s\" }," % (
                # line_split[6].split(' ')[0],
                # line_split[7])

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
                port_desc_parts = port_desc_tlv_parts[1].split(' ')
                if len(port_desc_parts) >= 2:
                    neighborport = port_desc_parts[1]
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

    # TODO: There is a problem with this call...
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
                     stdout=convert_lldptool_output_to_json(interface, lldpout, lsout),
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
