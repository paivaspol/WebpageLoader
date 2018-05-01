import json
import requests

import config

def close_all_tabs(device_configuration):
    '''
    Closes all the tabs in Chrome.
    '''
    base_url = 'http://localhost:{0}/json'
    url = base_url.format(get_debugging_port(device_configuration))
    try:
        response = requests.get(url)
        response_json = json.loads(response.text)
        for i in range(0, len(response_json) - 1):
            response = response_json[i]
            page_id = response['id']
            base_url = 'http://localhost:{0}/json/close/{1}'
            url = base_url.format(get_debugging_port(device_configuration), page_id)
            response = requests.get(url)
        print 'Cleared all tabs'
    except Exception as e:
        print 'Got exception: {0} but absorbing it...'.format(e)

def get_debugging_port(device_configuration):
    '''
    Returns the correct Chrome debug port.
    '''
    if device_configuration[config.DEVICE_TYPE] == config.DEVICE_PHONE:
        return device_configuration[config.ADB_PORT]
    elif device_configuration[config.DEVICE_TYPE] == config.DEVICE_MAC or \
        device_configuration[config.DEVICE_TYPE] == config.DEVICE_UBUNTU:
        return device_configuration[config.CHROME_DESKTOP_DEBUG_PORT]

def create_tab(device_configuration):
    '''
    Creates a new tab in Chrome.
    '''
    base_url = 'http://localhost:{0}/json/new'
    url = base_url.format(get_debugging_port(device_configuration))
    response = requests.get(url)
    response_json = json.loads(response.text)
    return extract_debugging_url_and_page_id(response_json)

def get_debugging_url(device_configuration):
    '''
    Connects the client to the debugging socket.
    '''
    base_url = 'http://localhost:{0}/json'
    url = base_url.format(get_debugging_port(device_configuration))
    response = requests.get(url)
    response_json = json.loads(response.text)
    target_tab = None
    for tab in response_json:
        if tab['type'] == 'service_worker':
            continue

    if target_tab is None:
        # Clear all existing pages.
        close_all_tabs(device_configuration)

        create_tab(device_configuration)
        base_url = 'http://localhost:{0}/json'
        url = base_url.format(get_debugging_port(device_configuration))
        response = requests.get(url)
        target_tab = json.loads(response.text)
    return extract_debugging_url_and_page_id(target_tab[0])

def close_tab(device_configuration, page_id):
    '''
    Connects the client to the debugging socket.
    '''
    base_url = 'http://localhost:{0}/json/close/{1}'
    url = base_url.format(get_debugging_port(device_configuration), page_id)
    response = requests.get(url)
    # response_json = json.loads(response.text)

def extract_debugging_url_and_page_id(response_json):
    page_id = response_json['id'] if 'id' in response_json else None
    debugging_url = response_json[config.WEB_SOCKET_DEBUGGER_URL]
    return debugging_url, page_id
