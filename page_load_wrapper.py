import subprocess
import json
import requests
import signal # For timeout.
import os

import common_module

from argparse import ArgumentParser
from ConfigParser import ConfigParser
from time import sleep
from PageLoadException import PageLoadException

from utils import phone_connection_utils, chrome_utils, config

DEFAULT_DEVICE = 'Nexus_6'

TIMEOUT = 1 * 60 # set to 30 seconds.
PAUSE = 1
BUFFER_FOR_TRACE = 5
TRY_LIMIT = 2

def main(pages_file, num_repetitions, output_dir, device_name, record_contents):
    signal.signal(signal.SIGALRM, timeout_handler) # Setup the timeout handler
    pages = common_module.get_pages(pages_file)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    url_to_hash, hash_to_url = GetPageHashes(args.use_page_hash)

    # We add one more load to the loads.
    if args.warm_cache:
        num_repetitions += 1

    print 'total pages: {0}'.format(len(pages))
    load_pages_with_measurement_disabled_but_tracing_enabled(pages, output_dir, num_repetitions, device_name, record_contents, url_to_hash)


def load_pages_with_measurement_disabled_but_tracing_enabled(pages, output_dir, num_repetitions, device_name, record_contents, url_to_hash):
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

        # Make sure that we don't have any dangling instances of Chrome.
        phone_connection_utils.stop_chrome(device_config_obj)
        while i < num_repetitions:
            try:
                print 'Starting Chrome...'
                phone_connection_utils.start_chrome(device_config_obj)
                sleep(1)
                signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                final_page = url_to_hash[page] if args.use_page_hash else page
                page_load_process = load_page(final_page, i, output_dir, False, device_name, False, record_contents)
                page_load_process.communicate()
                signal.alarm(0) # Reset the alarm
                while common_module.check_previous_page_load(i, output_dir, page):
                    signal.alarm(TIMEOUT) # Set alarm for TIMEOUT
                    page_load_process = load_page(final_page, i, output_dir, False, device_name, False, record_contents)
                    page_load_process.communicate()
                    signal.alarm(0) # Reset the alarm
                i += 1
                print 'Stopping Chrome...'
                phone_connection_utils.stop_chrome(device_config_obj)
            except PageLoadException as e:
                print 'Timeout for {0}-th load. Append to end of queue...'.format(i)
                if args.defer_stop:
                    page_load_process.terminate()
                    # page_load_process.kill()
                    # os.killpg(os.getpgid(page_load_process.pid), signal.SIGTERM)
                    sleep(2)
                    i += 1
                    continue

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

def load_page(url, run_index, output_dir, start_measurements, device_name, disable_tracing, record_contents=False, device_config_obj=None):
    # Create necessary directories
    base_output_dir = output_dir
    if not os.path.exists(base_output_dir):
        os.mkdir(base_output_dir)
    output_dir_run = os.path.join(base_output_dir, str(run_index))
    if not os.path.exists(output_dir_run):
        os.mkdir(output_dir_run)

    # Get the device configuration
    device_config = common_module.get_device_config_path(device_name, args.current_path)

    url = url.strip()
    chrome_msg_path = os.path.join(args.current_path, 'get_chrome_messages.py')
    cmd = 'python {0} {1} {2} "{3}" --output-dir {4}'.format(chrome_msg_path, device_config, device_name, url, output_dir_run) 
    if disable_tracing:
        cmd += ' --disable-tracing'
    if record_contents:
        cmd += ' --record-content'
    if args.collect_console:
        cmd += ' --collect-console'
    if args.collect_tracing:
        cmd += ' --collect-tracing'
    if args.defer_stop:
        cmd += ' --get-dependency-baseline'
    if args.get_dom:
        cmd += ' --get-dom'
    if args.take_heap_snapshot:
        cmd += ' --take-heap-snapshot'
    if args.warm_cache and run_index > 0:
        cmd += ' --preserve-cache'
    if args.use_page_hash:
        cmd += ' --get-page-from-hash={0}'.format(os.path.join(args.use_page_hash, 'hash_to_url'))
    print(cmd)
    return subprocess.Popen(cmd.split())

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
        device_config_path = common_module.get_device_config_path(device_name, args.current_path)
        config_reader = ConfigParser()
        config_reader.read(device_config_path)
        device_config_obj = config.get_device_configuration(config_reader, device_name)
    return device_config_obj


def GetPageHashes(path_to_page_hashes):
    if path_to_page_hashes is None:
        return ({}, {})
    with open(os.path.join(path_to_page_hashes, 'url_to_hash'), 'r') as input_file:
        url_to_hash = json.load(input_file)
    with open(os.path.join(path_to_page_hashes, 'hash_to_url'), 'r') as input_file:
        hash_to_url = json.load(input_file)
    return url_to_hash, hash_to_url


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('pages_file')
    parser.add_argument('num_repetitions', type=int)
    parser.add_argument('output_dir')
    # parser.add_argument('--start-measurements', default=None, choices=[ 'tcpdump', 'cpu', 'both' ])
    parser.add_argument('--use-device', default=DEFAULT_DEVICE)
    # parser.add_argument('--disable-tracing', default=False, action='store_true')
    parser.add_argument('--record-content', default=False, action='store_true')
    parser.add_argument('--collect-console', default=False, action='store_true')
    parser.add_argument('--collect-tracing', default=False, action='store_true')
    parser.add_argument('--defer-stop', default=False, action='store_true')
    parser.add_argument('--get-dom', default=False, action='store_true')
    parser.add_argument('--current-path', default='.')
    parser.add_argument('--take-heap-snapshot', default=False, action='store_true')
    parser.add_argument('--warm-cache', default=False, action='store_true')
    parser.add_argument('--use-page-hash', default=None)
    args = parser.parse_args()

    # Initialize globals
    global device_config_obj
    device_config_obj = None

    main(args.pages_file, args.num_repetitions, args.output_dir, args.use_device, args.record_content)
