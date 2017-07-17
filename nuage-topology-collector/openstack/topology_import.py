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
import collections
import ConfigParser
import json
import sys

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


def read_config(neutron_conf):
    config = ConfigParser.ConfigParser()
    config.read(neutron_conf)

    section = 'keystone_authtoken'
    settings = config.options(section)
    if 'auth_url' in settings:
        auth_url = config.get(section, 'auth_url')
    elif 'auth_host' in settings:
        host = config.get(section, 'auth_host')
        if 'auth_protocol' in settings:
            protocol = config.get(section, 'auth_protocol')
        else:
            protocol = 'https'
        if 'auth_port' in settings:
            port = config.get(section, 'auth_port')
        else:
            port = '35357'

        auth_url = '%s://%s:%s/v2.0' % (protocol, host, port)
    else:
        print "Failed to read keystone auth url."
        sys.exit(1)

    tenant_name = config.get(section, 'admin_tenant_name')
    username = config.get(section, 'admin_user')
    password = config.get(section, 'admin_password')
    Config = collections.namedtuple('Config', ['tenant_name', 'username',
                                               'password', 'auth_url'])
    return Config(tenant_name=tenant_name,
                  username=username,
                  password=password,
                  auth_url=auth_url)


def init_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', action='store',
                        default='/etc/neutron/neutron.conf',
                        help='The location of the neutron.conf file')
    parser.add_argument('topology_file', action='store',
                        help='The path to the topology json file.')
    return parser


def main():
    parser = init_arg_parser()
    args = parser.parse_args()
    config = read_config(args.config)

    neutronclient = neutron_client.Client(auth_url=config.auth_url,
                                          username=config.username,
                                          tenant_name=config.tenant_name,
                                          password=config.password)

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
