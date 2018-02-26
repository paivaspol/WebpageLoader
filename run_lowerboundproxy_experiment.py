from argparse import ArgumentParser

from utils import script_runner
from utils.pacfile import Pacfile

import common_module
import json
import os
import tempfile
import time
import subprocess
import urllib

CONFIG_PREFETCH_SERVER = 'prefetchServer'
CONFIG_DOWNLINK = 'downlink'
CONFIG_UPLINK = 'uplink'
CONFIG_RTT = 'rtt'

def main():
    config = GetConfig(args.config)
    SetupPacfile(config)
    ShapeNetwork(config)
    urls = GetUrls(config['pageList'])
    for url in urls:
        escaped_url = common_module.escape_page(url)

        # Start the proxy and prefetch injection webserver.
        # ./run_proxy.sh 8080 8081 proxy/important proxy/order
        start_proxy_command = [ \
                config['proxyLocation'] + '/run_proxy.sh', \
                config['proxyLocation'], \
                str(config['lowerboundProxyPort']), \
                str(config['prefetchServerPort']), \
                os.path.join(config['prefetchUrlsDir'], escaped_url), \
                os.path.join(config['requestOrderDir'], escaped_url) \
        ]
        print ' '.join(start_proxy_command)
        subprocess.Popen(start_proxy_command)
        time.sleep(2)
        ps_cmd = 'ps aux | grep "go"'
        proc = subprocess.Popen(ps_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        print stdout
        print ''
        print stderr

        # Generate the URL for prefetching.
        redirectUrl = GenerateRedirectURL(config[CONFIG_PREFETCH_SERVER], url)
        print 'redirectURL: {0}'.format(redirectUrl)
        url_file = tempfile.NamedTemporaryFile()
        url_file.write(redirectUrl)
        url_file.flush()

        # Shape the network and run the crawler.
        crawler_cmd = 'python page_load_wrapper.py {0} {1} {2} --use-device={3} --collect-tracing'.format(url_file.name, config['iterations'], config['outputDir'], config['device'])
        subprocess.call(crawler_cmd.split(' '))

        url_file.close()
        stop_proxy_command = [ config['proxyLocation'] + '/stop_proxy.sh' ]
        subprocess.call(stop_proxy_command)

        # Fix the filenames.
        RemovePrefetchServerPrefixes(config, redirectUrl, escaped_url)

def RemovePrefetchServerPrefixes(config, redirect_url, escaped_page):
    ''' Fixes the name of the results by removing the prefetch server prefixes '''
    for i in range(0, int(config['iterations'])):
        iter_dir = os.path.join(config['outputDir'], str(i))
        for p in os.listdir(iter_dir):
            prefixed_page = common_module.escape_page(redirect_url)
            page_dir = os.path.join(iter_dir, prefixed_page)

            # Change the file name that contains the prefetch server.
            for f in page_dir:
                if prefixed_page not in f:
                    continue
                first_idx = f.find(prefixed_page)
                unprefixed_f = f[:first_idx] + p

                # Move the file.
                src = os.path.join(page_dir, f)
                dst = os.path.join(page_dir, unprefixed_f)
                mv_cmd = 'mv {0} {1}'.format(src, dst)
                subprocess.call(mv_cmd.split())
    
            # Now that we fixed all the files in the directory, 
            # fix the page directory.
            src = os.path.join(iter_dir, prefixed_page)
            dst = os.path.join(iter_dir, escaped_page)
            mv_cmd = 'mv {0} {1}'.format(src, dst)
            subprocess.call(mv_cmd.split(' '))
    dst = os.path.join(config['outputDir'], escaped_page)


def SetupPacfile(config):
    ''' Setup pacfile creates a pac file and push it down to the device '''
    pacfile = Pacfile()
    pacfile.AddRule('shExpMatch(url, "*{0}/prefetch*")'.format(config[CONFIG_PREFETCH_SERVER]), 'DIRECT')
    pacfile.SetDefaultRule('PROXY ' + '{0}:{1}'.format(config['proxyHost'], config['lowerboundProxyPort']))
    pac_filename = 'tmp.pac'
    with open(pac_filename, 'w') as output_file:
        output_file.write(str(pacfile))
    print 'Pushing PAC file to phone'
    cmd = 'adb -s {0} push {1} {2}'.format(config['deviceSerial'], pac_filename, '/sdcard/Research/proxy.pac')
    subprocess.call(cmd.split())
    rm_cmd = 'rm ' + pac_filename
    subprocess.call(rm_cmd.split())


def ShapeNetwork(config):
    '''
    Shapes the network according to the parameters specified in the config file.
    '''
    print 'Shaping the network with DOWN: {0} UP: {1} RTT (each way): {2}'.format(config[CONFIG_DOWNLINK], config[CONFIG_UPLINK], config[CONFIG_RTT])
    if config[CONFIG_DOWNLINK] == 'inf' or \
        config[CONFIG_UPLINK] == 'inf' or \
        config[CONFIG_RTT] == 'inf':
        script_runner.clear_traffic_shaping()
    else:
        script_runner.shape_traffic(config[CONFIG_DOWNLINK], \
                                    config[CONFIG_UPLINK], \
                                    config[CONFIG_RTT])


def GenerateRedirectURL(prefetch_webserver, url):
    '''
    Returns the redirect URL in the form of prefetch_webserver + query_encoded(url)
    '''
    query = { 'dstPage': url }
    hostname = prefetch_webserver if prefetch_webserver.endswith('/') else prefetch_webserver + '/'
    return '{0}prefetch?{1}'.format(hostname, urllib.urlencode(query))


def GetConfig(config):
    '''
    Returns the config file
    '''
    with open(config, 'rb') as input_file:
        config = json.load(input_file)
        config[CONFIG_PREFETCH_SERVER] = 'http://{0}:{1}'.format(config['proxyHost'], config['prefetchServerPort'])
        return config


def GetUrls(page_list):
    '''
    Returns a list of pages specified in the page list file.
    It returns the redirected page.
    '''
    pages = []
    with open(page_list, 'r') as input_file:
        for l in input_file:
            if l.startswith('#'):
                continue
            l = l.strip().split()
            pages.append(l[len(l) - 1])
    return pages


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('config')
    args = parser.parse_args()
    main()
