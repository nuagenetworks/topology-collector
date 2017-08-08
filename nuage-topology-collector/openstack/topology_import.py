# Copyright 2017 NOKIA
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
import argparse
import getpass
import json

from keystoneauth1 import identity
from keystoneauth1 import session
from neutronclient.v2_0 import client as neutron_client


class TopologyReader(object):
    def __init__(self, path):
        super(TopologyReader, self).__init__()
        self.path = path
        self.json_data = self._load_json()

    def _load_json(self):
        with open(self.path) as topology_file:
            return json.load(topology_file)

    def interfaces(self):
        for compute_host in self.json_data['compute-hosts']:
            for interface in compute_host['interfaces']:
                interface['host_id'] = compute_host['service_host name']
                yield interface


class TopologyConverter(object):
    def __init__(self, neutronclient):
        super(TopologyConverter, self).__init__()
        self.neutron = neutronclient

    def interface_to_mappings(self, interface):
        base_mapping = {
            'switch_info': interface['neighbor-system-name'],
            'switch_id': interface['neighbor-system-mgmt-ip'],
            'port_id': interface['neighbor-system-port'],
            'host_id': interface['host_id']
        }
        interface_mappings = []
        for virtual_function in interface['vf_info']:
            vf_mapping = self.function_to_mapping(virtual_function)
            interface_mapping = dict(base_mapping, **vf_mapping)
            interface_mappings.append(interface_mapping)
        return interface_mappings

    def function_to_mapping(self, virtual_function):
        return {'pci_slot': virtual_function['pci-id']}


def init_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--keystone-auth-url', action='store',
                        dest='auth_url', required=True,
                        default='http://127.0.0.1/identity',
                        help='The auth url of the keystone service')
    parser.add_argument('--username', action='store', required=True,
                        help='The username to authenticate with keystone')
    parser.add_argument('--password', action='store',
                        default=None,
                        help='The password to authenticate with keystone')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project-name', action='store',
                       help='[v3] The keystone project name')
    group.add_argument('--tenant-name', action='store',
                       dest='project_name',
                       help='[v2] The keystone tenant name')

    parser.add_argument('--user-domain-id', action='store',
                        help='[v3] The keystone user domain id')
    parser.add_argument('--project-domain-id', action='store',
                        help='[v3] The keystone project domain id')

    parser.add_argument('topology_file', action='store',
                        help='The path to the topology json file.')
    return parser


def main():
    parser = init_arg_parser()
    args = parser.parse_args()

    password = args.password or getpass.getpass('Enter password for user %s:'
                                                % args.username)
    is_v3 = args.project_name is not None
    identity_args = {'auth_url': args.auth_url,
                     'username': args.username,
                     'password': password,
                     'project_name': args.project_name}
    if is_v3:
        identity_args['project_domain_id'] = args.project_domain_id
        identity_args['user_domain_id'] = args.user_domain_id

    auth = identity.Password(**identity_args)
    sess = session.Session(auth=auth)
    neutronclient = neutron_client.Client(retries=2, session=sess)

    reader = TopologyReader(args.topology_file)
    converter = TopologyConverter(neutronclient)
    for interface in reader.interfaces():
        switchport_mappings = converter.interface_to_mappings(interface)
        if switchport_mappings:
            print ("Sending interface %s to neutron."
                   % interface['neighbor-system-mgmt-ip'])
            neutronclient.post(
                '/net-topology/switchport_mappings',
                body={'switchport_mappings': switchport_mappings})

if __name__ == '__main__':
    main()
