#!/usr/bin/python
from netaddr import valid_ipv4

def ipv4(addr):
    return valid_ipv4(addr)

class FilterModule(object):
    ''' Query filter '''

    def filters(self):
        return {
            'ipv4': ipv4,
        }
