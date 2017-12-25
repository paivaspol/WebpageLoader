#! /usr/bin/env python
from argparse import ArgumentParser
from ConfigParser import RawConfigParser

import common_module

import os
import signal
import subprocess
import sys
import time

from utils import config as config_util
from utils import script_runner
from utils import phone_connection_utils as pcu

REPLAY_ENV_PATH = os.path.join('/home/vaspol/Research/MobileWebOptimization/page_load_setup/mahimahi/proxy_running_scripts', 'run_mahimahi_proxy.py')

RUN_LOG_FILENAME = 'experiment_run_log'
OK = 'OK'
FAILED = 'FAILED'

started_processes = [ ]

def run_experiment(config_filename):
    global started_processes

    config = config_util.parse(config_filename)
    missing_key = config_util.check_mandatory_fields(config)
    if missing_key is not None:
        reason = 'Missing key {0} in config file'.format(missing_key)
        write_experiment_status(config_filename, FAILED, reason)
        return
    setup_signal_handlers()

    # Setup traffic throttling.
    if config[config_util.DOWNLINK] == 'inf' or \
        config[config_util.UPLINK] == 'inf' or \
        config[config_util.RTT] == 'inf':
        script_runner.clear_traffic_shaping()
    else:
        script_runner.shape_traffic(config[config_util.DOWNLINK], \
                                    config[config_util.UPLINK], \
                                    config[config_util.RTT])

    # Build the replay environment
    script_runner.build_replay_env(config[config_util.REPLAY_SRC_DIR], config[config_util.REPLAY_ENV_BRANCH])

    # Run the replay environment.
    replay_env_proc = run_replay_environment(config)
    started_processes.append(replay_env_proc)

    # Run the reply driver and wait for it to finish.
    # python mahimahi_page_script.py page_list/next_news_and_sports_with_redirection.txt $CONFIG_FILENAME Nexus_6_2_chromium ${NUM_ITERATIONS} per_packet_delay_replay ../results/vroom_debugging/next_news_and_sports_vroom --use-openvpn --pac-file-location http://${REPLAY_HOSTNAME}/config_testing.pac --page-time-mapping page_to_timestamp_next_news_sports.txt --fetch-server-side-logs --start-measurements both --collect-tracing
    replay_driver_proc = run_replay_driver(config)
    started_processes.append(replay_driver_proc)
    replay_driver_proc.wait()

    # cleanup
    cleanup()

    populate_metadata(config_filename, config)
    write_experiment_status(config_filename, OK)
    ship_data(config[config_util.EXPERIMENT_OUTPUT_DIR])

def ship_data(exp_output_dir):
    dst = 'vault:/mnt/z/home/vaspol/MobileWebOptimization/results/fresh_experiments/'
    command = 'scp -q -r {0} {1}'.format(exp_output_dir, dst)
    subprocess.call(command.split())

def write_experiment_status(config_filename, status, reason=''):
    with open(RUN_LOG_FILENAME, 'ab') as output_file:
        status_line = '{0} STATUS: {1}'.format(config_filename, status)
        if status != OK:
            status_line += ' reason: ' + reason
        output_file.write(status_line + '\n')

def run_replay_environment(config):
    # First, write the necessary replay env configs.
    binary_dir = config[config_util.BINARY_DIR] if config_util.BINARY_DIR in config else '/home/vaspol/Research/MobileWebOptimization/page_load_setup/build'
    replay_env_conf_path = config_util.write_replay_env_config(config)

    # Start the replay environment as a daemon on one process.
    proc = subprocess.Popen('python {0} {1} {2}'.format(REPLAY_ENV_PATH, replay_env_conf_path, 5005), shell=True, preexec_fn=os.setsid)
    return proc

def populate_metadata(config_filename, config):
    experiment_output_dir = config[config_util.EXPERIMENT_OUTPUT_DIR]
    description = config[config_util.DESCRIPTION]
    output_description(experiment_output_dir, description)

    subprocess.call('cp {0} {1}'.format(config_filename, os.path.join(experiment_output_dir, 'configuration')), shell=True)

def run_replay_driver(config):
    experiment_output_dir = config[config_util.EXPERIMENT_OUTPUT_DIR]
    page_list = config[config_util.PAGE_LIST]
    if args.load_failed_pages:
        page_list = os.path.join(experiment_output_dir, 'failed_pages')
    iterations = config[config_util.ITERATIONS]
    replay_hostname = config[config_util.REPLAY_HOSTNAME]
    replay_driver_conf = config[config_util.REPLAY_DRIVER_CONF]
    page_to_timestamp = config[config_util.PAGE_TO_TIMESTAMP_FILE]
    with_dependencies = config[config_util.WITH_DEPENDENCIES]
    record_screen = config[config_util.RECORD_SCREEN]
    network_bottleneck = config[config_util.NETWORK_BOTTLENECK]
    preserve_cache = config[config_util.PRESERVE_CACHE]
    http_version = config[config_util.HTTP_VERSION]
    use_proxy = config[config_util.USE_PROXY]
    device = config[config_util.DEVICE]

    js_to_run = None
    if config_util.JS_ONLOAD in config:
        js_to_run = config[config_util.JS_ONLOAD]

    command = 'python mahimahi_page_script.py {0} {1} {7} {2} per_packet_delay_replay {3} --use-openvpn --pac-file-location http://{4}/config_testing.pac --page-time-mapping {5} --http-version {6} --fetch-server-side-logs --start-measurements both --collect-tracing --collect-console'.format(page_list, replay_driver_conf, iterations, experiment_output_dir, replay_hostname, page_to_timestamp, http_version, device)
    if with_dependencies != 'true':
        command += ' --without-dependencies'
    if record_screen == 'true':
        command += ' --record-screen'
    if network_bottleneck == 'true':
        command += ' --get-dependency-baseline'
    if preserve_cache == 'true':
        command += ' --preserve-cache'
    if js_to_run is not None:
        command += ' --execute-script-onload="{0}"'.format(js_to_run)
    if use_proxy == 'false':
        command += ' --no-proxy'
    proc = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
    return proc

def output_description(experiment_output_dir, description):
    if not os.path.exists(experiment_output_dir):
        os.mkdir(experiment_output_dir)

    with open(os.path.join(experiment_output_dir, 'README'), 'wb') as output_file:
        output_file.write(description)

def get_jobs(config_file_list):
    result = []
    with open(config_file_list, 'rb') as input_file:
        for l in input_file:
            if l.startswith('#') or len(l.strip()) == 0:
                continue
            result.append(l.strip())
    return result

def signal_handler(signum, frame):
    print 'here'
    cleanup()
    sys.exit(0)

def setup_signal_handlers():
    # Setup SIGTERM handler
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def cleanup():
    # Kill all the processes we started.
    global started_processes
    for p in started_processes:
        while p.poll() is None:
            p.kill()
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            time.sleep(.5)
    started_processes = [ ]

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('config_file_list')
    parser.add_argument('--load-failed-pages', default=False, action='store_true')
    args = parser.parse_args()
    if os.path.exists(RUN_LOG_FILENAME):
        os.remove(RUN_LOG_FILENAME)
    jobs = get_jobs(args.config_file_list) # Each config file is one experiment
    print 'Jobs: ' + str(jobs)
    for job in jobs:
        run_experiment(job)
        time.sleep(7) # Sleep for 7s before moving on to the next job.
