from ldclient.version import VERSION
from ldclient.util import _get_proxy_url, certifi, throw_if_unsuccessful_response, UnsuccessfulResponseException
from locust import events
import urllib3
import time
try:
  from urlparse import urlparse, urlunparse
except ImportError:
  from urllib.parse import urlparse, urlunparse

def _headers(sdk_key, client='PythonClient', with_auth=True):
  return {'Authorization': sdk_key, 'User-Agent': '{0}/{1}'.format(client, VERSION),
            'Content-Type': "application/json"}

def clean_name(method, url):
  x = urlparse(url)
  if method == 'GET' and (x.path.find('/meval/') == 0  or x.path.find('/users/') > -1 or x.path.find('/eval/') == 0):
    parts = x.path.split('/')
    parts.pop()
    parts.append('[user]')
    newpath = '/'.join(parts)
    x = x._replace(path=newpath)
    return urlunparse(x)
  return url
  
      
  
class LocustProxyPoolManager(urllib3.ProxyManager):
    def __init__(self, *args, **kwargs):
      super(LocustProxyPoolManager, self).__init__(*args, **kwargs)

    def urlopen(self, method, url, redirect=True, **kw):
        is_stream = not kw.get('preload_content', True)
        start_time = time.time()
        name = clean_name(method, url)
        req_type = method
        
        if is_stream and kw.get('headers', {}).get('Accept', 'lol') == 'text/event-stream':
          req_type = 'sse:connect'
        
        resp = None
        content_len = 0
        
        try:  
          resp = super(LocustProxyPoolManager, self).urlopen(method, url, redirect, **kw)
          if is_stream:
            content_len = int(resp.headers.get("content-length") or 0)
          else:
            content_len = len(resp.data or b"")
          throw_if_unsuccessful_response(resp)
        except UnsuccessfulResponseException as e:
          events.request_failure.fire(request_type=req_type, name=name, exception=e, response_length=content_len, response_time=int( (time.time() - start_time) * 1000 ))
          return resp
        except Exception as e:
          events.request_failure.fire(request_type=req_type, name=name, exception=e, response_length=content_len, response_time=int( (time.time() - start_time) * 1000 ))
          raise e
        events.request_success.fire(request_type=req_type, name=name, response_length=content_len, response_time=int( (time.time() - start_time) * 1000 ))
        return resp

class LocustPoolManager(urllib3.PoolManager):
    def __init__(self, *args, **kwargs):
      super(LocustPoolManager, self).__init__(*args, **kwargs)

    def urlopen(self, method, url, redirect=True, **kw):
        is_stream = not kw.get('preload_content', True)
        start_time = time.time()
        x = urlparse(url)
        name = url
        req_type = method
        if method == 'GET' and (x.path.find('/meval/') == 0  or x.path.find('/users/') > -1 or x.path.find('/eval/') == 0):
          parts = x.path.split('/')
          parts.pop()
          parts.append('[user]')
          newpath = '/'.join(parts)
          x = x._replace(path=newpath)
          name = urlunparse(x)
        

        if is_stream and kw.get('headers', {}).get('Accept', 'lol') == 'text/event-stream':
          req_type = 'sse:connect'
        
        resp = None
        content_len = 0
        
        try:  
          resp = super(LocustPoolManager, self).urlopen(method, url, redirect, **kw)
          if is_stream:
            content_len = int(resp.headers.get("content-length") or 0)
          else:
            content_len = len(resp.data or b"")
          throw_if_unsuccessful_response(resp)
        except UnsuccessfulResponseException as e:
          events.request_failure.fire(request_type=req_type, name=name, exception=e, response_length=content_len, response_time=int( (time.time() - start_time) * 1000 ))
          return resp
        except Exception as e:
          events.request_failure.fire(request_type=req_type, name=name, exception=e, response_length=content_len, response_time=int( (time.time() - start_time) * 1000 ))
          raise e
        events.request_success.fire(request_type=req_type, name=name, response_length=content_len, response_time=int( (time.time() - start_time) * 1000 ))
        return resp

def create_http_pool_manager(num_pools=1, verify_ssl=False, target_base_uri=None, force_proxy=None):
    proxy_url = force_proxy or _get_proxy_url(target_base_uri)

    if not verify_ssl:
        if proxy_url is None:
            return LocustPoolManager(num_pools=num_pools)
        else:
            return LocustProxyPoolManager(proxy_url, num_pools=num_pools)
    
    if proxy_url is None:
        return LocustPoolManager(
            num_pools=num_pools,
            cert_reqs='CERT_REQUIRED',
            ca_certs=certifi.where()
            )
    else:
        return LocustProxyPoolManager(
            proxy_url,
            num_pools=num_pools,
            cert_reqs='CERT_REQUIRED',
            ca_certs=certifi.where()
        )
