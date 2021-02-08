"""Python adapter for CLR library AdvionCMS_NET."""

import sys
from ctypes import c_double
from typing import List, Tuple, Union

import clr
import numpy as np

from .config import API_PATH
from .enums import (
    AcquisitionState,
    BinaryReadback,
    InstrumentState,
    InstrumentSwitch,
    NumberReadback,
    OperationMode,
    SourceType,
)
from .errors import check_return

sys.path.append(API_PATH)

clr.AddReference("AdvionCMS_NET")
import AdvionCMS_NET as cms


class _AbstractInstrument:
    def __init__(self):
        self._handle = None

    def switch(self, switch: InstrumentSwitch, value: bool):
        self._handle.setInstrumentSwitchOn(switch.value, value)

    def ignore_remaining_pumpdown_time(self):
        self._handle.ignoreRemainingPumpDownTime()

    @property
    def pumpdown_remaining_seconds(self):
        return self._handle.getPumpDownRemainingSeconds()

    @property
    def source_type(self):
        return SourceType(self._handle.getSourceType())

    def get_readback(self, readbacktype: Union[NumberReadback, BinaryReadback]):
        if isinstance(readbacktype, NumberReadback):
            return self._handle.getNumberReadback(readbacktype.value)
        elif isinstance(readbacktype, BinaryReadback):
            return self._handle.getBinaryReadback(readbacktype.value)


class SimulatedInstrument(_AbstractInstrument):
    def __init__(self, path: str):
        self._handle = cms.SimulatedInstrument(path)


class USBInstrument(_AbstractInstrument):
    def __init__(self, override_safeties:bool=False, override_pump:bool=False):
        self._handle = cms.USBInstrument(override_safeties, override_pump)


class InstrumentController:
    def __init__(self, instrument: Union[USBInstrument, SimulatedInstrument]):
        self.instrument = instrument

    def start_controller(self):
        check_return(cms.InstrumentController.startController(self.instrument._handle))

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


class AcquisitionManager:
    def __init__(
        self,
        method_xml_file: str,
        ion_source_xml_files: List[str],
        tune_xml_files: List[str],
        name: str,
        folder: str = "",
    ):
        self.method_xml = open(method_xml_file).read()
        self.ion_source_xml = [
            open(ion_source_xml_file).read()
            for ion_source_xml_file in ion_source_xml_files
        ]
        self.tune_xml = [open(tune_xml_file).read() for tune_xml_file in tune_xml_files]
        self.name = name
        self.folder = folder

    def pause(self, resume_on_digital_input: bool):
        check_return(cms.AcquisitionManager.pause(resume_on_digital_input))

    def extend(self, seconds: int) -> int:
        return cms.AcquisitionManager.extend(seconds)

    def resume(self):
        check_return(cms.AcquisitionManager.resume())

    def start(self):
        if len(self.ion_source_xml) == 2 and len(self.tune_xml) == 2:
            ion_source_xml1, ion_source_xml2 = self.ion_source_xml
            tune_xml1, tune_xml2 = self.tune_xml
            ret = cms.AcquisitionManager.startWithSwitching(
                self.method_xml,
                ion_source_xml1,
                ion_source_xml2,
                tune_xml1,
                tune_xml2,
                self.name,
                self.folder,
            )
        elif len(self.ion_source_xml) == 1 and len(self.tune_xml) == 1:
            ret = cms.AcquisitionManager.start(
                self.method_xml,
                self.ion_source_xml[0],
                self.tune_xml[0],
                self.name,
                self.folder,
            )
        else:
            raise ValueError("Must specify 1 or 2 ion source/tune files.")
        check_return(ret)

    def stop(self):
        check_return(cms.AcquisitionManager.stop())

    @property
    def state(self) -> AcquisitionState:
        return AcquisitionState(cms.AcquisitionManager.getState())

    @property
    def current_folder(self) -> str:
        return cms.AcquisitionManager.getCurrentFolder()

    @property
    def acquisition_bins_per_amu(self) -> int:
        return cms.AcquisitionManager.getAcquisitionBinsPerAMU()

    @acquisition_bins_per_amu.setter
    def acquisition_bins_per_amu(self, value: int):
        check_return(cms.AcquisitionManager.setAcquisitionBinsPerAMU(value))

    @property
    def max_num_masses(self) -> int:
        return cms.AcquisitionManager.getMaxNumMasses()

    @property
    def last_num_masses(self) -> int:
        return cms.AcquisitionManager.getLastNumMasses()

    @property
    def last_tic(self) -> float:
        return cms.AcquisitionManager.getLastTIC()

    @property
    def last_spectrum(self) -> Tuple[np.ndarray, np.ndarray]:
        num_peaks = self.last_num_masses
        masses = np.ndarray(num_peaks, dtype=c_double)
        intensities = np.ndarray(num_peaks, dtype=c_double)
        cms.AcquisitionManager.getLastSpectrumMasses(masses)
        cms.AcquisitionManager.getLastSpectrumIntensities(intensities)
        return masses, intensities
