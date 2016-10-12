def convert_to_ms_precision(timestamp):
    '''
    Converts the timestamp to millisecond precision.
    '''
    return timestamp * 1000

def extract_url_from_path(path):
    '''
    Extracts the url from the path.
    '''
    if path.endswith('/'):
        path = path[:len(path) - 1]
    last_delim_index = -1
    for i in range(0, len(path)):
        if path[i] == '/':
            last_delim_index = i
    url = path[last_delim_index + 1:].replace('/', '_')
    return url

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


def parse_pages_to_ignore(pages_to_ignore_filename):
    pages = set()
    if pages_to_ignore_filename is not None:
        with open(pages_to_ignore_filename, 'rb') as input_file:
            for raw_line in input_file:
                line = raw_line.strip()
                pages.add(escape_page(line))
    print pages
    return pages

def parse_page_start_end_time(filename):
    with open(filename, 'rb') as input_file:
        line = input_file.readline().strip().split()
        web_perf_nav_start = float(line[1])
        web_perf_load_event = float(line[2])
        chrome_ts_nav_start = float(line[3])
        chrome_ts_load_event = float(line[4])
        return (line[0], (web_perf_nav_start, web_perf_load_event), (chrome_ts_nav_start, chrome_ts_load_event))
