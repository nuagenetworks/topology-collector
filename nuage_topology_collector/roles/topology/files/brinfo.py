#!/usr/bin/python2
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

import getopt
import json
import sys

from ovsdbapp.backend.ovs_idl import command
from ovsdbapp.backend.ovs_idl import connection as n_conn
from ovsdbapp.backend.ovs_idl import idlutils
from ovsdbapp.schema.open_vswitch import commands as cmd
from ovsdbapp.schema.open_vswitch import impl_idl


class OvsdbQuery(object):
    IGNORE_TYPES = ['internal']

    def __init__(self, host, port):
        self.ovsdbclient = self._get_ovsdb_client(host, port)

    def _get_ovsdb_client(self, host, port):

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

            def get_iface(self, name):
                return GetIfaceCommand(self, name)

            def iface_to_br(self, name):
                return cmd.InterfaceToBridgeCommand(self, name)

        endpoint = ("tcp:%(host)s:%(port)s" % {'host': host, 'port': port})
        client = None
        try:
            idl = n_conn.OvsdbIdl.from_server(endpoint, 'Open_vSwitch')
            connection = n_conn.Connection(idl=idl, timeout=3)
            client = TcOvsdbIdl(connection)
        except Exception as e:
            print("could not connect to openvswitch. error: " + str(e))
            exit(2)
        return client

    def process_bridge(self, bridge, parent=None, ignore_types=[]):
        mapping = dict()
        ifaces = self.ovsdbclient.list_ifaces(bridge).execute(
            check_error=True)
        iflist = []
        for ifname in ifaces:
            iface = self.ovsdbclient.get_iface(ifname).execute(
                check_error=True)
            if iface.type in ignore_types:
                continue
            elif iface.type == 'patch':
                peer = iface.options.get('peer')
                peer_br = self.ovsdbclient.iface_to_br(peer).execute(
                    check_error=True)
                if peer_br not in ['br-int', 'br-tun']:
                    return self.process_bridge(peer_br, bridge,
                                               ignore_types + ['patch'])
                else:
                    continue
            iflist.append({'iface': iface.name,
                           'type': iface.type,
                           'parent': bridge})
        mapping[parent or bridge] = iflist
        return mapping

    def get_ovs_topology(self, bridge_mappings):
        ovs_topology = dict()
        bridges = self.ovsdbclient.list_br().execute(check_error=True)

        for br in bridges:
            if br in bridge_mappings.values():
                mapping = self.process_bridge(
                    br, ignore_types=self.IGNORE_TYPES)
                ovs_topology.update(mapping)
        return ovs_topology


def main(argv):
    host = port = bmapping = None
    result = dict()
    try:
        opts, _ = getopt.getopt(argv, "h:p:m:")
    except getopt.GetoptError:
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            host = arg
        elif opt == '-p':
            port = arg
        elif opt == '-m':
            bmapping = json.loads(arg)
        else:
            print("unknown oprtion: " + opt)
            exit(2)
    if host and port and bmapping:
        query = OvsdbQuery(host, port)
        bridgeinfo = query.get_ovs_topology(bmapping)
        result['brinfo'] = bridgeinfo
        print(json.dumps(result, indent=4))
    else:
        print("parameters not provided")
        exit(2)


if __name__ == '__main__':
    main(sys.argv[1:])
