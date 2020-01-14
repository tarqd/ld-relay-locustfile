from locust import HttpLocust, TaskSet, TaskSequence, task, between, seq_task, Locust
from locust.contrib.fasthttp import FastHttpLocust, FastHttpSession, FastResponse

from locust.events import request_success, request_failure, EventHook, quitting
import os
import sys
import json
import base64
import backoff
import logging
import time
import gevent
import traceback
import re
import random
from gevent.event import Event
import gevent
from util import create_http_pool_manager

import locust.runners as runners

def is_master():
    return isinstance(runners.locust_runner, runners.MasterLocustRunner) or isinstance(runners.locust_runner, runners.LocalLocustRunner)



import ldclient


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Custom LD Client classes instrumented to record stats to Locust
from ldclient_mobile import MobileLDClient, MobileConfig
from ldclient import LDClient, Config
from ldclient.event_processor import DefaultEventProcessor
from locust_feature_requester import FeatureRequesterImpl as LocustServerFeatureRequester
from locust_streaming import StreamingUpdateProcessor as LocustStreamingProcessor

import logging
log = logging.getLogger()
log.setLevel(logging.DEBUG)

try:
    with open(os.environ.get('LD_ENV_FILE', '/etc/ldlocust.json')) as json_file:
        log.debug('loading env from json file')
        data = json.load(json_file)
        for k, v in data.items():
            if os.environ.get(k) is None:
                log.debug('setting %s to %s', k, v)
                os.environ[k] = str(v)
except Exception:
    pass

class LaunchDarklyMobileTaskSet(TaskSequence):
    wait_time = between(1, 30)
    
    @seq_task(1)
    def init_ldclient(self):
        log.debug('connecting to client')
        ldclient = self.locust.ldclient
        if not ldclient.is_initialized():
            self.locust.close_client()
            raise Exception('failed to initialize client')
    @seq_task(2)
    class LDMobileTasks(TaskSet):
        wait_time = between(1, 30)
        @task(10)
        def evaluate_flags(self):
            flags = self.locust.ldclient.all_flags_state().to_values_map()
            flag, value = random.choice(list(flags.items()))
            log.debug('evaluating flag %s', flag)
            self.locust.ldclient.variation(flag, None)
        @task(3)
        def track_event(self):
            self.locust.ldclient.track('test_event', metric_value=1)
        @task(1)
        def done(self):
            self.interrupt()
    @seq_task(3)
    def disconnect(self):
        self.locust.close_client()

class LaunchDarklyServerTaskSet(TaskSequence):
    wait_time = between(1, 30)
    
    @seq_task(1)
    def init_ldclient(self):
        log.debug('connecting to client')
        ldclient = self.locust.ldclient
        if not ldclient.is_initialized():
            self.locust.close_client()
            raise Exception('failed to initialize client')
    @seq_task(2)
    class LDServerTasks(TaskSet):
        wait_time = between(1, 30)
        @task(10)
        def evaluate_flags(self):
            flags = self.locust.ldclient.all_flags_state(self.locust.user).to_values_map()
            flag, value = random.choice(list(flags.items()))
            log.debug('evaluating flag %s', flag)
            self.locust.ldclient.variation(flag,self.locust.user, None)
        @task(3)
        def track_event(self):
            self.locust.ldclient.track('test_event',self.locust.user, metric_value=1)
        @task(1)
        def done(self):
            self.interrupt()
    @seq_task(3)
    def disconnect(self):
        self.locust.close_client()



            
class LocustEventDispatcher(DefaultEventProcessor):
    def __init__(self,config, http=None, dispatcher_class=None):
        http = create_http_pool_manager(num_pools=1, verify_ssl=config.verify_ssl, target_base_uri=config.events_uri, force_proxy=config.http_proxy)
        super(LocustEventDispatcher, self).__init__(config, http=http, dispatcher_class=dispatcher_class)



class LaunchDarklyLocust(Locust):
    
    sdk_key = os.environ.get('LAUNCHDARKLY_SDK_KEY')
    user = {"anonymous": True, "key": "anonymous"}
    config_class = Config
    client_class = LDClient
    base_uri = os.environ.get('LAUNCHDARKLY_BASE_URI')
    events_uri = os.environ.get('LAUNCHDARKLY_EVENTS_URI')
    stream_uri = os.environ.get('LAUNCHDARKLY_STREAM_URI')
    event_processor_class = LocustEventDispatcher
    feature_requester_class = LocustServerFeatureRequester
    update_processor_class = LocustStreamingProcessor

    def __init__(self, *args, **kwargs):
        super(LaunchDarklyLocust, self).__init__(*args, **kwargs)
        self._ldclient = None
        if self.base_uri is None:
            self.base_uri = self.host
        if self.events_uri is None:
            self.events_uri = self.host
        if self.stream_uri is None:
            self.stream_uri = self.host

    def make_config(self):
        return self.config_class(sdk_key=self.sdk_key,
                                base_uri=self.base_uri,
                                events_uri=self.events_uri,
                                stream_uri=self.stream_uri,
                                event_processor_class=self.event_processor_class,
                                feature_requester_class=self.feature_requester_class,
                                update_processor_class=self.update_processor_class
                                )
    def make_client(self):
        return self.client_class(config=self.make_config())

    @property
    def ldclient(self):
        if self._ldclient is None:
            self._ldclient = self.make_client()
        return self._ldclient
        
    def close_client(self):
        try:
            if self._ldclient is not None:
                self._ldclient.close()
        except Exception:
            pass
        finally:
            self._ldclient = None

class LaunchDarklyMobileLocust(LaunchDarklyLocust):
    sdk_key = os.environ.get('LAUNCHDARKLY_MOBILE_KEY')
    client_class = MobileLDClient
    config_class = MobileConfig
    feature_requester_class=None 
    update_processor_class=None

    def make_client(self):
        return self.client_class(self.user, config=self.make_config())

    
class LaunchDarklyBasicMobile(LaunchDarklyMobileLocust):
    task_set = LaunchDarklyMobileTaskSet

class LaunchDarklyBasicServer(LaunchDarklyLocust):
    task_set = LaunchDarklyServerTaskSet






def update_heartbeat_thread():
    proj = os.environ.get('LOCUST_HEARTBEAT_PROJECT')
    api_key = os.environ.get('LOCUST_HEARTBEAT_API_KEY')
    if not proj:
        log.error('set LOCUST_HEARTBEAT_PROJECT in order to enable flag update metrics')
        return
    if not api_key:
        log.error('set LOCUST_HEARTBEAT_API_KEY in order to enable flag update metrics')
        return
   
    flag = 'locust-heartbeat'
    url_template = 'https://app.launchdarkly.com/api/v2/flags/{}/{}'
    update_endpoint = url_template.format(proj, flag)
    # wait for the runner
    while runners.locust_runner is None:
        gevent.sleep(5)
    
    if is_master():
        pool = create_http_pool_manager(num_pools=1, verify_ssl=True, target_base_uri='https://api.launchdarkly.com')

        while True:
            now = int(time.time() * 1000)
            body = [{
                "op": "replace",
                "path": "/variations/0/value",
                "value": now
            }, {
                "op": "replace",
                "path": "/variations/1/value",
                "value": now+1
            }]
            try:
                resp = pool.request('PATCH', update_endpoint, headers={
                    'Authorization': api_key,
                    'Content-Type': 'application/json-patch+json',
                    'Accept': 'application/json'
                }, body=json.dumps(body).encode('utf-8'))
            except Exception as e:
                log.error('failed to update heartbeat flag %s', e)
            gevent.sleep(30)




thread = gevent.spawn(update_heartbeat_thread)
quitting += lambda: gevent.kill(thread)

#x = MobileConfig(sdk_key=os.environ.get('LAUNCHDARKLY_MOBILE_KEY'))
#c = MobileLDClient({"key": "anonymous", "anonymous": True}, config=x)
#
#c.variation("fooooo", None)