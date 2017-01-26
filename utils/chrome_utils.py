import simplejson as json
import requests

import phone_connection_utils

def close_all_tabs(device_configuration):
    '''
    Closes all the tabs in Chrome.
    '''
    base_url = 'http://localhost:{0}/json'
    url = base_url.format(get_debugging_port(device_configuration))
    response = requests.get(url)
    response_json = json.loads(response.text)
    for i in range(0, len(response_json) - 1):
        response = response_json[i]
        page_id = response['id']
        base_url = 'http://localhost:{0}/json/close/{1}'
        url = base_url.format(get_debugging_port(device_configuration), page_id)
        response = requests.get(url)

def get_debugging_port(device_configuration):
    '''
    Returns the correct Chrome debug port.
    '''
    if device_configuration[phone_connection_utils.DEVICE_TYPE] == phone_connection_utils.DEVICE_PHONE:
        return device_configuration[phone_connection_utils.ADB_PORT]
    elif device_configuration[phone_connection_utils.DEVICE_TYPE] == phone_connection_utils.DEVICE_MAC or \
        device_configuration[phone_connection_utils.DEVICE_TYPE] == phone_connection_utils.DEVICE_UBUNTU:
        return device_configuration[phone_connection_utils.CHROME_DESKTOP_DEBUG_PORT]

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
    if len(response_json) == 0:
        create_tab(device_configuration)
        base_url = 'http://localhost:{0}/json'
        url = base_url.format(get_debugging_port(device_configuration))
        response = requests.get(url)
        response_json = json.loads(response.text)
    return extract_debugging_url_and_page_id(response_json[0])

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
    debugging_url = response_json[phone_connection_utils.WEB_SOCKET_DEBUGGER_URL]
    return debugging_url, page_id
