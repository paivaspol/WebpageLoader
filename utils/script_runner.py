import subprocess

def shape_traffic(uplink='28mbit', downlink='10mbit', rtt='80ms'):
    subprocess.call('sudo ./traffic_shaping.sh {0} {1} {2}'.format(uplink, downlink, rtt), shell=True)

def clear_traffic_shaping():
    subprocess.call('sudo ./clear_traffic_shaping.sh', shell=True)

def build_replay_env(replay_dir, branch):
    subprocess.call('sudo ./checkout_branch_and_build.sh {0} {1}'.format(replay_dir, branch), shell=True)
