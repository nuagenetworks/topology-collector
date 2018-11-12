import os
import sys
from helper.utils import Utils


def main():

    if (not os.path.isdir('/tmp/topo-coll/reports')) \
            and (not os.listdir("/tmp/topo-coll/reports/")):
        sys.stdout.write("ERROR: No report to import. Please generate the "
                         "topology report first.\n")
        sys.exit(1)

    Utils.cmds_run(["python /opt/nuage/topology-collector/"
                    "nuage_topology_collector/scripts/topology_import.py "
                    "`ls -t /tmp/topo-coll/reports/topo_report*json | "
                    "head -1`"])


if __name__ == "__main__":
    main()
