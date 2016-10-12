from argparse import ArgumentParser

import common_module
import os

def generate_page_list(escaped_page_list_filename, page_dict):
    with open(escaped_page_list_filename, 'rb') as input_file:
        for raw_line in input_file:
            page = raw_line.strip()
            if page in page_dict:
                print page_dict[page]

def get_page_dict(page_list_filename):
    result_dict = dict()
    with open(page_list_filename,'rb') as input_file:
        for raw_line in input_file:
            if not raw_line.startswith('#'):
                line = raw_line.strip().split()
                url = line[len(line) - 1]
                result_dict[escape_page(url)] = url
    return result_dict

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

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('page_list_filename')
    parser.add_argument('escaped_page_list')
    args = parser.parse_args()
    page_dict = get_page_dict(args.page_list_filename)
    generate_page_list(args.escaped_page_list, page_dict)
