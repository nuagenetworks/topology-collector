#!/usr/bin/python
# Copyright 2017 Nokia
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
from ansible.errors import AnsibleError
import re


uuid4hex = re.compile(
    '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def osc_env_dict(osc_env_string):
    ''' Given a string representation of the output of "cat osc_env_file",
    return a dictionary of env values for use with ansible commands. Assumes
    each line of the env file is of the form:

    export NAME=VALUE

    For example:

    export OS_USERNAME=admin
    export OS_AUTH_URL="http://10.100.100.20:35357/v3"
    '''
    PAIR_RE = r"export\s+(?P<name>\w+)=(?P<value>\S+)"
    dict = {}
    pairs = re.finditer(PAIR_RE, osc_env_string)
    for pair in pairs:
        dict[pair.group('name')] = pair.group('value').strip('"')
    return dict


def hypervisor_hostnames(hstring):
    ''' Given a string representation of the output of "nova hypervisor-list",
    return a list of just the enabled hypervisor hostnames.
    '''
    FINDRE = r"\|\s+[0-9]+\s+\|\s+(\S+)\s+\|\s+up\s+\|\s+enabled\s+\|"
    lines = hstring.split('\n')
    nlists = []
    for line in lines:
        if 'enabled' in line and 'up' in line:
            nlist = uuid4hex.findall(line)
            if not nlist:
                nlist = re.findall(FINDRE, line)
            nlists = nlists + nlist
    return nlists


def hypervisor_names(hstring):
    ''' Given a string representation of the output of "nova hypervisor-show",
    return a string with hypervisor hostname and service_host name in a format
    suitable for a host inventory file, e.g. 'hostname service_host=shostname'.
    '''

    HYPERHOSTNAMERE = r"\|\s+hypervisor_hostname\s+\|\s+(\S+)\s+\|"
    SERVICEHOSTNAMERE = r"\|\s+service_host\s+\|\s+(\S+)\s+\|"
    HYPERHOSTIPRE = r"\|\s+host_ip\s+\|\s+(\S+)\s+\|"

    scratch = ""

    host_ip = re.search(HYPERHOSTIPRE, hstring)
    if host_ip:
        scratch += host_ip.group(1) + " "
    else:
        raise AnsibleError("host_ip name not found")

    hyper = re.search(HYPERHOSTNAMERE, hstring)
    if hyper:
        scratch += "hostname=" + hyper.group(1) + " "
    else:
        raise AnsibleError("Hypervisor hostname not found")

    service = re.search(SERVICEHOSTNAMERE, hstring)
    if service:
        scratch += "service_host=" + service.group(1) + " "
    else:
        raise AnsibleError("service_host name not found")

    return scratch


class FilterModule(object):
    ''' Query filter '''

    def filters(self):
        return {
            'osc_env_dict': osc_env_dict,
            'hypervisor_hostnames': hypervisor_hostnames,
            'hypervisor_names': hypervisor_names
        }
