#!/usr/bin/python

from ansible.errors import AnsibleError
import re


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


def hypervisor_hostnames(hstring):
    ''' Given a string representation of the output of "nova hypervisor-list",
    return a list of just the enabled hypervisor hostnames.
    '''
    BORDER_RE = "\+-+\+-+\+-+\+-+\+"
    nlist = []
    scratch = re.split(BORDER_RE, hstring)
    if len(scratch) < 3:
        raise AnsibleError("unexpected output format")
    hlist = scratch[2].strip().split('\n')
    for host in hlist:
        if 'enabled' in host:
            parts = host.strip().split('|')
            if len(parts) < 3:
                raise AnsibleError("unexpected line format")
            nlist.append(parts[2].strip())
    return nlist


def hypervisor_names(hstring):
    ''' Given a string representation of the output of "nova hypervisor-show",
    return a string with hypervisor hostname and service_host name in a format
    suitable for a host inventory file, e.g. 'hostname service_host=shostname'.
    '''
    HYPERHOSTNAME = "hypervisor_hostname"
    SERVICEHOSTNAME = "service_host"
    scratch = ""
    lines = hstring.split('\n')
    found = False
    for line in lines:
        if HYPERHOSTNAME in line:
            parts = line.strip().split('|')
            if len(parts) < 3:
                raise AnsibleError("unexpected " + HYPERHOSTNAME + " line format")
            scratch += parts[2].strip() + " "
            found = True
            break
    if not found:
        raise AnsibleError("error finding " + HYPERHOSTNAME)
    found = False
    for line in lines:
        if SERVICEHOSTNAME in line:
            parts = line.strip().split('|')
            if len(parts) < 3:
                raise AnsibleError("unexpected " + SERVICEHOSTNAME + " line format")
            scratch += "service_host=" + parts[2].strip()
            found = True
            break
    if not found:
         raise AnsibleError("error finding " + SERVICEHOSTNAME)
    return scratch


class FilterModule(object):
    ''' Query filter '''

    def filters(self):
        return {
            'hypervisor_hostnames': hypervisor_hostnames,
            'hypervisor_names': hypervisor_names
        }

