"""Module for NMR spectral data loading and manipulating"""

import struct
import os
import logging
import time

import numpy as np

from ....analysis import AbstractSpectrum

# standard filenames for spectral data
FID_DATA = 'data.1d'
ACQUISITION_PARAMETERS = 'acqu.par'
PROCESSED_SPECTRUM = 'spectrum_processed.1d' # not always present
PROTOCOL_PARAMETERS = 'protocol.par'

# format used in acquisition parameters
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

# reserved for future use
JCAMP_DX_SPECTRUM = 'nmr_fid.dx'
CSV_SPECTRUM = 'spectrum.csv'


class SpinsolveNMRSpectrum(AbstractSpectrum):
    """Class for NMR spectrum loading and handling."""

    AXIS_MAPPING = {
        'x': 'ppm',
        'y': ''
    }

    INTERNAL_PROPERTIES = [
        'baseline',
        'parameters',
        'data_path',
    ]

    def __init__(self, path=None):

        if path is not None:
            os.makedirs(path, exist_ok=True)
            self.path = path
        else:
            self.path = os.path.join('.', 'nmr_data')
            os.makedirs(self.path, exist_ok=True)

        self.logger = logging.getLogger(
            'spinsolve.spectrum')

        super().__init__(self.path)

    def load_spectrum(self, data_path, start_time=None):
        """Loads the spectra from the given folder.

        *Note* current version only supports working with real part of the
        processed spectrum ('spectrum_processed.1d').

        Args:
            data_path (str): Path where NMR data has been saved.
            start_time (float, optional): Start time of the current experiment,
                used to calculate the timestamp for the spectrum. If omitted,
                uses the time since Epoch from the spectrum acquisition
                parameters.
        """

        # to avoid dropping parameters when called in parent class
        if self.x is not None:
            self.save_data()
            self._dump()

        # filepaths
        param_path = os.path.join(data_path, ACQUISITION_PARAMETERS)
        processed_path = os.path.join(data_path, PROCESSED_SPECTRUM)

        # loading parameters
        self.parameters = self.extract_parameters(param_path)
        self.data_path = data_path

        # extracting the time from acquisition parameters
        spectrum_time = time.strptime(
            self.parameters['CurrentTime'],
            TIME_FORMAT
        )

        if start_time is not None:
            timestamp = round(time.mktime(spectrum_time) - start_time)
        else:
            timestamp = round(time.mktime(spectrum_time))

        # processed spectrum is not always present
        if os.path.isfile(processed_path):
            # loading frequency axis and real part of the complex spectrum data
            ppm_axis, spectrum_data, _ = self.extract_data(processed_path)

        else:
            self.logger.warning('Current version of SpinsolveNMRSpectrum does \
not support raw FID data and now processed spectrum was found. Please change \
settings of the Spinsolve Software to enable default processing')
            raise AttributeError(f'Processed spectrum was not found in the \
supplied directory <{data_path}>')

        # loading all data
        super().load_spectrum(ppm_axis, spectrum_data, int(timestamp))

    ### PUBLIC METHODS TO LOAD RAW DATA ###

    def extract_data(self, spectrum_path):
        """Reads the Spinsolve spectrum file and extracts the spectrum data
        from it.

        Data is stored in binary format as C struct data type. First 32 bytes
        (8 integers * 4 bytes) contains the header information and can be
        discarded. The rest data is stored as float (4 byte) data points for X
        axis and complex number (as float, float for real and imaginary parts)
        data points for Y axis.

        Refer to the software manual (v 1.16, July 2019 Magritek) for details.

        Args:
            spectrum_path: Path to saved NMR spectrum data.

        Returns:
            tuple[x_axis, y_data_real, y_data_img]:
                x_axis (:obj: np.array, dtype='float32'): X axis points.
                y_data_real (:obj: np.array, dtype='float32'): real part of the
                    complex spectrum data.
                y_data_img (:obj: np.array, dtype='float32'): imaginary part of
                    the complex spectrum data.

        """

        # reading data with numpy fromfile
        # the header is discarded
        spectrum_data = np.fromfile(spectrum_path, dtype='<f')[8:]

        x_axis = spectrum_data[:len(spectrum_data) // 3]

        # breaking the rest of the data into real and imaginary part
        y_real = spectrum_data[len(spectrum_data) // 3:][::2]
        y_img = spectrum_data[len(spectrum_data) // 3:][1::2]

        return (x_axis, y_real, y_img)

    def extract_parameters(self, params_path):
        """Get the NMR parameters from the given folder.

        Args:
            params_path (str): Path to saved NMR data.

        Returns:
            Dict: Acquisition parameters.
        """

        # loading spectrum parameters
        spec_params = {}
        with open(params_path) as fileobj:
            param = fileobj.readline()
            while param:
                # in form of "Param"       = "Value"\n
                parameter, value = param.split('=')
                # stripping from whitespaces, newlines and extra doublequotes
                spec_params[parameter.strip()] = value.strip().strip('"')
                param = fileobj.readline()

        return spec_params
