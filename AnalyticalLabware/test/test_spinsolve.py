import sys
from os import path
from textwrap import dedent

sys.path.append(path.realpath(path.join(path.dirname(__file__), "..")))

from devices.Magritek import messages as msg


def strip(x: str):
    return dedent(x).strip()


def test_message():
    assert str(msg.Message(msg.CheckShim())) == strip(
        """
    <?xml version="1.0" encoding="UTF-8"?>
    <Message>
    <CheckShimRequestType />
    </Message>
    """
    )


def test_option():
    print()
    assert str(msg.Option("n", 123)) == strip(
        """
    <Option name='n' value='123' />
    """
    )


def test_script():
    assert str(msg.Script("test")) == strip(
        """
    <Script>
    test
    </Script>
    """
    )
