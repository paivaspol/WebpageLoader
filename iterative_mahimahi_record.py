#!/home/vaspol/Research/MobileWebOptimization/scripts/venv/bin/python
from argparse import ArgumentParser
from ConfigParser import ConfigParser
from PageLoadException import PageLoadException
from collections import defaultdict

import common_module
import datetime
import paramiko
import os
import signal
import subprocess
import sys
import requests
import time

from time import sleep
from utils import replay_config_utils
from utils import chrome_utils
from utils import phone_connection_utils

WAIT = 2
TIMEOUT = int(1 * 60)
TIMEOUT_DEPENDENCY_BASELINE = int(0.5 * 60)
MAX_TRIES = 20
MAX_PAGE_TRIES = 3

def main(config_filename, pages, iterations, device_name, mode, output_dir):
    signal.signal(signal.SIGALRM, timeout_handler) # Setup the timeout handler
    device_info = common_module.get_device_config(device_name) # Get the information about the device.
    common_module.initialize_browser(device_info) # Start the browser
    replay_configurations = replay_config_utils.get_page_replay_config(config_filename)
    current_times = None
    if args.times is None:
        current_times = generate_times(iterations)
    else:
        current_times = get_times(args.times)
    print 'Recording using times: ' + str(current_times)

    failed_pages = []
    page_to_tries = defaultdict(lambda: 0)
    page_to_continue_index = defaultdict(lambda: 0)

    for page in pages:
        print 'Page: ' + page
        page_to_tries[page] += 1
        if page_to_tries[page] > MAX_PAGE_TRIES:
            failed_pages.append(page)
            continue

        start_index = page_to_continue_index[page]
        print 'start_index: ' + str(start_index)
        for run_index in range(start_index, iterations):
            current_time = current_times[run_index]
            start_proxy(mode, page, current_time, replay_configurations)
            check_proxy_running_counter = 0
            while check_proxy_running_counter < MAX_TRIES and not check_proxy_running(replay_configurations, mode):
                # Keep on spinning when the proxy hasn't started yet.
                sleep(1.5)
                print 'Trying: {0}/{1}'.format(check_proxy_running_counter, MAX_TRIES)
                check_proxy_running_counter += 1
                if check_proxy_running_counter >= MAX_TRIES:
                    break

            if check_proxy_running_counter >= MAX_TRIES:
                failed_pages.append(page)
                stop_proxy(mode, page, current_time, replay_configurations)
                while not check_proxy_stopped(replay_configurations, mode):
                    sleep(1)
                print 'Stopped Proxy'
                sleep(5) # Default shutdown wait for squid
                continue

            print 'Started Proxy'
            returned_page = load_one_website(page, run_index, output_dir, device_info, mode, replay_configurations, current_time)
            if returned_page is not None:
                # There was an exception
                pages.append(returned_page)
                page_to_continue_index[page] = run_index
                common_module.initialize_browser(device_info) # Restart the browser
                break

            stop_proxy(mode, page, current_time, replay_configurations)
            check_proxy_running_counter = 0
            while check_proxy_running_counter < MAX_TRIES and not check_proxy_stopped(replay_configurations, mode):
                sleep(1)
                if check_proxy_running_counter % 4 == 0:
                    stop_proxy(mode, page, current_time, replay_configurations)
            if check_proxy_running_counter >= MAX_TRIES:
                print 'Failed at page: ' + page
                sys.exit(1)

            print 'Stopped Proxy'
            sleep(5) # Default shutdown wait for squid
    if mode == 'record':
        done(replay_configurations)

    print 'Failed pages: ' + str(failed_pages)
    print 'Times: ' + str(current_times)

def done(replay_configurations):
    start_proxy_url = 'http://{0}:{1}/done'.format( \
            replay_configurations[replay_config_utils.SERVER_HOSTNAME], \
            replay_configurations[replay_config_utils.SERVER_PORT])
    result = requests.get(start_proxy_url)
    print 'Done'

def start_proxy(mode, page, time, replay_configurations, delay=0):
    '''
    Starts the proxy
    '''
    # proxy_started = check_proxy_running(replay_configurations, mode)
    proxy_started = False
    # Ensure that the proxy has started before start loading the page
    while not proxy_started:
        server_mode = 'start_recording'
        start_proxy_url = 'http://{0}:{1}/{2}?page={3}&time={4}'.format( \
                replay_configurations[replay_config_utils.SERVER_HOSTNAME], \
                replay_configurations[replay_config_utils.SERVER_PORT], \
                server_mode, page, time)
        
        print start_proxy_url

        if mode == 'delay_replay':
            start_proxy_url += '&delay={0}'.format(args.delay)
            if args.http_version == 1:
                start_proxy_url += '&http={0}'.format(args.http_version)

        result = requests.get(start_proxy_url)
        # proxy_started = result.status_code == 200 and result.text.strip() == 'Proxy Started' \
        #         and check_proxy_running(replay_configurations, mode)
        proxy_started = result.status_code == 200 and result.text.strip() == 'Proxy Started'
        print 'request result: ' + result.text
        if proxy_started:
            return proxy_started
        sleep(1) # Have a 1 second interval between iterations

def stop_proxy(mode, page, time, replay_configurations):
    '''
    Stops the proxy
    '''
    server_mode = 'stop_recording'

    # Try every 10 iterations
    url = 'http://{0}:{1}/{2}?page={3}&time={4}'.format( \
                replay_configurations[replay_config_utils.SERVER_HOSTNAME], \
                replay_configurations[replay_config_utils.SERVER_PORT], \
                server_mode, page, time)
    result = requests.get(url)
    # proxy_started = not (result.status_code == 200 and result.text.strip() == 'Proxy Stopped') \
    #         and check_proxy_running(replay_configurations, mode)
    proxy_started = not (result.status_code == 200 and result.text.strip() == 'Proxy Stopped')
    if proxy_started:
        return proxy_started
    print 'request result: ' + result.text
    sleep(10)

def load_one_website(page, run_index, output_dir, device_info, mode, replay_configurations, current_time):
    '''
    Loads one website
    '''
    if args.get_chromium_logs:
        clear_chromium_logs(device_info[2]['id'])

    retval = load_page(page, run_index, output_dir, False, device_info, not args.start_tracing, mode, replay_configurations, current_time)
    if retval is not None:
        return retval

    while common_module.check_previous_page_load(run_index, output_dir, page):
        clear_chromium_logs(device_info[2]['id'])
        result = load_page(page, run_index, output_dir, False, device_info, not args.start_tracing, mode, replay_configurations, current_time)
        if result is not None:
            return result
    return None

def timeout_handler(signum, frame):
    '''
    Handle the case where the page fails to load
    '''
    print 'Raised PageLoadException'
    raise PageLoadException('Time\'s up for this load.')

def check_proxy_running(config, mode):
    print 'Checking if proxy running'
    if mode == 'record':
        server_check = 'is_record_proxy_running'
    elif mode == 'replay':
        server_check = 'is_replay_proxy_running'

    url = 'http://{0}:{1}/{2}'.format( \
                config[replay_config_utils.SERVER_HOSTNAME], \
                config[replay_config_utils.SERVER_PORT], \
                server_check)
    result = requests.get(url)
    return parse_check_result(result.text)

def check_proxy_stopped(config, mode):
    print 'Checking if proxy running'
    if mode == 'record':
        server_check = 'is_record_proxy_running'
    elif mode == 'replay':
        server_check = 'is_replay_proxy_running'

    url = 'http://{0}:{1}/{2}'.format( \
                config[replay_config_utils.SERVER_HOSTNAME], \
                config[replay_config_utils.SERVER_PORT], \
                server_check)
    result = requests.get(url)
    return parse_check_result(result.text, 'stopped')

def parse_check_result(result_str, mode='running'):
    '''
    Parses the results.
    '''
    print result_str
    splitted_result_str = result_str.split('\n')
    for line in splitted_result_str:
        splitted_line = line.split(' ')
        if mode == 'running' and splitted_line[1] == 'NO':
            return False
        elif mode == 'stopped' and splitted_line[1] == 'YES':
            return False
    return True

def load_page(raw_line, run_index, output_dir, start_measurements, device_info, disable_tracing, mode, replay_configurations, current_time):
    page_load_process = None
    # Create necessary directories
    base_output_dir = output_dir
    if not os.path.exists(base_output_dir):
        os.mkdir(base_output_dir)
    output_dir_run = os.path.join(base_output_dir, str(run_index))
    if not os.path.exists(output_dir_run):
        os.mkdir(output_dir_run)
    
    page = raw_line.strip()
    cmd = 'python get_chrome_messages.py {1} {2} {0} --output-dir {3}'.format(page, device_info[1], device_info[0], output_dir_run) 
    signal.alarm(TIMEOUT)
    if disable_tracing:
        cmd += ' --disable-tracing'
    if args.collect_streaming:
        cmd += ' --collect-streaming'
    if args.get_chromium_logs:
        cmd += ' --get-chromium-logs'
    if args.get_dependency_baseline:
        signal.alarm(0)
        signal.alarm(int(TIMEOUT_DEPENDENCY_BASELINE))
        cmd += ' --get-dependency-baseline'
    # if run_index > 0:
    #     cmd += ' --reload-page'
    print cmd
    page_load_process = subprocess.Popen(cmd.split())

    try:
        page_load_process.communicate()
        signal.alarm(0)
    except PageLoadException as e:
        print 'Timeout for {0}-th load. Append to end of queue...'.format(run_index)
        signal.alarm(0)
        if page_load_process is not None:
            print 'terminating'
            page_load_process.terminate()
            if args.get_chromium_logs:
                get_chromium_logs(run_index, output_dir, page, device_info[2]['id'])
        # Kill the browser and append a page.
        if not args.get_dependency_baseline:
            stop_proxy(mode, raw_line, current_time, replay_configurations)
        chrome_utils.close_all_tabs(device_info[2])
        if not args.get_chromium_logs:
            common_module.initialize_browser(device_info) # Start the browser
        return page
    return None

def clear_chromium_logs(device_id):
    cmd = 'adb -s {0} logcat -c'.format(device_id)
    subprocess.call(cmd.split())

def get_chromium_logs(run_index, output_dir, page_url, device_id):
    log_lines = []
    cmd = 'adb -s {0} logcat chromium:I'.format(device_id)
    adb_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    ms_since_epoch = common_module.get_start_end_time(run_index, output_dir, page_url)[1] if not args.get_dependency_baseline else time.time() * 1000
    if ms_since_epoch != -1:
        while True:
            line = adb_process.stdout.readline()
            log_line = line.strip().split()
            log_lines.append(line)
            timestamp = '2016-' + log_line[0] + ' ' + log_line[1]
            # 07-12 10:50:01.674 10179 10237 I chromium: [INFO:spdy_stream.cc(128)] Started a SPDY stream.
            try:
                date_object = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
                date_since_epoch = int(date_object.strftime('%s')) * 1000
                if int(date_since_epoch) > int(ms_since_epoch):
                    adb_process.terminate()
                    break
            except Exception as e:
                pass
        output_filename = os.path.join(output_dir, str(run_index), common_module.escape_page(page_url.strip()), 'chromium_log.txt')
        with open(output_filename, 'wb') as output_file:
            for log_line in log_lines:
                output_file.write(log_line)

def generate_times(num_iterations):
    result = []
    for i in range(0, num_iterations):
        print 'Generating time {0}'.format(i)
        result.append(time.time())
        sleep(3)

    return result

def get_times(times_filename):
    with open(times_filename, 'rb') as input_file:
        return [ line.strip() for line in input_file ]

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('pages_filename')
    parser.add_argument('replay_config_filename')
    parser.add_argument('device_name')
    parser.add_argument('iterations', type=int)
    parser.add_argument('mode', choices=[ 'record' ])
    parser.add_argument('output_dir')
    parser.add_argument('--times', default=None)
    parser.add_argument('--delay', default=None)
    parser.add_argument('--http-version', default=2, type=int)
    parser.add_argument('--start-tracing', default=False, action='store_true')
    parser.add_argument('--collect-streaming', default=False, action='store_true')
    parser.add_argument('--get-chromium-logs', default=False, action='store_true')
    parser.add_argument('--get-dependency-baseline', default=False, action='store_true')
    parser.add_argument('--use-openvpn', default=False, action='store_true')
    parser.add_argument('--pac-file-location', default=None)
    args = parser.parse_args()
    if args.mode == 'delay_replay' and args.delay is None:
        sys.exit("Must specify delay")
    pages = common_module.get_pages(args.pages_filename)
    main(args.replay_config_filename, pages, args.iterations, args.device_name, args.mode, args.output_dir)
