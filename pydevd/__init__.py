# What pydevd calls a "debugger", we might also call a debug adapter.
# ptvsd is thus a "debugger".  pydevd calls itself a "daemon".
ORIGIN_DEBUGGER = 'debugger'  # noqa
ORIGIN_DAEMON = 'daemon'  # noqa

from . import _commands
_commands.import_command_ids(vars())
del _commands


# Expose the remaining public parts of the package.
from ._command import KIND_REQUEST, KIND_RESPONSE, KIND_EVENT  # noqa
from ._message import (  # noqa
    MessageError,
    MalformedMessageError, InvalidMessageError, UnsupportedMessageError,
    StreamFailure, iter_messages,
    Message,
)
from ._handler import (  # noqa
    register_handler, look_up_payload, look_up_response, Handler,
)
