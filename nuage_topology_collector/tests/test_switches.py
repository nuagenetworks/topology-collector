import json
import os
import testtools

from nuage_topology_collector.library.topology import NokiaSwitch
from nuage_topology_collector.library.topology import CiscoSwitch

TESTS_PATH = 'nuage_topology_collector/tests/'
INPUTS_PATH = TESTS_PATH + 'inputs/'
OUTPUTS_PATH = TESTS_PATH + 'outputs/'


class TestSwitches(testtools.TestCase):

    def validate_json(self, switch, usecases=1):
        current_dir = os.getcwd()
        for i in range(usecases):
            abs_path_ls = os.path.join(
                current_dir, INPUTS_PATH + 'interface_vfs_pci_list')
            fname = switch.name + '_lldp_output_' + str(i)
            abs_path_n_lldp = os.path.join(current_dir, INPUTS_PATH) + fname
            fname = 'test_' + switch.name + '_switch_json' + '_' + str(i)
            abs_path_n_lldp_output = os.path.join(
                current_dir, OUTPUTS_PATH) + fname
            interface = "ensp0"
            with open(abs_path_ls) as file:
                lsout = file.read()
            with open(abs_path_n_lldp) as file:
                lldpout = file.read()
            with open(abs_path_n_lldp_output) as file:
                expected_json_obj = file.read()
            json_obj = switch.generate_json(interface, lldpout, lsout)
            self.assertEqual(json.loads(json_obj),
                             json.loads(expected_json_obj))

    def test_nokia_switch_json(self):
        self.validate_json(NokiaSwitch())

    def test_cisco_switch_json(self):
        self.validate_json(CiscoSwitch(), 2)
