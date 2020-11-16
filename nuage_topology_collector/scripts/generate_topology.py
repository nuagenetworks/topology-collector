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

# TODO(OPENSTACK-2892) :
#      This is temporary code for dealing with py2/py3 compatibility and have
#      unit tests pass, while the production code isn't deployed as a true
#      python package. This will be worked on in a subsequent release.
try:
    from .helper import constants
    from .helper.utils import Utils
    from .helper.utils import run_ansible
except (ImportError, ValueError):
    from helper import constants
    from helper.utils import Utils
    from helper.utils import run_ansible


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

    topo_playbook_path = os.path.join(constants.NUAGE_TC_PATH, "get_topo.yml")
    run_ansible(topo_playbook_path)


if __name__ == "__main__":
    main()
