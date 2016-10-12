from argparse import ArgumentParser

import common_module

def main(page_filename):
    with open(page_filename, 'rb') as input_file:
        for raw_line in input_file:
            line = raw_line.strip().split()
            if common_module.escape_page(line[0]) != common_module.escape_page(line[1]):
                print raw_line.strip()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('page_filename')
    args = parser.parse_args()
    main(args.page_filename)
