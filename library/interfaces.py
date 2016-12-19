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
module: interface
short_description: Given a required state and a regex to match the name, return a list of matching intefaces
options:
  state:
    description:
      - The required state of the interface. See putput of 'ip addr' command.
    required: true
  regex:
    description:
      - A regex to match interface names, e.g. 'en' will match all interface names that contain that string
    required: false
    default: ['*']
'''

EXAMPLES = '''
# Get a list of interfaces that are UP and contain 'en' in their names
- topology: state=UP regex=en
'''


def main():
    arg_spec = dict(
        state=dict(required=True),
        regex=dict(default=['*'])
    )

    module = AnsibleModule(argument_spec=arg_spec)

    state = module.params['state']
    regex = module.params['regex']

    IPCMD = module.get_bin_path('ip', True)

    startd = datetime.datetime.now()

    cmd = "%s addr" % (IPCMD)

    rc, out, err = module.run_command(cmd, check_rc=False)

    endd = datetime.datetime.now()

    delta = endd - startd

    if err is None:
        err = b('')

    if out is None:
        out = b('')

    if rc != 0:
        module.fail_json(msg="command failed",
                         rc=rc,
                         cmd=cmd,
                         stdout=out,
                         stderr=err,
                         start=str(startd),
                         end=str(endd),
                         delta=str(delta),
                         changed=False)

    parsed = []
    match = "state %s" % state
    for line in  out.split('\n'):
        if match in line:
            if re.search( regex, line.split(': ')[1] ):
                parsed.append(line.split(': ')[1])

    module.exit_json(cmd=cmd,
                     matches=parsed,
                     rawout=out,
                     regex=regex,
                     state=state,
                     start=str(startd),
                     end=str(endd),
                     delta=str(delta),
                     changed=True)

if __name__ == '__main__':
    main()
