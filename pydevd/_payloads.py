from collections import namedtuple

from _pydevd_bundle import pydevd_xml
import _pydevd_bundle.pydevd_comm as _pydevd
from _pydevd_bundle.pydevd_utils import quote_smart as quote,

from ._command import KIND_REQUEST, KIND_RESPONSE, KIND_EVENT
from ._commands import (
    CMD_ADD_EXCEPTION_BREAK,
    CMD_CHANGE_VARIABLE,
    CMD_GET_FRAME,
    CMD_GET_VARIABLE,
    CMD_LIST_THREADS,
    CMD_REMOVE_BREAK,
    CMD_REMOVE_EXCEPTION_BREAK,
    CMD_RETURN,
    CMD_RUN,
    CMD_SEND_CURR_EXCEPTION_TRACE,
    CMD_SEND_CURR_EXCEPTION_TRACE_PROCEEDED,
    CMD_SET_BREAK,
    CMD_STEP_INTO,
    CMD_STEP_OVER,
    CMD_STEP_RETURN,
    CMD_THREAD_CREATE,
    CMD_THREAD_KILL,
    CMD_THREAD_RUN,
    CMD_THREAD_SUSPEND,
    CMD_VERSION,
)
from ._handler import register_handler, look_up_payload
from ._payload import SCOPES, Payload


_NOT_SET = object()


def request(cmdid):
    """A class decorator factory for registering a request handler."""
    def deco(cls):
        register_handler(cmdid, KIND_REQUEST, cls)
        return cls
    return deco


def _validate_respid(cls, respid):
    resp = look_up_payload(respid, KIND_RESPONSE)
    if resp is None:
        raise RuntimeError('resp {!r} not registered'.format(respid))
    if not isinstance(resp, type):
        raise RuntimeError('resp {!r} not a class'.format(respid))
    if not issubclass(cls, resp):
        raise RuntimeError('cls not a subclass of resp {!r}'.format(respid))


def response(reqid, respid=None):
    """A class decorator factory for registering a response handler."""
    def deco(cls):
        if respid is not None:
            _validate_respid(cls, respid)
            try:
                match = cls.match
            except AttributeError:
                raise RuntimeError(
                    'cls {!r} missing match() method'.format(cls))
            register_handler(respid, KIND_RESPONSE, cls, match)
        register_handler(reqid, KIND_RESPONSE, cls)
        return cls
    return deco


def event(cmdid):
    """A class decorator factory for registering a event handler."""
    def deco(cls):
        register_handler(cmdid, KIND_EVENT, cls)
        return cls
    return deco


########################
# requests / responses

class EmptyRequest(Payload):
    """Base class for requests with an empty payload."""

    @classmethod
    def from_text(cls, text):
        _ensure_missing(text)
        return cls

    def as_text(self):
        return ''


class ThreadRequest(namedtuple('ThreadRequest', 'id'), Payload):
    """Base class for thread-targeting requests."""

    @classmethod
    def from_text(cls, text):
        payload = int(text)
        return cls(payload)

    def __new__(cls, id):
        id = int(id) if id or id is 0 else None
        self = super(ThreadRequest, cls).__new__(cls, id)
        return self

    def __init__(self, *args, **kwargs):
        if self.id is None:
            raise TypeError('missing id')

    def as_text(self):
        return str(self.id)


@response(CMD_RETURN)
class ReturnResponse():
    ...


# threads

class ThreadInfo(namedtuple('ThreadInfo', 'id name')):

    @classmethod
    def from_text(cls, text):
        raise NotImplementedError

    def __new__(cls, id, name=None):
        id = int(id) if id or id is 0 else None
        name = str(name) if name else None
        self = super(ThreadInfo, cls).__new__(cls, id, name)
        return self

    def __init__(self, *args, **kwargs):
        if self.id is None:
            raise TypeError('missing id')

    def as_text(self):
        name = self.name or ''
        name = pydevd_xml.make_valid_xml_value(name)
        return '<thread name="{}" id="{}" />'.format(
            quote(name),
            self.id,
        )


@request(CMD_THREAD_RUN)
class ThreadRunRequest(ThreadRequest):
    pass


@request(CMD_THREAD_SUSPEND)
class ThreadSuspendRequest(ThreadRequest):
    pass


@request(CMD_LIST_THREADS)
class ListThreadsRequest(EmptyRequest):
    pass


@response(CMD_LIST_THREADS, CMD_RETURN)
class ListThreadsResponse(ReturnResponse):

    @classmethod
    def match(cls, msg, kind=None, cause=None):
        if kind and kind is not KIND_RESPONSE:
            return None
        if msg.cmdid is not CMD_RETURN:
            return None
        if cause is None:
            # TODO: perhaps parse msg.payload?
            pass
        else:
            reqid = cause.cmdid
            if reqid is CMD_LIST_THREADS:
                return cls  # matched!
        return None

    @classmethod
    def from_text(cls, text):
        xml = untangle.parse(text).xml
        try:
            xthreads = xml.thread
        except AttributeError:
            xthreads = []

        threads = []
        for xthread in xthreads:
            tid = xthread['id']
            try:
                name = unquote(xthread['name'])
            except KeyError:
                name = None
            if name and name.startswith('pydevd.'):
                continue
            info = ThreadInfo(tid, name)
            threads.append(info)
        return cls(threads)

    def __init__(self, threads):
        ...

    def as_text(self):
        ...


# breakpoints

@request(CMD_SET_BREAK)
class SetBreakRequest(namedtuple('SetBreakRequest', 'id path line condition')):

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


@request(CMD_REMOVE_BREAK)
class RemoveBreakRequest(namedtuple('RemoveBreakRequest', 'x y z')):

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


@request(CMD_ADD_EXCEPTION_BREAK)
class AddExceptionBreakRequest(namedtuple('AddExceptionBreakRequest',
                                          'id path line condition')):

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


@request(CMD_REMOVE_EXCEPTION_BREAK)
class RemoveExceptionBreakRequest(namedtuple('RemoveExceptionBreakRequest',
                                             'x y z')):

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


# other execution flow

@request(CMD_RUN)
class ThreadRunRequest(ThreadRequest):
    pass


@request(CMD_STEP_INTO)
class StepIntoRequest(ThreadRequest):
    pass


@request(CMD_STEP_OVER)
class StepOverRequest(ThreadRequest):
    pass


@request(CMD_STEP_RETURN)
class StepReturnRequest(ThreadRequest):
    pass


# variables

class VariableInfo(namedtuple('VariableInfo', 'thread frame scope name')):

    def __new__(cls, thread, frame, scope, name):
        self = super(GetVariableRequest, cls).__new__(
            cls,
            int(thread) if thread or thread == 0 else None,
            int(frame) if frame or frame == 0 else None,
            str(scope) if scope else None,
            str(name) if name else None,
        )
        return self

    def __init__(self, *args, **kwargs):
        if self.thread is None:
            raise TypeError('missing thread')

        if self.frame is None:
            raise TypeError('missing frame')

        if not self.scope:
            raise TypeError('missing scope')
        elif self.scope not in SCOPES:
            raise ValueError('unsupported scope')

        if self.name is None:
            raise TypeError('missing name')


@request(CMD_GET_FRAME)
class GetFrameRequest(namedtuple('GetFrameRequest',
                                 'thread frame scope')):
    ...

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


@response(CMD_GET_FRAME)
class GetFrameResponse(namedtuple('GetFrameResponse',
                                  'thread frame scope attributes')):

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


@request(CMD_GET_VARIABLE)
class GetVariableRequest(namedtuple('GetVariableRequest',
                                    'thread frame scope attributes')):

    @classmethod
    def from_text(cls, text):
        thread, frame, scope, attributes = text.split('\t', 3)
        return cls(thread, frame, scope, attributes)

    def __new__(cls, thread, frame, scope, attributes=None):
        thread = int(thread) if thread or thread == 0 else None
        frame = int(frame) if frame or frame == 0 else None
        # TODO: parse attributes
        self = super(GetVariableRequest, cls).__new__(
            cls,
            thread,
            frame,
            scope,
            attributes,
        )
        return self

    def __init__(self, *args, **kwargs):
        if self.thread is None:
            raise TypeError('missing thread')

        if self.frame is None:
            raise TypeError('missing frame')

        if not self.scope:
            raise TypeError('missing scope')
        elif self.scope not in SCOPES:
            raise ValueError('unsupported scope')

    def as_text(self):
        return '{}\t{}\t{}\t{}'.format(*self)


@response(CMD_GET_VARIABLE)
class GetVariableResponse(namedtuple('GetVariableResponse',
                                     'thread frame scope attributes')):

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


@request(CMD_CHANGE_VARIABLE)
class ChangeVariableRequest(VariableInfo, Payload):

    @classmethod
    def from_text(cls, text):
        thread, frame, scope, name_and_value = text.split('\t', 3)
        tab_index = name_and_value.rindex('\t')
        name = name_and_value[0:tab_index].replace('\t', '.')
        value = name_and_value[tab_index + 1:]
        # TODO: skip value if "not set"?
        return cls(thread, frame, scope, name, value)

    def __new__(cls, thread, frame, scope, name, value=_NOT_SET):
        self = super(ChangeVariableRequest, cls).__new__(
            cls, thread, frame, scope, name)
        self._value = value

    @property
    def value(self):
        if self._value is _NOT_SET:
            raise AttributeError
        return self._value

    def as_text(self):
        if self.value is _NOT_SET:
            fmt = '{.thread}\t{.frame}\t{.scope}\t{.name}'
        else:
            fmt = '{.thread}\t{.frame}\t{.scope}\t{.name}\t{.value}'
        return fmt.format(self)


@response(CMD_CHANGE_VARIABLE, CMD_RETURN)
class ChangeVariableResponse(ReturnResponse):

    @classmethod
    def match(cls, msg, kind=None, cause=None):
        if kind and kind is not KIND_RESPONSE:
            return None
        if msg.cmdid is not CMD_RETURN:
            return None
        if cause is None:
            # TODO: perhaps parse msg.payload?
            pass
        else:
            reqid = cause.cmdid
            if reqid is CMD_CHANGE_VARIABLE:
                return cls  # matched!
        return None

    @classmethod
    def from_text(cls, text):
        ...
        xml = untangle.parse(resp_args).xml
        xvar = xml.var

        response = {
            'type': unquote(xvar['type']),
            'value': unquote(xvar['value']),
        }
        if bool(xvar['isContainer']):
            response['variablesReference'] = vsc_var

    def as_text(self):
        ...


# other info

@request(CMD_VERSION)
class VersionRequest(namedtuple('VersionRequest',
                                'version os breakpoints_by')):

    BREAKPOINTS_BY = {'ID', 'LINE'}

    @classmethod
    def from_text(cls, text):
        ...

    def __new__(cls, version, os=None, breakpoints_by=None):
        ...

    def as_text(self):
        ...


@response(CMD_VERSION)
class VersionResponse(namedtuple('VersionResponse', 'version')):
    pass

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


########################
# events

class ThreadEvent(namedtuple('ThreadEvent', 'id')):
    """Base class for thread-related events."""

    @classmethod
    def from_text(cls, text):
        payload = int(text)
        return cls(payload)

    def as_text(self):
        ...


@event(CMD_SEND_CURR_EXCEPTION_TRACE)
class SendCurrExceptionTraceEvent(object):

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


@event(CMD_SEND_CURR_EXCEPTION_TRACE_PROCEEDED)
class SendCurrExceptionTraceProceeded(object):

    @classmethod
    def from_text(cls, text):
        ...

    def as_text(self):
        ...


@event(CMD_THREAD_CREATE)
class ThreadCreateEvent(ThreadEvent):
    pass


@event(CMD_THREAD_KILL)
class ThreadKillEvent(ThreadEvent):
    pass


@event(CMD_THREAD_RUN)
class ThreadRunEvent(ThreadEvent):
    pass


@event(CMD_THREAD_SUSPEND)
class ThreadSuspendEvent(ThreadEvent):
    pass
