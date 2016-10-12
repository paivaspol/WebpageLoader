from ConfigParser import ConfigParser

CONFIG = 'config'

# Proxy Variables
PROXY_REPLAY_PATH = 'proxy_replay_path'
NGHTTPX_PATH = 'nghttpx_path'
NGHTTPX_PORT = 'nghttpx_port'
NGHTTPX_KEY_PATH = 'nghttpx_key_path'
NGHTTPX_CERT_PATH = 'nghttpx_cert_path'
RECORD_PAGES_PATH = 'record_pages_path'

# Local Variables
SERVER_KEY = 'server_key'
SERVER_HOSTNAME = 'server_hostname'
SERVER_USERNAME = 'server_username'
SERVER_PORT = 'server_port'

CONFIG_KEYS = [ SERVER_HOSTNAME, SERVER_PORT ]

def get_page_replay_config(config_filename):
    configuration = dict()
    config_parser = ConfigParser()
    config_parser.read(config_filename)
    for config_key in CONFIG_KEYS:
        configuration[config_key] = config_parser.get(CONFIG, config_key)
    return configuration

