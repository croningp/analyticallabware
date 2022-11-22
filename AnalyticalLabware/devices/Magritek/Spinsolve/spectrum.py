"""Module for NMR spectral data loading and manipulating"""

# pylint: disable=attribute-defined-outside-init
import os
import logging
import time
from typing import Union

import numpy as np
import scipy
import nmrglue as ng
import matplotlib.pyplot as plt

from ....analysis import AbstractSpectrum
from ....analysis.spec_utils import *

# standard filenames for spectral data
FID_DATA = "data.1d"
ACQUISITION_PARAMETERS = "acqu.par"
PROCESSED_SPECTRUM = "spectrum_processed.1d"  # not always present
PROTOCOL_PARAMETERS = "protocol.par"

# format used in acquisition parameters
TIME_FORMAT = r"%Y-%m-%dT%H:%M:%S.%f"

# reserved for future use
JCAMP_DX_SPECTRUM = "nmr_fid.dx"
CSV_SPECTRUM = "spectrum.csv"

# filename for shimming parameters
SHIMMING_PARAMETERS = "shim.par"
SHIMMING_FID = "sample_fid.1d"
SHIMMING_SPECTRUM = "spectrum.1d"


class SpinsolveNMRSpectrum(AbstractSpectrum):
    """Class for NMR spectrum loading and handling."""

    AXIS_MAPPING = {"x": "time", "y": ""}

    INTERNAL_PROPERTIES = {
        "baseline",
        "data_path",
        "_uc",
    }

    def __init__(self, path=None, autosaving=False):

        if path is None:
            path = os.path.join(".", "nmr_data")

        self.logger = logging.getLogger("spinsolve.spectrum")

        # updating public properties to include the universal dictionary
        self.PUBLIC_PROPERTIES.add("udic")
        # and parameters
        self.PUBLIC_PROPERTIES.add("parameters")

        # autosaving set to False, since spectra are saved by Spinsolve anyway
        super().__init__(path, autosaving)

        # universal dictionary for the acquisition parameters
        # placeholder, will be updated when spectral data is loaded
        self.udic = ng.fileio.fileiobase.create_blank_udic(1)  # 1D spectrum

        # placeholder to store shimming parameters in the current session
        self.last_shimming_time = None
        self.last_shimming_results = None

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
        try:
            self.parameters = self.extract_parameters(param_path)
        except FileNotFoundError:
            # this happens only if shimming was performed
            shim_path = os.path.join(data_path, SHIMMING_PARAMETERS)
            self.parameters = self.extract_parameters(shim_path)

            # updating placeholders
            self.last_shimming_results = {
                parameter: self.parameters[parameter]
                for parameter in self.parameters
                if parameter.startswith("shim")
            }

            # updating last shimming time
            self.last_shimming_time = time.strptime(
                self.parameters["CurrentTime"], TIME_FORMAT
            )

            # updating file names for the shimming
            processed_path = os.path.join(data_path, SHIMMING_SPECTRUM)

            # forcing preprocessed to deal with frequency domain not raw FID
            preprocessed = True

        self.data_path = data_path

        # extracting the time from acquisition parameters
        spectrum_time = time.strptime(self.parameters["CurrentTime"], TIME_FORMAT)

        if start_time is not None:
            timestamp = round(time.mktime(spectrum_time) - start_time)
        else:
            timestamp = round(time.mktime(spectrum_time))

        # loading raw fid data
        if not preprocessed:
            x_axis, y_real, y_img = self.extract_data(fid_path)
            spectrum_data = np.array(y_real + y_img * 1j)

            # updating the universal dictionary
            self.udic[0].update(
                # spectral width in kHz
                sw=self.parameters["bandwidth"] * 1e3,
                # carrier frequency
                car=self.parameters["bandwidth"] * 1e3 / 2
                + self.parameters["lowestFrequency"],
                # observed frequency
                obs=self.parameters["b1Freq"],
                # number of points
                size=self.parameters["nrPnts"],
                # time domain
                time=True,
                # label, e.g. 1H
                label=self.parameters["rxChannel"],
            )

            # changing axis mapping according to raw FID
            self.AXIS_MAPPING.update(x="time")

            # creating unit conversion object
            self._uc = ng.fileio.fileiobase.uc_from_udic(self.udic)

        # check for the preprocessed file, as it's not always present
        elif os.path.isfile(processed_path) and preprocessed:
            # loading frequency axis and real part of the complex spectrum data
            x_axis, spectrum_data, _ = self.extract_data(processed_path)
            # reversing spectrum order to match default nmr order
            # i.e. highest - left
            x_axis = x_axis[::-1]
            spectrum_data = spectrum_data[::-1]
            # updating axis mapping
            self.AXIS_MAPPING.update(x="ppm")

        else:
            self.logger.warning(
                "Current version of SpinsolveNMRSpectrum does \
not support raw FID data and no processed spectrum was found. Please change \
settings of the Spinsolve Software to enable default processing"
            )
            raise AttributeError(
                f"Processed spectrum was not found in the \
supplied directory <{data_path}>"
            )

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
        spectrum_data = np.fromfile(spectrum_path, dtype="<f")[8:]

        x_axis = spectrum_data[: len(spectrum_data) // 3]

        # breaking the rest of the data into real and imaginary part
        y_real = spectrum_data[len(spectrum_data) // 3 :][::2]
        y_img = spectrum_data[len(spectrum_data) // 3 :][1::2]

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
                parameter, value = param.split("=", maxsplit=1)
                # stripping from whitespaces, newlines and extra doublequotes
                parameter = parameter.strip()
                value = value.strip(' \n"')
                # special case: userData
                # converting to nested dict
                if parameter == "userData" and value:
                    values = value.split(";")
                    value = {}
                    for key_value in values:
                        key, val = key_value.split("=")
                        value[key] = val
                # converting values to float if possible
                try:
                    spec_params[parameter] = float(value)
                except (ValueError, TypeError):
                    spec_params[parameter] = value
                param = fileobj.readline()

        return spec_params

    def show_spectrum(
        self,
        filename=None,
        title=None,
        label=None,
    ):
        """Plots the spectral data using matplotlib.pyplot module.

        Redefined from ancestor class to support axis inverting.

        Args:
            filename (str, optional): Filename for the current plot. If omitted,
                file is not saved.
            title (str, optional): Title for the spectrum plot. If omitted, no
                title is set.
            label (str, optional): Label for the spectrum plot. If omitted, uses
                the spectrum timestamp.
        """
        if label is None:
            label = f"{self.timestamp}"

        fig, ax = plt.subplots(figsize=(12, 8))

        ax.plot(
            self.x,
            self.y,
            color="xkcd:navy blue",
            label=label,
        )

        ax.set_xlabel(self.AXIS_MAPPING["x"])
        ax.set_ylabel(self.AXIS_MAPPING["y"])

        if title is not None:
            ax.set_title(title)

        # plotting peaks if found
        if self.peaks is not None:
            plt.scatter(
                self.peaks[:, 1],
                self.peaks[:, 2],
                label="found peaks",
                color="xkcd:tangerine",
            )

        ax.legend()

        # inverting if ppm scale
        if self.AXIS_MAPPING["x"] == "ppm":
            ax.invert_xaxis()

        if filename is None:
            fig.show()

        else:
            path = os.path.join(self.path, "images")
            os.makedirs(path, exist_ok=True)
            fig.savefig(os.path.join(path, f"{filename}.png"), dpi=150)

    def fft(self, in_place=True):
        """Fourier transformation, NMR ordering of the results.

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
            self.AXIS_MAPPING.update(x="ppm")
            self.x = self._uc.ppm_scale()

            # updating the udic to frequency domain
            self.udic[0]["time"] = False
            self.udic[0]["freq"] = True

        else:
            return ng.proc_base.fft(self.y)

    def autophase(self, in_place=True, function="peak_minima", p0=0.0, p1=0.0):
        """Automatic linear phase correction. FFT is performed!

        This is the wrapper around nmrglue.process.proc_autophase.autops
        function. Please refer to original function documentation for details.

        Args:
            in_place (bool, optional): If True (default), self.y is updated;
                returns new array if False.
            function (Union[str, Callable], optional): Algorithm to use for
                phase scoring. Builtin functions can be specified by one of the
                following strings: "acme" or "peak_minima". This refers to
                nmrglue.process.proc_autophase.autops function, "peak_minima"
                (default) was found to perform best.
            p0 (float, optional): Initial zero order phase in degrees.
            p1 (float, optional): Initial first order phase in degrees.

        Returns:
            Union[:np.array:, None]: If in_place is True, will return new array
                after phase correction.
        """

        # check if fft was performed
        if self.AXIS_MAPPING["x"] == "time":
            self.fft()

        autophased = ng.process.proc_autophase.autops(self.y, function, p0, p1)

        if in_place:
            self.y = autophased
            return

        return autophased

    def correct_baseline(self, in_place=True, wd=20):
        """Automatic baseline correction using distribution based
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
        if self.AXIS_MAPPING["x"] == "time":
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
        if self.udic[0]["freq"]:
            self.AXIS_MAPPING.update(x="ppm")

        elif self.udic[0]["time"]:
            self.AXIS_MAPPING.update(x="time")

    def smooth_spectrum(self, in_place=True, routine="ng", **params):
        """Smoothes the spectrum.

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

        if routine == "savgol":
            super().smooth_spectrum(in_place=in_place, **params)

        elif routine == "ng":
            # using default value
            if not params:
                params = {"n": 5}

            if in_place:
                self.y = ng.process.proc_base.smo(self.y, **params)
                return

            return ng.process.proc_base.smo(self.y, **params)

        else:
            raise ValueError(
                'Please choose either nmrglue ("ng") or Savitsky-\
Golay ("savgol") smoothing routine'
            )

    def apodization(self, in_place=True, function="em", **params):
        """Applies a chosen window function.

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

        if function == "em":
            # converting lb value to NMRPipe-like
            if "lb" in params:
                # deviding by spectral width in Hz
                params["lb"] = params["lb"] / self.udic[0]["sw"]

            if in_place:
                self.y = ng.process.proc_base.em(self.y, **params)
                return

            return ng.process.proc_base.em(self.y, **params)

        elif function == "gm":
            # converting values into NMRPipe-like
            if "g1" in params:
                params["g1"] = params["g1"] / self.udic[0]["sw"]

            if "g2" in params:
                params["g2"] = params["g2"] / self.udic[0]["sw"]

            if in_place:
                self.y = ng.process.proc_base.gm(self.y, **params)
                return

            return ng.process.proc_base.gm(self.y, **params)

        elif function == "gmb":
            # converting values into NMRPipe-like
            # for formula reference see documentation and source code of
            # nmrglue.proc_base.gmb function and NMRPipe GMB command reference
            if "lb" in params:
                a = np.pi * params["lb"] / self.udic[0]["sw"]
            else:
                a = 0.0

            if "gb" in params:
                b = -a / (2.0 * params["gb"] * self.udic[0]["size"])
            else:
                b = 0.0

            if in_place:
                self.y = ng.process.proc_base.gmb(self.y, a=a, b=b)
                return

            return ng.process.proc_base.gmb(self.y, a=a, b=b)

    def zero_fill(self, n=1, in_place=True):
        """Zero filling the data by 2**n.

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
            if self.AXIS_MAPPING["x"] == "ppm":
                self.logger.warning(
                    "FFT already performed, zero filling \
skipped"
                )
                return

            # extending y axis
            self.y = ng.process.proc_base.zf_double(self.y, n)

            # extending x axis
            self.x = np.linspace(self.x[0], self.x[-1] * 2**n, self.y.shape[0])

            # updating udic and uc
            self.udic[0].update(size=self.x.size)
            self._uc = ng.fileio.fileiobase.uc_from_udic(self.udic)
            return

        return ng.process.proc_base.zf_double(self.y, n)

    def generate_peak_regions(
        self,
        magnitude=True,
        derivative=True,
        smoothed=True,
        d_merge=0.056,
        d_expand=0.0,
    ):
        """Generate regions if interest potentially containing compound peaks
            from the spectral data.

        Args:
            d_merge (float, Optional): arbitrary interval (in ppm!) to merge
                several regions, if the distance between is lower.
            d_expand (float, Optional): arbitrary value (in ppm!) to expand the
                regions after automatic assigning and filtering.

        Returns:
            :obj:np.array: 2D Mx2 array with peak regions indexes (rows) as left
                and right borders (columns).
        """

        # check if fft was performed
        if self.AXIS_MAPPING["x"] != "ppm":
            self.logger.warning("Please perform FFT first.")
            return np.array([[]])

        # placeholder
        peak_map = np.full_like(self.x, False)

        if magnitude:
            # looking for peaks in magnitude mode
            magnitude_spectrum = np.sqrt(self.y.real**2 + self.y.imag**2)
            # mapping
            peak_map = np.logical_or(
                create_binary_peak_map(magnitude_spectrum), peak_map
            )
        else:
            peak_map = np.logical_or(create_binary_peak_map(self.y), peak_map)

        # additionally in the derivative
        if derivative:
            try:
                derivative_map = create_binary_peak_map(np.gradient(magnitude_spectrum))
            except NameError:
                derivative_map = create_binary_peak_map(np.gradient(self.y))
            # combining
            peak_map = np.logical_or(derivative_map, peak_map)

        # and in the smoothed version
        if smoothed:
            try:
                smoothed = scipy.ndimage.gaussian_filter1d(magnitude_spectrum, 3)
            except NameError:
                # smoothing only supported on non-complex data
                smoothed = scipy.ndimage.gaussian_filter1d(self.y.real, 3)
            # combining
            peak_map = np.logical_or(create_binary_peak_map(smoothed), peak_map)

        # extracting the regions from the full map
        regions = combine_map_to_regions(peak_map)

        # Skip further steps if no peaks identified
        if not regions.size > 0:
            return regions

        # filtering, merging, expanding
        regions = filter_regions(self.x, regions)
        regions = filter_noisy_regions(self.y, regions)
        if d_merge:
            regions = merge_regions(self.x, regions, d_merge=d_merge)
        if d_expand:
            regions = expand_regions(self.x, regions, d_expand=d_expand)

        return regions

    def default_processing(self):
        """Default processing.

        Performs several processing methods with attributes chosen
        experimentally to achieve best results for the purpose of "fast",
        "reliable" and "reproducible" NMR analysis.
        """
        # TODO add processing for various nucleus
        if self.parameters["rxChannel"] == "19F":
            self.apodization(function="gm", g1=1.2, g2=4.5)
            self.zero_fill()
            self.fft()
            self.correct_baseline()
            self.autophase()
            self.correct_baseline()

    def integrate_area(self, area, rule="trapz"):
        """Integrate the spectrum within given area.

        Redefined from ancestor method to discard imaginary part of the
        resulting integral.

        Args:
            area (Tuple[float, float]): Tuple with left and right border (X axis
                obviously) for the desired area.
            rule (str, optional): Method for integration, "trapz" - trapezoidal
                rule (default), "simps" - Simpson's rule.
        Returns:
            float: Definite integral within given area as approximated by given
                method.
        """

        result = super().integrate_area(area, rule)

        # discarding imaginary part and returning the absolute value
        # due to "NMR-order" of the x axis
        return abs(result.real)

    def integrate_regions(self, regions):
        """Integrate the given regions using nmrglue integration method.

        Check the corresponding documentation for details.

        Args:
            regions (:obj:np.array): 2D Mx2 array, containing left and right
                borders for the regions of interest, potentially containing
                peak areas (as found by self.generate_peak_regions method).

        Return:
            result (:obj:np.array): 1D M-size array contaning integration for
                each region of interest.
        """

        result = ng.analysis.integration.integrate(
            data=self.y,
            unit_conv=self._uc,
            limits=self.x[regions],  # directly get the ppm values
        )

        # discarding imaginary part
        return np.abs(np.real(result))

    def reference_spectrum(
        self,
        new_position: float,
        reference: Union[float, str] = "highest",
    ) -> None:
        """Shifts the spectrum x axis according to the new reference.

        If old reference is omitted will shift the spectrum according to the
        highest peak.

        Args:
            new_position (float): The position to shift the peak to.
            reference (Union[float, str]): The current position of the reference
                peak or it's indication for shifting: either "highest" (default)
                or "closest" for selecting highest or closest to the new
                reference peak for shifting.
        """

        # find reference if not given
        if isinstance(reference, str):
            if reference == "highest":
                # Looking for highest point
                reference = self.x[np.argmax(self.y)]
            elif reference == "closest":
                # Looking for closest peak among found across whole spectrum
                # Specifying area not to update self.peaks
                peaks = self.find_peaks(area=(self.x.min(), self.x.max()))
                # x coordinate
                peaks_xs = peaks[:, 1].real
                reference = peaks[np.argmin(np.abs(peaks_xs - new_position))][1].real
            else:
                self.logger.warning(
                    'Please use either "highest" or "closest"\
reference, or give exact value.'
                )
                return

        new_position, _ = find_nearest_value_index(self.x, new_position)

        diff = new_position - reference

        # shifting the axis
        self.x = self.x + diff

        # if peaks are recorded, find new
        if self.peaks is not None:
            self.find_peaks()
