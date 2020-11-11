"""Module for HPLC chromatogram data loading and manipulating"""

import os
import logging
import time

import numpy as np

from .chemstation import CHFile

from ...analysis import AbstractSpectrum

# Chemstation data path
DATA_DIR = r"C:\Chem32\1\Data"


# standard filenames for spectral data
CHANNELS = {
    "A":"01",
    "B":"02",
    "C":"03",
    "D":"04"}

ACQUISITION_PARAMETERS = 'acq.txt'

# format used in acquisition parameters
TIME_FORMAT = '%Y-%m-%d-%H-%M'

class AgilentHPLCChromatogram(AbstractSpectrum):
    """Class for HPLC spectrum (chromatogram) loading and handling."""

    AXIS_MAPPING = {
        'x': 'min',
        'y': 'mAu'
    }

    INTERNAL_PROPERTIES = {
        'baseline',
        'parameters',
        'data_path',
    }

    # set of properties to be saved
    PUBLIC_PROPERTIES = {
        'x',
        'y',
        'peaks',
        'timestamp',
        'channel'
    }

    def __init__(self, path=None, channel='A'):

        if path is not None:
            os.makedirs(path, exist_ok=True)
            self.path = path
        else:
            self.path = os.path.join('.', 'hplc_data')
            os.makedirs(self.path, exist_ok=True)

        self.logger = logging.getLogger(
            'AgilentHPLCChromatogram')

        super().__init__(self.path)
        self.channel = channel

    def load_spectrum(self, data_path):
        """Loads the spectra from the given folder.

        Args:
            data_path (str): Path where HPLC data has been saved.
        """

        # to avoid dropping parameters when called in parent class
        if self.x is not None:
            self.save_data()
            self._dump()

        # get raw data
        x, y = self.extract_rawdata(data_path)

        # get timestamp
        tstr = data_path.split(".")[0].split("_")[-1]
        timestamp = time.mktime(time.strptime(tstr, TIME_FORMAT))

        # loading all data
        super().load_spectrum(x, y, timestamp)

    ### PUBLIC METHODS TO LOAD RAW DATA ###

    def extract_rawdata(self, experiment_dir: str):
        filename = os.path.join(experiment_dir, f"DAD1{self.channel}")
        npz_file = filename + ".npz"

        if os.path.exists(npz_file):
            # already processed
            data = np.load(npz_file)
            return data["times"], data["values"]
        else:
            self.logger.debug("NPZ file not found. First time loading data.")
            ch_file = filename + ".ch"
            data = CHFile(ch_file)
            np.savez_compressed(npz_file, times=data.times, values=data.values)
            return np.array(data.times), np.array(data.values)

    def extract_peakarea(self, experiment_dir: str):
        # filename = os.path.join(experiment_dir, f"REPORT{CHANNELS[channel]}.csv")
        # TODO parse file properly
        # data = np.genfromtxt(filename, delimiter=',')
        # return data
        pass
