from collections import namedtuple

from ._command import (
    KIND_REQUEST, KIND_RESPONSE, KIND_EVENT,
    extract_cmdid, PyDevdCommandID,
)
from ._commands import (
    SUPPORTED,
    POSSIBLE,
    POSSIBLE_RESPONSES_BY_REQUEST,
)


########################
# the registry

HANDLERS = {
    KIND_REQUEST: {},
    KIND_RESPONSE: {},
    KIND_EVENT: {},
}

MATCHERS = {
    KIND_REQUEST: {},
    KIND_RESPONSE: {},
    KIND_EVENT: {},
}


def _look_up_kind(kind):
    try:
        possible = POSSIBLE[kind]
        supported = SUPPORTED[kind]
        registry = HANDLERS[kind]
        matchers = MATCHERS[kind]
    except KeyError:
        raise ValueError('unsupported kind {!r}'.format(kind))
    return possible, supported, registry, matchers


def _look_up(cmdid, kind, strict=True):
    possible, supported, registry, matchers = _look_up_kind(kind)

    if strict:
        if cmdid not in possible:
            raise ValueError('unknown {} cmdid {!r}'.format(kind, cmdid))
    else:
        supported = _check_possible(cmdid, kind, possible, supported)
        if supported is None:
            raise ValueError('unknown {} cmdid {!r}'.format(kind, cmdid))

    if cmdid not in supported:
        # TODO: Issue a warning instead?
        raise ValueError('unsupported {} cmdid {!r}'.format(kind, cmdid))

    # TODO: require corresponding request if response?

    return registry, matchers


def _check_possible(cmdid, kind, possible, supported):
    if cmdid in possible:
        return supported
    if kind is not KIND_RESPONSE:
        return None

    reqid = cmdid
    try:
        respid = POSSIBLE_RESPONSES_BY_REQUEST[reqid]
    except KeyError:
        return None

    if respid not in possible:
        return None

    return {reqid} if respid in supported else supported


def _match(allmatchers, msg, kind, cause=None):
    cmdid = msg.cmdid
    if cmdid not in allmatchers:
        return None
    for match, default in allmatchers[cmdid]:
        try:
            handler = match(msg, kind, cause)
        except Exception:
            # TODO: log the error?
            continue
        if handler:
            if handler is True:
                handler = default
            return handler
    else:
        return None


def register_handler(cmdid, kind, handler, match=None, **kwargs):
    """Map the given command to the handler (in the registry).

    If match function is not provided then the handler is used
    exclusively.
    """
    try:
        cmdid = PyDevdCommandID(cmdid)
    except ValueError as err:
        raise ValueError(
            'bad cmdid (expected int, got {!r}): {!r}'.format(cmdid, err))

    if match is None:
        _register_handler(cmdid, kind, handler, **kwargs)
    else:
        _register_matcher(cmdid, kind, match, handler, **kwargs)


def _register_matcher(cmdid, kind, match, handler=None):
    _, allmatchers = _look_up(cmdid, kind)
    matchers = allmatchers.setdefault(cmdid, [])
    matchers.append((match, handler))


def _register_handler(cmdid, kind, handler, force=False):
    registry, _ = _look_up(cmdid, kind, strict=False)
    if cmdid in registry:
        if not force:
            raise RuntimeError('cmdid {!r} already registered'.format(cmdid))
        # TODO: else issue a warning?

    registry[cmdid] = handler
    return handler


def look_up_payload(cmdid, kind, cause=None, strict=False):
    """Return the handler to use for the given command ID."""
    cmdid, msg = extract_cmdid(cmdid)
    registry, allmatchers = _look_up(cmdid, kind, strict=False)

    if not strict:
        # TODO: search "global" matchers first?

        # Try the cmdid-specific matchers.
        if msg is not None:
            try:
            handler = _match(allmatchers, cmdid, kind, cause)
            if handler is not None:
                return handler

    # Try the registry.
    try:
        return registry[cmdid]
    except KeyError:
        return None


def look_up_response(req, resp=None):
    """Return the handler to use for the response to the given request."""
    handler = look_up_payload(req, KIND_RESPONSE, strict=True)
    if handler is not None or resp is None:
        return handler
    return look_up_payload(resp, KIND_RESPONSE, req)


##################################
# handlers

def noop(value):
    return value


_NOT_SET = object()


class Handler(namedtuple('Handler', 'from_text as_text')):
    """A generic PyDevd message payload."""

    def __new__(cls, from_text, as_text=_NOT_SET):
        if as_text is _NOT_SET:
            if from_text is str:
                as_text = noop
            else:
                as_text = str
        elif as_text is None:
            as_text = noop
        self = super(Handler, cls).__new__(cls, from_text, as_text)
        return self


def _ensure_missing(raw):
    if raw:
        raise ValueError('got unexpected payload')
    return None


NO_PAYLOAD = Handler(_ensure_missing, None)


##################################
# register all default handlers

from . import _payloads  # noqa
