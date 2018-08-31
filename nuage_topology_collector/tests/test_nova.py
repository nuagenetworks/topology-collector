import testtools

from nuage_topology_collector.filter_plugins.nova import hypervisor_hostnames


class TestNovaOutput(testtools.TestCase):

    def test_nova_hypervisor_list_output(self):
        # newton
        nhl_output_newton = \
            "+----+------------------------------------------+-------+" \
            "---------+\n" \
            "| ID | Hypervisor hostname                      | State |" \
            " Status  |\n" \
            "+----+------------------------------------------+-------+" \
            "---------+\n" \
            "| 1  | ovs-5-mvdce2esim03.us.alcatel-lucent.com | up    |" \
            " enabled |\n" \
            "| 2  | ovs-5-mvdce2esim03.mv.nuagenetworks.net  | down  |" \
            " enabled |\n" \
            "| 3  | sim-20-mvdce2esim03.mv.nuagenetworks.net | up    |" \
            " enabled |\n" \
            "+----+------------------------------------------+-------+" \
            "---------+"
        expected_output_newton = [
            "ovs-5-mvdce2esim03.us.alcatel-lucent.com",
            "sim-20-mvdce2esim03.mv.nuagenetworks.net"
        ]

        self.assertEqual(hypervisor_hostnames(nhl_output_newton),
                         expected_output_newton)
        # queens
        nhl_output_queens = \
            "+--------------------------------------+---------------------" \
            "-----------------+-------+---------+\n| ID                   " \
            "                | Hypervisor hostname                  | Stat" \
            "e | Status  |\n+--------------------------------------+------" \
            "--------------------------------+-------+---------+\n| b159ec" \
            "83-59a8-4d96-ac70-aa67c63d9981 | overcloud-computesriov-1.loc" \
            "aldomain | up    | enabled |\n| 1a8cac7a-a10e-4b47-9977-12f4f" \
            "84432d4 | overcloud-computesriov-0.localdomain | down  | enab" \
            "led |\n+--------------------------------------+--------------" \
            "------------------------+-------+---------+"
        expected_output_queens = [
            "b159ec83-59a8-4d96-ac70-aa67c63d9981",
        ]
        self.assertEqual(hypervisor_hostnames(nhl_output_queens),
                         expected_output_queens)
