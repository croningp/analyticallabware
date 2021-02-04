"""Python adapter for CLR library AdvionData_NET."""
import sys
from ctypes import c_double

import clr
import numpy as np

from .config import API_PATH
from .errors import check_return

sys.path.append(API_PATH)

clr.AddReference("AdvionData_NET")
import AdvionData_NET as adata


class AdvionData:
    def __init__(
        self, path: str, debug_output: bool = False, decode_spectra: bool = False
    ):
        self._handle = adata.DataReader(path.encode(), debug_output, decode_spectra)

    def num_masses(self) -> int:
        return self._handle.getNumMasses()

    def num_spectra(self) -> int:
        return self._handle.getNumSpectra()

    def date() -> str:
        return self._handle.getDate()

    def masses(self) -> np.ndarray:
        n = self.num_masses()
        buff = np.ndarray(n, dtype=c_double)
        check_return(self._handle.getMasses(buff), adviondata=True)
        return buff

    def retention_times(self) -> np.ndarray:
        n = self.num_spectra()
        buff = np.ndarray(n, dtype=c_double)
        check_return(self._handle.getRetentionTimes(buff), adviondata=True)
        return buff

    def spectrum(self, index: int) -> np.ndarray:
        n = self.num_masses()
        buff = np.ndarray(n, dtype=c_double)
        check_return(self._handle.getSpectrum(index, buff), adviondata=True)
        return buff

    def spectra(self, as_list=False) -> np.ndarray:
        N = self.num_spectra()
        specs = [self.spectrum(i) for i in range(N)]
        if as_list:
            return specs
        else:
            return np.stack(specs)

    def TIC(self, index: int) -> float:
        return self._handle.getTIC(index)

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

    def experiment_log(self) -> str:
        return self._handle.getExperimentLog()

    def scan_mode(self) -> int:
        return self._handle.getScanModeIndex()


if __name__ == "__main__":
    import sys

    print(sys.argv)
    input_filename = sys.argv[-2]
    output_file = sys.argv[-1]
    data = AdvionData(input_filename)
    data.write_npz(output_file)
