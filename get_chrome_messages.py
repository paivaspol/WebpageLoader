import common_module
import json
import requests
import signal
import subprocess
import sys
import os
import websocket
import shutil

from utils import phone_connection_utils, navigation_utils, chrome_utils, config

from argparse import ArgumentParser
from ConfigParser import ConfigParser   # Parsing configuration file.
from bs4 import BeautifulSoup # Beautify HTML
from time import sleep
from RDPMessageCollector.ChromeRDPWebsocketStreaming import ChromeRDPWebsocketStreaming # The websocket

HTTP_PREFIX = 'http://'
WWW_PREFIX = 'www.'
OUTPUT_DIR = None
PAGE_ID = None

def main(device_configuration, url, reload_page, url_hash):
    '''
    The main workflow of the script.
    '''
    if url_hash is None:
        output_directory = remove_and_create_output_directory_for_url(url)
    else:
        output_directory = remove_and_create_output_directory_for_url(url_hash)

    if not is_desktop_device(device_configuration):
        cpu_chrome_running_on = phone_connection_utils.get_cpu_running_chrome(device_configuration)
        output_cpu_running_chrome(output_directory, cpu_chrome_running_on)

    debugging_url, page_id = get_debugging_url(device_configuration)

    print 'Connected to Chrome...'
    device_configuration['page_id'] = page_id
    emulating_device_params = device_configuration[config.EMULATING_DEVICE] if config.EMULATING_DEVICE in device_configuration else None
    network_params = device_configuration[config.NETWORK] if config.NETWORK in device_configuration else None
    cpu_throttle_rate = device_configuration[config.CPU_THROTTLE_RATE] if config.CPU_THROTTLE_RATE in device_configuration else 1

    if args.get_dependency_baseline:
        debugging_socket = ChromeRDPWebsocketStreaming(debugging_url, url,
                emulating_device_params, network_params, cpu_throttle_rate, args.collect_console, args.collect_tracing, callback_on_received_event, None, args.preserve_cache, False, args.get_dom, args.take_heap_snapshot, url_hash)
        def timeout_handler(a, b):
            print('get_chrome_message.py Timeout Handler called...')
            callback_on_page_done_streaming(debugging_socket)
            sys.exit(0)

        print 'Setting SIGTERM handler'
        signal.signal(signal.SIGTERM, timeout_handler)
    else:
        debugging_socket = ChromeRDPWebsocketStreaming(debugging_url, url,
                emulating_device_params, network_params, cpu_throttle_rate, args.collect_console, args.collect_tracing, callback_on_received_event, callback_on_page_done_streaming, args.preserve_cache, False, args.get_dom, args.take_heap_snapshot, url_hash)
    debugging_socket.start()


def get_debugging_url(device_configuration):
    '''
    Returns a tuple of the URL for connection to DevTools and the page ID.
    '''
    while True:
        try:
            debugging_url, page_id = chrome_utils.get_debugging_url(device_configuration)
            print 'Debugging URL: ' + debugging_url + ' page_id: ' + page_id
            return debugging_url, page_id
        except (requests.exceptions.ConnectionError, KeyError) as e:
            pass
    # We are not suppose to get here.
    assert(False)

    
def output_cpu_running_chrome(output_directory, cpu_id):
    '''
    Outputs the CPU id that is running chrome.
    '''
    cpu_running_chrome_filename = os.path.join(output_directory, 'cpu_running_chrome.txt')
    with open(cpu_running_chrome_filename, 'wb') as output_file:
        output_file.write(cpu_id)

def remove_and_create_output_directory_for_url(url):
    '''
    Creates an output directory for the url
    '''
    base_dir = ConstructOutputDir(url)
    shutil.rmtree(base_dir, ignore_errors=True)
    os.mkdir(base_dir)
    return base_dir


def ConstructOutputDir(url):
    base_dir = ''
    if OUTPUT_DIR is not None:
        base_dir = os.path.join(base_dir, OUTPUT_DIR)
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
    
    final_url = common_module.escape_page(url)
    return os.path.join(base_dir, final_url)


def callback_on_received_event(debugging_socket, network_message, network_message_string):
    final_url = debugging_socket.url_hash if debugging_socket.url_hash is not None else common_module.escape_page(debugging_socket.url) 
    base_dir = ConstructOutputDir(final_url)
    if 'method' in network_message and network_message['method'].startswith('Network'):
        network_filename = os.path.join(base_dir, 'network_' + final_url)
        with open(network_filename, 'ab') as output_file:
            output_file.write('{0}\n'.format(network_message_string))

    elif 'method' in network_message and \
            (network_message['method'].startswith('Log') or network_message['method'].startswith('Runtime')):
        network_filename = os.path.join(base_dir, 'console_' + final_url)
        with open(network_filename, 'ab') as output_file:
            output_file.write('{0}\n'.format(network_message_string))
    elif 'method' in network_message and network_message['method'].startswith('Tracing'):
        tracing_filename = os.path.join(base_dir, 'tracing_' + final_url)
        with open(tracing_filename, 'ab') as output_file:
            output_file.write('{0}\n'.format(network_message_string))
    else:
        filename = os.path.join(base_dir, 'unknown_' + final_url)
        with open(filename, 'ab') as output_file:
            output_file.write('{0}\n'.format(network_message_string))


def callback_on_page_done_streaming(debugging_socket):
    try:
        debugging_socket.close_connection()
    except Exception as e:
        pass

    print 'Closed debugging socket connection'

    sleep(1)
    final_url = debugging_socket.url_hash if debugging_socket.url_hash is not None else common_module.escape_page(debugging_socket.url) 
    base_dir = ConstructOutputDir(final_url)
    new_debugging_websocket = websocket.create_connection(debugging_socket.debugging_url)

    # Get the start and end time of the execution
    start_time, end_time, dom_content_loaded = navigation_utils.get_start_end_time_with_socket(new_debugging_websocket)
    # print 'output dir: ' + base_dir
    print 'Load time: ' + str((start_time, end_time)) + ' ' + str((end_time - start_time))
    write_page_start_end_time(final_url, base_dir, start_time, end_time, dom_content_loaded, -1, -1)

    if args.record_content:
        body = navigation_utils.get_modified_html(new_debugging_websocket)
        with open(os.path.join(base_dir, 'onload_root_html'), 'wb') as output_file:
            output_file.write(body)

    if args.get_dom:
        with open(os.path.join(base_dir, 'unmodified_root_html'), 'wb') as output_file:
            output_file.write(str(debugging_socket.unmodified_html))

        dom = navigation_utils.get_dom_tree(new_debugging_websocket)
        with open(os.path.join(base_dir, 'dom'), 'wb') as output_file:
            output_file.write(dom)

    if args.take_heap_snapshot:
        with open(os.path.join(base_dir, 'js_heap_snapshot'), 'w') as output_file:
            output_file.write(debugging_socket.heap_snapshot_str)

    navigation_utils.navigate_to_page(new_debugging_websocket, 'about:blank')
    # sleep(0.2)
    new_debugging_websocket.close()
    clean_user_dir()


def clean_user_dir():
    '''
    Clears any temporary user data dir that was created during this experiment run.
    '''
    for d in os.listdir('/tmp/'):
        if 'chrome-' not in d:
            continue
        rm_cmd = 'rm -r ' + os.path.join('/tmp/', d)
        subprocess.call(rm_cmd, shell=True)


def is_desktop_device(device_configuration):
    return device_configuration[config.DEVICE_TYPE] == config.DEVICE_MAC or \
        device_configuration[config.DEVICE_TYPE] == config.DEVICE_UBUNTU


def write_page_start_end_time(escaped_url, base_dir, start_time, end_time, dom_content_loaded, original_request_ts=-1, load_event_ts=-1):
    start_end_time_filename = os.path.join(base_dir, 'start_end_time_' + escaped_url)
    with open(start_end_time_filename, 'wb') as output_file:
        output_file.write('{0} {1} {2} {3} {4} {5}\n'.format(escaped_url, start_time, end_time, original_request_ts, load_event_ts, dom_content_loaded))


def get_page_hashes(page_hash_mapping_filename):
    '''Returns a dictionary mapping from the page hash to the URL.'''
    with open(page_hash_mapping_filename, 'r') as input_file:
        return json.load(input_file)


if __name__ == '__main__':
    argparser = ArgumentParser()
    argparser.add_argument('config_filename')
    argparser.add_argument('device', help='The device name e.g. Nexus_6')
    argparser.add_argument('url', help='The URL to navigate to e.g. http://apple.com')
    argparser.add_argument('--output-dir', help='The output directory of the generated files', default=None)
    argparser.add_argument('--reload-page', default=False, action='store_true')
    argparser.add_argument('--record-content', default=False, action='store_true')
    argparser.add_argument('--collect-console', default=False, action='store_true')
    argparser.add_argument('--get-chromium-logs', default=False, action='store_true')
    argparser.add_argument('--get-dependency-baseline', default=False, action='store_true')
    argparser.add_argument('--collect-tracing', default=False, action='store_true')
    argparser.add_argument('--preserve-cache', default=False, action='store_true')
    argparser.add_argument('--get-dom', default=False, action='store_true')
    argparser.add_argument('--take-heap-snapshot', default=False, action='store_true')
    argparser.add_argument('--get-page-from-hash', default=None)
    args = argparser.parse_args()

    # Setup the config filename
    config_reader = ConfigParser()
    config_reader.read(args.config_filename)
    OUTPUT_DIR = args.output_dir

    # Get the device configuration.
    device_config = config.get_device_configuration(config_reader, args.device)

    url = args.url
    url_hash = None
    if url.startswith('"'):
        url = url[1:len(url) - 1]

    if args.get_page_from_hash is not None:
        # This assumes that the value passed through URL is the hash of the URL.
        page_hashes = get_page_hashes(args.get_page_from_hash)
        print(page_hashes)
        url_hash = url
        url = page_hashes[url]

    main(device_config, url, args.reload_page, url_hash)
