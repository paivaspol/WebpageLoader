from ConfigParser import ConfigParser
from utils import phone_connection_utils
from utils import chrome_utils

import requests
import os
import subprocess

import time
import threading

def convert_to_ms_precision(timestamp):
    '''
    Converts the timestamp to millisecond precision.
    '''
    return timestamp * 1000

def extract_url_from_path(path):
    '''
    Extracts the url from the path.
    '''
    if path.endswith('/'):
        path = path[:len(path) - 1]
    last_delim_index = -1
    for i in range(0, len(path)):
        if path[i] == '/':
            last_delim_index = i
    url = path[last_delim_index + 1:].replace('/', '_')
    return url

HTTP_PREFIX = 'http://'
HTTPS_PREFIX = 'https://'
WWW_PREFIX = 'www.'
def escape_page(url):
    if url.endswith('/'):
        url = url[:len(url) - 1]
    if url.startswith(HTTPS_PREFIX):
        url = url[len(HTTPS_PREFIX):]
    elif url.startswith(HTTP_PREFIX):
        url = url[len(HTTP_PREFIX):]
    if url.startswith(WWW_PREFIX):
        url = url[len(WWW_PREFIX):]
    return url.replace('/', '_')


def parse_pages_to_ignore(pages_to_ignore_filename):
    pages = set()
    if pages_to_ignore_filename is not None:
        with open(pages_to_ignore_filename, 'rb') as input_file:
            for raw_line in input_file:
                line = raw_line.strip()
                pages.add(escape_page(line))
    print pages
    return pages

def parse_page_start_end_time(filename):
    with open(filename, 'r') as input_file:
        line = input_file.readline().strip().split()
        web_perf_nav_start = float(line[1])
        web_perf_load_event = float(line[2])
        chrome_ts_nav_start = float(line[3])
        chrome_ts_load_event = float(line[4])
        return (line[0], (web_perf_nav_start, web_perf_load_event), (chrome_ts_nav_start, chrome_ts_load_event))

# Available devices to use.
DEVICES = {
        # Mobile devices
        'Nexus_6': '/device_config/nexus6.cfg',
        'Nexus_6_chromium': '/device_config/nexus6_chromium.cfg',
        'Nexus_6_2': '/device_config/nexus6_2.cfg',
        'Nexus_6_2_chromium': '/device_config/nexus6_2_chromium.cfg',
        'Nexus_5': '/device_config/nexus5.cfg',
        'pixel2': '/device_config/pixel2.cfg',
        'samsung_s8': '/device_config/samsung_s8.cfg',

        # Desktop devices
        'ubuntu': '/device_config/ubuntu.cfg',
        'ubuntu_emulate_nexus5': '/device_config/ubuntu_emulate_nexus5.cfg',
        'ubuntu_emulate_nexus5_second_instance': '/device_config/ubuntu_emulate_nexus5_second_instance.cfg',
        'ubuntu_with_cookies': '/device_config/ubuntu_with_cookies.cfg',
        'mac': '/device_config/mac.cfg',
}

def get_device_config_path(device_name, current_path='.'):
    '''
    Returns the path to the config of the device.

    If the device does not exists, the script will terminate.
    '''
    return './device_config/desktop_replay.cfg'
    # if device_name in DEVICES:
    #     return current_path + DEVICES[device_name]
    # print 'available devices: {0}'.format(str([ d for d in DEVICES.keys() ]))
    # exit()

def get_device_config(device, running_path='.'):
    from utils import config

    device_config_filename = ''
    device_config_object = None
    device_config_filename = get_device_config_path(device, running_path)

    config_reader = ConfigParser()
    config_reader.read(device_config_filename)
    device_config_obj = config.get_device_configuration(config_reader, device)

    return device, device_config_filename, device_config_obj

def initialize_browser(device_info):
    # Get the device configuration
    print 'initializing browser...'
    phone_connection_utils.wake_phone_up(device_info[2])
    print 'Stopping Chrome...'
    phone_connection_utils.stop_chrome(device_info[2])
    print 'Starting Chrome...'
    phone_connection_utils.start_chrome(device_info[2])
    closed_tabs = False
    while not closed_tabs:
        try:
            chrome_utils.close_all_tabs(device_info[2])
            closed_tabs = True
        except requests.exceptions.ConnectionError as e:
            pass
    chrome_utils.create_tab(device_info[2])

def check_previous_page_load(current_run_index, base_output_dir, raw_line):
    if current_run_index > 0:
        url = escape_page(raw_line.strip())
        output_dir_prev_run = os.path.join(os.path.join(base_output_dir, str(current_run_index - 1)), url)
        prev_run_start_end_time = os.path.join(output_dir_prev_run, 'start_end_time_' + url)
        output_dir_cur_run = os.path.join(os.path.join(base_output_dir, str(current_run_index)), url)
        cur_run_start_end_time = os.path.join(output_dir_cur_run, 'start_end_time_' + url)
        if not os.path.exists(prev_run_start_end_time) or not os.path.exists(cur_run_start_end_time):
            return False
        with open(prev_run_start_end_time, 'rb') as input_file:
            prev_line = input_file.readline()
        with open(cur_run_start_end_time, 'rb') as input_file:
            cur_line = input_file.readline()
        return prev_line == cur_line
    return False

def get_start_end_time(current_run_index, base_output_dir, page_url):
    url = escape_page(page_url.strip())
    output_dir_cur_run = os.path.join(os.path.join(base_output_dir, str(current_run_index)), url)
    cur_run_start_end_time = os.path.join(output_dir_cur_run, 'start_end_time_' + url)
    if not os.path.exists(cur_run_start_end_time):
        return -1, -1

    with open(cur_run_start_end_time, 'rb') as input_file:
        cur_line = input_file.readline().strip().split()
        start_time = int(cur_line[1])
        end_time = int(cur_line[2])
    return start_time, end_time

# def get_pages(pages_file):
#     pages = []
#     with open(pages_file, 'rb') as input_file:
#         for raw_line in input_file:
#             line = raw_line.strip()
#             if line.startswith('#') or len(line) == 0:
#                 continue
#             line = raw_line.strip().split()
#             pages.append(line[len(line) - 1])
#     return pages

# def get_pages_with_redirected_url(pages_file):
def get_pages(pages_file):
    pages = []
    with open(pages_file, 'rb') as input_file:
        for raw_line in input_file:
            line = raw_line.strip().split()
            if raw_line.startswith('#') or len(line) == 0 or len(line) > 2:
                # We assume that the pages file only have 2 tokens:
                # orignal_url redirection_url.
                continue
            pages.append(line)
    return pages

current_timer = None
stopped_cpu_measurements = False

def reset_cpu_measurements():
    global stopped_cpu_measurements
    stopped_cpu_measurements = False

def start_cpu_measurements(device, output_file, running_path='.'):
    device, device_config, device_config_obj = get_device_config(device, running_path=running_path)
    # start_cpu_measurement_command = 'python ./utils/start_cpu_measurement.py {0} {1}'.format(device_config, device)
    # print 'Executing: ' + start_cpu_measurement_command
    # subprocess.Popen(start_cpu_measurement_command, shell=True).wait()
    # read_command = 'adb shell "head -5 /proc/stat >> /sdcard/Research/result.txt"'.format(output_file)
    timestamp_command = 'adb -s {0} shell "echo \$EPOCHREALTIME" >> {1}'.format(device_config_obj['id'], output_file)
    subprocess.call(timestamp_command, shell=True)
    read_command = 'adb -s {0} shell "head -5 /proc/stat" >> {1}'.format(device_config_obj['id'], output_file)
    subprocess.call(read_command, shell=True)
    # read_command = 'adb shell dumpsys cpuinfo | grep chromium >> {0}'.format(output_file)
    global current_timer
    global stopped_cpu_measurements

    # if current_timer is not None:
    #     current_timer.cancel()
    if not stopped_cpu_measurements:
        current_timer = threading.Timer(0.06, start_cpu_measurements, [ device, output_file ])
        current_timer.start()

def get_process_ids(device, proc_name):
    device, device_config, device_config_obj = get_device_config(device)
    command = 'adb -s {0} shell \'ps | grep {1}\''.format(device_config_obj['id'], proc_name)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = process.communicate()
    lines = output.split('\n')
    result = []
    for l in lines:
        if 'grep' not in l and len(l) > 0:
            result.append(l.strip().split()[1])
    return result

def pin_process_to_cpu(device, bitmask, proc_id):
    device, device_config, device_config_obj = get_device_config(device)
    command = 'adb -s {0} shell \'su -c \'taskset -p {1} {2}\'\''.format(device_config_obj['id'], \
                                                                         bitmask, proc_id)
    subprocess.call(command, shell=True)

def start_tcpdump(device, running_path='.'):
    device, device_config, _ = get_device_config(device, running_path=running_path)
    start_tcpdump_command = 'python ./utils/start_tcpdump.py {0} {1}'.format(device_config, device)
    subprocess.Popen(start_tcpdump_command, shell=True).wait()

def start_screen_recording(device, running_path='.'):
    device, device_config, _ = get_device_config(device, running_path=running_path)
    start_screen_capture_command = 'python ./utils/start_screen_capture.py {0} {1}'.format(device_config, device)
    subprocess.Popen(start_screen_capture_command, shell=True).wait()

def stop_screen_recording(line, device, output_dir_run='.', running_path='.'):
    url = escape_page(line)
    device, device_config, _ = get_device_config(device, running_path=running_path)
    output_directory = os.path.join(output_dir_run, url)
    screen_record_filename = os.path.join(output_directory, 'screen_record.mp4')
    stop_screen_capture = 'python ./utils/stop_screen_capture.py {0} {1} --output-dir {2}'.format(device_config, device, screen_record_filename)
    subprocess.Popen(stop_screen_capture, shell=True).wait()

def start_tcpdump_and_cpu_measurement(device, cpu_utilization_output_filename, running_path='.'):
    start_cpu_measurements(device, cpu_utilization_output_filename, running_path=running_path)
    start_tcpdump(device, running_path)

def stop_cpu_measurements(line, device, output_dir_run='.', running_path='.'):
    # url = escape_page(line)
    # device, device_config, _ = get_device_config(device)
    # output_directory = os.path.join(output_dir_run, url)
    # cpu_measurement_output_filename = os.path.join(output_directory, 'cpu_measurement.txt')
    # stop_cpu_measurement = 'python ./utils/stop_cpu_measurement.py {0} {1} {2}'.format(device_config, device, cpu_measurement_output_filename)
    # subprocess.Popen(stop_cpu_measurement, shell=True).wait()
    global current_timer
    global stopped_cpu_measurements
    stopped_cpu_measurements = True
    current_timer.cancel()
    # current_timer.join()
    # current_timer = None
    print 'Stopped CPU measurements...'
    time.sleep(2)

def stop_tcpdump(line, device, output_dir_run='.', running_path='.'):
    url = escape_page(line)
    device, device_config, _ = get_device_config(device, running_path=running_path)
    output_directory = os.path.join(output_dir_run, url)
    pcap_output_filename = os.path.join(output_directory, 'output.pcap')
    stop_tcpdump = 'python ./utils/stop_tcpdump.py {0} {1} --output-dir {2} --no-sleep'.format(device_config, device, pcap_output_filename)
    subprocess.Popen(stop_tcpdump, shell=True).wait()

def stop_tcpdump_and_cpu_measurement(line, device, output_dir_run='.', running_path='.'):
    stop_cpu_measurements(line, device, output_dir_run, running_path)
    stop_tcpdump(line, device, output_dir_run, running_path)
