from pathlib import Path
from time import sleep
from typing import Union

import pytest
from AnalyticalLabware.devices.Advion.advion_cms import (
    AcquisitionManager,
    InstrumentController,
    SimulatedInstrument,
    USBInstrument,
)
from AnalyticalLabware.devices.Advion.config import API_PATH
from AnalyticalLabware.devices.Advion.enums import InstrumentState

data_path = Path(API_PATH) / ".." / "TestAPI" / "TestData"
method_file = data_path / "default.method"
tune_file = data_path / "positive.tune"
ion_source_file = data_path / "positiveESI.ion"

from AnalyticalLabware.devices.Advion.advion_cms import (
    SimulatedInstrument,
    USBInstrument,
    InstrumentController,
)


def pytest_addoption(parser):
    parser.addoption(
        "--instrument",
        action="store",
        default="simulated",
        help="Instrument type: simulated or usb",
    )


@pytest.fixture(scope="module")
def instrument(request):
    instrument_type = request.config.getoption("--instrument")
    if instrument_type == "simulated":
        inst = SimulatedInstrument(".")
    elif instrument_type == "usb":
        inst = USBInstrument()
    else:
        raise ValueError(f"Invalide instrument type {instrument_type}.")
    sleep(1.0)
    return inst


@pytest.fixture(scope="module")
def controller(instrument: Union[SimulatedInstrument, USBInstrument]):
    cont = InstrumentController(instrument)
    sleep(1.0)
    return cont


@pytest.fixture(scope="module")
def started_controller(controller: InstrumentController):
    controller.start_controller()
    sleep(1.0)
    assert controller.state == InstrumentState.Standby
    controller.operate()
    sleep(1.0)
    return controller


@pytest.fixture(scope="module")
def manager(started_controller: InstrumentController):
    mgr = AcquisitionManager(
        method_file, [ion_source_file], [tune_file], "test_acquisition", "."
    )
    sleep(1.0)
    return mgr
