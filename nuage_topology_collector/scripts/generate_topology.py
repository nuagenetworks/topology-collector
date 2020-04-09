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

import os
import sys
from helper.utils import Utils
from helper import constants


def get_hypervisors():
    from helper.osclient import NovaClient
    hypervisor_list = {}
    _environ = dict(os.environ)
    try:
        Utils.source_rc_files(constants.OVERCLOUDRC_FILE)
        nova_client = NovaClient()
        nova_client.authenticate()
        oc_hypervisor_list = nova_client.get_hypervisor_list()
        for hypervisor in oc_hypervisor_list:
            hypervisor_list[
                hypervisor.hypervisor_hostname.split('.')[0]] = hypervisor
    finally:
        os.environ.clear()
        os.environ.update(_environ)
    try:
        Utils.source_rc_files(constants.STACKRC_FILE)
        nova_client = NovaClient()
        nova_client.authenticate()
        uc_server_list = nova_client.get_server_list()
        for server in uc_server_list:
            if server.name in hypervisor_list.keys():
                hypervisor_list[
                    server.name].host_ip = server.networks['ctlplane'][0]
    finally:
        os.environ.clear()
        os.environ.update(_environ)
    hypervisor_inventory = open("%s" % constants.HYPERVISOR_FILE, "w+")
    hypervisor_inventory.write("[hypervisors]\n")
    for hypervisor in hypervisor_list.values():
        hypervisor_inventory.write("%s hostname=%s service_host=%s\n" % (
            hypervisor.host_ip, hypervisor.hypervisor_hostname,
            hypervisor.service["host"]
        ))

    hypervisor_inventory.close()
    Utils.cmds_run(
        ["sudo mv %s /opt/nuage/topology-collector/"
         "nuage_topology_collector/" % constants.HYPERVISOR_FILE]
    )


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

    get_hypervisors()
    Utils.cmds_run(["cd /opt/nuage/topology-collector/"
                    "nuage_topology_collector; "
                    "ansible-playbook -i ./hypervisors get_topo.yml"])


if __name__ == "__main__":
    main()
