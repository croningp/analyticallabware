"""Module for NMR spectral data loading and manipulating"""

import os
import logging
import time

import numpy as np
import nmrglue as ng
import matplotlib.pyplot as plt

from ....analysis import AbstractSpectrum

# standard filenames for spectral data
FID_DATA = 'data.1d'
ACQUISITION_PARAMETERS = 'acqu.par'
PROCESSED_SPECTRUM = 'spectrum_processed.1d' # not always present
PROTOCOL_PARAMETERS = 'protocol.par'

# format used in acquisition parameters
TIME_FORMAT = r'%Y-%m-%dT%H:%M:%S.%f'

# reserved for future use
JCAMP_DX_SPECTRUM = 'nmr_fid.dx'
CSV_SPECTRUM = 'spectrum.csv'


class SpinsolveNMRSpectrum(AbstractSpectrum):
    """Class for NMR spectrum loading and handling."""

    AXIS_MAPPING = {
        'x': 'time',
        'y': ''
    }

    INTERNAL_PROPERTIES = {
        'baseline',
        'data_path',
    }

    def __init__(self, path=None, autosaving=False):

        if path is None:
            path = os.path.join('.', 'nmr_data')

        self.logger = logging.getLogger('spinsolve.spectrum')

        # updating public properties to include the universal dictionary
        self.PUBLIC_PROPERTIES.add('udic')
        # and parameters
        self.PUBLIC_PROPERTIES.add('parameters')

        # autosaving set to False, since spectra are saved by Spinsolve anyway
        super().__init__(path, autosaving)

        # universal dictionary for the acquisition parameters
        # placeholder, will be updated when spectral data is loaded
        self.udic = ng.fileio.fileiobase.create_blank_udic(1) # 1D spectrum

        # unit converter from nmrglue library
        # placeholder, will be updated
        self._uc = None

    def load_spectrum(self, data_path, start_time=None, preprocessed=True):
        """Loads the spectra from the given folder.

        If preprocessed argument is True, loading the spectral data already
        processed by the Spinsolve software (fft + autophasing).

        Args:
            data_path (str): Path where NMR data has been saved.
            start_time (float, optional): Start time of the current experiment,
                used to calculate the timestamp for the spectrum. If omitted,
                uses the time since Epoch from the spectrum acquisition
                parameters.
            preprocessed (bool, optional): If True - will load preprocessed (by
                Spinsolve software) spectral data. If False (default) - base fid
                is loaded and used for further processing.
        """

        # this is needed to avoid dropping parameters when called in parent
        # class, since _dump() is called there as well
        if self.x is not None:
            if self.autosaving:
                self.save_data()
            self._dump()

        # filepaths
        param_path = os.path.join(data_path, ACQUISITION_PARAMETERS)
        processed_path = os.path.join(data_path, PROCESSED_SPECTRUM)
        fid_path = os.path.join(data_path, FID_DATA)

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

        # loading raw fid data
        if not preprocessed:
            x_axis, y_real, y_img = self.extract_data(fid_path)
            spectrum_data = np.array(y_real + y_img*1j)

            # updating the universal dictionary
            self.udic[0].update(
                # spectral width in kHz
                sw=self.parameters['bandwidth'] * 1e3,
                # carrier frequency
                car=self.parameters['bandwidth'] * 1e3 / 2 \
                    + self.parameters['lowestFrequency'],
                # observed frequency
                obs=self.parameters['b1Freq'],
                # number of points
                size=self.parameters['nrPnts'],
                # time domain
                time=True,
                # label, e.g. 1H
                label=self.parameters['rxChannel'],
            )

            # changing axis mapping according to raw FID
            self.AXIS_MAPPING.update(x='time')

            # creating unit conversion object
            self._uc = ng.fileio.fileiobase.uc_from_udic(self.udic)

        # check for the preprocessed file, as it's not always present
        elif os.path.isfile(processed_path) and preprocessed:
            # loading frequency axis and real part of the complex spectrum data
            x_axis, spectrum_data, _ = self.extract_data(processed_path)
            # updating axis mapping
            self.AXIS_MAPPING.update(x='ppm')

        else:
            self.logger.warning('Current version of SpinsolveNMRSpectrum does \
not support raw FID data and now processed spectrum was found. Please change \
settings of the Spinsolve Software to enable default processing')
            raise AttributeError(f'Processed spectrum was not found in the \
supplied directory <{data_path}>')

        # loading all data
        super().load_spectrum(x_axis, spectrum_data, int(timestamp))

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
                parameter = parameter.strip()
                value = value.strip().strip('"')
                # converting values to float if possible
                try:
                    spec_params[parameter] = float(value)
                except ValueError:
                    spec_params[parameter] = value
                param = fileobj.readline()

        return spec_params

    def show_spectrum(self, filename=None):
        # redefined to support axis inverting
        fig, ax = plt.subplots()

        # removing imaginary part
        y = ng.proc_base.di(self.y)
        ax.plot(self.x, y, color='black', label=f'{self.timestamp}')
        ax.set_xlabel(self.AXIS_MAPPING['x'])
        ax.set_ylabel(self.AXIS_MAPPING['y'])

        if self.peaks is not None:
            plt.scatter(
                self.peaks[:, 1],
                self.peaks[:, 2],
                label='found peaks'
            )

        # inverting axis if ppm scale needed
        if self.AXIS_MAPPING['x'] == 'ppm':
            ax.invert_xaxis()

        if filename is None:
            ax.legend()
            fig.show()

        else:
            fig.savefig(os.path.join(self.path, f'{filename}.png'))

    def fft(self, in_place=True):
        """ Fourier transformation, NMR ordering of the results.

        This is the wrapper around nmrglue.process.proc_base.fft function.
        Please refer to original function documentation for details.

        Args:
            in_place(bool, optional): If True (default), self.y is updated;
                returns new array if False.

        Returns:
            Union[:np.array:, None]: If in_place is True, will return new array
                after FFT.
        """

        if in_place:
            self.y = ng.proc_base.fft(self.y)

            # updating x and y axis
            self.AXIS_MAPPING.update(x='ppm')
            self.x = self._uc.ppm_scale()

            # updating the udic to frequency domain
            self.udic[0]['time'] = False
            self.udic[0]['freq'] = True

        else:
            return ng.proc_base.fft(self.y)

    def autophase(self, in_place=True, function='peak_minima', p0=0.0, p1=0.0):
        """ Automatic linear phase correction. FFT is performed!

        This is the wrapper around nmrglue.process.proc_autophase.autops
        function. Please refer to original function documentation for details.

        Args:
            in_place(bool, optional): If True (default), self.y is updated;
                returns new array if False.
            function(Union[str, Callable], optional): Algorithm to use for phase
                scoring. Builtin functions can be specified by one of the
                following strings: "acme" or "peak_minima". This refers to
                nmrglue.process.proc_autophase.autops function, "peak_minima"
                (default) was found to perform best.
            p0(float, optional): Initial zero order phase in degrees.
            p1(float, optional): Initial first order phase in degrees.

        Returns:
            Union[:np.array:, None]: If in_place is True, will return new array
                after phase correction.
        """

        # check if fft was performed
        if self.AXIS_MAPPING['x'] == 'time':
            self.fft()

        autophased = ng.process.proc_autophase.autops(
            self.y,
            function,
            p0,
            p1
        )

        if in_place:
            self.y = autophased
            return

        return autophased

    def correct_baseline(self, in_place=True, wd=20):
        """ Automatic baseline correction using distribution based
            classification method.

        Algorithm described in: Wang et al. Anal. Chem. 2013, 85, 1231-1239

        This is the wrapper around nmrglue.process.proc_bl.baseline_corrector
        function. Please refer to original function documentation for details.

        Args:
            in_place(bool, optional): If True (default), self.y is updated;
                returns new array if False.
            wd(float, optional): Median window size in pts.

        Returns:
            Union[:np.array:, None]: If in_place is True, will return new array
                after baseline correction.
        """

        # check if fft was performed
        if self.AXIS_MAPPING['x'] == 'time':
            self.fft()

        corrected = ng.process.proc_bl.baseline_corrector(self.y, wd)

        if in_place:
            self.y = corrected
            return

        return corrected

    def load_data(self, path):
        # overwritten from abstract class to allow updating of unit conversion
        super().load_data(path)
        self._uc = ng.fileio.fileiobase.uc_from_udic(self.udic)

        # updating axis mapping from "time" default
        if self.udic[0]['freq']:
            self.AXIS_MAPPING.update(x='ppm')

    def smooth_spectrum(self, in_place=True, routine='ng', **params):
        """ Smoothes the spectrum.

        Depending on the routine chosen will use either Savitsky-Golay filter
        from scipy.signal module or nmrglue custom function.

        !Note: savgol will cast complex dtype to float!

        Args:
            in_place(bool, optional): If True (default), self.y is updated;
                returns new array if False.

            routine(str, optional): Smoothing routine.
                "ng" (default) will use custom smoothing function from
                    nmrglue.process.proc_base module.

                "savgol" will use savgol_filter method from scipt.signal module
                    defined in ancestor method.

            parram in params: Keyword arguments for the chosen routine function.
                For "savgol" routine:

                    window_length (int): The length of the filter window (i.e.
                        thenumber of coefficients). window_length must be a
                        positive odd integer.

                    polyorder (int): The order of the polynomial used to fit the
                            samples. polyorder must be less than window_length.

                For "ng" routine:

                    n (int): Size of smoothing windows (+/- points).

        Returns:
            Union[:np.array:, None]: If in_place is True, will return new array
                after baseline correction.
        """

        if routine == 'savgol':
            super().smooth_spectrum(in_place=in_place, **params)

        elif routine == 'ng':
            # using default value
            if not params:
                params = {'n': 5}

            if in_place:
                self.y = ng.process.proc_base.smo(self.y, **params)
                return

            return ng.process.proc_base.smo(self.y, **params)

        else:
            raise ValueError('Please choose either nmrglue ("ng") or Savitsky-\
Golay ("savgol") smoothing routine')

    def apodization(self, in_place=True, function='em', **params):
        """ Applies a chosen window function.

        Args:
            in_place (bool, optional): If True (default), self.y is updated;
                returns new array if False.

            function (str, optional): Window function of choice.
                "em" - exponential multiply window (mimic NMRPipe EM function).
                "gm" - Lorentz-to-Gauss window function (NMRPipe GM function).
                "gmb" - Gauss-like window function (NMRPipe GMB function).

            param in params: Keyword arguments for the chosen window function:

                For "em":
                    See reference for nmrglue.proc_base.em and NMRPipe EM
                        functions.

                    lb (float): Exponential decay of the window in terms of a
                        line broadening in Hz. Negative values will generate an
                        increasing exponential window, which corresponds to a
                        line sharpening. The line-broadening parameter is often
                        selected to match the natural linewidth.

                For "gm":
                    See reference for nmrglue.proc_base.gm and NMRPipe GM
                        functions.

                    g1 (float): Specifies the inverse exponential to apply in
                        terms of a line sharpening in Hz. It is usually adjusted
                        to match the natural linewidth. The default value is
                        0.0, which means no exponential term will be applied,
                        and the window will be a pure Gaussian function.

                    g2 (float): Specifies the Gaussian to apply in terms of a
                        line broadening in Hz. It is usually adjusted to be
                        larger (x 1.25 - 4.0) than the line sharpening specified
                        by the g1 attribute.

                    g3 (float): Specifies the position of the Gaussian
                        function's maximum on the FID. It is specified as a
                        value ranging from 0.0 (Gaussian maximum at the first
                        point of the FID) to 1.0 (Gaussian maximum at the last
                        point of the FID). It most applications, the default
                        value of 0.0 is used.

                For "gmb":
                    See reference for nmrglue.proc_base.gmb and NMRPipe GMB
                        functions.

                    lb (float): Specifies an exponential factor in the chosen
                        Gauss window function. This value is usually specified
                        as a negative number which is about the same size as the
                        natural linewidth in Hz. The default value is 0.0, which
                        means no exponential term will be applied.

                    gb (float): Specifies a Gaussian factor gb, as used in the
                        chosen Gauss window function. It is usually specified as
                        a positive number which is a fraction of 1.0. The
                        default value is 0.0, which leads to an undefined window
                        function according to the formula; for this reason, the
                        Gaussian term is omitted from the calculation when gb
                        0.0 is given.

        Returns:
            Union[:np.array:, None]: If in_place is True, will return new array
                after baseline correction.
        """
        # TODO check for Fourier transformation!

        if function == 'em':
            # converting lb value to NMRPipe-like
            if 'lb' in params:
                # deviding by spectral width in Hz
                params['lb'] = params['lb']/ self.udic[0]['sw']

            if in_place:
                self.y = ng.process.proc_base.em(self.y, **params)
                return

            return ng.process.proc_base.em(self.y, **params)

        elif function == 'gm':
            # converting values into NMRPipe-like
            if 'g1' in params:
                params['g1'] = params['g1'] / self.udic[0]['sw']

            if 'g2' in params:
                params['g2'] = params['g2'] / self.udic[0]['sw']

            if in_place:
                self.y = ng.process.proc_base.gm(self.y, **params)
                return

            return ng.process.proc_base.gm(self.y, **params)

        elif function == 'gmb':
            # converting values into NMRPipe-like
            # for formula reference see documentation and source code of
            # nmrglue.proc_base.gmb function and NMRPipe GMB command reference
            if 'lb' in params:
                a = np.pi * params['lb'] / self.udic[0]['sw']
            else:
                a = 0.0

            if 'gb' in params:
                b = -a / (2.0 * params['gb'] * self.udic[0]['size'])
            else:
                b = 0.0

            if in_place:
                self.y = ng.process.proc_base.gmb(self.y, a=a, b=b)
                return

            return ng.process.proc_base.gmb(self.y, a=a, b=b)

    def zero_fill(self, n=1, in_place=True):
        """ Zero filling the data by 2**n.

        Args:
            n (int): power of 2 to append 0 to the data.
            in_place (bool, optional): If True (default), self.y is updated;
                returns new array if False.

        Returns:
            Union[:np.array:, None]: If in_place is True, will return new array
                after baseline correction.
        """

        if in_place:
            # zero fill is useless when fft performed
            if self.AXIS_MAPPING['x'] == 'ppm':
                self.logger.warning('FFT already performed, zero filling \
skipped')
                return

            # extending y axis
            self.y = ng.process.proc_base.zf_double(self.y, n)

            # extending x axis
            self.x = np.linspace(self.x[0], self.x[-1]*2**n, self.y.shape[0])
            return

        return ng.process.proc_base.zf_double(self.y, n)
