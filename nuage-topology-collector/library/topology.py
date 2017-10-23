#!/usr/bin/python

import datetime
import re
import os
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import b
# Copyright 2017 Nokia
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
short_description: Given an interface, returns VSG ToR port and VF PCI info in JSON
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

# convert_ifindex_to_ifname() is a function that converts the ifindex we get from
# the Port ID TLV output of lldptool into the ifname of the form x/y/z.
# ifindex is a string that represents an integer, e.g. "37781504".
# If ifindex does not represent an int we return "None".


def convert_ifindex_to_ifname(ifindex):
    if not ifindex.isdigit():
        return "None"
    return "%s/%s/%s" % (
        (int(ifindex) >> 25),
        (int(ifindex) >> 21) & 0xf,
        (int(ifindex) >> 15) & 0x3f)


# generate_json() is a function that takes two input strings of specific syntax and
# creates a JSON string from specific portions of those outputs. The input strings
# are generated from two specific commands. As such, this function is tightly comupled
# to the outputs of those commands. The first command is lldptool. The second is ls.
# The exact syntax of these commands is shown in the main() function in this file.
# If the outputs or commands change, the code in this function must change with them.


def generate_json(interface, lldpout, lsout):

    LLDPSYSTEMNAME = "System Name TLV"
    SYSTEMNAME_RE = LLDPSYSTEMNAME + "\s+(\S+)\s+"
    LLDPSYSTEMIP = "Management Address TLV"
    SYSTEMIP_RE = LLDPSYSTEMIP + "\s+\S+:\s+(\S+)\s+"
    LLDPSYSTEMPORT = "Port ID TLV"
    SYSTEMPORT_RE = LLDPSYSTEMPORT + "\s+\S+:\s+(\S+)\s+"

    NEIGHBORNAME = "neighbor-system-name"
    NEIGHBORIP = "neighbor-system-mgmt-ip"
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
            vf_parts = line.split()
            if len(vf_parts) >= 9:
                if not found_first_match:
                    found_first_match = True
                    fmt = "\n { \"device-name\": \"%s\""
                vf_info += fmt % vf_parts[8]
            if len(vf_parts) >= 11:
                pci_id_parts = vf_parts[10].split('/')
                if len(pci_id_parts) >= 2:
                    vf_info += ", \"pci-id\": \"%s\" }" % pci_id_parts[1]
    vf_info += "]"
    parsed += vf_info

    # Now add neighbor information
    scratch = re.search(SYSTEMNAME_RE, lldpout)
    if scratch:
        neighborname = scratch.group(1)
    else:
        neighborname = "None"
    scratch = re.search(SYSTEMIP_RE, lldpout)
    if scratch:
        neighborip = scratch.group(1)
    else:
        neighborip = "None"
    scratch = re.search(SYSTEMPORT_RE, lldpout)
    if scratch:
        neighborport = convert_ifindex_to_ifname(scratch.group(1))
    else:
        neighborport = "None"
    parsed += ",\n \"%s\": \"%s\"" % (NEIGHBORNAME, neighborname)
    parsed += ",\n \"%s\": \"%s\"" % (NEIGHBORIP, neighborip)
    parsed += ",\n \"%s\": \"%s\" " % (NEIGHBORPORT, neighborport)
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
    prefix = "sudo " if os.getlogin() != "root" else ""
    lldpcmd = prefix + "%s -t -n -i %s" % (LLDPTOOL, interface)

    lldprc, lldpout, lldperr = module.run_command(lldpcmd)
    if lldperr is None:
        lldperr = b('')
    if lldpout is None:
        lldpout = b('')
    if lldprc != 0:
        lldpout = b('')

    lscmd = "%s -la /sys/class/net/%s/device/" % (LS, interface)
    lsrc, lsout, lserr = module.run_command(lscmd)

    if lserr is None:
        lserr = b('')

    if lsout is None:
        lsout = b('')

    if lldprc != 0:
        lldpout = b('')

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
