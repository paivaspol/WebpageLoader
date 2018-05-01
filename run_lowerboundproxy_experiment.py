# python mahimahi_page_script.py /home/vaspol/Research/MobileWebOptimization/third_party_accelerate/random_25 ${RECORD_CONFIG_FILENAME} Nexus_6 6 third_party_speedup_lowerbound /home/vaspol/Research/MobileWebOptimization/results/third_party_accelerate/03_06_prioritized_fixed_bugs --collect-tracing --use-openvpn

from argparse import ArgumentParser

import common_module
import os
import subprocess
import shutil
import urllib

tmp_output_dir = '/tmp/load/'
tmp_page_file = '/tmp/page_file'
record_config_filename = 'replay_configurations/record_config.cfg'

def main():
    pages = GetPages()
    for p in pages:
        print 'Loading ' + p
        with open(tmp_page_file, 'w') as output_file:
            output_file.write(GeneratePageUrl(p) + '\n')

        page_prefetch_filename = os.path.join(args.prefetch_url_dir, common_module.escape_page(p))
        server = StartPrefetchServer(page_prefetch_filename)
        mode = 'third_party_speedup_lowerbound'
        if args.no_prefetch:
            mode = 'passthrough_proxy'

        command = 'python mahimahi_page_script.py {0} {1} Nexus_6_chromium {2} {3} {4} --collect-tracing --use-openvpn'.format(tmp_page_file, record_config_filename, args.iterations, mode, args.output_dir)
        # command = 'python mahimahi_page_script.py {0} {1} Nexus_6_chromium {2} {3} {4} --collect-tracing --use-openvpn --pac-file-location {5}'.format(tmp_page_file, record_config_filename, args.iterations, mode, args.output_dir, 'http://apple-pi.eecs.umich.edu/config_testing.pac')
        subprocess.call(command.split())

        StopPrefetchServer()
        os.remove(tmp_page_file)
    RenameResult()


def GeneratePageUrl(p):
    base_url = 'http://apple-pi.eecs.umich.edu:8080/?'
    get_vars = { 'dstPage': p, 'prefetch': 0 if args.no_prefetch else 1 }
    return base_url + urllib.urlencode(get_vars)


def StartPrefetchServer(page_prefetch_filename):
    cmd = 'go run /home/vaspol/go/src/github.com/paivaspol/lowerboundproxy/prefetch_webserver/prefetchwebserver.go -port=8080 -prefetch-urls={0}'.format(page_prefetch_filename)
    proc = subprocess.Popen(cmd.split())
    print 'Started prefetchserver with {0}'.format(page_prefetch_filename)
    return proc


def StopPrefetchServer():
    cmd = [ 'sudo', 'netstat', '-tulpn' ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = p.stdout.read()
    pid = -1
    for l in output.split('\n'):
        if ':8080' not in l:
            continue
        splitted_l = l.split()
        pid = splitted_l[6].split('/')[0]
        break
    
    cmd = [ 'sudo', 'kill', '-9', str(pid) ]
    print cmd
    subprocess.call(cmd)

def GetPages():
    pages = []
    with open(args.page_list, 'rb') as input_file:
        for l in input_file:
            if l.startswith('#'):
                continue
            splitted_line = l.strip().split()
            pages.append(splitted_line[len(splitted_line) - 1])
    return pages


def RenameResult():
    prefix_with_prefetch = 'apple-pi.eecs.umich.edu:8080_?prefetch=1&dstPage='
    prefix_without_prefetch = 'apple-pi.eecs.umich.edu:8080_?prefetch=0&dstPage='
    # First, rename all the files in the output directory
    for i in range(0, args.iterations):
        iteration_dir = os.path.join(args.output_dir, str(i))
        for p in os.listdir(iteration_dir):
            if not (prefix_with_prefetch in p or prefix_without_prefetch in p):
                # Skip pages without the prefix.
                continue

            prefix = prefix_with_prefetch
            if prefix_without_prefetch in p:
                prefix = prefix_without_prefetch

            page_dir = os.path.join(iteration_dir, p)
            prefix_idx = page_dir.find(prefix)
            escaped_page = common_module.escape_page(urllib.unquote(page_dir[prefix_idx + len(prefix):]))
            for f in os.listdir(page_dir):
                if prefix in f:
                    # Remove the prefix and convert to escaped page
                    f_prefix_idx = f.find(prefix)
                    dst = f[:f_prefix_idx] + escaped_page
                    cmd = 'mv {0} {1}'.format(os.path.join(page_dir, f), os.path.join(page_dir, dst))
                    subprocess.call(cmd.split())
            dst = page_dir[:prefix_idx] + escaped_page
            cmd = 'mv {0} {1}'.format(page_dir, dst)
            subprocess.call(cmd.split())


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('page_list')
    parser.add_argument('iterations', type=int)
    parser.add_argument('prefetch_url_dir')
    parser.add_argument('output_dir')
    parser.add_argument('--no-prefetch', default=False, action='store_true')
    args = parser.parse_args()
    main()
