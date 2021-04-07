#!/usr/bin/python
#  Copyright 2020 NOKIA
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

import re

from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: linuxbond

short_description: Query linux bonds

version_added: "2.4"

description:
    - "Query linux bonds"

author: Vlad Gridin (vladyslav.gridin@nokia.com)

options:
    brinfo:
        default: {}
        description:
            - Dict of phy itf/bridge relations
'''

EXAMPLES = '''
'''

RETURN = '''
brinfo:
    description: Dict with phy interface to ovs bridge mapping
    returned: always
    type: dict
    sample: {
        "eth0": "br-ex",
        "eth1": "br-public",
        "eth2": None
    }
'''


def check_linux_bond(iface):
    slaves = list()
    try:
        bond = open('/proc/net/bonding/%s' % iface).read()
        for line in bond.splitlines():
            m = re.match('^Slave Interface: (.*)', line)
            if m:
                slaves.append(m.groups()[0])
    except IOError:
        pass
    return slaves


def run_module():
    module_args = dict(
        brinfo=dict(type='dict', required=False, default=dict())
    )

    result = dict(
        changed=False,
        brinfo=dict()
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(**result)

    bridgeinfo = dict()
    for k, v in module.params['brinfo'].items():
        bridgeinfo[k] = v
        slaves = check_linux_bond(k)
        for slave in slaves:
            bridgeinfo[slave] = {'bridge': v.get('bridge'),
                                 'type': None}

    result['brinfo'] = bridgeinfo
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
