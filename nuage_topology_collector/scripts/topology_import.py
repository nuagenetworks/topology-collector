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
import json
import logging
import os
import sys

# TODO(OPENSTACK-2892) :
#      This is temporary code for dealing with py2/py3 compatibility and have
#      unit tests pass, while the production code isn't deployed as a true
#      python package. This will be worked on in a subsequent release.
try:
    from .helper import constants
    from .helper import script_logging
    from .helper.osclient import NeutronClient
    from .helper.utils import Utils
except (ImportError, ValueError):
    from helper import constants
    from helper import script_logging
    from helper.osclient import NeutronClient
    from helper.utils import Utils


script_name = 'topology_import'
LOG = logging.getLogger(script_name)
interface_of_compute_with_error = {}
compute_host_name = None


class TopologyReader(object):
    def __init__(self, path):
        super(TopologyReader, self).__init__()
        self.path = path
        self.json_data = self._load_json()

    def _load_json(self):
        with open(self.path) as topology_file:
            return json.load(topology_file)

    def interfaces(self):
        global compute_host_name
        compute_host_index = 0
        total_compute_host = len(self.json_data['compute-hosts'])
        for compute_host in self.json_data['compute-hosts']:
            compute_host_name = str(self.json_data['compute-hosts']
                                    [compute_host_index]
                                    ['hypervisor hostname'])
            msg = "\n Processing Compute Host - " + compute_host_name

            total_compute_host_left = total_compute_host - compute_host_index
            msg = msg + ", Total Computes Left: %s" % total_compute_host_left
            LOG.user(msg)
            compute_host_index = compute_host_index + 1
            total_interfaces_within_compute = len(compute_host['interfaces'])
            interfaces_within_compute_index = 0
            for interface in compute_host['interfaces']:
                with script_logging.indentation():
                    msg = " Procesing Interface - " + interface["name"]
                    total_interfaces_within_compute_left = \
                        total_interfaces_within_compute - \
                        interfaces_within_compute_index
                    msg = msg + (", Total Interfaces Left: %s" %
                                 total_interfaces_within_compute_left)
                    LOG.user(msg)
                    interfaces_within_compute_index = \
                        interfaces_within_compute_index + 1
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
        with script_logging.indentation():
            if not interface_mappings:
                LOG.user("No Interface mapping exsits for %s " %
                         interface["name"])
            else:
                LOG.user("Processing  %s  mappings" % len(interface_mappings))
        return interface_mappings

    def function_to_mapping(self, virtual_function):
        return {'pci_slot': virtual_function['pci-id']}


@script_logging.step(description="importing topology")
def import_interfaces(reader, converter):
    global compute_host_name, interface_of_compute_with_error
    for interface in reader.interfaces():
        with script_logging.indentation():
            mapping = []
            for switchport_mapping in converter.interface_to_mappings(
                    interface):
                if switchport_mapping:
                    LOG.debug("Sending %s",
                              {'switchport_mapping': switchport_mapping})

                try:
                    body = {'switchport_mapping': switchport_mapping}
                    converter.neutron.create_switchport_mapping(body)
                    LOG.debug("Successfully imported the SwitchPort Mapping")
                except Exception as e:
                    with script_logging.indentation():
                        msg_arg = {
                            "error_msg": e.message,
                            "switchport_mapping": switchport_mapping,
                            "interface": interface["name"]
                        }
                        LOG.user("Failed to import SwitchPort Mapping:"
                                 "%(switchport_mapping)s" % msg_arg,
                                 exc_info=True)
                        LOG.user("ERROR: %(error_msg)s" % msg_arg)
                        mapping.append(switchport_mapping)
                    interface_of_compute_with_error.update({
                        (compute_host_name, interface["name"]): mapping})

    LOG.debug("\n")
    LOG.debug("-----------------")
    LOG.debug("  Failure summary")
    LOG.debug("-------------------")
    LOG.debug("Errors occurred in:")

    for (compute_name, interface_name), switchport_mapping in \
            interface_of_compute_with_error.items():
        with script_logging.indentation():
            LOG.debug("Compute Host %s" % compute_name)
            with script_logging.indentation():
                LOG.debug("Interface Name: %s" % interface_name)
                with script_logging.indentation():
                    for mapping in switchport_mapping:
                        LOG.debug("SwitchPort Mapping: %s" % mapping)

    LOG.debug("\n")
    log_dir = os.path.expanduser('~') + '/nuage_logs'
    LOG.user("Complete!! Please check the log file %s for summary" % log_dir)


def main(argv):

    if len(argv) != 2:
        sys.stdout.write("ERROR: Please pass the new report as an argument.\n")
        sys.exit(1)

    if not script_logging.log_file:
        script_logging.init_logging(script_name)

    if not os.path.exists(argv[1]):
        sys.stdout.write("ERROR: The report %s does not exist. \n" % argv[1])
        sys.exit(1)

    if not Utils.check_user(constants.STACK_USER):
        sys.stdout.write("ERROR: Run the script as %s "
                         "user.\n" % constants.STACK_USER)
        sys.exit(1)

    if not os.path.isfile(constants.OVERCLOUDRC_FILE):
        sys.stdout.write("ERROR: %s does not exist."
                         "\n" % constants.OVERCLOUDRC_FILE)
        sys.exit(1)

    Utils.source_rc_files(constants.OVERCLOUDRC_FILE)

    neutron_client = NeutronClient()
    neutron_client.authenticate()

    reader = TopologyReader(argv[1])
    converter = TopologyConverter(neutron_client)
    import_interfaces(reader, converter)


if __name__ == '__main__':
    main(sys.argv)
