import subprocess
import requests
import signal # For timeout.
import os
import simplejson

import common_module

from argparse import ArgumentParser
from ConfigParser import ConfigParser
from time import sleep
from PageLoadException import PageLoadException

from utils import phone_connection_utils
from utils import chrome_utils

NEXUS_6_CONFIG = './device_config/nexus6.cfg'
NEXUS_6 = 'Nexus_6'
NEXUS_6_CHROMIUM_CONFIG = './device_config/nexus6_chromium.cfg'
NEXUS_6_CHROMIUM = 'Nexus_6_chromium'
NEXUS_6_2_CONFIG = './device_config/nexus6_2.cfg'
NEXUS_6_2 = 'Nexus_6_2'
NEXUS_6_2_CHROMIUM_CONFIG = './device_config/nexus6_2_chromium.cfg'
NEXUS_6_2_CHROMIUM = 'Nexus_6_2_chromium'
NEXUS_5_CONFIG = './device_config/nexus5.cfg'
NEXUS_5 = 'Nexus_5'
MAC_CONFIG = './device_config/mac.cfg'
MAC = 'mac'
UBUNTU_CONFIG = './device_config/ubuntu.cfg'
UBUNTU = 'ubuntu'

HTTP_PREFIX = 'http://'
HTTPS_PREFIX = 'https://'
WWW_PREFIX = 'www.'

TIMEOUT = 3 * 60 # set to 3 minutes
# TIMEOUT = 1
PAUSE = 2
BUFFER_FOR_TRACE = 5
TRY_LIMIT = 5

def main(pages_file, num_repetitions, output_dir, use_caching_proxy, start_measurements, device, disable_tracing, record_contents):
    signal.signal(signal.SIGALRM, timeout_handler) # Setup the timeout handler
    pages = common_module.get_pages(pages_file)
    if start_measurements and not disable_tracing:
        load_pages_with_measurement_and_tracing_enabled(pages, output_dir, num_repetitions, device, record_contents)
    elif not start_measurements and disable_tracing:
        load_pages_with_measurement_and_tracing_disabled(pages, output_dir, num_repetitions, device, record_contents)
    elif not start_measurements and not disable_tracing:
        load_pages_with_measurement_disabled_but_tracing_enabled(pages, output_dir, num_repetitions, device, record_contents)
    else:
        while len(pages) > 0:
            initialize_browser(device)
            page = pages.pop(0)
            print 'page: ' + page
            if use_caching_proxy:
                try:
                    # Special Case for Populating the proxy cache.
                    signal.alarm(TIMEOUT)
                    load_page(page, -1, output_dir, False, device, True)
                    signal.alarm(0) # Reset the alarm
                except PageLoadException as e:
                    print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                    pages.append(page)
            i = 0
            while i < num_repetitions:
                try:
                    common_module.start_tcpdump_and_cpu_measurement(device)
                    bring_chrome_to_foreground(device)
                    signal.alarm(TIMEOUT)
                    load_page(page, i, output_dir, start_measurements, device, disable_tracing)
                    if not disable_tracing:
                        # Kill the browser.
                        print 'initializing ' + str(i)
                        sleep(BUFFER_FOR_TRACE)
                        initialize_browser(device)
                    signal.alarm(0) # Reset the alarm
                    while common_module.check_previous_page_load(i, output_dir, page):
                        load_page(page, i, output_dir, start_measurements, device, disable_tracing, record_contents)
                    iteration_path = os.path.join(output_dir, str(i))
                    common_module.stop_tcpdump_and_cpu_measurement(page.strip(), device, output_dir_run=iteration_path)
                    i += 1
                except PageLoadException as e:
                    print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                    # Kill the browser and append a page.
                    device, device_config = get_device_config(device)
                    device_config_obj = get_device_config_obj(device, device_config)
                    # chrome_utils.close_all_tabs(device_config_obj)
                    initialize_browser(device)
                    pages.append(page)
                    break
                sleep(PAUSE)
    # shutdown_browser(device)

def load_pages_with_measurement_disabled_but_tracing_enabled(pages, output_dir, num_repetitions, device, record_contents):
    device, device_config = get_device_config(device)
    device_config_obj = get_device_config_obj(device, device_config)
    tried_counter = dict()
    failed_pages = []
    num_pages = len(pages)
    while len(pages) > 0:
        page = pages.pop(0)
        print 'page: ' + page
        i = 0
        if page not in tried_counter:
            tried_counter[page] = 0
        tried_counter[page] += 1
        while i < num_repetitions:
            try:
                print 'Starting Chrome...'
                phone_connection_utils.start_chrome(device_config_obj)
                sleep(1)
                signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                load_page(page, i, output_dir, False, device, False, record_contents)
                signal.alarm(0) # Reset the alarm
                while common_module.check_previous_page_load(i, output_dir, page):
                    signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                    load_page(page, i, output_dir, False, device, False, record_contents)
                    signal.alarm(0) # Reset the alarm
                i += 1
                print 'Stopping Chrome...'
                phone_connection_utils.stop_chrome(device_config_obj)
            except PageLoadException as e:
                print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                # Kill the browser and append a page.
                device, device_config = get_device_config(device)
                device_config_obj = get_device_config_obj(device, device_config)
                chrome_utils.close_all_tabs(device_config_obj)
                initialize_browser(device)
                if tried_counter[page] <= TRY_LIMIT:
                    pages.append(page)
                else:
                    failed_pages.append(page)
                break
            sleep(PAUSE)
        print '\033[92m' + str(num_pages - len(pages)) + '/' + str(num_pages) + ' completed' + '\033[0m'
    print_failed_pages(output_dir, failed_pages)

def print_failed_pages(output_dir, failed_pages):
    output_filename = os.path.join(output_dir, 'failed_pages.txt')
    with open(output_filename, 'wb') as output_file:
        for failed_page in failed_pages:
            output_file.write(failed_page + '\n')

def load_pages_with_measurement_and_tracing_disabled(pages, output_dir, num_repetitions, device, record_contents):
    initialize_browser(device)
    device, device_config = get_device_config(device)
    device_config_obj = get_device_config_obj(device, device_config)
    tried_counter = dict()
    failed_pages = []
    while len(pages) > 0:
        page = pages.pop(0)
        print 'page: ' + page
        i = 0
        if page not in tried_counter:
            tried_counter[page] = 0
        tried_counter[page] += 1
        while i < num_repetitions:
            try:
                signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                load_page(page, i, output_dir, False, device, True, record_contents, device_config_obj)
                signal.alarm(0) # Reset the alarm
                while common_module.check_previous_page_load(i, output_dir, page):
                    signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                    load_page(page, i, output_dir, False, device, True, record_contents, device_config_obj)
                    signal.alarm(0) # Reset the alarm
                i += 1
            except PageLoadException as e:
                print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                # Kill the browser and append a page.
                chrome_utils.close_all_tabs(device_config_obj)
                initialize_browser(device)
                if args.take_screenshots:
                    phone_connection_utils.stop_taking_screenshopts(device_config_obj)

                if tried_counter[page] <= TRY_LIMIT:
                    pages.append(page)
                else:
                    failed_pages.append(page)
                break
            sleep(PAUSE)
    print_failed_pages(output_dir, failed_pages)

def load_pages_with_measurement_and_tracing_enabled(pages, output_dir, num_repetitions, device, record_contents):
    while len(pages) > 0:
        page = pages.pop(0)
        print 'page: ' + page
        i = 0
        while i < num_repetitions:
            try:
                common_module.start_tcpdump_and_cpu_measurement(device)
                initialize_browser(device)
                signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                load_page(page, i, output_dir, True, device, False, record_contents)
                signal.alarm(0) # Reset the alarm
                iteration_path = os.path.join(output_dir, str(i))
                common_module.stop_tcpdump_and_cpu_measurement(page.strip(), device, output_dir_run=iteration_path)
                while common_module.check_previous_page_load(i, output_dir, page):
                    common_module.start_tcpdump_and_cpu_measurement(device)
                    initialize_browser(device)
                    signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                    load_page(page, i, output_dir, True, device, False, record_contents)
                    signal.alarm(0) # Reset the alarm
                    iteration_path = os.path.join(output_dir, str(i - 1))
                    common_module.stop_tcpdump_and_cpu_measurement(page.strip(), device, output_dir_run=iteration_path)
                i += 1
            except PageLoadException as e:
                print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                # Kill the browser and append a page.
                device, device_config = get_device_config(device)
                device_config_obj = get_device_config_obj(device, device_config)
                chrome_utils.close_all_tabs(device_config_obj)
                initialize_browser(device)
                pages.append(page)
                phone_connection_utils.stop_taking_screenshopts(device_config_obj)
                break
            sleep(PAUSE)

def initialize_browser(device):
    # Get the device configuration
    print 'initializing browser...'
    device, device_config = get_device_config(device)
    device_config_obj = get_device_config_obj(device, device_config)
    phone_connection_utils.wake_phone_up(device_config_obj)
    print 'Stopping Chrome...'
    phone_connection_utils.stop_chrome(device_config_obj)
    print 'Starting Chrome...'
    phone_connection_utils.start_chrome(device_config_obj)
    # closed_tabs = False
    # while not closed_tabs:
    #     try:
    #         chrome_utils.close_all_tabs(device_config_obj)
    #         closed_tabs = True
    #     except requests.exceptions.ConnectionError as e:
    #         pass

def get_device_config_obj(device, device_config):
    config_reader = ConfigParser()
    config_reader.read(device_config)
    device_config_obj = phone_connection_utils.get_device_configuration(config_reader, device)
    return device_config_obj

def shutdown_browser(device):
    device, device_config = get_device_config(device)
    config_reader = ConfigParser()
    config_reader.read(device_config)
    device_config_obj = phone_connection_utils.get_device_configuration(config_reader, device)
    print 'Stopping Chrome...'
    phone_connection_utils.stop_chrome(device_config_obj)

def load_page(raw_line, run_index, output_dir, start_measurements, device, disable_tracing, record_contents=False, device_config_obj=None):
    # Create necessary directories
    base_output_dir = output_dir
    if not os.path.exists(base_output_dir):
        os.mkdir(base_output_dir)
    output_dir_run = os.path.join(base_output_dir, str(run_index))
    if not os.path.exists(output_dir_run):
        os.mkdir(output_dir_run)

    if args.take_screenshots:
        if not os.path.exists(os.path.join(output_dir_run, 'screenshots')):
            os.mkdir(os.path.join(output_dir_run, 'screenshots'))
        destination = os.path.join(output_dir_run, 'screenshots', common_module.escape_page(raw_line.strip()))
        if not os.path.exists(destination):
            os.mkdir(destination)
        phone_connection_utils.start_taking_screenshot_every_x_s(device_config_obj, 0.1, destination)
    
    # Get the device configuration
    device, device_config = get_device_config(device)

    line = raw_line.strip()
    cmd = 'python get_chrome_messages.py {1} {2} {0} --output-dir {3}'.format(line, device_config, device, output_dir_run) 
    if disable_tracing:
        cmd += ' --disable-tracing'
    if record_contents:
        cmd += ' --record-content'
    if args.collect_console:
        cmd += ' --collect-console'
    if args.collect_tracing:
        cmd += ' --collect-tracing'
    # if run_index > 0:
    #     cmd += ' --reload-page'
    subprocess.Popen(cmd, shell=True).wait()

    if args.take_screenshots:
        phone_connection_utils.stop_taking_screenshots(device_config_obj)

def bring_chrome_to_foreground(device):
    device, device_config = get_device_config(device)
    device_config_obj = get_device_config_obj(device, device_config)
    phone_connection_utils.bring_chrome_to_foreground(device_config_obj)

def escape_url(url):
    if url.endswith('/'):
        url = url[:len(url) - 1]
    if url.startswith(HTTPS_PREFIX):
        url = url[len(HTTPS_PREFIX):]
    elif url.startswith(HTTP_PREFIX):
        url = url[len(HTTP_PREFIX):]
    if url.startswith(WWW_PREFIX):
        url = url[len(WWW_PREFIX):]
    return url.replace('/', '_')

def timeout_handler(signum, frame):
    '''
    Handle the case where the page fails to load
    '''
    raise PageLoadException('Time\'s up for this load.')

def get_device_config(device):
    if device == NEXUS_6:
        return NEXUS_6, NEXUS_6_CONFIG
    if device == NEXUS_6_2:
        return NEXUS_6_2, NEXUS_6_2_CONFIG
    elif device == NEXUS_5:
        return NEXUS_5, NEXUS_5_CONFIG
    elif device == MAC:
        return MAC, MAC_CONFIG
    elif device == NEXUS_6_CHROMIUM:
        return NEXUS_6_CHROMIUM, NEXUS_6_CHROMIUM_CONFIG
    elif device == NEXUS_6_2_CHROMIUM:
        return NEXUS_6_2_CHROMIUM, NEXUS_6_2_CHROMIUM_CONFIG
    elif device == UBUNTU:
        return UBUNTU, UBUNTU_CONFIG
    else:
        print 'available devices: {0}, {1}, {2}, {3}, {4}, {5}'.format(NEXUS_6, NEXUS_6_2, NEXUS_5, NEXUS_6_CHROMIUM, NEXUS_6_2_CHROMIUM, MAC, UBUNTU)
        exit()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('pages_file')
    parser.add_argument('num_repetitions', type=int)
    parser.add_argument('--output-dir', default='.')
    parser.add_argument('--use-caching-proxy', default=False, action='store_true')
    parser.add_argument('--start-measurements', default=False, action='store_true')
    parser.add_argument('--use-device', default=NEXUS_6_2)
    parser.add_argument('--disable-tracing', default=False, action='store_true')
    parser.add_argument('--record-content', default=False, action='store_true')
    parser.add_argument('--collect-console', default=False, action='store_true')
    parser.add_argument('--collect-tracing', default=False, action='store_true')
    parser.add_argument('--take-screenshots', default=False, action='store_true')
    args = parser.parse_args()
    main(args.pages_file, args.num_repetitions, args.output_dir, args.use_caching_proxy, args.start_measurements, args.use_device, args.disable_tracing, args.record_content)
