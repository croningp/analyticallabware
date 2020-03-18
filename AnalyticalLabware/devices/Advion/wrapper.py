"""Python adapter for C wrapper around AdvionData.dll."""

from ctypes import CDLL, POINTER, c_bool, c_char_p, c_double, c_int, c_void_p, c_float
from os import chdir
from os.path import abspath, dirname
from typing import Union, List

import numpy as np

from .enums import (
    AcquisitionState,
    InstrumentState,
    InstrumentSwitch,
    OperationMode,
    SourceType,
    NumberReadback,
    BinaryReadback,
)
from .errors import check_return

LIBNAME = "advion_wrapper.dll"

# Must cd into the dll's folder because of
# inter-dll dependencies. cd back to be polite.
cur_dir = abspath(".")
lib_path = abspath(dirname(__file__))
chdir(lib_path)
try:
    dll = CDLL(LIBNAME)
except OSError:
    raise ModuleNotFoundError('Could not load Advion bindings, please refer to README for possible causes.') from None
chdir(cur_dir)

# Type declarations
## Argument types
dll.simulated_instrument.argtypes = [c_char_p]
dll.extend.argtypes = [c_int]
dll.start.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p, c_char_p]
dll.set_acquisition_bins_per_amu.argtypes = [c_int]
dll.set_tune_parameters.argtypes = [c_char_p]
dll.set_ion_source_optimization.argtypes = [c_char_p]
dll.set_switch.argtypes = [c_void_p, c_int, c_bool]
dll.ignore_remaining_pumpdown_time.argtypes = [c_void_p]
dll.get_pumpdown_remaining_seconds.argtypes = [c_void_p]
dll.get_number_readback.argtypes = [c_void_p, c_int]
dll.get_binary_readback.argtypes = [c_void_p, c_int]
dll.make_reader.argtypes = [c_char_p, c_bool, c_bool]

## Return types
dll.extend.restype = c_int
dll.get_last_num_masses.restype = c_int
dll.get_max_num_masses.restype = c_int
dll.get_acquisition_bins_per_amu.restype = c_int
dll.get_current_folder.restype = c_char_p
dll.get_tune_parameters.restype = c_char_p
dll.get_ion_source_optimization.restype = c_char_p
dll.can_operate.restype = c_bool
dll.can_pump_down.restype = c_bool
dll.can_standby.restype = c_bool
dll.can_vent.restype = c_bool
dll.get_number_readback.restype = c_double
dll.get_binary_readback.restype = c_bool
dll.get_TIC.restype = c_float


class _AbstractInstrument:
    def __init__(self):
        self._ptr = None

    def switch(self, switch: InstrumentSwitch, value: bool):
        dll.set_switch(self._ptr, switch, value)

    def ignore_remaining_pumpdown_time(self):
        dll.ignore_remaining_pumpdown_time(self._ptr)

    @property
    def pumpdown_remaining_seconds(self):
        return dll.get_pumpdown_remaining_seconds(self._ptr)

    @property
    def source_type(self):
        return SourceType(dll.get_source_type(self._ptr))

    def get_readback(self, readbacktype: Union[NumberReadback]):
        if isinstance(readbacktype, NumberReadback):
            return dll.get_number_readback(self._ptr, readbacktype.value)
        elif isinstance(readbacktype, BinaryReadback):
            return dll.get_binary_readback(self._ptr, readbacktype.value)


class SimulatedInstrument(_AbstractInstrument):
    def __init__(self, path: str):
        self._ptr = dll.simulated_instrument(path.encode())


class USBInstrument(_AbstractInstrument):
    def __init__(self):
        self._ptr = dll.usb_instrument()


class InstrumentController:
    def __init__(self, instrument: Union[USBInstrument, SimulatedInstrument]):
        self.instrument = instrument

    def start_controller(self):
        check_return(dll.start_controller(self.instrument._ptr))

    def stop_controller(self):
        check_return(dll.stop_controller())

    @property
    def state(self) -> InstrumentState:
        return InstrumentState(dll.get_instrument_state())

    @property
    def operation_mode(self) -> OperationMode:
        return OperationMode(dll.get_operation_mode())

    @property
    def can_vent(self) -> bool:
        return dll.can_vent()

    def vent(self):
        check_return(dll.vent())

    @property
    def can_pump_down(self) -> bool:
        return dll.can_vent()

    def pump_down(self):
        check_return(dll.pump_down())

    @property
    def tune_parameters(self) -> str:
        return dll.get_tune_parameters().decode()

    @tune_parameters.setter
    def tune_parameters(self, tune_xml: str):
        """
        tune_xml (str): XML representation of tune parameters.
        """
        check_return(dll.set_tune_parameters(tune_xml.encode()))

    @property
    def ion_source_optimization(self) -> str:
        return dll.get_ion_source_optimization().decode()

    @ion_source_optimization.setter
    def ion_source_optimization(self, ion_source_xml: str):
        """
        tune_xml (str): XML representation of tune parameters.
        """
        check_return(dll.set_ion_source_optimization(ion_source_xml.encode()))

    @property
    def can_operate(self) -> bool:
        return dll.can_operate()

    def operate(self):
        check_return(dll.operate())

    @property
    def can_standby(self) -> bool:
        return dll.can_standby()

    def standby(self):
        check_return(dll.standby())


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

    def pause(self):
        check_return(dll.pause())

    def extend(self, seconds: int) -> int:
        return dll.extend(seconds).value

    def resume(self):
        check_return(dll.resume())

    def start(self):
        if len(self.ion_source_xml) == 2 and len(self.tune_xml) == 2:
            ion_source_xml1, ion_source_xml2 = self.ion_source_xml
            tune_xml1, tune_xml2 = self.tune_xml
            ret = dll.start_with_switching(
                self.method_xml.encode(),
                ion_source_xml1.encode(),
                ion_source_xml2.encode(),
                tune_xml1.encode(),
                tune_xml2.encode(),
                self.name.encode(),
                self.folder.encode(),
            )
        elif len(self.ion_source_xml) == 1 and len(self.tune_xml) == 1:
            ret = dll.start_with_switching(
                self.method_xml.encode(),
                self.ion_source_xml[0].encode(),
                self.tune_xml[0].encode(),
                self.name.encode(),
                self.folder.encode(),
            )
        else:
            raise ValueError("Must specify 1 or 2 ion source/tune files.")
        check_return(ret)

    def stop(self):
        check_return(dll.stop())

    @property
    def state(self) -> AcquisitionState:
        return AcquisitionState(dll.get_state())

    @property
    def current_folder(self) -> str:
        return dll.get_current_folder().decode()

    @property
    def acquisition_bins_per_amu(self) -> int:
        return dll.get_acquisition_bins_per_amu()

    @acquisition_bins_per_amu.setter
    def acquisition_bins_per_amu(self, value: int):
        return dll.set_acquisition_bins_per_amu(value)

    @property
    def max_num_masses(self) -> int:
        return dll.get_max_num_masses()

    @property
    def last_num_masses(self) -> int:
        return dll.get_last_num_masses()

    @property
    def last_spectrum(self) -> np.array:
        num_peaks = self.last_num_masses
        masses = np.ndarray(num_peaks, dtype=c_double)
        intensities = np.ndarray(num_peaks, dtype=c_double)
        dll.get_last_spectrum_masses(masses.ctypes.data_as(POINTER(c_double)))
        dll.get_last_spectrum_intensities(intensities.ctypes.data_as(POINTER(c_double)))
        return masses, intensities


class AdvionData:
    def __init__(
        self, path: str, debug_output: bool = False, decode_spectra: bool = False
    ):
        self._handle = dll.make_reader(path.encode(), debug_output, decode_spectra)

    def __del__(self):
        dll.free_reader(self._handle)

    def num_spectra(self) -> int:
        return dll.num_spectra(self._handle)

    def masses(self) -> np.array:
        n = dll.num_masses(self._handle)
        buff = (c_float * n)()
        check_return(dll.get_masses(self._handle, buff), adviondata=True)
        return np.array(buff)

    def retention_times(self) -> np.array:
        n = dll.num_spectra(self._handle)
        buff = (c_float * n)()
        check_return(dll.retention_times(self._handle, buff), adviondata=True)
        return np.array(buff)

    def spectrum(self, index: int) -> np.array:
        n = dll.num_masses(self._handle)
        buff = (c_float * n)()
        check_return(dll.get_spectrum(self._handle, index, buff), adviondata=True)
        return np.array(buff)

    def spectra(self, as_list=False) -> np.array:
        N = self.num_spectra()
        specs = [self.spectrum(i) for i in range(N)]
        if as_list:
            return specs
        else:
            return np.stack(specs)

    def TIC(self, index: int) -> float:
        return dll.get_TIC(self._handle, index)

    def write_csv(self, csv_filename: str):
        # use AdvionData to get the information out of the .datx file
        ms_arr = self.spectra()
        xs, ys = ms_arr.nonzero()
        positive_ints = zip(list(xs), list(ys))
        ms_masses = self.masses()
        ms_ret_times = self.retention_times()

        with open(csv_filename, "w") as f:
            header_line = "rt,m/z,intensity\n"
            f.write(header_line)
            for (i, j) in positive_ints:
                f.write(f"{ms_ret_times[i]},{ms_masses[j]},{ms_arr[i, j]}\n")

    def write_npz(self, npz_filename: str):
        np.savez_compressed(
            npz_filename,
            spectra=self.spectra(),
            retention_times=self.retention_times(),
            masses=self.masses(),
        )


if __name__ == "__main__":
    import sys

    print(sys.argv)
    input_filename = sys.argv[-2]
    output_file = sys.argv[-1]
    data = AdvionData(input_filename)
    data.write_npz(output_file)
