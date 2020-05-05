import testtools

# test the imports
from nuage_topology_collector.scripts.topology_import import TopologyConverter
from nuage_topology_collector.scripts.topology_import import TopologyReader


class TestTopologyImport(testtools.TestCase):

    def test_import(self):
        yield TopologyReader  # reference the import for pep8 compatibility
        yield TopologyConverter  # reference the import for pep8 compatibility
