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
from RDPMessageCollector.ChromeRDPWithoutTracking import ChromeRDPWithoutTracing

HTTP_PREFIX = 'http://'
WWW_PREFIX = 'www.'
OUTPUT_DIR = None
PAGE_ID = None

def main(device_configuration, url, disable_tracing, reload_page):
    '''
    The main workflow of the script.
    '''
    output_directory = create_output_directory_for_url(url)
    
    if not is_desktop_device(device_configuration):
        cpu_chrome_running_on = phone_connection_utils.get_cpu_running_chrome(device_configuration)
        output_cpu_running_chrome(output_directory, cpu_chrome_running_on)

    got_debugging_url = False
    while not got_debugging_url:
        try:
            debugging_url, page_id = chrome_utils.get_debugging_url(device_configuration)
            print 'Debugging URL: ' + debugging_url + ' page_id: ' + page_id
            got_debugging_url = True
        except (requests.exceptions.ConnectionError, KeyError) as e:
            pass

    print 'Connected to Chrome...'
    device_configuration['page_id'] = page_id
    user_agent_str = None
    screen_size_config = None
    if config.USER_AGENT in device_configuration:
        user_agent_str = device_configuration[config.USER_AGENT]
    if config.SCREEN_SIZE in device_configuration:
        screen_size_config = device_configuration[config.SCREEN_SIZE]

    if disable_tracing:
        chrome_rdp_object_without_tracing = ChromeRDPWithoutTracing(debugging_url, url, user_agent_str, screen_size_config)
        start_time, end_time = chrome_rdp_object_without_tracing.navigate_to_page(url, reload_page)
        print str((start_time, end_time)) + ' ' + str((end_time - start_time))
        escaped_url = common_module.escape_page(url)
        print 'output_directory: ' + output_directory
        write_page_start_end_time(escaped_url, output_directory, start_time, end_time, -1)
    else:
        # First, remove the network file, if it exists
        escaped_url = common_module.escape_page(url)
        network_filename = os.path.join(output_directory, 'network_' + escaped_url)
        if os.path.exists(network_filename):
            os.remove(network_filename)
        tracing_filename = os.path.join(output_directory, 'tracing_' + escaped_url)
        if os.path.exists(tracing_filename):
            os.remove(tracing_filename)

        if args.get_dependency_baseline:
            debugging_socket = ChromeRDPWebsocketStreaming(debugging_url, url, device_configuration, user_agent_str, args.collect_console, args.collect_tracing, callback_on_received_event, None, args.preserve_cache, args.defer_stop)
            def timeout_handler(a, b):
                callback_on_page_done_streaming(debugging_socket)
                sys.exit(0)

            print 'Setting SIGTERM handler'
            signal.signal(signal.SIGTERM, timeout_handler)
        else:
            debugging_socket = ChromeRDPWebsocketStreaming(debugging_url, url, device_configuration, user_agent_str, args.collect_console, args.collect_tracing, callback_on_received_event, callback_on_page_done_streaming, args.preserve_cache, args.defer_stop)
        debugging_socket.start()
    
def output_cpu_running_chrome(output_directory, cpu_id):
    '''
    Outputs the CPU id that is running chrome.
    '''
    cpu_running_chrome_filename = os.path.join(output_directory, 'cpu_running_chrome.txt')
    with open(cpu_running_chrome_filename, 'wb') as output_file:
        output_file.write(cpu_id)

def create_output_directory_for_url(url):
    '''
    Creates an output directory for the url
    '''
    base_dir = ''
    if OUTPUT_DIR is not None:
        base_dir = os.path.join(base_dir, OUTPUT_DIR)
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
    
    final_url = common_module.escape_page(url)

    base_dir = os.path.join(base_dir, final_url)
    # Create the directory if the directory doesn't exist.
    if not os.path.exists(base_dir):
        os.mkdir(base_dir)
    return base_dir

def callback_on_received_event(debugging_socket, network_message, network_message_string):
    url = debugging_socket.get_navigation_url()
    base_dir = create_output_directory_for_url(url)
    final_url = common_module.escape_page(url)
    if 'method' in network_message and network_message['method'].startswith('Network'):
        network_filename = os.path.join(base_dir, 'network_' + final_url)
        with open(network_filename, 'ab') as output_file:
            output_file.write('{0}\n'.format(network_message_string))
    elif 'method' in network_message and network_message['method'].startswith('Console'):
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
    debugging_socket.close_connection()
    print 'Closed debugging socket connection'

    sleep(2)
    url = debugging_socket.get_navigation_url()
    debugging_url = debugging_socket.get_debugging_url()
    final_url = common_module.escape_page(url)
    base_dir = create_output_directory_for_url(url)
    
    new_debugging_websocket = websocket.create_connection(debugging_url)
    # Get the start and end time of the execution
    start_time, end_time, dom_content_loaded = navigation_utils.get_start_end_time_with_socket(new_debugging_websocket)
    # print 'output dir: ' + base_dir
    print 'Load time: ' + str((start_time, end_time)) + ' ' + str((end_time - start_time))
    write_page_start_end_time(final_url, base_dir, start_time, end_time, dom_content_loaded, -1, -1)
    print 'getting DOM tree'
    if args.record_content:
        body = navigation_utils.get_modified_html(new_debugging_websocket)
        with open(os.path.join(base_dir, 'root_html'), 'wb') as output_file:
            output_file.write(body)

    if args.get_dom:
        dom = navigation_utils.get_dom_tree(new_debugging_websocket)
        with open(os.path.join(base_dir, 'dom'), 'wb') as output_file:
            output_file.write(dom)


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


if __name__ == '__main__':
    argparser = ArgumentParser()
    argparser.add_argument('config_filename')
    argparser.add_argument('device', help='The device name e.g. Nexus_6')
    argparser.add_argument('url', help='The URL to navigate to e.g. http://apple.com')
    argparser.add_argument('--output-dir', help='The output directory of the generated files', default=None)
    argparser.add_argument('--disable-tracing', default=False, action='store_true')
    argparser.add_argument('--reload-page', default=False, action='store_true')
    argparser.add_argument('--record-content', default=False, action='store_true')
    argparser.add_argument('--collect-console', default=False, action='store_true')
    argparser.add_argument('--get-chromium-logs', default=False, action='store_true')
    argparser.add_argument('--get-dependency-baseline', default=False, action='store_true')
    argparser.add_argument('--collect-tracing', default=False, action='store_true')
    argparser.add_argument('--preserve-cache', default=False, action='store_true')
    argparser.add_argument('--defer-stop', default=False, action='store_true')
    argparser.add_argument('--get-dom', default=False, action='store_true')
    args = argparser.parse_args()

    # Setup the config filename
    config_reader = ConfigParser()
    config_reader.read(args.config_filename)
    OUTPUT_DIR = args.output_dir

    # Get the device configuration.
    device_config = config.get_device_configuration(config_reader, args.device)
    main(device_config, args.url, args.disable_tracing, args.reload_page)
