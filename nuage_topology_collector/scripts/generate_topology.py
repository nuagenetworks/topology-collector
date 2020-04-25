# Copyright 2020 NOKIA
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

import os
import sys

from helper import constants
from helper.utils import Utils
from helper.utils import run_ansible


def get_nova_client(rc_file):
    from helper.osclient import NovaClient
    _environ = dict(os.environ)
    try:
        Utils.source_rc_files(rc_file)
        nova_client = NovaClient()
        nova_client.authenticate()
        return nova_client
    finally:
        os.environ.clear()
        os.environ.update(_environ)


def get_hypervisors():
    hypervisors = {}
    # overcloud hypervisors
    for hypervisor in get_nova_client(
            constants.OVERCLOUDRC_FILE).get_hypervisor_list():
        hypervisors[
            hypervisor.hypervisor_hostname.split('.')[0]] = hypervisor
    # undercloud vm instances (servers)
    for server in get_nova_client(
            constants.STACKRC_FILE).get_server_list():
        if server.name in hypervisors.keys():
            # when match, add the (1st) host ip to the hypervisor dict value
            hypervisors[
                server.name].host_ip = server.networks['ctlplane'][0]
    return hypervisors


def dump_hypervisors(file_name, hypervisors):
    with open(file_name, "w+") as hypervisor_inventory:
        hypervisor_inventory.write("[hypervisors]\n")
        for hypervisor in hypervisors.values():
            hypervisor_inventory.write("%s hostname=%s service_host=%s\n" % (
                hypervisor.host_ip, hypervisor.hypervisor_hostname,
                hypervisor.service["host"]
            ))


def main():
    if not Utils.check_user(constants.STACK_USER):
        sys.stdout.write("ERROR: Run the script as %s user.\n" %
                         constants.STACK_USER)
        sys.exit(1)

    if not os.path.isfile(constants.STACKRC_FILE):
        sys.stdout.write("ERROR: %s does not exist."
                         "\n" % constants.OVERCLOUDRC_FILE)
        sys.exit(1)

    if not os.path.isfile(constants.OVERCLOUDRC_FILE):
        sys.stdout.write("ERROR: %s does not exist."
                         "\n" % constants.OVERCLOUDRC_FILE)
        sys.exit(1)

    hypervisors = get_hypervisors()
    hypervisor_file_path = os.path.join(constants.NUAGE_TC_PATH,
                                        "hypervisors")
    dump_hypervisors(hypervisor_file_path, hypervisors)
    topo_playbook_path = os.path.join(constants.NUAGE_TC_PATH, "get_topo.yml")
    run_ansible(hypervisor_file_path, topo_playbook_path)


if __name__ == "__main__":
    main()
