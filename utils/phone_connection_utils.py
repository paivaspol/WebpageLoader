import subprocess
import threading
import os
import random

from time import sleep
from ConfigParser import ConfigParser

PCAP_DIRECTORY = '/sdcard/Research/output.pcap'
SCREEN_RECORD_DIR = '/sdcard/Research/page_load.mp4'
RESULT_DIRECTORY = '../result/'

DEVICE_ID = 'id'
IP = 'ip'
ADB_PORT = 'adb_port'
CHROME_DESKTOP_DEBUG_PORT = 'chrome_desktop_debugging_port'
DEVICE_TYPE = 'type'
CHROME_INSTANCE = 'chrome_instance'
WEB_SOCKET_DEBUGGER_URL = 'webSocketDebuggerUrl'
USE_CHROMIUM = 'use_chromium'

DEVICE_PHONE = 'phone'
DEVICE_MAC = 'mac'
DEVICE_UBUNTU = 'ubuntu'

ANDROID_CHROME_INSTANCE = 'com.android.chrome/com.google.android.apps.chrome.Main'
ANDROID_CHROMIUM_INSTANCE = 'org.chromium.chrome/com.google.android.apps.chrome.Main'
MAC_CHROME_INSTANCE = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
UBUNTU_CHROME_INSTANCE = '"/opt/google/chrome/google-chrome"'

CHANGE_USER_AGENT = 'change_user_agent'
SCREEN_SIZE = 'screen_size'
USER_AGENT = 'user_agent'
IGNORE_CERTIFICATE_ERRORS = 'ignore_certificate_errors'
USER_AGENT_STR = 'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 6 Build/MMB29S) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2645.0 Mobile Safari/537.36'
PAC_FILE_PATH = 'pac_file_path'

global chrome_proc
chrome_proc = None
global devnull

def start_chrome(device_configuration):
    '''
    Setup and run chrome on Android.
    '''
    if device_configuration[DEVICE_TYPE] == DEVICE_PHONE:
        # Setup port-forwarding for RDP
        cmd_base = 'adb -s {0} forward tcp:{1} localabstract:chrome_devtools_remote'
        cmd = cmd_base.format(device_configuration[DEVICE_ID], device_configuration[ADB_PORT])
        p = subprocess.Popen(cmd, shell=True)
        bring_chrome_to_foreground(device_configuration)
        sleep(3) # So we have enough time to forward the port.

        return p
    elif device_configuration[DEVICE_TYPE] == DEVICE_MAC or \
        device_configuration[DEVICE_TYPE] == DEVICE_UBUNTU:
        # print 'device config: ' + str(device_configuration)
        # Run Chrome.
        print "Run experiment chrome"
        cmd = [ device_configuration[CHROME_INSTANCE] ]
        args = '--disable-extensions --remote-debugging-port={0} --disable-logging --enable-devtools-experiments --user-data-dir=/tmp/chrome-{1} --no-first-run'.format(device_configuration[CHROME_DESKTOP_DEBUG_PORT], random.random())
        if PAC_FILE_PATH in device_configuration:
            args += ' --proxy-pac-url={0}'.format(device_configuration[PAC_FILE_PATH])
        if IGNORE_CERTIFICATE_ERRORS in device_configuration:
            args += ' --ignore-certificate-errors'
        cmd.extend(args.split(' '))
        global chrome_proc
        global devnull
        devnull = open(os.devnull, 'wb')
        chrome_proc = subprocess.Popen(cmd, stdout=devnull, stderr=devnull)
        sleep(3)
        return chrome_proc

def bring_chrome_to_foreground(device_configuration):
    # Run chrome
    cmd_base = 'adb -s {0} shell "am start -a android.intent.action.VIEW -n {1}"'
    cmd = cmd_base.format(device_configuration[DEVICE_ID], device_configuration[CHROME_INSTANCE])
    p = subprocess.Popen(cmd, shell=True)

def stop_chrome(device_configuration):
    '''
    Kill the chrome process that is running.
    '''
    if device_configuration[DEVICE_TYPE] == DEVICE_PHONE:
        chrome_instance = "com.android.chrome"
        if device_configuration[CHROME_INSTANCE] == ANDROID_CHROMIUM_INSTANCE:
            chrome_instance = "org.chromium.chrome"
        cmd_base = 'adb -s {0} shell am force-stop {1}'
        cmd = cmd_base.format(device_configuration[DEVICE_ID], chrome_instance)
        # print cmd
        subprocess.call(cmd, shell=True)
    elif device_configuration[DEVICE_TYPE] == DEVICE_MAC or \
        device_configuration[DEVICE_TYPE] == DEVICE_UBUNTU:
        global chrome_proc
        global devnull
        if chrome_proc is not None:
            chrome_proc.kill()
            devnull.close()
            # os.killpg(os.getpgid(chrome_proc.pid), signal.SIGTERM)
            # subprocess.call('pkill -9 chrome', shell=True)

def bring_openvpn_connect_foreground(device_configuration):
    # Run chrome
    cmd_base = 'adb -s {0} shell "am start -a android.intent.action.VIEW -n net.openvpn.openvpn/net.openvpn.openvpn.OpenVPNClient"'
    cmd = cmd_base.format(device_configuration[DEVICE_ID], device_configuration[CHROME_INSTANCE])
    subprocess.call(cmd, shell=True)
    sleep(2)

def toggle_openvpn_button(device_configuration):
    cmd = 'adb -s {0} shell input tap 706 780'.format(device_configuration[DEVICE_ID])
    subprocess.call(cmd, shell=True)
    sleep(1)

def is_connected_to_vpn(device_configuration):
    cmd = 'adb -s {0} shell ifconfig'.format(device_configuration[DEVICE_ID])
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    return 'tun0' in stdout

def start_screen_recording(device_configuration):
        # cmd_base = 'adb -s {0} shell \'su -c \'/tcpdump -i wlan0 -n -s 0 -w {1}\'\''
    cmd = 'adb -s {0} shell screenrecord /sdcard/Research/page_load.mp4'.format(device_configuration[DEVICE_ID])
    subprocess.Popen(cmd, shell=True)

def end_screen_recording(device_configuration, sleep_before_kill=True):
    # if sleep_before_kill:
    #     sleep(3)
    kill_process_on_phone('screenrecord', device_configuration[DEVICE_ID])
    sleep(5)

def start_tcpdump(device_configuration):
    '''
    Starts tcpdump on the phone.
    '''
    tcpdump_started = False
    while not tcpdump_started:
        # cmd_base = 'adb -s {0} shell \'su -c \'/tcpdump -i wlan0 -n -s 0 -w {1}\'\''
        interface = 'wlan0'
        cmd_base = 'adb -s {0} shell ifconfig'.format(device_configuration[DEVICE_ID])
        proc = subprocess.Popen(cmd_base, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if 'rndis0' in stdout:
            interface = 'rndis0'
        cmd_base = 'adb -s {0} shell \'su -c \'/tcpdump -i {1} -n -s 0 -w {2}\'\''
        cmd = cmd_base.format(device_configuration[DEVICE_ID], interface, PCAP_DIRECTORY)
        retval = subprocess.Popen(cmd, shell=True)
        get_tcp_dump_process = 'adb -s {0} shell \'su -c \'ps | grep tcpdump\'\''.format(device_configuration[DEVICE_ID])
        result = subprocess.check_call(get_tcp_dump_process, shell=True)
        # print result
        tcpdump_started = True
    return retval

def stop_tcpdump(device_configuration, sleep_before_kill=True):
    '''
    Stops tcpdump on the phone.
    '''
    if sleep_before_kill:
        print 'Sleeping before killing tcpdump.'
        sleep(45) # Give sometime for tcpdump to be finished.
    # cmd_base = 'adb -s {0} shell ps | grep tcpdump | awk \'{{ print $2 }}\' | xargs adb -s {0} shell "su -c kill -9"'
    # cmd_base = 'adb -s {0} shell ps | grep tcpdump | awk \'{{ print $1 }}\' | xargs adb -s {0} shell "su -c kill -9"' # with busybox installed
    # cmd = cmd_base.format(device_configuration[DEVICE_ID])
    # return subprocess.Popen(cmd, shell=True)
    kill_process_on_phone('tcpdump', device_configuration[DEVICE_ID])
    # print cmd

def kill_process_on_phone(process_name, device_id):
    cmd_base = 'adb -s {0} shell ps | grep {1} | awk \'{{ print $1 }}\' | xargs adb -s {0} shell "su -c kill -2"' # with busybox installed
    cmd = cmd_base.format(device_id, process_name)
    subprocess.call(cmd, shell=True)

def fetch_pcap(device_configuration, pcap_directory=PCAP_DIRECTORY, destination_directory=RESULT_DIRECTORY):
    '''
    Fetches the pcap file from the phone.
    '''
    fetch_file(device_configuration, pcap_directory, destination_directory, remove_file=True)

def fetch_screen_record(device_configuration, screen_record_directory=SCREEN_RECORD_DIR, destination_directory=RESULT_DIRECTORY):
    '''
    Fetches the pcap file from the phone.
    '''
    fetch_file(device_configuration, screen_record_directory, destination_directory, remove_file=True)

def fetch_cpu_measurement_file(device_configuration, measurement_dir, destination_directory):
    print 'Fetching CPU Measurement file...'
    fetch_file(device_configuration, measurement_dir, destination_directory, remove_file=True)

def fetch_file(device_configuration, file_location_on_phone, destination_directory, remove_file=False):
    print 'destination directory: ' + destination_directory
    cmd_base = 'adb -s {0} pull {1} {2}'
    cmd = cmd_base.format(device_configuration[DEVICE_ID], file_location_on_phone, destination_directory)
    os.system(cmd)
    if remove_file:
        cmd_base = 'adb -s {0} shell rm {1}'
        cmd = cmd_base.format(device_configuration[DEVICE_ID], file_location_on_phone)
        os.system(cmd)

def push_file(device_configuration, source, destination):
    cmd = 'adb -s {0} push {1} {2}'.format(device_configuration[DEVICE_ID], source, destination)
    subprocess.call(cmd.split())

def kill_cpu_measurement(device_configuration):
    command = 'adb -s {0} shell am force-stop edu.michigan.pageloadcpumeasurement'
    cmd = command.format(device_configuration[DEVICE_ID])
    subprocess.Popen(cmd, shell=True)

def start_cpu_measurement(device_configuration):
    command = 'adb -s {0} shell am start -n edu.michigan.pageloadcpumeasurement/.MainActivity'
    cmd = command.format(device_configuration[DEVICE_ID])
    subprocess.Popen(cmd, shell=True)

def bring_cpu_measurement_to_foreground(device_configuration):
    command = 'adb -s {0} shell am broadcast -a "android.intent.action.PROCESS_TEXT"'
    cmd = command.format(device_configuration[DEVICE_ID])
    subprocess.Popen(cmd, shell=True).wait()

def get_device_configuration(config_reader, device):
    '''
    Constructs a device configuration map.
    '''
    device_config = dict()
    device_config[IP] = config_reader.get(device, IP)
    device_type = config_reader.get(device, DEVICE_TYPE)
    device_config[DEVICE_TYPE] = device_type
    if device_type == DEVICE_PHONE:
        device_config[ADB_PORT] = int(config_reader.get(device, ADB_PORT))
        device_config[CHROME_INSTANCE] = ANDROID_CHROMIUM_INSTANCE if config_reader.get(device, USE_CHROMIUM) == 'True' else ANDROID_CHROME_INSTANCE
        device_config[DEVICE_ID] = config_reader.get(device, DEVICE_ID)
    elif device_type == DEVICE_MAC:
        device_config[CHROME_DESKTOP_DEBUG_PORT] = int(config_reader.get(device, CHROME_DESKTOP_DEBUG_PORT))
        device_config[CHROME_INSTANCE] = MAC_CHROME_INSTANCE
        if config_reader.get(device, CHANGE_USER_AGENT) == 'True':
            device_config[USER_AGENT] = USER_AGENT_STR
        if config_reader.has_option(device, PAC_FILE_PATH):
            device_config[PAC_FILE_PATH] = config_reader.get(device, PAC_FILE_PATH)
    elif device_type == DEVICE_UBUNTU:
        device_config[CHROME_DESKTOP_DEBUG_PORT] = int(config_reader.get(device, CHROME_DESKTOP_DEBUG_PORT))
        device_config[CHROME_INSTANCE] = UBUNTU_CHROME_INSTANCE
        if config_reader.get(device, CHANGE_USER_AGENT) == 'True':
            device_config[USER_AGENT] = USER_AGENT_STR
        if config_reader.has_option(device, PAC_FILE_PATH):
            device_config[PAC_FILE_PATH] = config_reader.get(device, PAC_FILE_PATH)
        if config_reader.has_option(device, SCREEN_SIZE):
            screen_configs = config_reader.get(device, SCREEN_SIZE).split('$')
            screen_config_dict = dict()
            for screen_config in screen_configs:
                key, value = screen_config.split("=")
                screen_config_dict[key] = value
            device_config[SCREEN_SIZE] = screen_config_dict
        if config_reader.has_option(device, IGNORE_CERTIFICATE_ERRORS):
            device_config[IGNORE_CERTIFICATE_ERRORS] = config_reader.get(device, IGNORE_CERTIFICATE_ERRORS)
    return device_config

def get_cpu_running_chrome(device_config):
    command = 'adb -s {0} shell \'ps -c | grep chrome\''.format(device_config[DEVICE_ID])
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = process.communicate()
    return output.split()[5]

def get_process_ids(device_config, proc_name):
    command = 'adb -s {0} shell \'ps -c | grep {1}\''.format(device_config[DEVICE_ID], proc_name)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = process.communicate()
    lines = output.split()
    result = []
    for l in lines:
        if 'grep' not in l:
            result.append(l.strip().split()[0])
    return result

def pin_process_to_cpu(device_config, bitmask, proc_id):
    command = 'adb -s {0} shell \'su -c \'taskset {1} -p {2}\'\''.format(device_config[DEVICE_ID], \
                                                                         bitmask, proc_id)
    subprocess.call(command, shell=True)

def wake_phone_up(device_config):
    if device_config[DEVICE_TYPE] == DEVICE_PHONE:
        command = 'adb -s {0} shell input keyevent KEYCODE_WAKEUP'.format(device_config[DEVICE_ID])
        subprocess.call(command, shell=True)
        print 'Waking up the phone'

timer = None
index = 0

def start_taking_screenshot_every_x_s(device_config, interval, destination):
    if device_config[DEVICE_TYPE] == DEVICE_PHONE:
        command = 'adb -s {0} shell screencap -p | perl -pe \'s/\\x0D\\x0A/\\x0A/g\' > {1}.png'.format(device_config[DEVICE_ID], os.path.join(destination, str(index)))
        subprocess.call(command, shell=True)
        global timer
        global index
        index += 1
        timer = threading.Timer(interval, start_taking_screenshot_every_x_s, [device_config, interval, destination])
        timer.start()
        print 'Taking screenshot: ' + str(index)

def stop_taking_screenshots(device_config):
    if device_config[DEVICE_TYPE] == DEVICE_PHONE:
        global timer
        global index
        timer.cancel()
        index = 0

SCREEN_OFF_AND_LOCKED = 0
SCREEN_ON_BUT_LOCKED = 1
SCREEN_ON_AND_UNLOCKED = 2
def get_phone_status():
    command = 'adb shell dumpsys power | grep \'mHolding\''
    result = subprocess.check_output(command, shell=True)
    splitted_lines = result.split('\n')
    if 'true' in splitted_lines[0] and \
        'true' in splitted_lines[1]:
        return SCREEN_ON_AND_UNLOCKED
    elif 'false' in splitted_lines[0] and \
        'true' in splitted_lines[1]:
        return SCREEN_ON_BUT_LOCKED
    elif 'false' in splitted_lines[0] and \
        'false' in splitted_lines[1]:
        return SCREEN_OFF_AND_LOCKED

def unlock_phone():
    command = 'adb shell input keyevent 82'
    subprocess.call(command.split())
    command = 'adb shell input text 1111'
    subprocess.call(command.split())
    command = 'adb shell input keyevent 66'
    subprocess.call(command.split())
