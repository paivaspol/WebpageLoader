from argparse import ArgumentParser

import simplejson as json
import os

def main(root_dir, original_pages):
    pages = os.listdir(root_dir)
    mapping = dict()
    for page in pages:
        network_filename = os.path.join(root_dir, page, 'network_' + page)
        if not os.path.exists(network_filename):
            continue
        first_url, url = get_url(network_filename, page)
        mapping[first_url] = url

    for page in original_pages:
        # print page
        if page in mapping:
            url = mapping[page]
            if args.print_first_url:
                try:
                    print page + ' ' + url
                except:
                    pass
            else:
                print url

def get_url(network_filename, page):
    with open(network_filename, 'rb') as network_file:
        first_request_id = None
        final_url = None
        first_url = None
        for raw_line in network_file:
            try:
                network_event = json.loads(json.loads(raw_line.strip()))
            except Exception:
                network_event = json.loads(raw_line.strip())
            if network_event['method'] == 'Network.requestWillBeSent':
                if first_request_id is None and escape_page(network_event['params']['request']['url']) == page:
                    first_request_id = network_event['params']['requestId']
                    final_url = network_event['params']['request']['url']
                    first_url = final_url
                elif first_request_id is not None and first_request_id == network_event['params']['requestId']:
                    final_url = network_event['params']['request']['url']
        if first_url is not None and final_url is not None:
            return first_url[:len(first_url) - 1], final_url
        else:
            return None, None

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

def get_pages(pages_filename):
    with open(pages_filename, 'rb') as input_file:
        return [ x.strip() for x in input_file ]

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    parser.add_argument('original_page_list')
    parser.add_argument('--print-first-url', default=False, action='store_true')
    args = parser.parse_args()
    pages = get_pages(args.original_page_list)
    main(args.root_dir, pages)
