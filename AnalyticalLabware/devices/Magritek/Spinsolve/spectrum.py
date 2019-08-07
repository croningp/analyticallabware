"""Module for NMR spectral data loading and manipulating"""

from os.path import join
import queue
import struct
import numpy as np

class Spectrum:
    """Class for spectrum loading and handling"""

    def __init__(self, data_folder_queue):
        """
        Args:
            data_folder_queue (:obj: queue.Queue): A queue object containing data folders
                with NMR data
        """

        self.data_folder_queue = data_folder_queue

        