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

    def load_spectra(self):
        """ Loads the spectra from the available folder"""
        try:
            nmr_path = self.data_folder_queue.get_nowait()
        except queue.Empty:
            raise AttributeError("No spectra measured!")

        ### The following code has been copied from Jarek ###
        spectrum_parameters = open(join(nmr_path, 'acqu.par'), 'r')
        parameters = spectrum_parameters.readlines()
        param_dict = {}
        for param in parameters:
            param_dict[param.split('= ')[0].strip(' ')] = \
                param.split('= ')[1].strip('\n')
        print(param_dict)

        # open file with nmr data
        spectrum_path = join(nmr_path, 'data.1d')
        # open binary file with spectrum
        nmr_data = open(spectrum_path, mode='rb')
        # read first eight bytes
        spectrum = []
        # unpack the data
        while True:
            data = nmr_data.read(4)
            if not data:
                break
            spectrum.append(struct.unpack('<f', data))
        # remove fisrt eight points and divide data into three parts
        lenght = int(len(spectrum[8:]) / 3)
        # print (type(spectrum))
        fid = spectrum[lenght + 8:]
        fid_real = []
        fid_img = []
        for i in range(int(len(fid) / 2)):
            fid_real.append(fid[2 * i][0])
            fid_img.append(fid[2 * i + 1][0])
        fid_complex = []
        for i in range(len(fid_real)):
            fid_complex.append(np.complex(fid_real[i], fid_img[i] * -1))

        return fid_complex
        