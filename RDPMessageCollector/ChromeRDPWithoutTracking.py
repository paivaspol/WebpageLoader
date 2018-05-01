import json
import websocket
import threading

from utils import navigation_utils

from time import sleep

METHOD = 'method'
PARAMS = 'params'
REQUEST_ID = 'requestId'
TIMESTAMP = 'timestamp'

WAIT = 3

class ChromeRDPWithoutTracing(object):

    def __init__(self, url, target_url, user_agent, screen_size_config):
        self.url = target_url
        self.debugging_url = url
        self.user_agent = user_agent
        self.screen_size_config = screen_size_config
        self.ws = websocket.WebSocket()
        self.ws.connect(self.debugging_url)

    def navigate_to_page(self, url, reload_page):
        if self.user_agent is not None:
            navigation_utils.set_user_agent(self.ws, self.user_agent)

        if self.screen_size_config is not None:
            navigation_utils.set_device_screen_size(self.ws, self.screen_size_config)

        # if reload_page:
        #     navigation_utils.reload_page(self.ws)
        # else:
        navigation_utils.navigate_to_page(self.ws, url)
        sleep(WAIT)
        result = self.ws.recv()
        start_time, end_time = navigation_utils.get_start_end_time_with_socket(self.ws)
        navigation_utils.clear_cache(self.ws)
        return start_time, end_time

    def __del__(self):
        self.ws.close()
