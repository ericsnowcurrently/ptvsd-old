
SCOPES = {'GLOBAL', 'FRAME'}


class Payload(object):
    """The base class for other payload types."""

    @classmethod
    def from_text(cls, text):
        """Return a new Payload corresponding to the given text."""
        return cls(text)

    def as_text(self):
        """Return the wire-format text corresponding to the payload."""
        raise NotImplementedError
