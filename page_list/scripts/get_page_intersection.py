from argparse import ArgumentParser

import requests

HTTP_PREFIX = 'http://'
WWW_PREFIX = 'www.'

def escape_page(url):
    url = url[len(HTTP_PREFIX):]
    if url.startswith(WWW_PREFIX):
        url = url[len(WWW_PREFIX):]
    return url.replace('/', '_')

def read_pages_file(page_list_filename):
    result = set()
    with open(page_list_filename, 'rb') as input_file:
        for line in input_file:
            result.add(escape_page(line.strip()))
    return result

def get_http2_adoption_list(url='http://isthewebhttp2yet.com/data/lists/H2-true-2016-02-11.txt'):
    request = requests.get(url)
    return set(request.text.split())

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('page_list_filename')
    args = parser.parse_args()
    http2_adopted_pages = get_http2_adoption_list()
    top_page_list = read_pages_file(args.page_list_filename)
    intersection = set.intersection(http2_adopted_pages, top_page_list)
    print '# HTTP/2 adopted pages: {0}, # Top Pages: {1}, # intersection: {2}'.format(len(http2_adopted_pages), len(top_page_list), len(intersection))
    print 'intersection: {0}'.format(intersection)
