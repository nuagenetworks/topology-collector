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
module: bridgeinfo

short_description: Query Open vSwitch bridges

version_added: "2.4"

description:
    - "Query Open vSwitch bridges"

author: Vlad Gridin (vladyslav.gridin@nokia.com)

options:
    host:
        default: '127.0.0.1'
        description:
            - OVS Manager address
    port:
        default: '6640'
        description:
            - OVS Manager port
    bridge_mappings:
        default: {}
        description:
            - Dict of physnet/bridge relations from OVS agent
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


class OvsdbQuery(object):

    def __init__(self, module):
        self.module = module
        self.ovsdbclient = self._get_ovsdb_client(module)

    def _get_ovsdb_client(self, module):
        try:
            from ovsdbapp.backend.ovs_idl import command
            from ovsdbapp.backend.ovs_idl import connection
            from ovsdbapp.backend.ovs_idl import idlutils
            from ovsdbapp.schema.open_vswitch import impl_idl
        except ImportError as e:
            self.module.log(msg=str(e))
            self.module.fail_json(msg="ovsdbapp module is required")

        class GetIfaceCommand(command.ReadOnlyCommand):
            def __init__(self, api, iface):
                super(GetIfaceCommand, self).__init__(api)
                self.iface = iface

            def run_idl(self, txn):
                iface = idlutils.row_by_value(self.api.idl,
                                              'Interface',
                                              'name',
                                              self.iface)
                self.result = iface

        class TcOvsdbIdl(impl_idl.OvsdbIdl):
            def __init__(self, connection):
                super(TcOvsdbIdl, self).__init__(connection)

            def get_iface(self, iface):
                return GetIfaceCommand(self, iface)

        endpoint = ("tcp:%(host)s:%(port)s" % module.params)
        client = None
        try:
            idl = connection.OvsdbIdl.from_server(endpoint, 'Open_vSwitch')
            connection = connection.Connection(idl=idl, timeout=3)
            client = TcOvsdbIdl(connection)
        except Exception as e:
            self.module.fail_json(msg=("could not connect to openvswitch. "
                                       "error: %s") % str(e))
        return client

    def check_linux_bond(self, iface):
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

    def get_ovs_topology(self):
        ovs_topology = dict()
        bridge_mappings = self.module.params['bridge_mappings']
        bridges = self.ovsdbclient.list_br().execute(check_error=True)

        for br in bridges:
            if br in bridge_mappings.values():
                ifaces = self.ovsdbclient.list_ifaces(br).execute(
                    check_error=True)
                for ifname in ifaces:
                    bond_slaves = self.check_linux_bond(ifname)
                    for slave in bond_slaves:
                        ovs_topology[slave] = {'bridge': br,
                                               'type': None}
                    iface = self.ovsdbclient.get_iface(ifname).execute(
                        check_error=True)
                    ovs_topology[ifname] = {'bridge': br,
                                            'type': iface.type}
        return ovs_topology


def run_module():
    module_args = dict(
        host=dict(type='str', required=False, default='127.0.0.1'),
        port=dict(type='str', required=False, default='6640'),
        bridge_mappings=dict(type='dict', required=False, default=dict())
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

    query = OvsdbQuery(module)
    bridgeinfo = query.get_ovs_topology()
    result['brinfo'] = bridgeinfo
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
