from argparse import ArgumentParser

import tldextract
import random

TARGET = 1000

def sample_data(page_list_file):
    sampled_domains = set()
    websites = []
    with open(page_list_file, 'rb') as input_file:
        for raw_line in input_file:
            line = raw_line.strip()
            websites.append('http://www.' + line)

    index_ranges = []
    index_ranges.append(range(0, 10000))
    index_ranges.append(range(10000, 100000))
    index_ranges.append(range(100000, 1000000))

    chosen_indexes = set()
    counter = 1
    for index_range in index_ranges:
        while len(chosen_indexes) < counter * TARGET:
            index = random.sample(index_range, 1)[0]
            sampled_domain = extract_domain(websites[index])
            if sampled_domain not in sampled_domains and \
                index not in chosen_indexes:
                chosen_indexes.add(index)
                sampled_domains.add(sampled_domain)
        counter += 1

    for i in chosen_indexes:
        print websites[i]

def extract_domain(url):
    parsed_uri = tldextract.extract(url)
    return parsed_uri.domain + '.' + parsed_uri.suffix

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('page_list_file')
    args = parser.parse_args()
    sample_data(args.page_list_file)
