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

# Standard filenames for spectral data
CHANNELS = {"A": "01", "B": "02", "C": "03", "D": "04"}

ACQUISITION_PARAMETERS = "acq.txt"

# Format used in acquisition parameters
TIME_FORMAT = r"%d-%b-%y, %H:%M:%S"

# File format for DAD detectors
DAD_FILE_FORMAT = "DAD1{}"

# File suffixes
NPZ_FILE_SUFFIX = ".npz"
CHEMSTATION_FILE_SUFFIX = ".ch"

# Found experimentally
BASELINE_CORRECTION_CONFIG = {
    "lmbd": 1e5,
    "p": 0.0001,
    "n_iter": 10,
}


class AgilentHPLCChromatogram(AbstractSpectrum):
    """Class for HPLC spectrum (chromatogram) loading and handling."""

    AXIS_MAPPING = {"x": "min", "y": "mAu"}

    INTERNAL_PROPERTIES = {
        "baseline",
        "parameters",
        "data_path",
    }

    # Set of properties to be saved
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

    def load_spectrum(
        self,
        data_path: Union[str, 'os.PathLike'],
        channel: str = "A"
    ) -> None:
        """Loads the spectra from the given folder.

        Args:
            data_path (Union[str, os.PathLike]): Path where HPLC data has been
                saved.
            channel (str): Detector channel. Depends on the method used and
                detector installed, defaults to "A" for DAD detector.
        """

        # Get raw data
        x, y, metadata = self.extract_rawdata(data_path, channel)

        # Extracting timestamp from metadata
        try:
            timestamp = time.mktime(
                time.strptime(metadata['date'], TIME_FORMAT)
            )
        # If no date information in metadata
        # Set timestamp to 0
        except KeyError:
            timestamp = 0.0

        # Loading all data
        super().load_spectrum(x, y, timestamp)
        self.parameters = metadata

    ### PUBLIC METHODS TO LOAD RAW DATA ###

    def extract_rawdata(
        self,
        experiment_dir: Union[str, 'os.PathLike'],
        channel: str,
    ) -> tuple['np.ndarray', 'np.ndarray', dict[str, Any]]:
        """ Reads raw data and metadata from Chemstation .CH files.

        Args:
            experiment_dir (Union[str, os.PathLike]): .D directory with the
                .CH files.
            channel (str): Selected channel in the detector.

        Returns:
            tuple[np.ndarray, np.ndarray, dict[str, Any]]: Tuple of raw
                chromatographic data and metadata:
                    - times (np.ndarray): Time scale.
                    - values (np.ndarray): Readings from the detector.
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

        # Loading data from chemstation file
        data = CHFile(filename.with_suffix(CHEMSTATION_FILE_SUFFIX))

        # Saving .npz for legacy use
        np.savez_compressed(npz_file, times=data.times, values=data.values)

        return data.times, data.values, data.metadata

    def _treat_npz_file(
        self,
        npz_filepath: Union[str, 'os.PathLike']
    ) -> tuple['np.ndarray', 'np.ndarray', dict[str, Any]]:
        """ Legacy method to read from .npz compressed arrays. """

        warnings.warn("Manipulating .npz files is deprecated and will be \
removed soon. Consider using save_data() and load_data() methods to work with \
pickled files.", FutureWarning)

        data = np.load(npz_filepath)

        return (data['times'], data['values'], {})

    def extract_peakarea(self, experiment_dir: str):
        """
        Reads processed data from Chemstation report files.

        Args:
            experiment_dir: .D directory with the report files
        """
        raise NotImplementedError

    def default_processing(self):
        """
        Processes the chromatogram in place.
        """
        # Parameters found to work best for chromatogram data
        self.correct_baseline(BASELINE_CORRECTION_CONFIG)

        # Get all peaks in processed chromatogram
        self.find_peaks()
