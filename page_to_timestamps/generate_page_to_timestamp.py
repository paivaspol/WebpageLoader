import sys

pages_file = sys.argv[1]

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

page_to_timestamp = {}
with open('page_to_timestamp_all.txt', 'rb') as input_file:
    for raw_line in input_file:
        l = raw_line.strip().split()
        page_to_timestamp[l[0]] = l[1]

with open(pages_file, 'rb') as input_file:
    for raw_line in input_file:
        l = raw_line.strip().split()
        escaped_page = escape_page(l[0])
        if escaped_page in page_to_timestamp:
            print '{0} {1}'.format(escaped_page, page_to_timestamp[escaped_page])
