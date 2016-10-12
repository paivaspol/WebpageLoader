from argparse import ArgumentParser

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('page_list')
    parser.add_argument('output_dir')
    args = parser.parse_args()
