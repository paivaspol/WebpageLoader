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
import urlparse

from time import sleep
from utils import replay_config_utils, chrome_utils, phone_connection_utils, config

WAIT = 2
TIMEOUT = int(1 * 60)
TIMEOUT_DEPENDENCY_BASELINE = 20 # 42seconds
TIMEOUT_SCREEN_RECORD = 45
MAX_TRIES = 7
MAX_LOAD_TRIES = 2

# Modes
THIRD_PARTY_SPEEDUP = 'third_party_speedup_lowerbound'
PROXY_WITHIN_REPLAY = 'proxy_within_replay'

def main(config_filename, pages, iterations, device_name, mode, output_dir):
    failed_pages = []
    completed_pages = []
    try:
        signal.signal(signal.SIGALRM, timeout_handler) # Setup the timeout handler
        device_info = config.get_device_config(device_name) # Get the information about the device.
        common_module.initialize_browser(device_info) # Start the browser
        replay_configurations = replay_config_utils.get_page_replay_config(config_filename)
        current_time = time.time()
        current_time_map = None
        if args.page_time_mapping is not None:
            current_time_map = get_page_time_mapping(args.page_time_mapping)

        page_to_tries_counter = dict()

        for page_tuple in pages:
            page = page_tuple[0]
            redirected_page = page_tuple[len(page_tuple) - 1]
            print 'Page: ' + page
            if page not in page_to_tries_counter:
                page_to_tries_counter[page] = 0
            page_to_tries_counter[page] += 1
            if page_to_tries_counter[page] > MAX_LOAD_TRIES:
                failed_pages.append(page_tuple)
                continue

            if current_time_map is not None:
                current_time = current_time_map[common_module.escape_page(page)]

            start_proxy(mode, page, current_time, replay_configurations)
            check_proxy_running_counter = 0
            while check_proxy_running_counter < MAX_TRIES and not check_proxy_running(replay_configurations, mode):
                # Keep on spinning when the proxy hasn't started yet.
                sleep(0.5)
                print 'Trying: {0}/{1}'.format(check_proxy_running_counter, MAX_TRIES)
                check_proxy_running_counter += 1
                if check_proxy_running_counter >= MAX_TRIES:
                    break

            if check_proxy_running_counter >= MAX_TRIES:
                failed_pages.append(page_tuple)
                stop_proxy(mode, page, current_time, replay_configurations)
                while not check_proxy_stopped(replay_configurations, mode):
                    sleep(1)
                print 'Stopped Proxy'
                continue

            print 'Started Proxy'
            if args.use_openvpn:
                start_vpn(device_info[2])
                sleep(2)

            if args.pac_file_location is not None:
                fetch_and_push_pac_file(args.pac_file_location, device_info)
                common_module.initialize_browser(device_info) # Restart the browser
            # Load the page.
            returned_page, timed_out_index = load_one_website(redirected_page, iterations, output_dir, device_info, mode, replay_configurations, current_time)
            if returned_page is not None:
                # There was an exception
                print 'Page: ' + returned_page + ' timed out. Appending to queue...'
                pages.append(page_tuple)
                common_module.initialize_browser(device_info) # Restart the browser
            else:
                completed_pages.append(page)

            if args.use_openvpn:
                # common_module.initialize_browser(device_info) # Restart the browser
                phone_connection_utils.bring_openvpn_connect_foreground(device_info[2])
                phone_connection_utils.toggle_openvpn_button(device_info[2])
            stop_proxy(mode, page, current_time, replay_configurations)
            while not check_proxy_stopped(replay_configurations, mode):
                sleep(0.25)
            print 'Stopped Proxy'

            # Now, fetch the server-side log if possible.
            if args.fetch_server_side_logs:
                escaped_page = common_module.escape_page(page)
                server_side_output_dir = os.path.join(output_dir, 'server_side_logs')
                if not os.path.exists(server_side_output_dir):
                    os.mkdir(server_side_output_dir)
                fetch_server_side_logs(escaped_page, server_side_output_dir)
                server_side_output_dir = os.path.join(output_dir, 'reverse_proxy_logs')
                if not os.path.exists(server_side_output_dir):
                    os.mkdir(server_side_output_dir)
                fetch_reverse_proxy_logs(escaped_page, server_side_output_dir)

            if mode == 'record' or mode == 'passthrough_proxy' or mode == THIRD_PARTY_SPEEDUP or mode == PROXY_WITHIN_REPLAY:
                sleep(3)
        if mode == 'record' or mode == 'passthrough_proxy' or mode == THIRD_PARTY_SPEEDUP or mode == PROXY_WITHIN_REPLAY:
            done(replay_configurations)

        print 'Failed pages: ' + str(failed_pages)
        output_failed_pages(output_dir, failed_pages)

    except KeyboardInterrupt as e:
        print 'Pages: ' + str(pages)
        print 'Failed pages: ' + str(failed_pages)
        print 'Completed pages: ' + str(completed_pages)
        exit(0)

def output_failed_pages(output_dir, failed_pages):
    with open(os.path.join(output_dir, 'failed_pages'), 'wb') as output_file:
        for p in failed_pages:
            if len(p) > 1:
                output_file.write(p[0] + ' ' + p[1] + '\n')
                continue
            output_file.write(p[0] + '\n')

def start_vpn(device_info):
    phone_connection_utils.bring_openvpn_connect_foreground(device_info)
    phone_connection_utils.toggle_openvpn_button(device_info)
    while not phone_connection_utils.is_connected_to_vpn(device_info):
        phone_connection_utils.toggle_openvpn_button(device_info)
        sleep(0.1)
    phone_connection_utils.bring_chrome_to_foreground(device_info)

def fetch_server_side_logs(page, output_dir):
    output_filename = os.path.join(output_dir, page)
    # command = 'scp -i ~/.ssh/vaspol_aws_key.pem ubuntu@ec2-54-159-140-131.compute-1.amazonaws.com:~/build/logs/{0} {1}'.format(page, output_dir)
    command = 'scp vaspol@apple-pi.eecs.umich.edu:/home/vaspol/Research/MobileWebOptimization/page_load_setup/build/logs/{0} {1}'.format(page, output_dir)
    subprocess.call(command, shell=True)

def fetch_reverse_proxy_logs(page, output_dir):
    output_filename = os.path.join(output_dir, page)
    # command = 'scp -i ~/.ssh/vaspol_aws_key.pem ubuntu@ec2-54-159-140-131.compute-1.amazonaws.com:~/build/logs/{0} {1}'.format(page, output_dir)
    command = 'scp vaspol@apple-pi.eecs.umich.edu:/home/vaspol/Research/MobileWebOptimization/page_load_setup/build/error-logs/{0} {1}'.format(page + '.log', output_dir)
    subprocess.call(command, shell=True)

def get_page_time_mapping(page_time_mapping_filename):
    result = dict()
    with open(page_time_mapping_filename, 'rb') as input_file:
        for raw_line in input_file:
            line = raw_line.strip().split()
            result[line[0]] = line[1]
    return result

def done(replay_configurations):
    start_proxy_url = 'http://{0}:{1}/done'.format( \
            replay_configurations[replay_config_utils.SERVER_HOSTNAME], \
            replay_configurations[replay_config_utils.SERVER_PORT])
    sleep(0.01)
    result = requests.get(start_proxy_url)
    print 'Done'

def fetch_and_push_pac_file(pac_file_location, device_config):
    wget_cmd = 'wget {0} -O temp.pac'.format(pac_file_location)
    subprocess.call(wget_cmd.split())
    phone_connection_utils.push_file(device_config[2], 'temp.pac', '/sdcard/Research/proxy.pac')
    rm_cmd = 'rm temp.pac'
    subprocess.call(rm_cmd.split())

def toogle_vpn(device_config):
    # Brings the OpenVPN Connect app to foreground and toggle the connect button.
    phone_connection_utils.bring_openvpn_connect_foreground(device_config[2])
    sleep(0.5)
    phone_connection_utils.toggle_openvpn_button(device_config[2])

def start_proxy(mode, page, time, replay_configurations, delay=0):
    '''
    Starts the proxy
    '''
    # proxy_started = check_proxy_running(replay_configurations, mode)
    proxy_started = False
    # Ensure that the proxy has started before start loading the page
    while not proxy_started:
        if mode == 'record' or mode == 'passthrough_proxy':
            server_mode = 'start_recording'
        elif mode == 'replay' or mode == 'per_packet_delay_replay':
            server_mode = 'start_proxy'
        elif mode == 'delay_replay':
            server_mode = 'start_delay_replay_proxy'
        elif mode == THIRD_PARTY_SPEEDUP:
            server_mode = 'start_third_party_speedup_proxy'
            # Make sure that we don't send the dummy page URL.
            print page
            prefix = 'apple-pi.eecs.umich.edu:8080/?dstPage='
            prefix_idx = page.find(prefix)
            if prefix_idx != -1:
                queries = urlparse.parse_qs(urlparse.urlparse(page).query)
                page = queries['dstPage'][0]
                print 'Page: ' + page

        elif mode == PROXY_WITHIN_REPLAY:
            server_mode = 'start_proxy_within_replay'

        start_proxy_url = 'http://{0}:{1}/{2}?page={3}&time={4}'.format( \
                replay_configurations[replay_config_utils.SERVER_HOSTNAME], \
                replay_configurations[replay_config_utils.SERVER_PORT], \
                server_mode, page, time)

        if mode == 'per_packet_delay_replay':
            start_proxy_url += '&replay_mode={0}'.format('per_packet_delay')
        else:
            start_proxy_url += '&replay_mode={0}'.format('regular_replay')

        if mode == 'delay_replay':
            start_proxy_url += '&delay={0}'.format(args.delay)
        if args.http_version == 1:
            start_proxy_url += '&http={0}'.format(args.http_version)

        if args.without_dependencies:
            start_proxy_url += '&dependencies=no'
        else:
            start_proxy_url += '&dependencies=yes'

        if mode == 'passthrough_proxy':
            start_proxy_url += '&storage=noop'

        print start_proxy_url
        sleep(0.01)
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
    if mode == 'record' or mode == 'passthrough_proxy':
        server_mode = 'stop_recording'
        sleep(10)
    elif mode == 'replay' or mode == 'per_packet_delay_replay':
        server_mode = 'stop_proxy'
    elif mode == 'delay_replay':
        server_mode = 'stop_delay_replay_proxy'
    elif mode == THIRD_PARTY_SPEEDUP:
        server_mode = 'stop_third_party_speedup_proxy'
    elif mode == PROXY_WITHIN_REPLAY:
        server_mode = 'stop_proxy_within_replay'

    # Try every 10 iterations
    url = 'http://{0}:{1}/{2}?page={3}&time={4}'.format( \
                replay_configurations[replay_config_utils.SERVER_HOSTNAME], \
                replay_configurations[replay_config_utils.SERVER_PORT], \
                server_mode, page, time)
    sleep(0.01)
    result = requests.get(url)
    # proxy_started = not (result.status_code == 200 and result.text.strip() == 'Proxy Stopped') \
    #         and check_proxy_running(replay_configurations, mode)
    proxy_started = not (result.status_code == 200 and result.text.strip() == 'Proxy Stopped')
    if proxy_started:
        return proxy_started
    print 'request result: ' + result.text
    sleep(2)

def load_one_website(page, iterations, output_dir, device_info, mode, replay_configurations, current_time):
    '''
    Loads one website
    '''
    for run_index in range(0, iterations):
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        iteration_path = os.path.join(output_dir, str(run_index))
        if not os.path.exists(iteration_path):
            os.mkdir(iteration_path)

        if args.start_measurements is not None and args.start_measurements == 'both':
            escaped_page = common_module.escape_page(page)
            if not os.path.exists(os.path.join(iteration_path, escaped_page)):
                os.mkdir(os.path.join(iteration_path, escaped_page))

            cpu_output_filename = os.path.join(iteration_path, escaped_page, 'cpu_measurements.txt')
            common_module.reset_cpu_measurements()
            common_module.start_tcpdump_and_cpu_measurement(device_info[0], cpu_output_filename)
        elif args.start_measurements is not None and args.start_measurements == 'tcpdump':
            common_module.start_tcpdump(device_info[0])
        elif args.start_measurements is not None and args.start_measurements == 'cpu':
            print 'Starting CPU measurements...'
            escaped_page = common_module.escape_page(page)
            if not os.path.exists(os.path.join(iteration_path, escaped_page)):
                os.mkdir(os.path.join(iteration_path, escaped_page))

            output_filename = os.path.join(iteration_path, escaped_page, 'cpu_measurements.txt')
            common_module.reset_cpu_measurements()
            common_module.start_cpu_measurements(device_info[0], output_filename)

        if args.record_screen:
            # pin Chrome to 3 cpus.
            # (1) Get all pid associated to chrome.
            # for p in pids:
                # (2) Run pin_process_to_cpu
            proc_ids = common_module.get_process_ids(device_info[0], 'chromium')
            for pid in proc_ids:
                common_module.pin_process_to_cpu(device_info[0], 7, pid)

            common_module.start_screen_recording(device_info[0])

            # pin screenrecord to 1cpu.
            proc_ids = common_module.get_process_ids(device_info[0], 'screenrecord')
            for pid in proc_ids:
                common_module.pin_process_to_cpu(device_info[0], 8, pid)

        if args.get_chromium_logs:
            clear_chromium_logs(device_info[2]['id'])

        # Second False is always start tracing.
        result = load_page(page, run_index, output_dir, args.start_measurements is not None, device_info, False, mode, replay_configurations, current_time)

        if args.start_measurements is not None and args.start_measurements == 'both':
            common_module.stop_tcpdump_and_cpu_measurement(page.strip(), device_info[0], output_dir_run=iteration_path)
        elif args.start_measurements is not None and args.start_measurements == 'tcpdump':
            common_module.stop_tcpdump(page.strip(), device_info[0], output_dir_run=iteration_path)
        elif args.start_measurements is not None and args.start_measurements == 'cpu':
            common_module.stop_cpu_measurements(page.strip(), device_info[0], output_dir_run=iteration_path)

        if args.record_screen:
            common_module.stop_screen_recording(page.strip(), device_info[0], output_dir_run=iteration_path)

        if result is not None:
            return result, run_index

        while common_module.check_previous_page_load(run_index, output_dir, page):
            clear_chromium_logs(device_info[2]['id'])
            # Second False is always start tracing.
            result = load_page(page, run_index, output_dir, False, device_info, False, mode, replay_configurations, current_time)
            if result is not None:
                return result, run_index
        chrome_utils.close_all_tabs(device_info[2])
    return None, -1

def timeout_handler(signum, frame):
    '''
    Handle the case where the page fails to load
    '''
    print 'Raised PageLoadException'
    raise PageLoadException('Time\'s up for this load.')

def check_proxy_running(config, mode):
    print 'Checking if proxy running'
    if mode == 'record' or mode == 'passthrough_proxy':
        server_check = 'is_record_proxy_running'
    elif mode == 'replay' or mode == 'per_packet_delay_replay':
        server_check = 'is_replay_proxy_running'
    elif mode == THIRD_PARTY_SPEEDUP:
        server_check = 'is_third_party_speedup_proxy_running'
    elif mode == PROXY_WITHIN_REPLAY:
        server_check = 'is_proxy_within_replay_running'

    url = 'http://{0}:{1}/{2}?http={3}'.format( \
                config[replay_config_utils.SERVER_HOSTNAME], \
                config[replay_config_utils.SERVER_PORT], \
                server_check, \
                args.http_version)

    sleep(0.01)
    result = requests.get(url)
    return parse_check_result(result.text)

def check_proxy_stopped(config, mode):
    print 'Checking if proxy running'
    if mode == 'record' or mode == THIRD_PARTY_SPEEDUP or mode == 'passthrough_proxy':
        server_check = 'is_record_proxy_running'
    elif mode == PROXY_WITHIN_REPLAY:
        server_check = 'is_proxy_within_replay_running'
    elif mode == 'replay' or mode == 'per_packet_delay_replay':
        server_check = 'is_replay_proxy_running'

    url = 'http://{0}:{1}/{2}'.format( \
                config[replay_config_utils.SERVER_HOSTNAME], \
                config[replay_config_utils.SERVER_PORT], \
                server_check)
    sleep(0.01)
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
    cmd = 'python get_chrome_messages.py {1} {2} "{0}" --output-dir {3}'.format(page, device_info[1], device_info[0], output_dir_run)
    signal.alarm(int(TIMEOUT))
    if args.get_chromium_logs:
        cmd += ' --get-chromium-logs'
    if args.get_dependency_baseline:
        signal.alarm(0)
        signal.alarm(int(TIMEOUT_DEPENDENCY_BASELINE))
        cmd += ' --get-dependency-baseline'
    if args.record_screen:
        signal.alarm(0)
        signal.alarm(int(TIMEOUT_SCREEN_RECORD))
        cmd += ' --get-dependency-baseline'
    if args.collect_console:
        cmd += ' --collect-console'
    if args.collect_tracing:
        cmd += ' --collect-tracing'
    if args.preserve_cache and run_index > 0:
        # Only preserve the cache after the cache is warmed in the first run.
        cmd += ' --preserve-cache'
    print cmd
    page_load_process = subprocess.Popen(cmd.split())

    try:
        page_load_process.communicate()
        signal.alarm(0)

        if args.get_chromium_logs:
            get_chromium_logs(run_index, output_dir, page, device_info[2]['id'])

    except PageLoadException as e:
        print 'Timeout for {0}-th load. Append to end of queue...'.format(run_index)
        print 'page_load_process: {0}'.format(page_load_process)
        signal.alarm(0)
        if page_load_process is not None:
            print 'terminating'
            page_load_process.terminate()
            if args.get_chromium_logs:
                get_chromium_logs(run_index, output_dir, page, device_info[2]['id'])
        # Kill the browser and append a page.
        if not (args.get_dependency_baseline or args.record_screen):
            stop_proxy(mode, raw_line, current_time, replay_configurations)
            try:
                chrome_utils.close_all_tabs(device_info[2])
                if not args.get_chromium_logs:
                    common_module.initialize_browser(device_info) # Start the browser
            except Exception as e:
                print 'Got exception ' + str(e) + ', but we\'ll just ignore it'
            return page
        else: # This is when we are getting the dependencies baseline
            return None
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

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('pages_filename')
    parser.add_argument('replay_config_filename')
    parser.add_argument('device_name')
    parser.add_argument('iterations', type=int)
    parser.add_argument('mode', choices=[ 'replay', 'delay_replay', 'per_packet_delay_replay', 'record', 'passthrough_proxy', THIRD_PARTY_SPEEDUP, PROXY_WITHIN_REPLAY ])
    parser.add_argument('output_dir')
    parser.add_argument('--delay', default=None)
    parser.add_argument('--http-version', default=2, type=int)
    parser.add_argument('--collect-console', default=False, action='store_true')
    parser.add_argument('--get-chromium-logs', default=False, action='store_true')
    parser.add_argument('--get-dependency-baseline', default=False, action='store_true')
    parser.add_argument('--use-openvpn', default=False, action='store_true')
    parser.add_argument('--pac-file-location', default=None)
    parser.add_argument('--page-time-mapping', default=None)
    parser.add_argument('--without-dependencies', default=False, action='store_true')
    parser.add_argument('--fetch-server-side-logs', default=False, action='store_true')
    parser.add_argument('--start-measurements', default=None, choices=[ 'tcpdump', 'cpu', 'both' ])
    parser.add_argument('--collect-tracing', default=False, action='store_true')
    parser.add_argument('--record-screen', default=False, action='store_true')
    parser.add_argument('--preserve-cache', default=False, action='store_true')
    args = parser.parse_args()
    if args.mode == 'delay_replay' and args.delay is None:
        sys.exit("Must specify delay")

    pages = common_module.get_pages_with_redirected_url(args.pages_filename)
    main(args.replay_config_filename, pages, args.iterations, args.device_name, args.mode, args.output_dir)
