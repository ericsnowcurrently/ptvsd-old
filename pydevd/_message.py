from collections import namedtuple
try:
    from urllib.parse import quote as urlquote, unquote as urlunquote
except ImportError:
    from urllib import quote as urlquote, unquote as urlunquote

import _pydevd_bundle.pydevd_comm as _pydevd

from . import ORIGIN_DEBUGGER, ORIGIN_DAEMON
from ._command import extract_cmdid, PyDevdCommandID
from ._handler import look_up_payload, Handler
from ._payload import Payload


class MessageError(Exception):
    """The base for all message-related errors."""

    def __init__(self, err=None, msg=None, reason=None):
        if err is None:
            err = 'problem with message'
            if msg is not None:
                err += '{msg!r}'
        if msg is not None:
            err = err.format(msg=msg)
        if reason is not None:
            err += ' (reason: {})'.format(reason)
        super(MessageError, self).__init__(err)
        self.msg = msg
        self.reason = reason


class MalformedMessageError(MessageError):
    """The line-formatted message was unrecognizable."""

    def __init__(self, msg, reason=None):
        err = 'bad line-formatted message {msg!r}'
        super(MalformedMessageError, self).__init__(err, msg, reason)


class InvalidMessageError(MessageError):
    """A message is invalid."""

    def __init__(self, msg, reason=None):
        err = 'invalid message {msg!r}'
        super(InvalidMessageError, self).__init__(err, msg, reason)


class UnsupportedMessageError(InvalidMessageError):
    """A message has an unsupported command."""

    def __init__(self, msg):
        super(UnsupportedMessageError, self).__init__(
            msg,
            reason='unsupported command',
        )


class StreamFailure(namedtuple('Failure', 'direction message exception')):
    """Captures info about a failure during a stream-related operation."""


def iter_messages(stream, killed):
    """Yield each message found int the stream (after de-serializing)."""
    while not killed():
        try:
            # TODO: buffer 1k chunks and extract lines from there?
            for line in stream:
                yield Message.from_bytes(line)
        except Exception as exc:
            yield StreamFailure('recv', None, exc)


def kind_from_msg(msg, seq=None, text=None, **kwargs):
    """Return the kind for the given message."""
    if seq is None:
        if text is None:
            cmdid, seq, text = msg
        else:
            raise TypeError('missing seq')
    else:
        cmdid = PyDevdCommandID(msg)
    return _kind_from_msg(cmdid, seq, text, **kwargs)


def _kind_from_msg(cmdid, seq, text=None, response=False):
    seq = Sequence(seq)
    if response:
        if seq.origin is ORIGIN_DEBUGGER:
            return KIND_RESPONSE
        else:  # origin: daemon / pydevd
            raise NotImplementedError
    else:
        if seq % 2:  # origin: debugger / adapter
            return KIND_REQUEST
        else:
            return KIND_EVENT


def _look_up_payload(cmdid, seq, text, **kwargs):
    req = kwargs.pop('req', None)
    kind = _kind_from_msg(cmdid, seq, text, response=(req is not None))
    if kind is KIND_RESPONSE and req is not None:
        resp = Message(cmdid, seq, text)
        return look_up_response(req, resp)
    else:
        return look_up_payload(cmdid, kind, **kwargs)


class Sequence(int):
    """An int used to globally, uniquely identify a message."""

    __slots__ = []

    _seq = 0

    @classmethod
    def _inc(cls):
        seq = cls._seq
        cls._seq += 2
        return seq

    @classmethod
    def iter(cls, origin=ORIGIN_DEBUGGER):
        """Yield each successive globally unique ID."""
        while True:
            yield cls(origin=origin)

    def __new__(cls, seq=None, origin=None):
        if seq is None:
            seq = cls._next()
            if origin is None or origin is ORIGIN_DEBUGGER:
                seq += 1
            elif origin is not ORIGIN_DAEMON:
                raise ValueError('unsupported origin {!r}'.format(origin))
        elif type(seq) is cls:
            return seq
        elif origin is not None:
            # TODO: okay if matches seq?
            raise ValueError('got unexpected origin {!r}'.format(origin))

        return super(Sequence, cls).__new__(cls, seq)

    def __init__(self, *args, **kwargs):
        if self < 0:
            raise ValueError(
                'seq must be a non-negative int, got {!r}'.format(int(self)))

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, int(self))

    def __str__(self):
        return str(int(self))

    @property
    def origin(self):
        return ORIGIN_DEBUGGER if self % 2 else ORIGIN_DAEMON



class Message(namedtuple('Message', 'cmdid seq payload')):
    """A PyDevd message."""

    LOOK_UP_PAYLOAD = _look_up_payload

    @classmethod
    def origin_debugger(cls, cmdid, payload):
        """Return a new debugger message."""
        seq = Sequence(origin=ORIGIN_DEBUGGER)
        return cls(cmdid, seq, payload)

    @classmethod
    def origin_daemon(cls, cmdid, payload):
        """Return a new daemon message."""
        seq = Sequence(origin=ORIGIN_DAEMON)
        return cls(cmdid, seq, payload)

    @classmethod
    def from_bytes(cls, raw, **kwargs):
        """Return a new message based on the given bytes."""
        return cls._from_bytes(raw, **kwargs)

    @classmethod
    def _from_bytes(cls, raw, resolve=True, **kwargs):
        data = raw.decode('utf-8')
        cmdid, seq, text = data.split('\t', 2)
        text = urlunquote(text)
        if resolve:
            return cls.resolve(cmdid, seq, text, **kwargs)
        else:
            return cls(cmdid, seq, text, **kwargs)

    @classmethod
    def resolve(cls, cmdid, seq, text, **kwargs):
        """Return a Message with a resolved payload."""
        handler = cls.LOOK_UP_PAYLOAD(cmdid, seq, text, **kwargs)
        if handler is None:
            raw = Message(cmdid, seq, text)
            raise UnsupportedMessageError(raw)
        payload = handler.from_text(text)
        return cls(cmdid, seq, payload, handler.as_text)

    def __new__(cls, cmdid, seq, payload, payload_as_text=None):
        cmdid = PyDevdCommandID(cmdid) if cmdid or cmdid == 0 else None
        seq = Sequence(seq) if seq or seq == 0 else None
        self = super(Message, cls).__new__(cls, cmdid, seq, payload)
        self._payload_as_text = payload_as_text
        return self

    def __init__(self, *args, **kwargs):
        # validation
        if self.cmdid is None:
            raise InvalidMessageError(self, 'missing cmdid')
        if self.seq is None:
            raise InvalidMessageError(self, 'missing seq')

        if self._payload_as_text is None:
            if isinstance(self.payload, str):
                self._payload_as_text = (lambda p: p)
            elif isinstance(self.payload, (Payload, Handler)):
                self._payload_as_text = (lambda p: p.as_text())
            else:
                raise InvalidMessageError(self, 'bad payload')

    @property
    def command(self):
        try:
            return _pydevd.ID_TO_MEANING[str(self.cmdid)]
        except KeyError:
            return '???'

    @property
    def origin(self):
        return ORIGIN_DEBUGGER if self.seq % 2 else ORIGIN_DAEMON

    @property
    def payload_as_text(self):
        return self._payload_as_text(self.payload)

    def as_bytes(self, payload_as_text=None):
        """Return the sendable bytes representing the message."""
        text = self._payload_as_text(self.payload)
        text = urlquote(text or '')
        raw = '{}\t{}\t{}\n'.format(self.cmdid, self.seq, text)
        return raw.encode('utf-8')
