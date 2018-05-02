import os
import json
import websocket
import threading

from time import sleep

from utils import config, navigation_utils

METHOD = 'method'
PARAMS = 'params'
REQUEST_ID = 'requestId'
TIMESTAMP = 'timestamp'

WAIT = 1
PAGE_STABLE_THRESHOLD = 5000 # 2s virtual time budget

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

    def __init__(self, ws_url, page_url, emulating_device_params, collect_console, collect_tracing, message_callback, callback_page_done, preserve_cache, use_virtual_time_budget, get_main_html):
        '''
        Initialize the object. 
        '''
        websocket.enableTrace(True)

        # Conditions for a page to finish loading.
        self.originalRequestMs = None
        self.domContentEventFiredMs = None
        self.loadEventFiredMs = None
        self.mainHtmlRequestId = None
        self.tracingCollectionCompleted = False
        self.start_page = False
        self.use_virtual_time_budget = use_virtual_time_budget
        self.virtual_time_expired = False
        self.get_main_html = get_main_html
        self.waiting_for_main_html = False
        self.unmodified_html = ''

        self.url = page_url       # The URL to navigate to.
        self.collect_console = collect_console
        self.collect_tracing = collect_tracing # Never start tracing.
        self.message_callback = message_callback
        self.callback_page_done = callback_page_done    # The callback method
        # self.user_agent = user_agent_str
        self.emulating_device_params = emulating_device_params
        self.debugging_url = ws_url
        self.preserve_cache = preserve_cache
        self.ws = websocket.WebSocketApp(ws_url,\
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
        self.message_callback(self, message_obj, message)
        if METHOD not in message_obj:
            if message_obj['id'] == navigation_utils.METHOD_IDS['Network.getResponseBody']:
                self.unmodified_html = message_obj['result']['body'].encode('utf-8')
                self.waiting_for_main_html = False

        elif message_obj[METHOD].startswith('Network'):
            if message_obj[METHOD] == 'Network.requestWillBeSent' and \
                escape_page(message_obj[PARAMS]['request']['url']) == escape_page(self.url):
                self.start_page = True
                self.originalRequestMs = message_obj[PARAMS][TIMESTAMP] * 1000
                self.mainHtmlRequestId = message_obj[PARAMS][REQUEST_ID]

            elif self.get_main_html and \
                    message_obj[METHOD] == 'Network.loadingFinished' and \
                    message_obj[PARAMS]['requestId'] == self.mainHtmlRequestId:
                self.waiting_for_main_html = True
                navigation_utils.get_response_body(self.ws, self.mainHtmlRequestId)

        elif message_obj[METHOD].startswith('Page'):
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

        elif message_obj[METHOD].startswith('Tracing'):
            if message_obj[METHOD] == 'Tracing.tracingComplete':
                self.tracingCollectionCompleted = True

        elif message_obj[METHOD].startswith('Emulation'):
            # print message_obj
            if message_obj[METHOD] == 'Emulation.virtualTimeBudgetExpired':
                # print 'Virtual time expired'
                self.virtual_time_expired = True

        #print '{0} {1} {2}'.format(self.originalRequestMs, self.domContentEventFiredMs, self.loadEventFiredMs)
        #if self.originalRequestMs is not None and \
        #    self.domContentEventFiredMs is not None and \
        #    self.loadEventFiredMs is not None :
        #    if self.collect_tracing and self.tracing_started:
        #        self.stop_trace_collection(self.ws)

        if (not self.use_virtual_time_budget and \
            (self.originalRequestMs is not None and \
            self.domContentEventFiredMs is not None and \
            self.loadEventFiredMs is not None and \
            (not self.collect_tracing or \
            (self.collect_tracing and self.tracingCollectionCompleted)) and \
            (not self.get_main_html or \
            self.get_main_html and not self.waiting_for_main_html) and \
            self.callback_page_done is not None)) or \
            (self.use_virtual_time_budget and \
            self.virtual_time_expired):
                self.disable_network_tracking(self.ws)
                self.disable_page_tracking(self.ws)
                self.disable_dom(self.ws)
                if self.collect_console:
                    self.disable_console_tracking(self.ws)
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

        self.emulate_device(self.ws, self.emulating_device_params)

        if not self.preserve_cache:
            self.clear_cache(self.ws)
        
        sleep(WAIT)

        if self.collect_tracing:
            self.enable_trace_collection(self.ws)

        print 'navigating to url: ' + str(self.url)
        navigation_utils.navigate_to_page(self.ws, self.url)

        if self.use_virtual_time_budget:
            self.set_virtual_time_budget(self.ws)

    def close_connection(self):
        self.ws.close()
        print 'Connection closed'

    def clear_cache(self, debug_connection):
        navigation_utils.clear_cache(debug_connection)

    def emulate_device(self, debug_connection, device_params):
        print device_params
        user_agent = device_params[config.USER_AGENT]
        if user_agent is not None:
            navigation_utils.set_user_agent(debug_connection, user_agent)
        self.set_touch_mode(debug_connection)
        self.set_device_metrics_override(debug_connection, device_params['width'], device_params['height'], device_params['density'])

    def set_touch_mode(self, conn):
        conn.send(json.dumps({"id": 23, "method": "Emulation.setTouchEmulationEnabled", "params": {"enabled": True}}))
        print 'enabled touch mode'

    def set_device_metrics_override(self, conn, width, height, scale_factor):
        msg = { "id": 235, "method": "Emulation.setDeviceMetricsOverride", "params": {
                "width": int(width),
                "height": int(height), 
                "fitWindow": False, 
                "deviceScaleFactor": float(scale_factor),
                "mobile": True
            }
        }
        conn.send(json.dumps(msg))
        print 'set device metrics override'


    def disable_network_tracking(self, debug_connection):
        '''
        Disable Network tracking in Chrome.
        '''
        disable_network = { "id": 2, "method": "Network.disable" }
        debug_connection.send(json.dumps(disable_network))
        print 'Disable network tracking.'

    def disable_page_tracking(self, debug_connection):
        '''
        Disable Page tracking in Chrome.
        '''
        disable_page = { 'id': 3, 'method': 'Page.disable' }
        debug_connection.send(json.dumps(disable_page))
        print 'Disable page tracking.'

    def enable_network_tracking(self, debug_connection):
        '''
        Enables Network tracking in Chrome.
        '''
        enable_network = { "id": 4, "method": "Network.enable" }
        debug_connection.send(json.dumps(enable_network))
        print 'Enabled network tracking.'
        # disable_cache = { "id": 10, "method": "Network.setCacheDisabled", "params": { "cacheDisabled": True } }
        # debug_connection.send(json.dumps(disable_cache))
        # print 'Disable debugging connection.'

    def enable_console_tracking(self, debug_connection):
        '''
        Enables Console Tracking.
        '''
        enable_console = { "id": 5, "method": "Console.enable" }
        debug_connection.send(json.dumps(enable_console))
        print 'Enabled console tracking.'

    def disable_console_tracking(self, debug_connection):
        '''
        Disable Console tracking in Chrome.
        '''
        disable_console = { 'id': 6, 'method': 'Console.disable' }
        debug_connection.send(json.dumps(disable_console))
        print 'Disable console tracking.'

    def enable_page_tracking(self, debug_connection):
        '''
        Enables Page tracking in Chrome.
        '''
        enable_page = { 'id': 7, 'method': 'Page.enable' }
        debug_connection.send(json.dumps(enable_page))
        print 'Enabled page tracking.'


    def enable_dom(self, debug_connection):
        '''
        Enables DOM domain tracing.
        '''
        enable_dom = { 'id': 1010, 'method': 'DOM.enable' }
        print 'enabled DOM'
        debug_connection.send(json.dumps(enable_dom))


    def disable_dom(self, debug_connection):
        '''
        Disables DOM domain tracing.
        '''
        disable_dom = { 'id': 1020, 'method': 'DOM.disable' }
        debug_connection.send(json.dumps(disable_dom))


    def get_document(self, debug_connection):
        print 'getting document'
        get_document = { 'id': 1019, 'method': 'DOM.getDocument', 'params': { 'depth': -1 } }
        debug_connection.send(json.dumps(get_document))
        result = debug_connection.recv()

    
    def request_child_nodes(self, debug_connection, node_id):
        '''
        '''
        request_child_nodes = { 'id': 1030, 'method': 'DOM.requestChildNodes', 'params': { 'nodeId': node_id, 'depth': -1 }}
        debug_connection.send(json.dumps(request_child_nodes))

    def enable_runtime(self, debug_connection):
        '''
        Enables Runtime in Chrome.
        '''
        enable_page = { 'id': 8, 'method': 'Runtime.enable' }
        debug_connection.send(json.dumps(enable_page))
        print 'Enabled Runtime.'

    def enable_trace_collection(self, debug_connection):
        '''
        Enables the tracing collection.
        '''
        enable_trace_collection = { "id": 9, 'method': 'Tracing.start', 'params': { 'categories': 'blink, devtools.timeline, disabled-by-default-devtools.timeline, disabled-by-default-devtools.screenshot', "options": "sampling-frequency=10000" } }
        debug_connection.send(json.dumps(enable_trace_collection))
        self.tracing_started = True
        print 'Enabled trace collection'

    def stop_trace_collection(self, debug_connection):
        '''
        Disable the tracing collection.
        '''
        disable_trace_collection = { "id": 10, 'method': 'Tracing.end' }
        debug_connection.send(json.dumps(disable_trace_collection))
        self.tracing_started = False
        print 'Disables trace collection'


    def capture_screenshot(self, debug_connection):
        '''
        Enables the tracing collection.
        '''
        print 'capturing screenshot'
        capture_screenshot = { 'method': 'Page.captureScreenshot' }
        debug_connection.send(json.dumps(capture_screenshot))


    def set_virtual_time_budget(self, debug_connection):
        '''
        Sets up the virtual time budget.
        '''
        setup_virtual_time_budget = { 'id': 314, \
                'method': 'Emulation.setVirtualTimePolicy', \
                'params': { \
                    "policy": "pauseIfNetworkFetchesPending", \
                    "budget": PAGE_STABLE_THRESHOLD \
                } \
        }
        debug_connection.send(json.dumps(setup_virtual_time_budget))
