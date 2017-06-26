import phone_connection_utils

from argparse import ArgumentParser
from ConfigParser import ConfigParser

if __name__ == '__main__':
    argparser = ArgumentParser()
    argparser.add_argument('config_filename')
    argparser.add_argument('device', help='The device name e.g. Nexus_6')
    argparser.add_argument('--output-dir')
    argparser.add_argument('--no-sleep', default=False, action='store_true')
    args = argparser.parse_args()

    # Setup the config filename
    config_reader = ConfigParser()
    config_reader.read(args.config_filename)

    # Get the device configuration.
    device_config = phone_connection_utils.get_device_configuration(config_reader, args.device)
    phone_connection_utils.end_screen_recording(device_config, not args.no_sleep)
    if args.output_dir is not None:
        phone_connection_utils.fetch_screen_record(device_config, destination_directory=args.output_dir)
    else:
        phone_connection_utils.fetch_screen_record(device_config)

