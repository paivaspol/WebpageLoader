from argparse import ArgumentParser
from ConfigParser import ConfigParser

import common_module
import os
import paramiko
import replay_config_utils

MM_PROXYREPLAY = 'mm-proxyreplay'
NGHTTPX = 'nghttpx'
APACHE = 'apache'

processes_to_close = [ MM_PROXYREPLAY, NGHTTPX, APACHE ]

def start_proxy(config, page):
    print 'Starting proxy...'
    ssh_client = paramiko.SSHClient()
    private_key = paramiko.RSAKey.from_private_key_file(config[replay_config_utils.SERVER_KEY])
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=config[replay_config_utils.SERVER_HOSTNAME], \
                       username=config[replay_config_utils.SERVER_USERNAME], \
                       pkey=private_key)
    record_page_path = os.path.join(config[replay_config_utils.RECORD_PAGES_PATH], \
                                    common_module.escape_page(page))
    command = 'nohup {0} {1} {2} {3} {4} {5} &'.format( \
            config[replay_config_utils.PROXY_REPLAY_PATH], \
            record_page_path, \
            config[replay_config_utils.NGHTTPX_PATH], \
            config[replay_config_utils.NGHTTPX_PORT], \
            config[replay_config_utils.NGHTTPX_KEY_PATH], \
            config[replay_config_utils.NGHTTPX_CERT_PATH])
    stdin, stdout, stderr = ssh_client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    print 'Successfully started the proxy'
    ssh_client.close()

def stop_proxy(config):
    print 'Stopping proxy...'
    ssh_client = paramiko.SSHClient()
    private_key = paramiko.RSAKey.from_private_key_file(config[replay_config_utils.SERVER_KEY])
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect( \
            hostname=config[replay_config_utils.SERVER_HOSTNAME], \
            username=config[replay_config_utils.SERVER_USERNAME], \
            pkey=private_key)
    for process_to_close in processes_to_close:
        command = 'pkill {0}'.format(process_to_close)
        stdin, stdout, stderr = ssh_client.exec_command(command)
        channel = stdout.channel
        status = channel.recv_exit_status()
    ssh_client.close()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('config_filename')
    parser.add_argument('job', choices=['start', 'stop'])
    args = parser.parse_args()
    replay_config = replay_config_utils.get_page_replay_config(args.config_filename)
    if args.job == 'start':
        start_proxy(replay_config, args.url)
    elif args.job == 'stop':
        stop_proxy(replay_config)
