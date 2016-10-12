from argparse import ArgumentParser
from ConfigParser import ConfigParser

import common_module
import subprocess
import websocket
import os

CONFIG = 'CONFIG'
MM_REPLAY_PATH = 'mm-replay-path'
PAGE_LOAD_SCRIPT_PATH = 'page_load_script_path'
RECORD_DIR = 'record_dir'
SCREEN_SIZE = 'screen_size'

def record_pages(pages, record_dir, page_load_config):
    for page in pages:
        print 'Recording: ' + page
        web_record_path = page_load_config[MM_REPLAY_PATH]
        page_record_dir = os.path.join(record_dir, \
                                       common_module.escape_page(page))
        tmp_filename = create_tmp_file(page)
        page_load_command = 'python {0} {1} 1 --dont-start-measurements \
                             --use-device ubuntu --output-dir .'.format(page_load_config[PAGE_LOAD_SCRIPT_PATH], \
                                                                        tmp_filename)
        command = '{0} {1} {2}'.format(web_record_path, \
                                       page_record_dir, \
                                       page_load_command)
        subprocess.call(command, shell=True)
        delete_tmp_file(tmp_filename)

def create_tmp_file(url):
    tmp_file_path = os.path.join('/tmp', common_module.escape_page(url))
    with open(tmp_file_path, 'wb') as output_file:
        output_file.write(url)
    return tmp_file_path

def delete_tmp_file(tmp_file_path):
    os.remove(tmp_file_path)

def get_pages(pages_filename):
    pages = []
    with open(pages_filename, 'rb') as input_file:
        for raw_line in input_file:
            line = raw_line.strip().split()
            pages.append(line[len(line) - 1])
    return pages

def get_page_load_configuration(config_filename):
    config = dict()
    config_parser = ConfigParser()
    config_parser.read(args.config_filename)
    config[MM_REPLAY_PATH] = config_parser.get(CONFIG, MM_REPLAY_PATH)
    config[PAGE_LOAD_SCRIPT_PATH] = config_parser.get(CONFIG, PAGE_LOAD_SCRIPT_PATH)
    return config

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('pages_filename')
    parser.add_argument('config_filename')
    parser.add_argument('record_dir')
    args = parser.parse_args()
    config = get_page_load_configuration(args.config_filename)
    pages = get_pages(args.pages_filename)
    record_pages(pages, args.record_dir, config)
