from argparse import ArgumentParser

import common_module

def main(base_filename, other_page_files):
    wanted_pages = set()
    for other_page_file in other_page_files:
        wanted_pages.update(get_pages(other_page_file))

    base_file = get_base_file(base_filename)
    for page in base_file:
        escaped_page = common_module.escape_page(page)
        if escaped_page in wanted_pages:
            print '{0} {1}'.format(page, base_file[page])


    

def get_base_file(base_filename):
    with open(base_filename, 'rb') as input_file:
        temp = [ line.strip().split() for line in input_file ]
        return { key: value for key, value in temp }

def get_pages(pages_filename):
    with open(pages_filename, 'rb') as input_file:
        return { common_module.escape_page(line.strip()) for line in input_file }

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('base_filename')
    parser.add_argument('other_page_files', nargs='+')
    args = parser.parse_args()
    main(args.base_filename, args.other_page_files)
