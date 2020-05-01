import os
import yaml

NUAGE_TC_PATH = '/opt/nuage/topology-collector/nuage_topology_collector'


def get_env_variable(variable):
    USER_VARS = os.path.join(NUAGE_TC_PATH, "user_vars.yml")
    defaults = {
        'output_dir': '/tmp/topo-coll/reports',
        'output_file_prefix': 'topo_report',
        'undercloud_env_file': str(os.getenv('HOME')) + '/stackrc',
        'osc_env_file': str(os.getenv('HOME')) + '/overcloudrc'
    }
    if os.path.exists(USER_VARS):
        with open(USER_VARS, 'r') as stream:
            try:
                extra_vars = yaml.safe_load(stream)
                if extra_vars.get(variable) and len(extra_vars[variable]) > 0:
                    return extra_vars[variable]
            except Exception:
                pass
    return defaults[variable]


STACK_USER = 'stack'
STACKRC_FILE = get_env_variable('undercloud_env_file')
OVERCLOUDRC_FILE = get_env_variable('osc_env_file')
OUTPUT_DIR = get_env_variable('output_dir')
OUTPUT_FILE_PREFIX = get_env_variable('output_file_prefix')
