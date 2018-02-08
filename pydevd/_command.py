from _pydevd_bundle.pydevd_comm import ID_TO_MEANING


KIND_REQUEST = 'request'
KIND_RESPONSE = 'response'
KIND_EVENT = 'event'


def extract_cmdid(msg):
    """Return (cmdid, msg) based on the given message."""
    try:
        cmdid = msg.cmdid
    except AttributeError:
        cmdid = msg
        msg = None
    try:
        cmdid = PyDevdCommandID(cmdid)
    except ValueError as err:
        raise ValueError(
            'bad cmdid (expected int, got {!r}): {!r}'.format(cmdid, err))
    return cmdid, msg


class PyDevdCommandID(int):
    """A PyDevd command ID."""

    __slots__ = []

    @classmethod
    def from_name(cls, name):
        """Return the corresponding command ID."""
        for cmdid, cmdname in ID_TO_MEANING.items():
            if name == cmdname:
                return cls(cmdid)
        else:
            raise ValueError('unknown cmdid {!r}'.format(name))

    def __new__(cls, cmdid, **kwargs):
        if isinstance(cmdid, str) and cmdid.startswith('CMD_'):
            return cls.from_name(cmdid)
        if type(cmdid) is PyDevdCommandID:
            return cmdid
        return super(PyDevdCommandID, cls).__new__(cls, cmdid)

    def __init__(self, cmdid, force=False):
        if not force and str(self) not in ID_TO_MEANING:
            raise ValueError('unknown cmdid {}'.format(self))

    def __repr__(self):
        return '{} ({})'.format(self.name, int(self))

    def __str__(self):
        return str(int(self))

    @property
    def name(self):
        return ID_TO_MEANING.get(str(self), 'UNKNOWN')
