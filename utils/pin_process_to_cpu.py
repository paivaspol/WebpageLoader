import subprocess

def get_process_ids(proc_name):
    command = 'adb shell \'ps | grep {0}\''.format(proc_name)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = process.communicate()
    lines = output.split('\n')
    print output
    result = []
    for l in lines:
        if 'grep' not in l and len(l) > 0:
            result.append(l.strip().split()[0])
    return result

def pin_process_to_cpu(bitmask, proc_id):
    command = 'adb shell \'su -c \'taskset -p {0} {1}\'\''.format(bitmask, proc_id)
    subprocess.call(command, shell=True)

pids = get_process_ids('chromium')
print pids
for pid in pids:
    pin_process_to_cpu('f', pid)

