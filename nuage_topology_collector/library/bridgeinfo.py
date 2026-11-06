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

import json

try:
    import pipes
except ImportError:
    import shlex as pipes

from ansible.module_utils.basic import AnsibleModule

OVSDB_UNIX_SOCKET = 'unix:/var/run/openvswitch/db.sock'
LOCAL_OVSDB_HOSTS = frozenset(['127.0.0.1', 'localhost', '::1'])

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
        self.endpoint = self._resolve_endpoint(module)
        self.ovsdbclient = self._get_ovsdb_client(module)

    @staticmethod
    def _resolve_endpoint(module):
        host = module.params['host']
        port = module.params['port']
        if host in LOCAL_OVSDB_HOSTS:
            return OVSDB_UNIX_SOCKET
        if host.startswith('[') and host.endswith(']'):
            return 'tcp:%s:%s' % (host, port)
        return 'tcp:%s:%s' % (host, port)

    def _uses_local_unix_socket(self):
        return self.endpoint.startswith('unix:')

    def _get_ovsdb_client(self, module):
        try:
            from ovsdbapp.backend.ovs_idl import command
            from ovsdbapp.backend.ovs_idl import connection
            from ovsdbapp.backend.ovs_idl import idlutils
            from ovsdbapp.schema.open_vswitch import impl_idl
        except ImportError as e:
            self.module.log(msg=str(e))
            return None

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

        client = None
        try:
            idl = connection.OvsdbIdl.from_server(self.endpoint,
                                                  'Open_vSwitch')
            connection = connection.Connection(idl=idl, timeout=3)
            client = TcOvsdbIdl(connection)
        except Exception as e:
            error_str = str(e)
            # Skip ovsdbapp if schema parsing fails (version mismatch with remote OVSDB)
            if 'schema' in error_str.lower() or 'type mismatch' in error_str.lower():
                self.module.log(msg=("OVSDB schema version mismatch detected for %s. "
                                     "Skipping ovsdbapp, will use fallback methods. Details: %s") %
                                (self.endpoint, error_str))
            else:
                self.module.log(msg=("failed to initialize ovsdbapp client for "
                                     "%s: %s") % (self.endpoint, error_str))
        return client

    @staticmethod
    def _normalize_ovs_vsctl_value(value):
        value = value.strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            return value[1:-1]
        if value == '[]':
            return ''
        return value

    def _run_ovs_vsctl(self, *args):
        vsctl = self.module.get_bin_path('ovs-vsctl', required=False)
        if not vsctl:
            raise RuntimeError('ovs-vsctl executable not found')
        cmd = [vsctl, '--timeout=3']
        if not self._uses_local_unix_socket():
            cmd.append('--db=%s' % self.endpoint)
        cmd.extend(args)
        quoted_cmd = ' '.join(pipes.quote(arg) for arg in cmd)
        rc, out, err = self.module.run_command(quoted_cmd)
        if rc != 0:
            raise RuntimeError(err.strip() or out.strip() or
                               'ovs-vsctl command failed')
        return out

    def _run_ovsdb_client_transact(self, operations):
        ovsdb_client = self.module.get_bin_path('ovsdb-client', required=False)
        if not ovsdb_client:
            raise RuntimeError('ovsdb-client executable not found')
        payload = json.dumps(['Open_vSwitch'] + operations)
        cmd = [ovsdb_client, 'transact', self.endpoint, payload]
        rc, out, err = self.module.run_command(cmd)
        if rc != 0:
            raise RuntimeError(err.strip() or out.strip() or
                               'ovsdb-client transact failed')
        try:
            return json.loads(out)
        except ValueError as e:
            raise RuntimeError('invalid ovsdb-client JSON output: %s' % str(e))

    @staticmethod
    def _decode_ovsdb_value(value):
        if isinstance(value, list) and len(value) == 2:
            if value[0] in ('uuid', 'named-uuid'):
                return value[1]
            if value[0] == 'set':
                return [OvsdbQuery._decode_ovsdb_value(item)
                        for item in value[1]]
            if value[0] == 'map':
                decoded_map = {}
                for item in value[1]:
                    if isinstance(item, list) and len(item) == 2:
                        decoded_map[item[0]] = OvsdbQuery._decode_ovsdb_value(
                            item[1])
                return decoded_map
        return value

    def _get_ovs_topology_via_ovsdbapp(self):
        ovs_topology = dict()
        bridge_mappings = self.module.params['bridge_mappings']
        bridges = self.ovsdbclient.list_br().execute(check_error=True)

        for br in bridges:
            if br in bridge_mappings.values():
                ifaces = self.ovsdbclient.list_ifaces(br).execute(
                    check_error=True)
                for ifname in ifaces:
                    iface = self.ovsdbclient.get_iface(ifname).execute(
                        check_error=True)
                    ovs_topology[ifname] = {'bridge': br,
                                            'type': iface.type}
        return ovs_topology

    def _get_ovs_topology_via_vsctl(self):
        ovs_topology = dict()
        bridge_mappings = self.module.params['bridge_mappings']
        bridges = self._run_ovs_vsctl('list-br').splitlines()

        for br in (br.strip() for br in bridges if br.strip()):
            if br in bridge_mappings.values():
                ifaces = self._run_ovs_vsctl('list-ifaces', br).splitlines()
                for ifname in (iface.strip() for iface in ifaces if
                               iface.strip()):
                    iface_type = self._run_ovs_vsctl(
                        '--if-exists', 'get', 'Interface', ifname, 'type')
                    ovs_topology[ifname] = {
                        'bridge': br,
                        'type': self._normalize_ovs_vsctl_value(iface_type)
                    }
        return ovs_topology

    def _get_ovs_topology_via_ovsdb_client_raw(self):
        ovs_topology = dict()
        bridge_mappings = self.module.params['bridge_mappings']
        target_bridges = set(bridge_mappings.values())

        response = self._run_ovsdb_client_transact([
            {'op': 'select', 'table': 'Bridge', 'columns': ['_uuid', 'name', 'ports'], 'where': []},
            {'op': 'select', 'table': 'Port', 'columns': ['_uuid', 'interfaces'], 'where': []},
            {'op': 'select', 'table': 'Interface', 'columns': ['_uuid', 'name', 'type'], 'where': []}
        ])

        if not isinstance(response, list) or len(response) != 3:
            raise RuntimeError('unexpected ovsdb-client transact response')

        bridge_rows = response[0].get('rows', [])
        port_rows = response[1].get('rows', [])
        iface_rows = response[2].get('rows', [])

        ports_by_uuid = {}
        for row in port_rows:
            port_uuid = self._decode_ovsdb_value(row.get('_uuid'))
            if not port_uuid:
                continue
            interfaces = self._decode_ovsdb_value(row.get('interfaces', []))
            if isinstance(interfaces, list):
                ports_by_uuid[port_uuid] = interfaces
            elif interfaces:
                ports_by_uuid[port_uuid] = [interfaces]
            else:
                ports_by_uuid[port_uuid] = []

        ifaces_by_uuid = {}
        for row in iface_rows:
            iface_uuid = self._decode_ovsdb_value(row.get('_uuid'))
            if not iface_uuid:
                continue
            ifaces_by_uuid[iface_uuid] = {
                'name': self._decode_ovsdb_value(row.get('name', '')),
                'type': self._decode_ovsdb_value(row.get('type', ''))
            }

        for bridge in bridge_rows:
            bridge_name = self._decode_ovsdb_value(bridge.get('name', ''))
            if bridge_name not in target_bridges:
                continue

            bridge_ports = self._decode_ovsdb_value(bridge.get('ports', []))
            if not isinstance(bridge_ports, list):
                bridge_ports = [bridge_ports] if bridge_ports else []

            for port_uuid in bridge_ports:
                iface_uuids = ports_by_uuid.get(port_uuid, [])
                for iface_uuid in iface_uuids:
                    iface = ifaces_by_uuid.get(iface_uuid)
                    if iface is None:
                        continue
                    ifname = iface.get('name')
                    if ifname:
                        ovs_topology[ifname] = {
                            'bridge': bridge_name,
                            'type': iface.get('type', '')
                        }

        return ovs_topology

    def get_ovs_topology(self):
        ovsdbapp_error = None
        raw_ovsdb_error = None
        vsctl_error = None

        if self.ovsdbclient is not None:
            try:
                result = self._get_ovs_topology_via_ovsdbapp()
                self.module.log(msg="Successfully queried OVS topology via ovsdbapp")
                return result
            except Exception as e:
                ovsdbapp_error = str(e)
                self.module.log(msg=("failed to query OVS topology via "
                                     "ovsdbapp for %s: %s") %
                                (self.endpoint, ovsdbapp_error))
        else:
            self.module.log(msg="ovsdbapp client not available, attempting fallback methods")

        try:
            result = self._get_ovs_topology_via_ovsdb_client_raw()
            self.module.log(msg="Successfully queried OVS topology via raw ovsdb-client")
            return result
        except Exception as e:
            raw_ovsdb_error = str(e)
            self.module.log(msg=("failed to query OVS topology via "
                                 "raw ovsdb-client transact for %s: %s") %
                            (self.endpoint, raw_ovsdb_error))

        try:
            result = self._get_ovs_topology_via_vsctl()
            self.module.log(msg="Successfully queried OVS topology via ovs-vsctl fallback")
            return result
        except Exception as e:
            vsctl_error = str(e)
            self.module.log(msg=("failed to query OVS topology via "
                                 "ovs-vsctl fallback for %s: %s") %
                            (self.endpoint, vsctl_error))

        # All methods failed - compile detailed error message
        details = []
        if ovsdbapp_error:
            details.append('ovsdbapp error: %s' % ovsdbapp_error)
        if raw_ovsdb_error:
            details.append('raw ovsdb-client fallback error: %s' % raw_ovsdb_error)
        if vsctl_error:
            details.append('ovs-vsctl fallback error: %s' % vsctl_error)

        error_msg = "could not connect to openvswitch via any method. %s" % '; '.join(details) if details else "could not connect to openvswitch."
        self.module.fail_json(msg=error_msg)


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
