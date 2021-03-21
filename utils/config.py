from collections import defaultdict

import os

# Default section
SECTION_DEFAULT = 'default'

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
BASE_CONFIG = 'base_config'

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
ADDITIONAL_ARGS = 'additional_args'
CPU_THROTTLE_RATE = 'cpu_throttle_rate'
PER_SITE_CPU_THROTTLING_FILE = 'cpu_throttle_map_file'

# Hardcoded values for the Chrome instances.
ANDROID_CHROME_INSTANCE = 'com.android.chrome/com.google.android.apps.chrome.Main'
ANDROID_CHROMIUM_INSTANCE = 'org.chromium.chrome/com.google.android.apps.chrome.Main'
MAC_CHROME_INSTANCE = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
UBUNTU_CHROME_INSTANCE = '/opt/google/chrome/google-chrome'
# UBUNTU_CHROME_INSTANCE = '/usr/bin/chromium-browser'

def get_device_configuration(config_reader, device):
    '''
    Constructs a device configuration map.
    '''
    print('Getting config for ' + device)
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

    def extract_list_config(device_config, config_reader, section, key):
        '''
        Extracts the values and returns a list corresponding to the values.
        '''
        configs = config_reader.get(section, key).split('$')
        result = []
        for config in configs:
            result.append(config)
        return result

    device_config = dict()
    device_config[IP] = config_reader.get(SECTION_DEFAULT, IP)
    device_type = config_reader.get(SECTION_DEFAULT, DEVICE_TYPE)
    device_config[DEVICE_TYPE] = device_type

    if device_type == DEVICE_PHONE:
        device_config[ADB_PORT] = int(config_reader.get(device, ADB_PORT))
        device_config[CHROME_INSTANCE] = ANDROID_CHROMIUM_INSTANCE if config_reader.get(device, USE_CHROMIUM) == 'True' else ANDROID_CHROME_INSTANCE
        device_config[DEVICE_ID] = config_reader.get(device, DEVICE_ID)

    elif device_type == DEVICE_UBUNTU:
        # Pull mandatory fields.
        device_config[CHROME_DESKTOP_DEBUG_PORT] = int(config_reader.get(SECTION_DEFAULT, CHROME_DESKTOP_DEBUG_PORT))
        default_chrome_binary = config_reader.get(SECTION_DEFAULT, CHROME_BINARY)
        device_config[CHROME_INSTANCE] = get_config(config_reader, device, CHROME_BINARY, default_chrome_binary)
        populate_if_exists(device_config, config_reader, SECTION_DEFAULT, PAC_FILE_PATH)
        populate_if_exists(device_config, config_reader, SECTION_DEFAULT, IGNORE_CERTIFICATE_ERRORS)
        populate_if_exists(device_config, config_reader, SECTION_DEFAULT, EXTENSION)
        device_config[USER_DATA_DIR] = get_config(config_reader, SECTION_DEFAULT, USER_DATA_DIR, 'random')
        if config_reader.has_option(SECTION_DEFAULT, ADDITIONAL_ARGS):
            device_config[ADDITIONAL_ARGS] = extract_list_config(device_config, config_reader, SECTION_DEFAULT, ADDITIONAL_ARGS)

        # Pull per-device fields. For the experiment setup.
        base_config = config_reader.get(device, BASE_CONFIG)
        device_config[CHROME_RUNNING_MODE] = get_config(config_reader, base_config, CHROME_RUNNING_MODE, 'headless')
        # Try to populate CPU throttling with base config first. Otherwise, try with device.
        populate_if_exists(device_config, config_reader, base_config,
                CPU_THROTTLE_RATE)
        populate_if_exists(device_config, config_reader, device,
                CPU_THROTTLE_RATE)
        populate_if_exists(device_config, config_reader, device,
                PER_SITE_CPU_THROTTLING_FILE)

        # populate CPU throttling.
        # TODO: populate as a map with the overall as * instead of per site.
        if PER_SITE_CPU_THROTTLING_FILE in device_config:
            per_site_cpu_throttling_map = generate_per_site_cpu_throttling(device_config[PER_SITE_CPU_THROTTLING_FILE])
        elif CPU_THROTTLE_RATE in device_config:
            per_site_cpu_throttling_map = { '*': device_config[CPU_THROTTLE_RATE] }
        else:
            per_site_cpu_throttling_map = { '*': '1' }
        device_config[CPU_THROTTLE_RATE] = per_site_cpu_throttling_map

        device_config[EMULATING_DEVICE] = { USER_AGENT: get_config(config_reader, base_config, USER_AGENT, None) } 
        if config_reader.has_option(base_config, SCREEN_SIZE):
            screen_config_dict = extract_kv_config(device_config, config_reader, base_config, SCREEN_SIZE)
            device_config[EMULATING_DEVICE].update(screen_config_dict)
        if config_reader.has_option(device, NETWORK):
            device_config[NETWORK] = extract_kv_config(device_config, config_reader, device, NETWORK)
    else:
        raise RuntimeError('DeviceNotSupported: ' + device_type + ' is not supported.')
    print(device_config)
    return device_config

def generate_per_site_cpu_throttling(per_site_input_filename):
    retval = {}
    with open(per_site_input_filename, 'r') as input_file:
        for l in input_file:
            l = l.strip().split(' ')
            retval[l[0]] = int(round(float(l[1])))
    return retval
