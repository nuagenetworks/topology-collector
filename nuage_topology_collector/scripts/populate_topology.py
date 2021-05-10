#!/usr/bin/env python

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

import glob
import os
import sys

# TODO(OPENSTACK-2892) :
#      This is temporary code for dealing with py2/py3 compatibility and have
#      unit tests pass, while the production code isn't deployed as a true
#      python package. This will be worked on in a subsequent release.
try:
    from .helper import constants
except (ImportError, ValueError):
    from helper import constants
import topology_import


def main():

    if (not os.path.isdir(constants.OUTPUT_DIR)) \
            and (not os.listdir(constants.OUTPUT_DIR)):
        sys.stdout.write('ERROR: No report to import. Please generate the '
                         'topology report first.\n')
        sys.exit(1)
    output_file_regex_path = constants.OUTPUT_DIR + '/' + \
        constants.OUTPUT_FILE_PREFIX + '*json'
    list_of_files = glob.glob(output_file_regex_path)
    if len(list_of_files) == 0:
        sys.stdout.write('ERROR: No files found under dir '
                         '%s' % constants.OUTPUT_DIR)

    # get the latest report file created in /tmp/topo-coll dir
    topo_repo_file_path = max(list_of_files, key=os.path.getctime)
    if os.path.exists(topo_repo_file_path):
        sys.stdout.write('Processing %s\n\n' % topo_repo_file_path)
        topology_import.main(['topology_import.py', topo_repo_file_path])
    else:
        sys.stdout.write('ERROR: No file named %s found under '
                         '%s \n' % (topo_repo_file_path, constants.OUTPUT_DIR))


if __name__ == "__main__":
    main()
