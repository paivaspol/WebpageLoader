from argparse import ArgumentParser

import simplejson as json
import os

def main(root_dir):
    pages = os.listdir(root_dir)
    for page in pages:
        network_filename = os.path.join(root_dir, page, 'network_' + page)
        if not os.path.exists(network_filename):
            continue
        first_url, url = get_url(network_filename, page)
        if args.print_first_url:
            print first_url + ' ' + url
        else:
            print url

def get_url(network_filename, page):
    with open(network_filename, 'rb') as network_file:
        first_request_id = None
        final_url = None
        first_url = None
        for raw_line in network_file:
            network_event = json.loads(json.loads(raw_line.strip()))
            if network_event['method'] == 'Network.requestWillBeSent':
                if first_request_id is None and escape_page(network_event['params']['request']['url']) == page:
                    first_request_id = network_event['params']['requestId']
                    final_url = network_event['params']['request']['url']
                    first_url = final_url
                elif first_request_id is not None and first_request_id == network_event['params']['requestId']:
                    final_url = network_event['params']['request']['url']
        return first_url, final_url

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
    parser.add_argument('root_dir')
    parser.add_argument('--print-first-url', default=False, action='store_true')
    args = parser.parse_args()
    main(args.root_dir)
