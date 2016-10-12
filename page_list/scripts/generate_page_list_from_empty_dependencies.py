from argparse import ArgumentParser

import common_module
import os

def find_pages_with_zero_dependencies(dependency_directory, page_dict):
    pages = os.listdir(dependency_directory)
    for page in pages:
        dependency_filename = os.path.join(dependency_directory, page, 'dependency_tree.txt')
        if os.path.exists(dependency_filename):
            with open(dependency_filename, 'rb') as input_file:
                num_lines = len(input_file.readlines())
                if num_lines == 0 and page in page_dict:
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
    parser.add_argument('dependency_directory')
    args = parser.parse_args()
    page_dict = get_page_dict(args.page_list_filename)
    find_pages_with_zero_dependencies(args.dependency_directory, page_dict)

