from argparse import ArgumentParser

import common_module
import os

def main(root_dir, num_iterations, pages):
    for i in range(0, num_iterations):
        directory = os.path.join(root_dir, str(i))
        pages_in_directory = set(os.listdir(directory))
        missing_pages = pages - pages_in_directory
        print '{0} {1}'.format(i, missing_pages)

def get_pages(pages_filename):
    with open(pages_filename, 'rb') as input_file:
        return { common_module.escape_page(x.strip()) for x in input_file }

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    parser.add_argument('pages_filename')
    parser.add_argument('num_iterations', type=int)
    args = parser.parse_args()
    pages = get_pages(args.pages_filename)
    main(args.root_dir, args.num_iterations, pages)
