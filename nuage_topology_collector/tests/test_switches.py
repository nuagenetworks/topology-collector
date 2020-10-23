import json
import os
import testtools

from nuage_topology_collector.library.topology import get_switch
from nuage_topology_collector.library.topology import NokiaSwitch

TESTS_PATH = 'nuage_topology_collector/tests/'
INPUTS_PATH = TESTS_PATH + 'inputs/'
OUTPUTS_PATH = TESTS_PATH + 'outputs/'


class TestSwitches(testtools.TestCase):

    def validate_json(self, vendor, usecases=1):
        current_dir = os.getcwd()
        for i in range(usecases):
            abs_path_ls = os.path.join(
                current_dir, INPUTS_PATH + 'interface_vfs_pci_list')
            fname = vendor + '_lldp_output_' + str(i)
            abs_path_n_lldp = os.path.join(current_dir, INPUTS_PATH) + fname
            fname = 'test_' + vendor + '_switch_json' + '_' + str(i)
            abs_path_n_lldp_output = os.path.join(
                current_dir, OUTPUTS_PATH) + fname
            interface = "ensp0"
            with open(abs_path_ls) as file:
                lsout = file.read()
            with open(abs_path_n_lldp) as file:
                lldpout = file.read()
            with open(abs_path_n_lldp_output) as file:
                expected_json_obj = file.read()
            switch = get_switch(lldpout)
            json_obj = switch.generate_json(interface, lldpout, lsout)
            self.assertEqual(json.loads(expected_json_obj),
                             json.loads(json_obj))

    def test_nokia_switch_json(self):
        self.validate_json('nokia')

    def test_nokia_switch_ifindex(self):
        switch = NokiaSwitch()
        ifindex = {
            # Scheme B Connector
            '1/1/c1/1': '1610899521',
            # Scheme B None-Connector
            '1/2/4': '1610907680',
            # Scheme C Connector
            '1/2/c2/3': '37830659',
            # Scheme C None-Connector
            '2/1/5': '69369856',
            # Scheme D Connector
            '1/2/c2/6': '1258889350',
            # Scheme D None-Connector
            '3/1/3': '1259896835',
        }
        for ifname, ifindex in ifindex.items():
            self.assertEqual(ifname,
                             switch.convert_ifindex_to_ifname(ifindex))

    def test_cisco_switch_json(self):
        self.validate_json('cisco', 4)
