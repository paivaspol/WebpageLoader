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

from utils import phone_connection_utils, chrome_utils, config

# Available devices to use.
DEVICES = {
        # Mobile devices
        'Nexus_6': '/device_config/nexus6.cfg',
        'Nexus_6_chromium': '/device_config/nexus6_chromium.cfg',
        'Nexus_6_2': '/device_config/nexus6_2.cfg',
        'Nexus_6_2_chromium': '/device_config/nexus6_2_chromium.cfg',
        'Nexus_5': '/device_config/nexus5.cfg',
        'pixel2': '/device_config/pixel2.cfg',

        # Desktop devices
        'ubuntu': '/device_config/ubuntu.cfg',
        'ubuntu_with_cookies': '/device_config/ubuntu_with_cookies.cfg',
        'mac': '/device_config/mac.cfg',
}
DEFAULT_DEVICE = 'Nexus_6'

TIMEOUT = 1 * 60 # set to 3 minutes
PAUSE = 1
BUFFER_FOR_TRACE = 5
TRY_LIMIT = 2

def main(pages_file, num_repetitions, output_dir, start_measurements, device_name, disable_tracing, record_contents):
    signal.signal(signal.SIGALRM, timeout_handler) # Setup the timeout handler
    pages = common_module.get_pages(pages_file)
    print 'total pages: {0}'.format(len(pages))
    if start_measurements and not disable_tracing:
        load_pages_with_measurement_and_tracing_enabled(pages, output_dir, num_repetitions, device_name, record_contents)
    elif not start_measurements and disable_tracing:
        load_pages_with_measurement_and_tracing_disabled(pages, output_dir, num_repetitions, device_name, record_contents)
    elif not start_measurements and not disable_tracing:
        load_pages_with_measurement_disabled_but_tracing_enabled(pages, output_dir, num_repetitions, device_name, record_contents)
    else:
        while len(pages) > 0:
            initialize_browser(device_name)
            page = pages.pop(0)
            print 'page: ' + page
            i = 0
            while i < num_repetitions:
                try:
                    common_module.start_tcpdump_and_cpu_measurement(device_name)
                    bring_chrome_to_foreground(device_name)
                    signal.alarm(TIMEOUT)
                    load_page(page, i, output_dir, start_measurements, device_name, disable_tracing)
                    if not disable_tracing:
                        # Kill the browser.
                        print 'initializing ' + str(i)
                        sleep(BUFFER_FOR_TRACE)
                        initialize_browser(device_name)
                    signal.alarm(0) # Reset the alarm
                    while common_module.check_previous_page_load(i, output_dir, page):
                        load_page(page, i, output_dir, start_measurements, device_name, disable_tracing, record_contents)
                    iteration_path = os.path.join(output_dir, str(i))
                    common_module.stop_tcpdump_and_cpu_measurement(page.strip(), device_name, output_dir_run=iteration_path)
                    i += 1
                except PageLoadException as e:
                    print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                    # Kill the browser and append a page.
                    device_config_obj = get_device_config_obj(device_name)
                    # chrome_utils.close_all_tabs(device_config_obj)
                    initialize_browser(device_name)
                    pages.append(page)
                    break
                sleep(PAUSE)
    # shutdown_browser(device)

def load_pages_with_measurement_disabled_but_tracing_enabled(pages, output_dir, num_repetitions, device_name, record_contents):
    device_config_obj = get_device_config_obj(device_name)
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
                load_page(page, i, output_dir, False, device_name, False, record_contents)
                signal.alarm(0) # Reset the alarm
                while common_module.check_previous_page_load(i, output_dir, page):
                    signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                    load_page(page, i, output_dir, False, device_name, False, record_contents)
                    signal.alarm(0) # Reset the alarm
                i += 1
                print 'Stopping Chrome...'
                phone_connection_utils.stop_chrome(device_config_obj)
            except PageLoadException as e:
                print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                # Kill the browser and append a page.
                chrome_utils.close_all_tabs(device_config_obj)
                initialize_browser(device_name)
                if tried_counter[page] <= TRY_LIMIT:
                    pages.append(page)
                else:
                    failed_pages.append(page)
                break
            sleep(PAUSE)
        print '\033[92m' + str(num_pages - len(pages)) + '/' + str(num_pages) + ' completed' + '\033[0m'
    print_failed_pages(output_dir, failed_pages)

def print_failed_pages(output_dir, failed_pages):
    '''
    Prints the failed pages.
    '''
    output_filename = os.path.join(output_dir, 'failed_pages.txt')
    with open(output_filename, 'wb') as output_file:
        for failed_page in failed_pages:
            output_file.write(failed_page + '\n')


def load_pages_with_measurement_and_tracing_disabled(pages, output_dir, num_repetitions, device_name, record_contents):
    initialize_browser(device_name)
    device_config_obj = get_device_config_obj(device_name)
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
                load_page(page, i, output_dir, False, device_name, True, record_contents, device_config_obj)
                signal.alarm(0) # Reset the alarm
                while common_module.check_previous_page_load(i, output_dir, page):
                    signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                    load_page(page, i, output_dir, False, device_name, True, record_contents, device_config_obj)
                    signal.alarm(0) # Reset the alarm
                i += 1
            except PageLoadException as e:
                print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                # Kill the browser and append a page.
                chrome_utils.close_all_tabs(device_config_obj)
                initialize_browser(device_name)
                if tried_counter[page] <= TRY_LIMIT:
                    pages.append(page)
                else:
                    failed_pages.append(page)
                break
            sleep(PAUSE)
    print_failed_pages(output_dir, failed_pages)

def load_pages_with_measurement_and_tracing_enabled(pages, output_dir, num_repetitions, device_name, record_contents):
    while len(pages) > 0:
        page = pages.pop(0)
        print 'page: ' + page
        i = 0
        initialize_browser(device_name)
        while i < num_repetitions:
            try:
                if not os.path.exists(output_dir):
                    os.mkdir(output_dir)

                iteration_path = os.path.join(output_dir, str(i))
                if not os.path.exists(iteration_path):
                    os.mkdir(iteration_path)

                print device_name

                if args.start_measurements is not None and args.start_measurements == 'both':
                    escaped_page = common_module.escape_page(page)
                    if not os.path.exists(os.path.join(iteration_path, escaped_page)):
                        os.mkdir(os.path.join(iteration_path, escaped_page))

                    cpu_output_filename = os.path.join(iteration_path, escaped_page, 'cpu_measurements.txt')
                    common_module.reset_cpu_measurements()
                    common_module.start_tcpdump_and_cpu_measurement(device_name, cpu_output_filename, running_path=args.current_path)
                elif args.start_measurements is not None and args.start_measurements == 'tcpdump':
                    common_module.start_tcpdump(device_name, running_path=args.current_path)
                elif args.start_measurements is not None and args.start_measurements == 'cpu':
                    print 'Starting CPU measurements...'
                    escaped_page = common_module.escape_page(page)
                    if not os.path.exists(os.path.join(iteration_path, escaped_page)):
                        os.mkdir(os.path.join(iteration_path, escaped_page))

                    output_filename = os.path.join(iteration_path, escaped_page, 'cpu_measurements.txt')
                    common_module.reset_cpu_measurements()
                    common_module.start_cpu_measurements(device_name, output_filename, running_path=args.current_path)

                signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                load_page(page, i, output_dir, True, device_name, False, record_contents)
                signal.alarm(0) # Reset the alarm
                iteration_path = os.path.join(output_dir, str(i))

                if args.start_measurements is not None and args.start_measurements == 'both':
                    common_module.stop_tcpdump_and_cpu_measurement(page.strip(), device_name, output_dir_run=iteration_path, running_path=args.current_path)
                elif args.start_measurements is not None and args.start_measurements == 'tcpdump':
                    common_module.stop_tcpdump(page.strip(), device_name, output_dir_run=iteration_path, running_path=args.current_path)
                elif args.start_measurements is not None and args.start_measurements == 'cpu':
                    common_module.stop_cpu_measurements(page.strip(), device_name, output_dir_run=iteration_path, running_path=args.current_path)

                while common_module.check_previous_page_load(i, output_dir, page):
                    if args.start_measurements is not None and args.start_measurements == 'both':
                        escaped_page = common_module.escape_page(page)
                        if not os.path.exists(os.path.join(iteration_path, escaped_page)):
                            os.mkdir(os.path.join(iteration_path, escaped_page))

                        cpu_output_filename = os.path.join(iteration_path, escaped_page, 'cpu_measurements.txt')
                        common_module.reset_cpu_measurements()
                        common_module.start_tcpdump_and_cpu_measurement(device_name, cpu_output_filename, running_path=args.current_path)
                    elif args.start_measurements is not None and args.start_measurements == 'tcpdump':
                        common_module.start_tcpdump(device_name, running_path=args.current_path)
                    elif args.start_measurements is not None and args.start_measurements == 'cpu':
                        print 'Starting CPU measurements...'
                        escaped_page = common_module.escape_page(page)
                        if not os.path.exists(os.path.join(iteration_path, escaped_page)):
                            os.mkdir(os.path.join(iteration_path, escaped_page))

                        output_filename = os.path.join(iteration_path, escaped_page, 'cpu_measurements.txt')
                        common_module.reset_cpu_measurements()
                        common_module.start_cpu_measurements(device_name, output_filename, running_path=args.current_path)

                    signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                    load_page(page, i, output_dir, True, device_name, False, record_contents)
                    signal.alarm(0) # Reset the alarm
                    iteration_path = os.path.join(output_dir, str(i - 1))
                    if args.start_measurements is not None and args.start_measurements == 'both':
                        common_module.stop_tcpdump_and_cpu_measurement(page.strip(), device_name, output_dir_run=iteration_path)
                    elif args.start_measurements is not None and args.start_measurements == 'tcpdump':
                        common_module.stop_tcpdump(page.strip(), device_name, output_dir_run=iteration_path)
                    elif args.start_measurements is not None and args.start_measurements == 'cpu':
                        common_module.stop_cpu_measurements(page.strip(), device_name, output_dir_run=iteration_path)
                i += 1
            except PageLoadException as e:
                print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                # Kill the browser and append a page.
                device_config_obj = get_device_config_obj(device_name)
                chrome_utils.close_all_tabs(device_config_obj)
                initialize_browser(device_name)
                pages.append(page)
                break
            sleep(PAUSE)


def initialize_browser(device_name):
    # Get the device configuration
    print 'initializing browser...'
    device_config_obj = get_device_config_obj(device_name)
    phone_connection_utils.wake_phone_up(device_config_obj)
    print 'Stopping Chrome...'
    phone_connection_utils.stop_chrome(device_config_obj)
    print 'Starting Chrome...'
    phone_connection_utils.start_chrome(device_config_obj)
    closed_tabs = False
    while not closed_tabs:
        try:
            chrome_utils.close_all_tabs(device_config_obj)
            closed_tabs = True
        except requests.exceptions.ConnectionError as e:
            pass

def shutdown_browser(device_name):
    device_config_obj = get_device_config_obj(device_name)
    print 'Stopping Chrome...'
    phone_connection_utils.stop_chrome(device_config_obj)

def load_page(raw_line, run_index, output_dir, start_measurements, device_name, disable_tracing, record_contents=False, device_config_obj=None):
    # Create necessary directories
    base_output_dir = output_dir
    if not os.path.exists(base_output_dir):
        os.mkdir(base_output_dir)
    output_dir_run = os.path.join(base_output_dir, str(run_index))
    if not os.path.exists(output_dir_run):
        os.mkdir(output_dir_run)

    # Get the device configuration
    device_config = get_device_config_path(device_name)

    line = raw_line.strip()
    chrome_msg_path = os.path.join(args.current_path, 'get_chrome_messages.py')
    cmd = 'python {0} {1} {2} {3} --output-dir {4}'.format(chrome_msg_path, device_config, device_name, line, output_dir_run) 
    if disable_tracing:
        cmd += ' --disable-tracing'
    if record_contents:
        cmd += ' --record-content'
    if args.collect_console:
        cmd += ' --collect-console'
    if args.collect_tracing:
        cmd += ' --collect-tracing'
    if args.defer_stop:
        cmd += ' --defer-stop'
    if args.get_dom:
        cmd += ' --get-dom'
    subprocess.Popen(cmd, shell=True).wait()

def bring_chrome_to_foreground(device_name):
    device_config_obj = get_device_config_obj(device_name)
    phone_connection_utils.bring_chrome_to_foreground(device_config_obj)

def timeout_handler(signum, frame):
    '''
    Handle the case where the page fails to load
    '''
    raise PageLoadException('Time\'s up for this load.')

def get_device_config_obj(device_name):
    '''
    Returns the dictionary that holds the device configuations.
    '''
    global device_config_obj
    if device_config_obj is None:
        device_config_path = get_device_config_path(device_name)
        config_reader = ConfigParser()
        config_reader.read(device_config_path)
        device_config_obj = config.get_device_configuration(config_reader, device_name)
    return device_config_obj


def get_device_config_path(device_name):
    '''
    Returns the path to the config of the device.

    If the device does not exists, the script will terminate.
    '''
    if device_name in DEVICES:
        return args.current_path + DEVICES[device_name]
    print 'available devices: {0}'.format(str([ d for d in DEVICES.keys() ]))
    exit()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('pages_file')
    parser.add_argument('num_repetitions', type=int)
    parser.add_argument('output_dir')
    parser.add_argument('--start-measurements', default=None, choices=[ 'tcpdump', 'cpu', 'both' ])
    parser.add_argument('--use-device', default=DEFAULT_DEVICE)
    parser.add_argument('--disable-tracing', default=False, action='store_true')
    parser.add_argument('--record-content', default=False, action='store_true')
    parser.add_argument('--collect-console', default=False, action='store_true')
    parser.add_argument('--collect-tracing', default=False, action='store_true')
    parser.add_argument('--defer-stop', default=False, action='store_true')
    parser.add_argument('--get-dom', default=False, action='store_true')
    parser.add_argument('--current-path', default='.')
    args = parser.parse_args()

    # Initialize globals
    global device_config_obj
    device_config_obj = None

    main(args.pages_file, args.num_repetitions, args.output_dir, args.start_measurements, args.use_device, args.disable_tracing, args.record_content)
