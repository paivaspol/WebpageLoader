from argparse import ArgumentParser

import subprocess
import os

TEMP_DIRECTORY = 'load_page_temp'
SERVER_SIDE_LOGS = 'server_side_logs'

command = 'python mahimahi_page_script.py {0} replay_configuration_ec2_238.cfg Nexus_6_2_chromium 1 per_packet_delay_replay {1} --collect-streaming --use-openvpn --pac-file-location http://ec2-54-85-76-238.compute-1.amazonaws.com//config_testing.pac --page-time-mapping page_to_timestamp.txt --fetch-server-side-logs'

def run_page_loads(page_list, iterations, output_dir):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    server_side_logs_output_directory = os.path.join(output_dir, SERVER_SIDE_LOGS)
    if not os.path.exists(server_side_logs_output_directory):
        os.mkdir(server_side_logs_output_directory)

    for i in range(0, iterations):
        # Call the command.
        call_command = command.format(page_list, TEMP_DIRECTORY)
        if args.without_dependencies:
            call_command += ' --without-dependencies'
        subprocess.call(command.format(page_list, TEMP_DIRECTORY), shell=True)

        # Move the stuffs to the appropriate output directory.
        iteration_output_directory = os.path.join(output_dir, str(i))
        if not os.path.exists(iteration_output_directory):
            os.mkdir(iteration_output_directory)
        
        # First, move the server-side logs
        iteration_server_side_logs_output_dir = os.path.join(server_side_logs_output_directory, str(i))
        if not os.path.exists(iteration_server_side_logs_output_dir):
            os.mkdir(iteration_server_side_logs_output_dir)

        server_side_logs_dir = os.path.join(TEMP_DIRECTORY, 'server_side_logs')
        for log_filename in os.listdir(server_side_logs_dir):
            src = os.path.join(server_side_logs_dir, log_filename)
            dst = os.path.join(iteration_server_side_logs_output_dir, log_filename)
            move_command = 'mv {0} {1}'.format(src, dst) 
            subprocess.call(move_command, shell=True)

        # Now, move all the stuffs to the output directory.
        temp_page_output = os.path.join(TEMP_DIRECTORY, str(0))
        iteration_output_dir = os.path.join(output_dir, str(i))
        for page_directory in os.listdir(temp_page_output):
            src = os.path.join(temp_page_output, page_directory)
            move_command = 'mv {0} {1}'.format(src, iteration_output_dir)
            subprocess.call(move_command, shell=True)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('page_list')
    parser.add_argument('iterations', type=int)
    parser.add_argument('output_dir')
    parser.add_argument('--without-dependencies', default=False, action='store_true')
    args = parser.parse_args()
    run_page_loads(args.page_list, args.iterations, args.output_dir)
