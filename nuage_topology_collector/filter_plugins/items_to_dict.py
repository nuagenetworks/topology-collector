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


'''  OSP13 has ansible 2.6 which does not have items2dict '''


def items_to_dict(mylist, key_name='key', value_name='value'):
    ''' takes a list of dicts with each having a 'key' and 'value' keys,
        and transforms the list into a dictionary,
        effectively as the reverse of dict2items '''

    return dict((item[key_name], item[value_name]) for item in mylist)


class FilterModule(object):
    ''' Query filter '''

    def filters(self):
        return {
            'items_to_dict': items_to_dict,
        }
