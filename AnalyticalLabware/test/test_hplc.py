import sys
import os
import pytest
import time

from AnalyticalLabware.devices.Agilent.hplc import HPLCController

@pytest.fixture(scope="function")
def ctrlr():
    yield HPLCController(os.path.dirname(sys.argv[-1]))

def test_send(ctrlr):
    ctrlr.send('Print "Hi"')
    with open(ctrlr.cmd_file, "r") as cmd_file:
                command = cmd_file.read()
    assert command == '1 Print "Hi"'

def test_receive(ctrlr):
    ctrlr.send('Print "Hi"')
    response = ctrlr.receive()
    assert response == "1 ACK\n1 \n1 DONE\n"

def test_reset(ctrlr):
    for _ in range(256):
        ctrlr.send('Print "Hi"')
    time.sleep(1)
    ctrlr.send('Print "Hi"')
    time.sleep(1)
    ctrlr.send('Print "Hi"')
    assert ctrlr.cmd_no == 1





