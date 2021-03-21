from argparse import ArgumentParser

import common_module
import os
import json
import shutil
import subprocess
import tempfile

def Main():
    if not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)

    pages = common_module.get_pages(args.page_list)

    for p in pages:
        for i in range(0, args.iterations):
            iteration_output_dir = os.path.join(args.output_dir, str(i))
            if not os.path.exists(iteration_output_dir):
                os.mkdir(iteration_output_dir)
            print(iteration_output_dir)

            record_output_dir = os.path.join(iteration_output_dir, 'records')
            devtools_log_output_dir = os.path.join(iteration_output_dir, 'devtools_logs')
            if not os.path.exists(record_output_dir):
                os.mkdir(record_output_dir)
                os.mkdir(devtools_log_output_dir)

            GeneratePageHashFile(pages, iteration_output_dir)

            # command: rm -rf temp_record && /home/vaspol/Research/MobileWebOptimization/page_load_setup/build/bin/mm-webrecord temp_record ./run_plw.sh
            p = p[-1]
            with tempfile.NamedTemporaryFile() as temp:
                temp.write('{0} {0}\n'.format(p))
                temp.flush()
                escaped_page = common_module.escape_page(p)
                if args.use_page_hash:
                    escaped_page = str(hash(p))
                page_record_dir = os.path.join(record_output_dir, escaped_page)
                if os.path.exists(page_record_dir):
                    shutil.rmtree(page_record_dir)
                page_devtools_logs_dir = os.path.join(devtools_log_output_dir, escaped_page)
                command = [
                        '/home/vaspol/Research/MobileWebOptimization/page_load_setup/build/bin/mm-webrecord',
                        page_record_dir, 'python', 'page_load_wrapper.py',
                        temp.name, '1', devtools_log_output_dir,
                        '--use-device=ubuntu_no_throttle', '--collect-console',
                        '--collect-tracing', '--defer-stop' ]
                if args.use_page_hash:
                    command.append('--use-page-hash={0}'.format(iteration_output_dir))

                print(command)
                subprocess.call(command)
            subprocess.call([ 'pkill', 'chrome' ])
            # all_veths = FindNetworkInterfaces(subprocess.check_output([ 'ifconfig' ]))
            # for veth in all_veths:
            #     try:
            #         p = subprocess.Popen(["sudo", "-S", "ifconfig", veth, 'down' ], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            #         p.communicate("Themag1e@\n")
            #         p.terminate()
            #     except Exception as e:
            #         pass


def FindNetworkInterfaces(ifconfig_output):
    all_veths = []
    for l in ifconfig_output:
        if l.startswith('veth'):
            # line: veth-3058 Link encap:Ethernet  HWaddr 9a:a9:24:89:7a:7e
            l = l.strip().split()
            all_veths.append(l[0])
    return all_veths


def GeneratePageHashFile(page_list, output_dir):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    hash_to_url = {}
    url_to_hash = {}
    for l in page_list:
        url = l[-1].strip()
        hash_val = str(hash(url))
        hash_to_url[hash_val] = url
        url_to_hash[url] = hash_val

    with open(os.path.join(output_dir, 'hash_to_url'), 'w') as output_file:
        json.dump(hash_to_url, output_file)

    with open(os.path.join(output_dir, 'url_to_hash'), 'w') as output_file:
        json.dump(url_to_hash, output_file)
    return url_to_hash, hash_to_url


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('page_list')
    parser.add_argument('output_dir')
    parser.add_argument('--use-page-hash', default=False, action='store_true')
    parser.add_argument('--iterations', default=1, type=int)
    args = parser.parse_args()
    Main()
