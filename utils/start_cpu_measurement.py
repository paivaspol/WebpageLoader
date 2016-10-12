import subprocess
import phone_connection_utils

from time import sleep
from argparse import ArgumentParser
from ConfigParser import ConfigParser

if __name__ == '__main__':
    argparser = ArgumentParser()
    argparser.add_argument('config_filename')
    argparser.add_argument('device')
    argparser.add_argument('--kill-existing-measurement', action='store_true')
    args = argparser.parse_args()

    # Setup the config filename
    config_reader = ConfigParser()
    config_reader.read(args.config_filename)
    # Get the device configuration.
    device_config = phone_connection_utils.get_device_configuration(config_reader, args.device)
    if args.kill_existing_measurement:
        phone_connection_utils.kill_cpu_measurement(device_config)
    sleep(5)
    phone_connection_utils.start_cpu_measurement(device_config)
