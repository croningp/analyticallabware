"""Python adapter for CLR library AdvionData_NET."""
import sys
from typing import List, Union

import clr
import System
import numpy as np

from .config import API_PATH
from .enums import AcquisitionScanMode
from .errors import check_return

sys.path.append(API_PATH)

clr.AddReference("AdvionData_NET")
import AdvionData_NET as adata


class AdvionData:
    def __init__(
        self, path: str, debug_output: bool = False, decode_spectra: bool = False
    ):
        """Initialize `AdvionData` object.

        Args:
            path (str): Path to .datx file.
                Absolute and relative paths with / and \\ as separator work.
            debug_output (bool, optional): Produce debug output. Defaults to False.
            decode_spectra (bool, optional): TBD. Defaults to False.
        """
        self._handle = adata.DataReader(path, debug_output, decode_spectra)

    def num_masses(self) -> int:
        """
        Returns:
            int: Number of masses in data file.
        """
        return self._handle.getNumMasses()

    def num_spectra(self) -> int:
        """
        Returns:
            int: Number of spectra in data file.
        """
        return self._handle.getNumSpectra()

    def date(self) -> str:
        """
        Returns:
            str: Sample run date.
        """
        return self._handle.getDate()

    def masses(self) -> np.ndarray:
        """
        Returns:
            np.ndarray: Array of masses sampled (common to all spectra).
        """
        n = self.num_masses()
        buff = System.Array.CreateInstance(System.Single, n)
        check_return(self._handle.getMasses(buff), adviondata=True)
        return np.fromiter(buff, dtype="float")

    def retention_times(self) -> np.ndarray:
        """
        Returns:
            np.ndarray: Chromatogram retention times.
        """
        n = self.num_spectra()
        buff = System.Array.CreateInstance(System.Single, n)
        check_return(self._handle.getRetentionTimes(buff), adviondata=True)
        return np.fromiter(buff, dtype="float")

    def spectrum(self, index: int) -> np.ndarray:
        """Retrieve a given spectrum in data file.

        Args:
            index (int): Spectrum index in chromatogram.
                Valid range: 0 - (num_spectra - 1)

        Returns:
            np.ndarray: Intensities for each mass (in `self.masses`).
        """
        n = self.num_masses()
        buff = System.Array.CreateInstance(System.Single, n)
        check_return(self._handle.getSpectrum(index, buff), adviondata=True)
        return np.fromiter(buff, dtype="float")

    def spectra(self, as_list=False) -> Union[np.ndarray, List[np.ndarray]]:
        """Retrieve all spectra in data file.

        Args:
            as_list (bool, optional): Return a Python list of spectra
                instead of a matrix. Defaults to False.

        Returns:
            np.ndarray: If `as_list` is set to `True` a Python list of
                spectra (each a numpy array), otherwise a matrix of shape
                (num_spectra, num_masses).
        """
        N = self.num_spectra()
        specs = [self.spectrum(i) for i in range(N)]
        if as_list:
            return specs
        else:
            return np.stack(specs)

    def TIC(self, index: int) -> float:
        """Retreive total ion current at a given point in the chromatogram.

        Args:
            index (int): Index with chromatogram. Valid range 0 - (num_spectra - 1)

        Returns:
            float: Total ion current.
        """
        return self._handle.getTIC(index)

    def write_csv(self, csv_filename: str):
        """Write all spectra to a CSV file.

        Args:
            csv_filename (str): Destination CSV filename.
        """
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
        """Write all spectra to a NPZ file.

        Args:
            npz_filename (str): Destination NPZ file.
        """
        np.savez_compressed(
            npz_filename,
            spectra=self.spectra(),
            retention_times=self.retention_times(),
            masses=self.masses(),
        )

    def experiment_log(self) -> str:
        """
        Returns:
            str: Experiment log.
        """
        return self._handle.getExperimentLog()

    def scan_mode(self) -> AcquisitionScanMode:
        """
        Returns:
            AcquisitionScanMode: Acquisition scan mode.
        """
        return AcquisitionScanMode(self._handle.getScanModeIndex())
