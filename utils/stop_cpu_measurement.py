import phone_connection_utils

from argparse import ArgumentParser
from ConfigParser import ConfigParser
from time import sleep

measurement_directory = '/sdcard/Research/result.txt'

if __name__ == '__main__':
    argparser = ArgumentParser()
    argparser.add_argument('config_filename')
    argparser.add_argument('device')
    argparser.add_argument('output_dir')
    args = argparser.parse_args()

    # Setup the config filename
    config_reader = ConfigParser()
    config_reader.read(args.config_filename)
    # Get the device configuration.
    device_config = phone_connection_utils.get_device_configuration(config_reader, args.device)
    # phone_connection_utils.toggle_cpu_measurement(device_config)
    phone_connection_utils.bring_cpu_measurement_to_foreground(device_config)
    sleep(10)
    phone_connection_utils.kill_cpu_measurement(device_config)
    phone_connection_utils.fetch_cpu_measurement_file(device_config, measurement_directory, args.output_dir)
