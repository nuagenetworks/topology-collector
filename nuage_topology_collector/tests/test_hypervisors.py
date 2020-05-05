import mock
import testtools

from nuage_topology_collector.scripts.generate_topology import get_hypervisors


# Overcloud Hypervisor
class Hypervisor(object):
    def __init__(self, ID, hypervisor_hostname, state, status):
        self.ID = ID
        self.hypervisor_hostname = hypervisor_hostname
        self.state = state
        self.status = status


# Undercloud Nova (BM) Instance (Server)
class Server(object):
    def __init__(self, ID, name, status, networks):
        self.ID = ID
        self.name = name
        self.status = status
        self.networks = networks


class FakeNovaClient(object):
    @staticmethod
    def get_hypervisor_list():
        avrs_0 = Hypervisor('5f9d749a-1119-47ea-9733-270c28fe893',
                            'overcloud-computeavrs-0.domain',
                            'up',
                            'enabled')
        avrs_1 = Hypervisor('69989cd8-b706-40b5-8ca4-4f80d98e68d2',
                            'overcloud-computeavrs-1.domain',
                            'up',
                            'enabled')
        return [avrs_0, avrs_1]

    @staticmethod
    def get_server_list():
        avrs_0 = Server('53018e5d-edc4-4e1a-bd0a-222c1149b6a9',
                        'overcloud-computeavrs-0',
                        'ACTIVE',
                        {'ctlplane': ['192.168.24.6']})
        avrs_1 = Server('fc4e7714-2d10-4829-90e5-75848123e2a5',
                        'overcloud-computeavrs-1',
                        'ACTIVE',
                        {'ctlplane': ['192.168.24.10']})
        controller = Server('aa7b6ec8-64f7-4857-9b26-1131f4b0f819',
                            'overcloud-controller-0',
                            'ACTIVE',
                            {'ctlplane': ['192.168.24.12']})
        return [avrs_0, avrs_1, controller]


class TestHypervisors(testtools.TestCase):

    @mock.patch('nuage_topology_collector.scripts.generate_topology.'
                'get_nova_client', return_value=FakeNovaClient())
    def test_get_hypervisors(self, *_):
        hypervisors = get_hypervisors()
        self.assertEqual(2, len(hypervisors))
        avrs_0 = hypervisors['overcloud-computeavrs-0']
        self.assertEqual('192.168.24.6', avrs_0.host_ip)
        avrs_1 = hypervisors['overcloud-computeavrs-1']
        self.assertEqual('192.168.24.10', avrs_1.host_ip)
