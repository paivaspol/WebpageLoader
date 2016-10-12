import subprocess
import os
import requests
import time
import sys

if len(sys.argv) == 1:
    print 'Usage: wrapper.py [number of loads]'
    exit(1)

num_loads = sys.argv[1]

start_squid_proxy = 'http://ec2-54-237-249-55.compute-1.amazonaws.com:5005/start_squid_proxy'
result = requests.get(start_squid_proxy)

time.sleep(10)
print 'starting page load...'

command = 'python -u page_load_wrapper.py ../page_list/selected_test_pages.txt {0} --use-device Nexus_6_chromium --dont-start-measurements --disable-tracing --collect-streaming --output-dir ../../results/real_load_to_record_comparison/regular_load_new_{0}_loads'.format(num_loads)
# command = 'python -u page_load_wrapper.py ../page_list/continue_page_load.txt 5 --use-device Nexus_6_chromium --dont-start-measurements --disable-tracing --collect-streaming --output-dir ../../results/real_load_to_record_comparison/regular_load_new'
subprocess.call(command.split())

print 'stopping squid proxy'
stop_squid_proxy = 'http://ec2-54-237-249-55.compute-1.amazonaws.com:5005/stop_squid_proxy'
result = requests.get(stop_squid_proxy)
