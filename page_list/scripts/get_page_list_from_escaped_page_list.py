from argparse import ArgumentParser

def get_pages(filename):
    result = set()
    with open(filename, 'rb') as input_file:
        for raw_line in input_file:
            result.add(raw_line.strip())
    return result

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
    parser.add_argument('original_file')
    parser.add_argument('escaped_page_file')
    args = parser.parse_args()
    escaped_page_set = get_pages(args.escaped_page_file)
    with open(args.original_file, 'rb') as input_file:
        for raw_line in input_file:
            escaped_url = escape_page(raw_line.strip())
            if escaped_url in escaped_page_set:
                print raw_line.strip()
