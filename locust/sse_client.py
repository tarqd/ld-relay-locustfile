"""
Server-Sent Events implementation for streaming.

Based on: https://bitbucket.org/btubbs/sseclient/src/a47a380a3d7182a205c0f1d5eb470013ce796b4d/sseclient.py?at=default&fileviewer=file-view-default
"""
# currently excluded from documentation - see docs/README.md

import re
import time

import six

import urllib3

from util import create_http_pool_manager, clean_name
from ldclient.util import log
from ldclient.util import throw_if_unsuccessful_response
from locust import events
request_success = events.request_success
request_failure = events.request_failure
import time
# Technically, we should support streams that mix line endings.  This regex,
# however, assumes that a system will provide consistent line endings.
end_of_field = re.compile(r'\r\n\r\n|\r\r|\n\n')


class SSEClient(object):
    def __init__(self, url, last_id=None, retry=3000, connect_timeout=10, read_timeout=300, chunk_size=10000,
                 verify_ssl=False, http=None, http_proxy=None, **kwargs):
        self.url = url
        self.last_id = last_id
        self.retry = retry
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._chunk_size = chunk_size

        # Optional support for passing in an HTTP client
        self.http = create_http_pool_manager(num_pools=1, verify_ssl=verify_ssl, target_base_uri=url,
            force_proxy=http_proxy)

        # Any extra kwargs will be fed into the request call later.
        self.requests_kwargs = kwargs

        # The SSE spec requires making requests with Cache-Control: nocache
        if 'headers' not in self.requests_kwargs:
            self.requests_kwargs['headers'] = {}
        self.requests_kwargs['headers']['Cache-Control'] = 'no-cache'

        # The 'Accept' header is not required, but explicit > implicit
        self.requests_kwargs['headers']['Accept'] = 'text/event-stream'

        # Keep data here as it streams in
        self.buf = u''

        self._connect()

    def _connect(self):
        self._last_heartbeat = None
        self._connect_start = time.time()
        if self.last_id:
            self.requests_kwargs['headers']['Last-Event-ID'] = self.last_id

        # Use session if set.  Otherwise fall back to requests module.
        self.resp = self.http.request(
            'GET',
            self.url,
            timeout=urllib3.Timeout(connect=self._connect_timeout, read=self._read_timeout),
            preload_content=False,
            retries=0, # caller is responsible for implementing appropriate retry semantics, e.g. backoff
            **self.requests_kwargs)
        # Raw readlines doesn't work because we may be missing newline characters until the next chunk
        # For some reason, we also need to specify a chunk size because stream=True doesn't seem to guarantee
        # that we get the newlines in a timeline manner
        self.resp_file = self.resp.stream(amt=self._chunk_size)

        # TODO: Ensure we're handling redirects.  Might also stick the 'origin'
        # attribute on Events like the Javascript spec requires.
        throw_if_unsuccessful_response(self.resp)

    def _event_complete(self):
        return re.search(end_of_field, self.buf[len(self.buf)-self._chunk_size-10:]) is not None  # Just search the last chunk plus a bit

    def __iter__(self):
        return self

    def __next__(self):
        while not self._event_complete():
            try:
                nextline = next(self.resp_file)
                # There are some bad cases where we don't always get a line: https://github.com/requests/requests/pull/2431
                if not nextline:
                    raise EOFError()
                self.buf += nextline.decode("utf-8")
            except (StopIteration, EOFError) as e:
                request_failure.fire(request_type='sse:disconnect', name="/meval", response_time=int((time.time() - self._connect_start) * 1000), response_length=0, exception=e)
                time.sleep(self.retry / 1000.0)
                

                # The SSE spec only supports resuming from a whole message, so
                # if we have half a message we should throw it out.
                head, sep, tail = self.buf.rpartition('\n')
                self.buf = head + sep
                continue

        split = re.split(end_of_field, self.buf)
        head = split[0]
        tail = "".join(split[1:])

        self.buf = tail
        msg = Event.parse(head, instance=self)

        # If the server requests a specific retry delay, we need to honor it.
        if msg.retry:
            self.retry = msg.retry

        # last_id should only be set if included in the message.  It's not
        # forgotten if a message omits it.
        if msg.id:
            self.last_id = msg.id

        return msg

    # The following two lines make our iterator class compatible with both Python 2.x and 3.x,
    # even though they expect different magic method names. We could accomplish the same thing
    # by importing builtins.object and deriving from that, but this way it's easier to see
    # what we're doing.
    if six.PY2:
        next = __next__


class Event(object):

    sse_line_pattern = re.compile('(?P<name>[^:]*):?( ?(?P<value>.*))?')

    def __init__(self, data='', event='message', id=None, retry=None):
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry
        self._last_heartbeat = None

    def dump(self):
        lines = []
        if self.id:
            lines.append('id: %s' % self.id)

        # Only include an event line if it's not the default already.
        if self.event != 'message':
            lines.append('event: %s' % self.event)

        if self.retry:
            lines.append('retry: %s' % self.retry)

        lines.extend('data: %s' % d for d in self.data.split('\n'))
        return '\n'.join(lines) + '\n\n'

    @classmethod
    def parse(cls, raw, instance=None):
        """
        Given a possibly-multiline string representing an SSE message, parse it
        and return a Event object.
        """
        msg = cls()
        for line in raw.split('\n'):
            m = cls.sse_line_pattern.match(line)
            if m is None:
                # Malformed line.  Discard but warn.
                log.warning('Invalid SSE line: "%s"' % line)
                continue

            name = m.groupdict()['name']
            value = m.groupdict()['value']
            if name == '':
                if instance is not None:
                    now = time.time()
                    last_heartbeat = instance._last_heartbeat or instance._connect_start
                    duration = int((now - last_heartbeat) * 1000)
                    request_success.fire(request_type='sse:heartbeat', name=clean_name('GET', instance.url), response_time=duration, response_length=0)
                    instance._last_heartbeat = now
                # line began with a ":", so is a comment.  Ignore
                continue

            if name == 'data':
                # If we already have some data, then join to it with a newline.
                # Else this is it.
                if msg.data:
                    msg.data = '%s\n%s' % (msg.data, value)
                else:
                    msg.data = value
            elif name == 'event':
                msg.event = value
            elif name == 'id':
                msg.id = value
            elif name == 'retry':
                msg.retry = int(value)

        return msg

    def __str__(self):
        return self.data
