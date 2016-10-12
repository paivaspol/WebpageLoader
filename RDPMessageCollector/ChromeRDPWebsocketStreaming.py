import os
import simplejson as json
import websocket
import threading

from time import sleep

from utils import navigation_utils

METHOD = 'method'
PARAMS = 'params'
REQUEST_ID = 'requestId'
TIMESTAMP = 'timestamp'

WAIT = 3.0

HTTP_PREFIX = 'http://'
HTTPS_PREFIX = 'https://'
WWW_PREFIX = 'www.'
def escape_page(url):
    if url.endswith('/'):
        url = url[:len(url) - 1]
    if url.startswith(HTTPS_PREFIX):
        url = url[len(HTTPS_PREFIX):]
    elif url.startswith(HTTP_PREFIX):
        url = url[len(HTTP_PREFIX):]
    if url.startswith(WWW_PREFIX):
        url = url[len(WWW_PREFIX):]
    return url.replace('/', '_')

class ChromeRDPWebsocketStreaming(object):

    def __init__(self, url, target_url, device_configuration, user_agent_str, collect_console, collect_tracing, callback_on_network_event, callback_page_done):
        '''
        Initialize the object. 
        url - the websocket url
        target_url - the url to navigate to
        '''
        # websocket.enableTrace(True)

        # Conditions for a page to finish loading.
        self.originalRequestMs = None
        self.domContentEventFiredMs = None
        self.loadEventFiredMs = None
        self.tracingCollectionCompleted = False
        self.start_page = False

        self.url = target_url       # The URL to navigate to.
        self.collect_console = collect_console
        self.collect_tracing = False # Never start tracing.
        self.callback_on_network_event = callback_on_network_event
        self.callback_page_done = callback_page_done    # The callback method
        self.user_agent = user_agent_str
        self.device_configuration = device_configuration # The device configuration
        self.debugging_url = url
        self.ws = websocket.WebSocketApp(url,\
                                        on_message = self.on_message,\
                                        on_error = self.on_error,\
                                        on_close = self.on_close)
        self.ws.on_open = self.on_open

        self.tracing_started = False

    def start(self):
        self.ws.run_forever() # start running this socket.

    def on_message(self, ws, message):
        '''
        Handle each message.
        '''
        message_obj = json.loads(message)
        self.callback_on_network_event(self, message_obj, message)
        # self.tracingCollectionCompleted = True
        if METHOD in message_obj and message_obj[METHOD].startswith('Network'):
            if message_obj[METHOD] == 'Network.requestWillBeSent' and \
                escape_page(message_obj[PARAMS]['request']['url']) == escape_page(self.url):
                self.start_page = True
                self.callback_on_network_event(self, message_obj, message)
                self.originalRequestMs = message_obj[PARAMS][TIMESTAMP] * 1000
        elif METHOD in message_obj and message_obj[METHOD].startswith('Page'):
            if message_obj[METHOD] == 'Page.domContentEventFired' and self.start_page:
                self.domContentEventFiredMs = message_obj[PARAMS][TIMESTAMP] * 1000
            elif message_obj[METHOD] == 'Page.loadEventFired' and self.start_page:
                self.loadEventFiredMs = message_obj[PARAMS][TIMESTAMP] * 1000
                if self.collect_tracing and self.tracing_started:
                    self.stop_trace_collection(self.ws)
            elif message_obj[METHOD] == 'Page.javascriptDialogOpening':
                if message_obj[PARAMS]['type'] == 'alert' or \
                    message_obj[PARAMS]['type'] == 'beforeunload':
                    navigation_utils.handle_js_dialog(self.ws)
                elif message_obj[PARAMS]['type'] == 'confirm' or \
                    message_obj[PARAMS]['type'] == 'prompt':
                    navigation_utils.handle_js_dialog(self.ws, accept=False)
        elif METHOD in message_obj and message_obj[METHOD].startswith('Tracing'):
            if message_obj[METHOD] == 'Tracing.tracingComplete':
                self.tracingCollectionCompleted = True

        #print '{0} {1} {2}'.format(self.originalRequestMs, self.domContentEventFiredMs, self.loadEventFiredMs)
        #if self.originalRequestMs is not None and \
        #    self.domContentEventFiredMs is not None and \
        #    self.loadEventFiredMs is not None :
        #    if self.collect_tracing and self.tracing_started:
        #        self.stop_trace_collection(self.ws)

        if self.originalRequestMs is not None and \
            self.domContentEventFiredMs is not None and \
            self.loadEventFiredMs is not None and \
            (not self.collect_tracing or \
            (self.collect_tracing and self.tracingCollectionCompleted)):
            self.disable_network_tracking(self.ws)
            self.disable_page_tracking(self.ws)
            if self.collect_console:
                self.disable_console_tracking(self.ws)
            #if self.collect_tracing:
            #    self.stop_trace_collection(self.ws)
            print 'Start time {0}, Load completed: {1}'.format(self.originalRequestMs, self.loadEventFiredMs)
            self.callback_page_done(self)

    def on_error(self, ws, error):
        '''
        Handle the error.
        '''
        print error
    
    def on_close(self, ws):
        '''
        Handle when socket is closed
        '''
        print 'Socket for {0} is closed.'.format(self.url)

    def on_open(self, ws):
        '''
        Initialization logic goes here.
        '''
        self.enable_network_tracking(self.ws)
        self.enable_page_tracking(self.ws)
        
        if self.collect_console:
            self.enable_console_tracking(self.ws)


        if self.user_agent is not None:
            navigation_utils.set_user_agent(self.ws, self.user_agent)

        if os.getenv("EMULATE_DEVICE", "") != "":
            self.emulate_device(self.ws, os.getenv("EMULATE_DEVICE"))

        self.clear_cache(self.ws)
        
        # self.enable_trace_collection(self.ws)
        navigation_utils.navigate_to_page(self.ws, 'about:blank')
        sleep(WAIT)

        if self.collect_tracing:
            self.enable_trace_collection(self.ws)
        print 'navigating to url: ' + str(self.url)
        navigation_utils.navigate_to_page(self.ws, self.url)

    def close_connection(self):
        self.ws.close()
        print 'Connection closed'

    def get_navigation_url(self):
        return self.url

    def clear_cache(self, debug_connection):
        navigation_utils.clear_cache(debug_connection)

    def emulate_device(self, debug_connection, device_name):
        configs = [{
            "device": {
                "title": "Apple iPhone 6",
                "screen": {
                    "horizontal": {
                        "width": 667,
                        "height": 375
                    },
                    "device-pixel-ratio": 2,
                    "vertical": {
                        "width": 375,
                        "height": 667
                    }
                },
                "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 8_0 like Mac OS X) AppleWebKit/600.1.3 (KHTML, like Gecko) Version/8.0 Mobile/12A4345d Safari/600.1.4",
            }
        },{
            "device": {
                "title": "Google Nexus 6",
                "screen": {
                    "horizontal": {
                        "width": 732,
                        "height": 412
                    },
                    "device-pixel-ratio": 3.5,
                    "vertical": {
                        "width": 412,
                        "height": 732
                    }
                },
                "user-agent": "Mozilla/5.0 (Linux; Android 5.1.1; Nexus 6 Build/LYZ28E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.20 Mobile Safari/537.36",
            }
        },{
            "device": {
                "title": "Google Nexus 10",
                "screen": {
                    "horizontal": {
                        "width": 1280,
                        "height": 800
                    },
                    "device-pixel-ratio": 2,
                    "vertical": {
                        "width": 800,
                        "height": 1280
                    }
                },
                "user-agent": "Mozilla/5.0 (Linux; Android 4.3; Nexus 10 Build/JSS15Q) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2307.2 Safari/537.36",
            }
        }]

        cfg = None
        for c in configs:
            if c["device"]["title"] == device_name:
                cfg = c
                break
        if cfg is None:
            valid_devices = ", ".join(c["device"]["title"] for c in configs)
            raise ValueError("invalid device %s: known devices are %s" % (device_name, valid_devices))
        navigation_utils.set_user_agent(debug_connection, cfg["device"]["user-agent"])
        self.set_touch_mode(debug_connection)
        self.set_device_metrics_override(
            debug_connection,
            cfg["device"]["screen"]["vertical"]["width"],
            cfg["device"]["screen"]["vertical"]["height"])

    def set_touch_mode(self, conn):
        conn.send(json.dumps({"id": 23, "method": "Page.setTouchEmulationEnabled", "params": {"enabled": True}}))
        print 'enabled touch mode'
        sleep(WAIT)

    def set_device_metrics_override(self, conn, width, height):
        msg = { "id": 235, "method": "Page.setDeviceMetricsOverride", "params": {
            "width": width, "height": height, "fontScaleFactor": 1, "fitWindow": False}}
        conn.send(json.dumps(msg))
        print 'set device metrics override'
        sleep(WAIT)

    def can_clear_cache(self, debug_connection):
        '''
        Clears the cache in the browser
        '''
        clear_cache = { "id": 1, "method": "Network.canClearBrowserCache" }
        debug_connection.send(json.dumps(clear_cache))
        print 'Cleared browser cache'
        sleep(WAIT)

    def disable_network_tracking(self, debug_connection):
        '''
        Disable Network tracking in Chrome.
        '''
        disable_network = { "id": 2, "method": "Network.disable" }
        debug_connection.send(json.dumps(disable_network))
        print 'Disable network tracking.'
        sleep(WAIT)

    def disable_page_tracking(self, debug_connection):
        '''
        Disable Page tracking in Chrome.
        '''
        disable_page = { 'id': 3, 'method': 'Page.disable' }
        debug_connection.send(json.dumps(disable_page))
        print 'Disable page tracking.'
        sleep(WAIT)

    def enable_network_tracking(self, debug_connection):
        '''
        Enables Network tracking in Chrome.
        '''
        enable_network = { "id": 4, "method": "Network.enable" }
        debug_connection.send(json.dumps(enable_network))
        print 'Enabled network tracking.'
        sleep(WAIT)
        # disable_cache = { "id": 10, "method": "Network.setCacheDisabled", "params": { "cacheDisabled": True } }
        # debug_connection.send(json.dumps(disable_cache))
        # print 'Disable debugging connection.'
        # sleep(WAIT)

    def enable_console_tracking(self, debug_connection):
        '''
        Enables Console Tracking.
        '''
        enable_console = { "id": 5, "method": "Console.enable" }
        debug_connection.send(json.dumps(enable_console))
        print 'Enabled console tracking.'
        sleep(WAIT)

    def disable_console_tracking(self, debug_connection):
        '''
        Disable Console tracking in Chrome.
        '''
        disable_console = { 'id': 6, 'method': 'Console.disable' }
        debug_connection.send(json.dumps(disable_console))
        print 'Disable console tracking.'
        sleep(WAIT)

    def enable_page_tracking(self, debug_connection):
        '''
        Enables Page tracking in Chrome.
        '''
        enable_page = { 'id': 7, 'method': 'Page.enable' }
        debug_connection.send(json.dumps(enable_page))
        print 'Enabled page tracking.'
        sleep(WAIT)

    def enable_runtime(self, debug_connection):
        '''
        Enables Runtime in Chrome.
        '''
        enable_page = { 'id': 8, 'method': 'Runtime.enable' }
        debug_connection.send(json.dumps(enable_page))
        print 'Enabled Runtime.'
        sleep(WAIT)

    def enable_trace_collection(self, debug_connection):
        '''
        Enables the tracing collection.
        '''
        #enable_trace_collection = { "id": 9, 'method': 'Tracing.start' }
        enable_trace_collection = { "id": 9, 'method': 'Tracing.start', 'params': { 'categories': 'devtools.timeline, disabled-by-default-devtools.timeline, disabled-by-default-devtools.screenshot', "options": "sampling-frequency=10000" } }
        # enable_trace_collection = { 'id': 4, 'method': 'Timeline.start' }
        debug_connection.send(json.dumps(enable_trace_collection))
        self.tracing_started = True
        print 'Enabled trace collection'
        sleep(WAIT)

    def stop_trace_collection(self, debug_connection):
        '''
        Disable the tracing collection.
        '''
        disable_trace_collection = { "id": 10, 'method': 'Tracing.end' }
        debug_connection.send(json.dumps(disable_trace_collection))
        self.tracing_started = False
        print 'Disables trace collection'
        sleep(WAIT)

    def capture_screenshot(self, debug_connection):
        '''
        Enables the tracing collection.
        '''
        print 'capturing screenshot'
        capture_screenshot = { 'method': 'Page.captureScreenshot' }
        debug_connection.send(json.dumps(capture_screenshot))
        # print 'Disables trace collection'
        sleep(WAIT)

    def get_debugging_url(self):
        '''
        Returns the debugging url.
        '''
        return self.debugging_url
