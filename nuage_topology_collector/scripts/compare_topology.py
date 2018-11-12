import json
import os
import sys

from helper import constants
from helper.utils import Utils


def create_old_report():
    from helper.osclient import NeutronClient
    neutron_client = NeutronClient()
    neutron_client.authenticate()
    sw_maps = neutron_client.get_switchport_mapping()
    return sw_maps["switchport_mappings"]


def generate_new_report_map(new_report_json):
    new_report_map = {}
    for compute in new_report_json["compute-hosts"]:
        for interface in compute["interfaces"]:
            for vf in interface["vf_info"]:
                new_report_map[(compute["service_host name"], vf["pci-id"])] \
                    = (interface["neighbor-system-mgmt-ip"],
                       interface["neighbor-system-port"])

    return new_report_map


def print_tuple(pair):
    return ", ".join(str(x) for x in pair)


def compare_reports(old_report_json, new_report_map):
    for port in old_report_json:
        new_port_info = new_report_map.pop((port["host_id"],
                                            port["pci_slot"]), None)
        if new_port_info is None:
            print("Port deleted : " + print_tuple((port["host_id"],
                  port["pci_slot"])) + "\n")
        elif new_port_info != (port["switch_id"], port["port_id"]):
            print("Port Modified : "
                  "" + print_tuple((port["host_id"], port["pci_slot"])))
            print(print_tuple((port["switch_id"], port["port_id"])) + " ===> "
                  "" + print_tuple(new_port_info) + "\n")

    for port in new_report_map.keys():
        print("New Port added: " + print_tuple(port) + " ===> "
              "" + print_tuple(new_report_map[port]) + "\n")


def main(argv):
    if len(sys.argv) != 2:
        sys.stdout.write("Please pass the new report as an argument.\n")
        sys.exit(1)

    new_report = argv[1]

    if not os.path.exists(new_report):
        sys.stdout.write("ERROR: The report %s does not exist.\n" % argv[1])
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

    with open(new_report) as new_report_data:
        new_report_json = json.load(new_report_data)

    new_report_map = generate_new_report_map(new_report_json)

    old_report_json = create_old_report()

    if not old_report_json:
        sys.stdout.write("No existing imported topology.\n")
        return

    compare_reports(old_report_json, new_report_map)


if __name__ == "__main__":
    main(sys.argv)
