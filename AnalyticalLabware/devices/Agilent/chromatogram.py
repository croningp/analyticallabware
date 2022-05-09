"""Module for HPLC chromatogram data loading and manipulating"""

import logging
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Union, Any

import numpy as np

from .chemstation import CHFile

from ...analysis import AbstractSpectrum

if TYPE_CHECKING:
    import os

# Chemstation data path
DATA_DIR = r"C:\Chem32\1\Data"


# standard filenames for spectral data
CHANNELS = {"A": "01", "B": "02", "C": "03", "D": "04"}

ACQUISITION_PARAMETERS = "acq.txt"

# format used in acquisition parameters
TIME_FORMAT = "%Y-%m-%d-%H-%M"

# file format for DAD detectors
DAD_FILE_FORMAT = "DAD1{}"

# file suffixes
NPZ_FILE_SUFFIX = ".npz"
CHEMSTATION_FILE_SUFFIX = ".ch"


class AgilentHPLCChromatogram(AbstractSpectrum):
    """Class for HPLC spectrum (chromatogram) loading and handling."""

    AXIS_MAPPING = {"x": "min", "y": "mAu"}

    INTERNAL_PROPERTIES = {
        "baseline",
        "parameters",
        "data_path",
    }

    # set of properties to be saved
    PUBLIC_PROPERTIES = {
        "x",
        "y",
        "peaks",
        "timestamp",
    }

    def __init__(self, path=None, autosaving=False):

        # Creating path if None
        if path is None:
            path = Path(".", "hplc_data")

        self.logger = logging.getLogger("AgilentHPLCChromatogram")

        super().__init__(path=path, autosaving=autosaving)

    def load_spectrum(self, data_path, channel="A"):
        """Loads the spectra from the given folder.

        Args:
            data_path (str): Path where HPLC data has been saved.
        """

        # to avoid dropping parameters when called in parent class
        if self.x is not None:
            if self.autosaving:
                self.save_data(filename=f"{data_path}_{channel}")
                self._dump()

        # get raw data
        x, y = self.extract_rawdata(data_path, channel)

        # get timestamp
        tstr = data_path.split(".")[0].split("_")[-1]
        timestamp = time.mktime(time.strptime(tstr, TIME_FORMAT))

        # loading all data
        super().load_spectrum(x, y, timestamp)

    ### PUBLIC METHODS TO LOAD RAW DATA ###

    def extract_rawdata(
        self,
        experiment_dir: Union[str, 'os.PathLike'],
        channel: str,
    ) -> tuple(np.array, np.array, dict[str, Any]):
        """ Reads raw data and metadata from Chemstation .CH files.

        Args:
            experiment_dir (Union[str, os.PathLike]): .D directory with the
                .CH files.
            channel (str): Selected channel in the detector.

        Returns:
            tuple(np.array, np.array, dict[str, Any]): Tuple of raw
                chromatographic data and metadata:
                    - times (np.array): Time scale.
                    - values (np.array): Readings from the detector.
                    - metadata (dict[str, Any]): Dictionary with metadata,
                        associated with the given acquisition.

        Notes:
            Only looks for DAD detector data.
        """
        filename = Path(experiment_dir).joinpath(
            DAD_FILE_FORMAT.format(channel))
        npz_file = filename.with_suffix(NPZ_FILE_SUFFIX)

        if npz_file.is_file():
            # already processed
            return self._treat_npz_file(npz_filepath=npz_file)

        self.logger.debug("NPZ file not found. First time loading data.")
        ch_file = filename.with_suffix(CHEMSTATION_FILE_SUFFIX)
        data = CHFile(ch_file)
        np.savez_compressed(npz_file, times=data.times, values=data.values)
        return np.array(data.times), np.array(data.values)

    def _treat_npz_file(
        self,
        npz_filepath: Union[str, 'os.PathLike']
    ) -> tuple(np.array, np.array, str):
        """ Legacy method to read from .npz compressed arrays. """

        warnings.warn("Manipulating .npz files is deprecated and will be \
removed soon. Consider using save_data() and load_data() methods to work with \
pickled files.", FutureWarning)

        data = np.load(npz_filepath)

        return (data['times'], data['values'])

    def extract_peakarea(self, experiment_dir: str):
        """
        Reads processed data from Chemstation report files.

        Args:
            experiment_dir: .D directory with the report files
        """
        # filename = os.path.join(experiment_dir, f"REPORT{CHANNELS[channel]}.csv")
        # TODO parse file properly
        # data = np.genfromtxt(filename, delimiter=',')
        # return data
        pass

    def default_processing(self):
        """
        Processes the chromatogram in place.
        """
        # trim first 5 min and last 3 min of run
        self.trim(5, 25)
        # parameters found to work best for chromatogram data
        self.correct_baseline(lmbd=1e5, p=0.0001, n_iter=10)
        # get all peaks in processed chromatogram
        self.find_peaks()
