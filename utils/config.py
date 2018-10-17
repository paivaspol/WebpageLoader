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
REPLAY_MODE = 'replay-mode'
DEVICE = 'device'

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
            NETWORK_BOTTLENECK: 'false',
            REPLAY_MODE: 'per_packet_delay_replay',
            DEVICE: 'Nexus_6'
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
        replay_env.write('mm-http1-replay-no-proxy = /bin/mm-http1-proxyreplay-no-proxy\n')
        replay_env.write('nghttpx_port = 3000\n')
        replay_env.write('nghttpx_key = /certs/reverse_proxy_key.pem\n')
        replay_env.write('nghttpx_cert = /certs/reverse_proxy_cert.pem\n')
        replay_env.write('mm-phone-webrecord = /bin/mm-phone-webrecord\n')
        replay_env.write('mm-third-party-speedup-proxy = /bin/mm-serialized-phone-webrecord-using-vpn\n')
        replay_env.write('mm-delayshell-with-port-forwarded = /bin/mm-delayshell-port-forwarded\n')
        replay_env.write('mm-proxy-within-replay = /bin/mm-proxy-in-replay\n')
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
        replay_env.write('third_party_speedup_prefetch_dir_path = {0}\n'.format(dep_dir))
        # replay_env.write('third_party_speedup_prefetch_dir_path = {0}/home/vaspol/Research/MobileWebOptimization/third_party_accelerate/prefetch_resources/02_21\n')
        replay_env.write('base_record_dir = {0}\n'.format(record_dir))
        replay_env.write('base_result_dir = {0}\n'.format(replay_dir))
    return os.path.join(os.getcwd(), replay_env_filename)


##########################################
# Device Configurations
##########################################
from ConfigParser import ConfigParser

ADB_PORT = 'adb_port'
CHROME_DESKTOP_DEBUG_PORT = 'chrome_desktop_debugging_port'
CHROME_INSTANCE = 'chrome_instance'
DEVICE_ID = 'id'
DEVICE_TYPE = 'type'
IP = 'ip'
USE_CHROMIUM = 'use_chromium'
USER_DATA_DIR = 'user_data_dir'
WEB_SOCKET_DEBUGGER_URL = 'webSocketDebuggerUrl'

DEVICE_PHONE = 'phone'
DEVICE_MAC = 'mac'
DEVICE_UBUNTU = 'ubuntu'

CHROME_RUNNING_MODE = 'mode'
EXTENSION = 'extension'
IGNORE_CERTIFICATE_ERRORS = 'ignore_certificate_errors'
PAC_FILE_PATH = 'pac_file_path'
SCREEN_SIZE = 'screen_size'
USER_AGENT = 'user_agent'
CHROME_BINARY = 'chrome_bin'
EMULATING_DEVICE = 'emulating_device'
NETWORK = 'network'

# Hardcoded values for the Chrome instances.
ANDROID_CHROME_INSTANCE = 'com.android.chrome/com.google.android.apps.chrome.Main'
ANDROID_CHROMIUM_INSTANCE = 'org.chromium.chrome/com.google.android.apps.chrome.Main'
MAC_CHROME_INSTANCE = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
UBUNTU_CHROME_INSTANCE = '/opt/google/chrome/google-chrome'

def get_device_configuration(config_reader, device):
    '''
    Constructs a device configuration map.
    '''
    def get_config(config_reader, section, key, default):
        '''
        Returns the string if the key exists in the config_reader_obj otherwise returns default value specified.
        '''
        if config_reader.has_option(section, key):
            return config_reader.get(section, key)
        return default

    def populate_if_exists(device_config, config_reader, section, key):
        '''
        Populates device_config with the value in the config_reader if the key exists.
        '''
        if config_reader.has_option(section, key):
            device_config[key] = config_reader.get(section, key)


    def extract_kv_config(device_config, config_reader, section, key):
        '''
        Extracts the key value configurations.
        '''
        configs = config_reader.get(section, key).split('$')
        config_dict = dict()
        for config in configs:
            key, value = config.split("=")
            config_dict[key] = value
        return config_dict


    device_config = dict()
    device_config[IP] = config_reader.get(device, IP)
    device_type = config_reader.get(device, DEVICE_TYPE)
    device_config[DEVICE_TYPE] = device_type
    if device_type == DEVICE_PHONE:
        device_config[ADB_PORT] = int(config_reader.get(device, ADB_PORT))
        device_config[CHROME_INSTANCE] = ANDROID_CHROMIUM_INSTANCE if config_reader.get(device, USE_CHROMIUM) == 'True' else ANDROID_CHROME_INSTANCE
        device_config[DEVICE_ID] = config_reader.get(device, DEVICE_ID)

    elif device_type == DEVICE_MAC:
        device_config[CHROME_DESKTOP_DEBUG_PORT] = int(config_reader.get(device, CHROME_DESKTOP_DEBUG_PORT))
        device_config[CHROME_INSTANCE] = get_config(config_reader, device, CHROME_BINARY, MAC_CHROME_INSTANCE)
        device_config[EMULATING_DEVICE] = { USER_AGENT: get_config(config_reader, device, USER_AGENT, None) }
        populate_if_exists(device_config, config_reader, device, PAC_FILE_PATH)

    elif device_type == DEVICE_UBUNTU:
        device_config[CHROME_DESKTOP_DEBUG_PORT] = int(config_reader.get(device, CHROME_DESKTOP_DEBUG_PORT))
        device_config[CHROME_INSTANCE] = get_config(config_reader, device, CHROME_BINARY, UBUNTU_CHROME_INSTANCE)
        populate_if_exists(device_config, config_reader, device, PAC_FILE_PATH)
        populate_if_exists(device_config, config_reader, device, IGNORE_CERTIFICATE_ERRORS)
        populate_if_exists(device_config, config_reader, device, EXTENSION)
        device_config[USER_DATA_DIR] = get_config(config_reader, device, USER_DATA_DIR, 'random')
        device_config[CHROME_RUNNING_MODE] = get_config(config_reader, device, CHROME_RUNNING_MODE, 'headless')

        device_config[EMULATING_DEVICE] = { USER_AGENT: get_config(config_reader, device, USER_AGENT, None) } 
        if config_reader.has_option(device, SCREEN_SIZE):
            screen_config_dict = extract_kv_config(device_config, config_reader, device, SCREEN_SIZE)
            device_config[EMULATING_DEVICE].update(screen_config_dict)
        if config_reader.has_option(device, NETWORK):
            device_config[NETWORK] = extract_kv_config(device_config, config_reader, device, NETWORK)

    return device_config
