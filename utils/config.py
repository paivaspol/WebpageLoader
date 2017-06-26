from collections import defaultdict

import os

# MANDATORY FIELDS
DEPENDENCY_DIR = 'dependency-dir'
RECORD_DIR = 'record-dir'
REPLAY_DIR = 'replay-dir'
DOWNLINK = 'downlink'
UPLINK = 'uplink'
RTT = 'rtt'
REPLAY_ENV_BRANCH = 'replay-env-branch'
REPLAY_SRC_DIR = 'replay-src-dir'

REPLAY_HOSTNAME = 'replay-hostname'
REPLAY_DRIVER_CONF = 'replay-driver-conf'
ITERATIONS = 'iterations'
PAGE_LIST = 'page-list'
EXPERIMENT_OUTPUT_DIR = 'experiment-output-dir'
PAGE_TO_TIMESTAMP_FILE = 'page-to-timestamp-file'
WITH_DEPENDENCIES = 'with-dependencies'
BINARY_DIR = 'binary-dir'
RECORD_SCREEN = 'record-screen'
NETWORK_BOTTLENECK = 'network-bottleneck'
PRESERVE_CACHE = 'preserve-cache'
HTTP_VERSION = 'http-version'

# OPTIONAL FIELDS
DESCRIPTION = 'description'

def parse(config_filename):
    result = defaultdict(lambda: '')
    with open(config_filename, 'rb') as input_file:
        for raw_line in input_file:
            line = raw_line.strip()
            if (line.startswith('#') or len(line) == 0 or ': ' not in line):
                continue
            line = raw_line.strip().split(': ')
            result[line[0]] = line[1]
    populate_optional_fields(result)
    return result

def populate_optional_fields(config_dict):
    optional_fields_vals = {
            PRESERVE_CACHE: 'false', 
            HTTP_VERSION: 2, 
            RECORD_SCREEN: 'false',
            NETWORK_BOTTLENECK: 'false'
         }
    for f, v in optional_fields_vals.iteritems():
        if f not in config_dict:
            config_dict[f] = v

def check_mandatory_fields(config_dict):
    keys = [ DEPENDENCY_DIR, RECORD_DIR, REPLAY_DIR, DOWNLINK, UPLINK, \
             RTT, REPLAY_HOSTNAME, REPLAY_DRIVER_CONF, ITERATIONS, PAGE_LIST, \
             EXPERIMENT_OUTPUT_DIR, PAGE_TO_TIMESTAMP_FILE, WITH_DEPENDENCIES, \
             REPLAY_ENV_BRANCH, REPLAY_SRC_DIR ]
    for k in keys:
        if k not in config_dict.keys():
            return k
    return None

def write_replay_env_config(configs):
    '''
    Writes the necessary environment configuration and 
    return the full path to the config.
    '''
    replay_env_filename = 'replay_env.conf'
    with open(replay_env_filename, 'wb') as replay_env:
        replay_env.write('[proxy_running_config]\n')
        binary_dir = configs[BINARY_DIR] if BINARY_DIR in configs else '/home/vaspol/Research/MobileWebOptimization/page_load_setup/build'
        replay_env.write('build-prefix = {0}\n'.format(binary_dir))
        replay_env.write('mm-proxyreplay = /bin/mm-proxyreplay\n')
        replay_env.write('mm-http1-proxyreplay = /bin/mm-http1-proxyreplay\n')
        replay_env.write('nghttpx_port = 3000\n')
        replay_env.write('nghttpx_key = /certs/reverse_proxy_key.pem\n')
        replay_env.write('nghttpx_cert = /certs/reverse_proxy_cert.pem\n')
        replay_env.write('mm-phone-webrecord = /bin/mm-phone-webrecord\n')
        replay_env.write('mm-delayshell-with-port-forwarded = /bin/mm-delayshell-port-forwarded\n')
        replay_env.write('squid_port = 3128\n')
        replay_env.write('openvpn_port = 1194\n')
        replay_env.write('squid = /sbin/squid\n')
        replay_env.write('start_tcpdump = True\n')
        replay_env.write('nghttpx = /bin/nghttpx\n')
        replay_env.write('\n')

        dep_dir = configs[DEPENDENCY_DIR]
        record_dir = configs[RECORD_DIR]
        replay_dir = configs[REPLAY_DIR]

        replay_env.write('dependency_directory_path = {0}\n'.format(dep_dir))
        replay_env.write('base_record_dir = {0}\n'.format(record_dir))
        replay_env.write('base_result_dir = {0}\n'.format(replay_dir))
    return os.path.join(os.getcwd(), replay_env_filename)
