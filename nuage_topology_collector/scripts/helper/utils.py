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

import getpass
import os
import subprocess
import sys
import traceback

from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.playbook_executor import PlaybookExecutor
from oslo_utils import uuidutils

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class OSCredentials(object):
    def __init__(self, auth_url, username, password, project_name,
                 identity_api_version,
                 user_domain_id=None, user_domain_name=None,
                 project_domain_id=None, project_domain_name=None,
                 verify_ca=True, ca_cert=None):
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.project_name = project_name
        self.verify_ca = verify_ca
        self.ca_cert = ca_cert if verify_ca else None
        self.identity_api_version = identity_api_version
        if identity_api_version == 3:
            self.auth_url = self.assure_endswith(self.auth_url, '/v3')
            self.user_domain_id = user_domain_id
            self.user_domain_name = user_domain_name
            self.project_domain_id = project_domain_id
            self.project_domain_name = project_domain_name
        else:
            self.auth_url = self.assure_endswith(self.auth_url, '/v2.0')

    @staticmethod
    def assure_endswith(url, endswith):
        return url if url.endswith(endswith) else (url + endswith)


class Utils(object):

    @staticmethod
    def env_error(msg, *args):
        raise EnvironmentError((msg % tuple(args)) if args else msg)

    @staticmethod
    def report_traceback(reporter):
        reporter.report(traceback.format_exc())

    @staticmethod
    def get_env_var(name, default=None, required=False):
        assert default is None or not required  # don't set default and
        #                                         required at same time
        try:
            if os.environ[name] is not None:
                return os.environ[name]
            else:
                return default
        except KeyError:
            if not required:
                return default
            else:
                Utils.env_error('Please set %s. Aborting.', name)

    @staticmethod
    def get_env_bool(name, default=False):
        return (str(Utils.get_env_var(name, default)).lower()
                in ['t', 'true', 'yes', 'y', '1'])

    @staticmethod
    def is_uuid(uuid):
        return uuidutils.is_uuid_like(uuid)

    @staticmethod
    def check_user(required_user):
        current_user = getpass.getuser()
        if current_user == required_user:
            return True
        else:
            return False

    @staticmethod
    def get_os_credentials():
        auth_url = Utils.get_env_var('OS_AUTH_URL', required=True)
        username = Utils.get_env_var('OS_USERNAME', required=True)
        password = Utils.get_env_var('OS_PASSWORD', required=True)

        project_name = Utils.get_env_var(
            'OS_PROJECT_NAME', Utils.get_env_var('OS_TENANT_NAME'))
        if not project_name:
            Utils.env_error('OS_PROJECT_NAME nor OS_TENANT_NAME '
                            'is defined. Please set either of both.')

        identity_api_version = float(  # deal with version '2.0' e.g.
            Utils.get_env_var('OS_IDENTITY_API_VERSION', 2))

        if identity_api_version == 3:
            user_domain_id = Utils.get_env_var('OS_USER_DOMAIN_ID')
            user_domain_name = Utils.get_env_var('OS_USER_DOMAIN_NAME')
            if not user_domain_name and not user_domain_id:
                Utils.env_error('OS_USER_DOMAIN_ID '
                                'nor OS_USER_DOMAIN_NAME '
                                'is defined. Please set either of both.')

            project_domain_id = Utils.get_env_var('OS_PROJECT_DOMAIN_ID')
            project_domain_name = Utils.get_env_var('OS_PROJECT_DOMAIN_NAME')
            if not project_domain_name and not project_domain_id:
                Utils.env_error('OS_PROJECT_DOMAIN_ID '
                                'nor OS_PROJECT_DOMAIN_NAME '
                                'is defined. Please set either of both.')
        else:
            user_domain_id = user_domain_name = None
            project_domain_id = project_domain_name = None

        # below is not a standard OS env setting -> to be documented
        verify_ca = Utils.get_env_bool('OS_VERIFY_CA', True)
        # below is standard --
        ca_cert = Utils.get_env_var('OS_CACERT')

        return OSCredentials(
            auth_url, username, password, project_name,
            identity_api_version,
            user_domain_id, user_domain_name,
            project_domain_id, project_domain_name,
            verify_ca, ca_cert)

    @staticmethod
    def source_rc_files(rc_file_path):
        rc_lines = Utils.cmds_run(["env -i bash -c 'source "
                                   "%s && env'" % rc_file_path])
        rc_variables = rc_lines.split('\n')
        for variable in rc_variables:
            (key, _, value) = variable.partition("=")
            if key != '':
                os.environ[key] = value

    @staticmethod
    def cmds_run(cmds):
        if not cmds:
            return
        output_list = []
        for cmd in cmds:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    shell=True, close_fds=True)
            out = ""
            err = ""
            while True:
                output = proc.stdout.readline().decode()
                err = err + proc.stderr.readline().decode()
                if output == '' and proc.poll() is not None:
                    break
                if output:
                    out = out + output
            proc.poll()
            if proc.returncode and err and err.split():
                sys.stdout.write("error occurred during command:\n"
                                 " %s\n error:\n %s "
                                 "\n exiting" % (cmd, err))
                sys.exit(1)
            output_list.append(out)

        if len(cmds) == 1:
            return output_list[0]
        else:
            return output_list


def run_ansible(ansible_playbook_path, opts):
    loader = DataLoader()
    inventory = InventoryManager(loader=loader,
                                 sources=[])
    variable_manager = VariableManager(loader=loader,
                                       inventory=inventory)
    passwords = {}
    display.verbosity = opts.verbosity

    # Since ansible has deprecated the options and introduced
    # new library context starting from 2.8
    try:
        from ansible import context
        from ansible.cli import CLI
        from ansible.module_utils.common.collections import ImmutableDict

        context.CLIARGS = ImmutableDict(
            listtags=False, listtasks=False, listhosts=False,
            syntax=False, connection='smart', module_path=None, forks=100,
            remote_user='slotlocker', timeout=10, become=False,
            become_ask_pass=False, ask_pass=False, become_method='sudo',
            become_user='root', verbosity=opts.verbosity,
            check=opts.check, diff=False, subset=opts.subset,
            step=False, start_at_task=None)

        CLI.get_host_list(inventory, context.CLIARGS['subset'])
        playbook = PlaybookExecutor(
            playbooks=[ansible_playbook_path], inventory=inventory,
            variable_manager=variable_manager, loader=loader,
            passwords=passwords)

    except (ImportError, ValueError):
        from collections import namedtuple
        from ansible.cli import CLI
        Options = namedtuple(
            'Options',
            [
                'listtags', 'listtasks', 'listhosts', 'syntax', 'connection',
                'module_path', 'forks', 'remote_user', 'private_key_file',
                'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args',
                'scp_extra_args', 'become', 'become_method', 'become_user',
                'verbosity', 'check', 'diff'])

        options = Options(
            listtags=False, listtasks=False, listhosts=False,
            syntax=False, connection='ssh', module_path=None, forks=100,
            remote_user='slotlocker', private_key_file=None,
            ssh_common_args=None, ssh_extra_args=None,
            sftp_extra_args=None, scp_extra_args=None, become=False,
            become_method='sudo', become_user='root', verbosity=opts.verbosity,
            check=opts.check, diff=False)
        CLI.get_host_list(inventory, opts.subset)
        playbook = PlaybookExecutor(
            playbooks=[ansible_playbook_path], inventory=inventory,
            variable_manager=variable_manager, loader=loader,
            options=options, passwords=passwords)

    rc = playbook.run()
    if rc == 0:
        sys.stdout.write("\n Running Ansible Completed !! \n")
    else:
        sys.stdout.write("\n Running Ansible seems to have some error !! \n")
