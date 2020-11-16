#!/usr/bin/python

import json
import os

from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient import client
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
nova = client.Client(2, session=session)

oc_servers = {server.name: server.networks['ctlplane'][0]
              for server in nova.servers.list()
              if server.networks.get('ctlplane')}
print(json.dumps(oc_servers, indent=4))
