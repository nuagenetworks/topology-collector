# TODO(OPENSTACK-2892) :
#      This is temporary code for dealing with py2/py3 compatibility and have
#      unit tests pass, while the production code isn't deployed as a true
#      python package. This will be worked on in a subsequent release.
try:
    from .utils import Utils
except (ImportError, ValueError):
    from utils import Utils


class KeystoneClient(object):
    def __init__(self):
        self.client = None
        self.session = None
        self.credentials = Utils.get_os_credentials()

    def authenticate(self, init_client=True):
        from keystoneauth1.exceptions.auth import AuthorizationFailure \
            as KeyStoneAuthorizationFailure
        from keystoneauth1.identity import v2 as keystone_v2
        from keystoneauth1.identity import v3 as keystone_v3
        from keystoneauth1 import session as keystone_session

        from keystoneclient.v2_0 import client as keystone_v2_client
        from keystoneclient.v3 import client as keystone_client

        from osc_lib.exceptions import AuthorizationFailure
        from osc_lib.exceptions import Unauthorized

        try:
            if self.credentials.identity_api_version == 3:
                auth = keystone_v3.Password(
                    auth_url=self.credentials.auth_url,
                    username=self.credentials.username,
                    password=self.credentials.password,
                    project_name=self.credentials.project_name,
                    project_domain_id=self.credentials.project_domain_id,
                    project_domain_name=self.credentials.project_domain_name,
                    user_domain_id=self.credentials.user_domain_id,
                    user_domain_name=self.credentials.user_domain_name)

                self.session = keystone_session.Session(
                    auth=auth,
                    verify=(self.credentials.ca_cert if
                            self.credentials.verify_ca and self.credentials.
                            ca_cert else self.credentials.verify_ca))
                if init_client:
                    self.client = keystone_client.Client(session=self.session)
            else:
                auth = keystone_v2.Password(
                    auth_url=self.credentials.auth_url,
                    username=self.credentials.username,
                    password=self.credentials.password,
                    tenant_name=self.credentials.project_name)

                self.session = keystone_session.Session(auth=auth)
                if init_client:
                    self.client = keystone_v2_client.Client(
                        username=self.credentials.username,
                        password=self.credentials.password,
                        tenant_name=self.credentials.project_name,
                        auth_url=self.credentials.auth_url)
            return self

        except (AuthorizationFailure, KeyStoneAuthorizationFailure,
                Unauthorized) as e:
            raise EnvironmentError('Authentication failure: ' + str(e))


class NeutronClient(object):
    def __init__(self):
        self.client = None
        self.switchport_mapping_path = "/net-topology/switchport_mappings"

    def authenticate(self):
        from neutronclient.neutron import client as neutron_client
        from neutronclient.v2_0 import client as neutron_client_v2

        keystone_client = KeystoneClient().authenticate(init_client=False)
        self.client = (
            neutron_client.Client(
                api_version='2.0',
                session=keystone_client.session) if keystone_client.session
            else neutron_client_v2.Client(
                username=keystone_client.credentials.username,
                password=keystone_client.credentials.password,
                tenant_name=keystone_client.credentials.project_name,
                auth_url=keystone_client.credentials.auth_url))
        return self

    def get_switchport_mapping(self):
        return self.client.list('switchport_mappings',
                                self.switchport_mapping_path)

    def create_switchport_mapping(self, body):
        return self.client.post(self.switchport_mapping_path, body)
