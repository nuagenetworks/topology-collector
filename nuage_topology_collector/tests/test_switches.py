import testtools

from nuage_topology_collector.library.topology import get_switch
from nuage_topology_collector.library.topology import NokiaSwitch


class TestSwitches(testtools.TestCase):

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

    def test_switch_basic(self):
        self.data = {
            'interfaces': {
                'enp3s0': {
                    'lldp': [
                        [1, "0450e0ef38aed1"],
                        [2, "073335393133373238"],
                        [3, "0015"],
                        [4, "616e6532652d7372696f7630322d7372696f763033"],
                        [5, "616e6532652d7372696f7630322d7762783031"],
                        [7, "00140014"],
                        [6, '54694d4f532d44432d422d362e302e31302d333831206'
                            '26f74682f783836204e554147452032313020436f7079'
                            '72696768742028632920323030302d32303230204e6f6'
                            'b69612e0d0a416c6c2072696768747320726573657276'
                            '65642e20416c6c20757365207375626a65637420746f2'
                            '06170706c696361626c65206c6963656e736520616772'
                            '65656d656e74732e0d0a4275696c74206f6e204672692'
                            '04f637420322032303a33303a34342045445420323032'
                            '30205b6563306263625d206279206275696c646572206'
                            '96e202f72656c362e302d44432f72656c656173652f70'
                            '616e6f732f6d61696e0d0a'],
                        [8, '05010a1efe28020000000128000000010000000300000'
                            '0060000000100000004000000010000197f0000000100'
                            '00001200000004']],
                    'vfinfo': {
                        "vf_list": []
                    }
                }
            }
        }

        itf = self.data['interfaces']['enp3s0']
        switch = get_switch(itf['lldp'])
        report = switch.generate_json('enp3s0',
                                      itf['lldp'],
                                      itf['vfinfo'],
                                      None)
        self.assertEquals(report['neighbor-system-mgmt-ip'],
                          "10.30.254.40")
        self.assertEquals(report['neighbor-system-name'],
                          "ane2e-sriov02-wbx01")
        self.assertEquals(report['neighbor-system-port'], "1/1/8")
        self.assertEquals(report['ovs-bridge'], None)

    def test_switch_cisco_nxos(self):
        self.data = {
            'interfaces': {
                'eno3': {
                    'lldp': [
                        [1, "0470ea1a7328a0"],
                        [2, "0545746865726e6574312f31"],
                        [3, "0078"],
                        [4, "45746865726e6574312f31"],
                        [5, "6532652d6d756c746930322d636973636f4e394b"],
                        [7, "00140014"],
                        [6, '436973636f204e65787573204f7065726174696e67205'
                            '3797374656d20284e582d4f532920536f667477617265'
                            '20372e3028332949372836290a54414320737570706f7'
                            '2743a20687474703a2f2f7777772e636973636f2e636f'
                            '6d2f7461630a436f70797269676874202863292032303'
                            '0322d323031392c20436973636f2053797374656d732c'
                            '20496e632e20416c6c207269676874732072657365727'
                            '665642e'],
                        [8, '05010a1e81fa020500000000'],
                        [127, '0001420101'],
                        [127, '0080c2010001'],
                        [8, '070670ea1a7328a0020500000000'],
                        [0, '']],
                    'vfinfo': {
                        "vf_list": []
                    }
                }
            }
        }

        itf = self.data['interfaces']['eno3']
        switch = get_switch(itf['lldp'])
        report = switch.generate_json('eno3',
                                      itf['lldp'],
                                      itf['vfinfo'],
                                      None)
        self.assertEquals(report['neighbor-system-mgmt-ip'],
                          "10.30.129.250")
        self.assertEquals(report['neighbor-system-name'],
                          "e2e-multi02-ciscoN9K")
        self.assertEquals(report['neighbor-system-port'], "eth1/1")
        self.assertEquals(report['ovs-bridge'], None)
