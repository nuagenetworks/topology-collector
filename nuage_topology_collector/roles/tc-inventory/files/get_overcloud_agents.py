#!/usr/bin/python

import json
import os

from keystoneauth1.identity import v3
from keystoneauth1 import session
from neutronclient.v2_0 import client

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

auth_url = os.environ["OS_AUTH_URL"]
if os.environ.get("OS_IDENTITY_API_VERSION") == "3":
    if 'v3' not in auth_url:
        auth_url = urljoin(auth_url, 'v3')
username = os.environ.get("OS_USERNAME")
password = os.environ.get("OS_PASSWORD")
project_name = os.environ.get("OS_TENANT_NAME",
                              os.environ.get("OS_PROJECT_NAME"))
user_domain_name = os.environ.get("OS_USER_DOMAIN_NAME")
project_domain_name = os.environ.get("OS_PROJECT_DOMAIN_NAME")

auth = v3.Password(auth_url=auth_url,
                   username=username,
                   password=password,
                   project_name=project_name,
                   user_domain_name=user_domain_name,
                   project_domain_name=project_domain_name,
                   )
session = session.Session(auth=auth, verify=False)
neutron = client.Client(session=session)
filter = {
    'agent_type': 'NIC Switch agent'
}
agents = neutron.list_agents(**filter)['agents']
filter = {
    'agent_type': 'Open vSwitch agent'
}
agents.extend(neutron.list_agents(**filter)['agents'])
result = dict()
for agent in agents:
    confs = dict()
    if agent['agent_type'] == 'NIC Switch agent':
        confs.update(
            {'device_mappings': agent['configurations']['device_mappings']})
    else:
        confs.update(
            {'bridge_mappings': agent['configurations']['bridge_mappings']})
    hostname = agent.get('host').split('.')[0]
    if hostname in result.keys():
        result[hostname]['configurations'].update(confs)
    else:
        result[hostname] = {
            'host': agent['host'],
            'configurations': confs
        }
print(json.dumps(result, indent=4))
