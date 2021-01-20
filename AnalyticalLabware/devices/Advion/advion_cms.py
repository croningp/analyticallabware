import sys
from typing import List, Union

import clr

from .config import API_PATH
from .enums import (AcquisitionState, BinaryReadback, InstrumentState,
                    InstrumentSwitch, NumberReadback, OperationMode,
                    SourceType)
from .errors import check_return

sys.path.append(API_PATH)

clr.AddReference("AdvionCMS_NET")

import AdvionCMS_NET as cms


class _AbstractInstrument:
    def __init__(self):
        self._ptr = None

    def switch(self, switch: InstrumentSwitch, value: bool):
        self._ptr.setInstrumentSwitchOn(switch.value, value)

    def ignore_remaining_pumpdown_time(self):
        self._ptr.ignoreRemainingPumpDownTime()

    @property
    def pumpdown_remaining_seconds(self):
        return self._ptr.getPumpDownRemainingSeconds()

    @property
    def source_type(self):
        return SourceType(self._ptr.getSourceType())

    def get_readback(self, readbacktype: Union[NumberReadback, BinaryReadback]):
        if isinstance(readbacktype, NumberReadback):
            return self._ptr.getNumberReadback(readbacktype.value)
        elif isinstance(readbacktype, BinaryReadback):
            return self._ptr.getBinaryReadback(readbacktype.value)


class SimulatedInstrument(_AbstractInstrument):
    def __init__(self, path: str):
        self._ptr = cms.SimulatedInstrument(path)


class USBInstrument(_AbstractInstrument):
    def __init__(self):
        self._ptr = cms.USBInstrument()

class InstrumentController:
    def __init__(self, instrument: Union[USBInstrument, SimulatedInstrument]):
        self.instrument = instrument

    def start_controller(self):
        check_return(cms.InstrumentController.startController(self.instrument._ptr))

    def stop_controller(self):
        check_return(cms.InstrumentController.stopController())

    @property
    def state(self) -> InstrumentState:
        return InstrumentState(cms.InstrumentController.getState())

    @property
    def operation_mode(self) -> OperationMode:
        return OperationMode(cms.InstrumentController.getOperationMode())

    @property
    def can_vent(self) -> bool:
        return cms.InstrumentController.canVent()

    def vent(self):
        check_return(cms.InstrumentController.vent())

    @property
    def can_pump_down(self) -> bool:
        return cms.InstrumentController.canPumpDown()

    def pump_down(self):
        check_return(cms.InstrumentController.pumpDown())

    @property
    def tune_parameters(self) -> str:
        return cms.InstrumentController.getTuneParameters()

    @tune_parameters.setter
    def tune_parameters(self, tune_xml: str):
        """
        tune_xml (str): XML representation of tune parameters.
        """
        check_return(cms.InstrumentController.setTuneParameters(tune_xml))

    @property
    def ion_source_optimization(self) -> str:
        return cms.InstrumentController.getIonSourceOptimization()

    @ion_source_optimization.setter
    def ion_source_optimization(self, ion_source_xml: str):
        """
        ion_source_xml (str): XML representation of ion source optimization.
        """
        check_return(cms.InstrumentController.setIonSourceOptimization(ion_source_xml))

    @property
    def can_operate(self) -> bool:
        return cms.InstrumentController.canOperate()

    def operate(self):
        check_return(cms.InstrumentController.operate())

    @property
    def can_standby(self) -> bool:
        return cms.InstrumentController.canStandby()

    def standby(self):
        check_return(cms.InstrumentController.standby())
