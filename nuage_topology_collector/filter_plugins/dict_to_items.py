#!/usr/bin/python
# Copyright 2020 Nokia
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

from ansible.errors import AnsibleFilterError
from collections import Mapping


'''  Cbis is on ansible 2.5 which does not have dict2items '''


def dict_to_items(mydict, key_name='key', value_name='value'):
    ''' takes a dictionary and transforms it into a list of dictionaries,
        with each having a 'key' and 'value' keys that correspond to the
        keys and values of the original '''

    if not isinstance(mydict, Mapping):
        raise AnsibleFilterError("dict_to_items requires a dictionary, "
                                 "got %s instead." % type(mydict))

    ret = []
    for key in mydict:
        ret.append({key_name: key, value_name: mydict[key]})
    return ret


class FilterModule(object):
    ''' Query filter '''

    def filters(self):
        return {
            'dict_to_items': dict_to_items,
        }
