from AnalyticalLabware.devices.Advion.enums import InstrumentState
from typing import Union
import pytest

from AnalyticalLabware.devices.Advion.advion_cms import SimulatedInstrument, USBInstrument, InstrumentController

def pytest_addoption(parser):
    parser.addoption(
        "--instrument", action="store", default="simulated", help="Instrument type: simulated or usb"
    )

@pytest.fixture(scope="module")
def instrument(request):
    instrument_type = request.config.getoption("--instrument")
    if instrument_type == "simulated":
        return SimulatedInstrument(".")
    elif instrument_type == "usb":
        return USBInstrument()
    else:
        raise ValueError(f"Invalide instrument type {instrument_type}.")

@pytest.fixture(scope="module")
def controller(instrument: Union[SimulatedInstrument, USBInstrument]):
    return InstrumentController(instrument)

@pytest.fixture(scope="module")
def started_controller(controller: InstrumentController):
    controller.start_controller()
    return controller

