from argparse import ArgumentParser

def extract_pages(top_pages_filename, num_sites):
    with open(top_pages_filename, 'rb') as input_file:
        counter = 0
        for raw_line in input_file:
            line = raw_line.strip().split()
            if line[1] != 'Hidden':
                print 'http://www.' + line[1]
                counter += 1
                if num_sites != -1 and counter > num_sites:
                    break

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('top_pages_filename')
    parser.add_argument('--num-sites', type=int, default=-1)
    args = parser.parse_args()
    extract_pages(args.top_pages_filename, args.num_sites)
