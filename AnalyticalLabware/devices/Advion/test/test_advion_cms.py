from os import path
from time import sleep
from typing import Union

from AnalyticalLabware.devices.Advion import enums
from AnalyticalLabware.devices.Advion.advion_cms import (
    AcquisitionManager,
    InstrumentController,
    SimulatedInstrument,
    USBInstrument,
)
from AnalyticalLabware.devices.Advion.errors import AdvionCMSError


def test_binary_readback(instrument: Union[SimulatedInstrument, USBInstrument]):
    for readback_type in enums.BinaryReadback:
        readback = instrument.get_readback(readback_type)
        print(f"{readback_type!s}: {readback}")
        assert isinstance(readback, bool)


def test_number_readback(instrument: Union[SimulatedInstrument, USBInstrument]):
    for readback_type in enums.NumberReadback:
        readback = instrument.get_readback(readback_type)
        print(f"{readback_type!s}: {readback}")
        assert isinstance(readback, int) or isinstance(readback, float)


def test_source_type(instrument: Union[SimulatedInstrument, USBInstrument]):
    assert isinstance(instrument.source_type, enums.SourceType)


def test_switch(instrument: Union[SimulatedInstrument, USBInstrument]):
    for switch in enums.InstrumentSwitch:
        assert instrument.switch(switch, True) is None
        assert instrument.switch(switch, False) is None


def test_ignore_remaining_pumpdown_time(
    instrument: Union[SimulatedInstrument, USBInstrument]
):
    assert instrument.ignore_remaining_pumpdown_time() is None


def test_pumpdown_remaining_seconds(
    instrument: Union[SimulatedInstrument, USBInstrument]
):
    assert isinstance(instrument.pumpdown_remaining_seconds, int)


def test_start_controller(controller: InstrumentController):
    assert controller.start_controller() is None


def test_stop_controller(controller: InstrumentController):
    assert controller.stop_controller() is None


def test_controller_state(controller: InstrumentController):
    assert isinstance(controller.state, enums.InstrumentState)


def test_operation_mode(controller: InstrumentController):
    assert isinstance(controller.operation_mode, enums.OperationMode)


def test_vent_pump(started_controller: InstrumentController):
    if started_controller.can_vent:
        assert started_controller.vent() is None
        sleep(1.0)
    if started_controller.can_pump_down:
        assert started_controller.pump_down() is None


def test_tune_parameters(controller: InstrumentController):
    tune_parameters = controller.tune_parameters
    assert isinstance(tune_parameters, str)
    controller.tune_parameters = tune_parameters
    assert tune_parameters == controller.tune_parameters


def test_ion_source_optimization(controller: InstrumentController):
    ion_source_optimization = controller.ion_source_optimization
    assert isinstance(ion_source_optimization, str)
    print(ion_source_optimization)
    controller.ion_source_optimization = ion_source_optimization
    assert ion_source_optimization == controller.ion_source_optimization


# def test_operate(started_controller: InstrumentController):
#     try:
#         started_controller.operate()
#     except AdvionCMSError:
#         if started_controller.can_operate:
#             raise

# def test_standby(started_controller: InstrumentController):
#     try:
#         started_controller.standby()
#     except AdvionCMSError:
#         print(started_controller.can_standby)
#         if started_controller.can_standby:
#             raise


def test_acquisition_control(manager: AcquisitionManager):
    assert manager.state == enums.AcquisitionState.Ready
    manager.start()
    sleep(1.0)
    assert manager.state == enums.AcquisitionState.Underway
    manager.pause(False)
    sleep(1.0)
    assert manager.state == enums.AcquisitionState.Paused
    manager.resume()
    sleep(1.0)
    assert manager.state == enums.AcquisitionState.Underway
    manager.extend(2)


def test_acquisition_folder(manager: AcquisitionManager):
    assert path.exists(manager.current_folder)


def test_last_spectrum(manager: AcquisitionManager):
    masses, intensities = manager.last_spectrum
    assert len(masses) == len(intensities)
    assert masses.dtype == intensities.dtype
    assert masses.max() > 0.0
    assert intensities.max() > 0.0
