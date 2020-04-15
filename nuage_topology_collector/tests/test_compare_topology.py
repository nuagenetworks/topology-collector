#!/usr/bin/env python

try:
    from StringIO import StringIO  # for Python 2
except ImportError:
    from io import StringIO  # for Python 3

import filecmp
import json
import mock
import os
import sys
import testtools

from nuage_topology_collector.scripts import compare_topology
from nuage_topology_collector.scripts.helper.utils import Utils

TESTS_PATH = 'nuage_topology_collector/tests/'
INPUTS_PATH = TESTS_PATH + 'inputs/'
OUTPUT_PATH = TESTS_PATH + 'outputs/'


def mock_old_report():
    current_dir = os.getcwd()
    old_report_path = os.path.join(
        current_dir, INPUTS_PATH + 'compare_topology_old.json')
    with open(old_report_path) as old_report_data:
        old_report_json = json.load(old_report_data)

    return old_report_json


old_report_json = mock_old_report()


class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout


class CompareTopology(testtools.TestCase):
    @mock.patch.object(compare_topology, 'create_old_report',
                       return_value=old_report_json)
    @mock.patch.object(Utils, 'check_user', return_value=True)
    @mock.patch.object(os.path, 'isfile', return_value=True)
    @mock.patch.object(Utils, 'source_rc_files', return_value=None)
    def test_module_main(self, *mock):
        current_dir = os.getcwd()
        new_report_path = os.path.join(
            current_dir, INPUTS_PATH + 'compare_topology_new.json')
        mock_generated_output_path = os.path.join(
            current_dir, OUTPUT_PATH + 'generated_output.txt')
        mock_expected_output_path = os.path.join(
            current_dir, OUTPUT_PATH + 'test_compare_topology')

        with Capturing() as output:
            compare_topology.main([self, new_report_path])
        with open(mock_generated_output_path, 'w') as generated_output:
            for line in output:
                generated_output.write(line + "\n")
        self.assertTrue(filecmp.cmp(mock_generated_output_path,
                                    mock_expected_output_path),
                        'The output does not match the expected output')
