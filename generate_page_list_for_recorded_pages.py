from argparse import ArgumentParser

import os

def generate_pages_file(root_dir):
    dirs = os.listdir(root_dir)
    for directory in dirs:
        recorded_page = os.path.join(directory, 'response_body', 'index.html')
        prefix = 'http://localhost/website_content/'
        final_url = prefix + recorded_page
        print final_url

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    args = parser.parse_args()
    generate_pages_file(args.root_dir)
