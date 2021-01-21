"""Python adapter for C wrapper around AdvionData.dll."""

from ctypes import CDLL, POINTER, c_bool, c_char_p, c_double, c_int, c_void_p, c_float
from os import chdir
from os.path import abspath, dirname
from typing import Union, List


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
