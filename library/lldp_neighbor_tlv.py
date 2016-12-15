#!/usr/bin/python

import datetime
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
  interface:
    description:
      - The network interface to interrogate
    required: true
    default: null
'''

EXAMPLES = '''
# Verify the state of program "ntpd-status" state.
- lldpneighbortlv: interfaace=eth0
'''

# convert_lldptool_output_to_json is a function that takes an output string from a
# specific run of lldptool and converts it to JSON. The specific form of the lldptool
# command is 'lldptool -t -n -i <interface>'. That is the form used to gather the
# interrface's neighbor TLV. The code, below, is tied very tightly to the exact
# format of the command output. If that output changes, this function must change.


def convert_lldptool_output_to_json(lldptool_out):
    if lldptool_out is None:
        return "{}"
    scratch = lldptool_out.replace('End of LLDPDU TLV', '').replace('\n\t', '\t').strip()
    parsed = ""
    for line in scratch.split('\n'):
        first_split_list = line.split('\t')
        if len(first_split_list) == 2:
            second_split_list = first_split_list[1].split(': ')
            if 2 == len(second_split_list):
                parsed += "\"%s\": { \"%s\": \"%s\" }," % (
                    first_split_list[0],
                    second_split_list[0],
                    second_split_list[1])
            else:
                parsed += "\"%s\": \"%s\"," % (
                    first_split_list[0],
                    first_split_list[1])
        else:
            sub = ""
            if 2 == len(first_split_list[3].split(': ')):
                sub = first_split_list[3].split(': ')[1]
            parsed += "\"%s\": { \"%s\": \"%s\", \"%s\": \"%s\", \"%s\": \"%s\" }" % (
                first_split_list[0],
                first_split_list[1].split(': ')[0],
                first_split_list[1].split(': ')[1],
                first_split_list[2].split(': ')[0],
                first_split_list[2].split(': ')[1],
                first_split_list[3].split(': ')[0],
                sub)
    return "{ %s }" % parsed


def main():
    arg_spec = dict(
        interface=dict(required=True)
    )

    module = AnsibleModule(argument_spec=arg_spec)

    interface = module.params['interface']

    LLDPTOOL = module.get_bin_path('lldptool', True)

    startd = datetime.datetime.now()

    cmd = "%s -t -n -i %s" % (LLDPTOOL, interface)
    rc, out, err = module.run_command(cmd, check_rc=True)

    endd = datetime.datetime.now()

    delta = endd - startd

    if err is None:
        err = b('')

    if out is None:
        out = b('')

    parsed = convert_lldptool_output_to_json(out)

    module.exit_json(cmd=cmd,
                     stdout=parsed,
                     stderr=err.strip(),
                     rawout=out,
                     rc=rc,
                     start=str(startd),
                     end=str(endd),
                     delta=str(delta),
                     changed=True)

if __name__ == '__main__':
    main()
