"""
Module for handling Raman spectroscopic data

.. moduleauthor:: Artem Leonov, Graham Keenan
"""
import json
import logging
import os

import numpy as np
import matplotlib.pyplot as plt
from scipy import sparse
from scipy import signal
from scipy.sparse.linalg import spsolve
from scipy.interpolate import UnivariateSpline

LASER_POWER = 785
WAVELENGTHS = 'wavelengths'
ORIGINAL = 'original'
INTENSITIES = 'intensities'
WAVENUMBERS = 'wavenumbers'
PEAKS = 'peaks'
REFERENCE = 'reference'
BASELINE = 'baseline'
TIMESTAMP = 'timestamp'
MIN_X = 780
MAX_X = 1006

def _convert_wavelength_to_wavenumber(data):
    """Converts wavelengths from spectrometer to Raman shift in wavenumbers

    Arguments:
        data (iterable): Wavelength data to convert

    Returns:
        (:obj: np.array): Wavenumbers data
    """

    wavenumbers = [(10**7 / LASER_POWER) - (10**7 / wv) for wv in data]

    return np.array(wavenumbers)

class RamanSpectrum():
    """Defines methods for Raman spectroscopic data handling
    
    Args:
        path(str, optional): Valid path to save the spectral data.
            If not provided, uses .//raman_data
    """

    def __init__(self, path=None):
        self.original = None
        self.intensities = None
        self.wavelengths = None
        self.wavenumbers = None
        self.reference = None
        self.baseline = None
        self.peaks = {}
        self.timestamp = None

        self.smoothed = False

        if path is not None:
            os.makedirs(path, exist_ok=True)
            self.path = path
        else:
            self.path = os.path.join('.', 'raman_data')
            os.makedirs(self.path, exist_ok=True)

        self.logger = logging.getLogger('oceanoptics.spectrometer.raman.spectrum')

    def _dump(self):
        """Dumps all the data"""

        self.original = None
        self.intensities = None
        self.wavelengths = None
        self.wavenumbers = None
        self.baseline = None
        self.peaks = {}
        self.timestamp = None
        self.smoothed = False
    
    def _generate_baseline(self, lmbd, p, n_iter=10):
        """Generates the baseline for the given spectrum

        Copied from Jarek's NMR spectrum class
        Based on Eilers, P; Boelens, H. (2005): Baseline Correction with Asymmetric Least Squares Smoothing.

        Args:
            lmbd (float): Arbitrary parameter to define the smoothness of the baseline
                the larger lmbd is, the smoother baseline will be, recommended value between 1e2 and 1e5
            p (float): An assymetric least squares parameter to compute the weights of the residuals, 
                chosen arbitrary, recommended values between 0.1 and 0.001
            n_iter (int, optinal): Number of iterations to perform the fit, recommended value between 5 and 10
        """

        L = len(self.intensities)
        D = sparse.csc_matrix(np.diff(np.eye(L), 2))
        w = np.ones(L)
        for _ in range(n_iter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lmbd * D.dot(D.transpose())
            z = spsolve(Z, w * self.intensities)
            w = p * (self.intensities > z) + (1 - p) * (self.intensities < z)
        self.baseline = z

    def find_peaks_iteratively(self, threshold=10, steps=100):
        """Finds all peaks iteratively moving the threshold"""

        gradient = np.linspace(self.intensities.max(), self.intensities.min(), steps)
        pl = [0,] # peaks length

        # Looking for peaks and decreasing height
        for i, n in enumerate(gradient):
            peaks, _ = signal.find_peaks(self.intensities, height=n)
            pl.append(len(peaks))
            diff = pl[-1] - pl[-2]
            if diff > threshold:
                self.logger.debug('stopped at iteration %s, with heigth %s, diff - %s', i+1, n, diff)
                break
        
        # Final peaks at previous iteration
        peaks, _ = signal.find_peaks(self.intensities, height=gradient[i-1])

        # Packing for peak dictionary
        peaks_coordinates = list(zip(self.wavelengths[peaks], self.intensities[peaks]))
        peaks_ids = [round(y_id, 1) for y_id in self.wavelengths[peaks]]
        for i, peak_id in enumerate(peaks_ids):
            self.peaks[peak_id] = {'coordinates': peaks_coordinates[i]}

        return peaks_ids

    def find_peaks(self, threshold=0.1, min_width=2, min_dist=None):
        """Finds all peaks above the threshold with at least min_width width
        
        Args:
            threshold (float, optional): Relative peak height with respect to the maximum
            min_width (int, optional): Minimum peak width
            min_dist (int, optional): Minimum distance between peaks

        Return:
            (List): List of peaks ids as rounded peak_y coordinate value

        Also updates the self.peaks attrbiute as:
            (Dict): Dictionary of peaks: {peak_id: {'coordinates': (peak_y, peak_x}}, where:
                peak_id (float): Rounded peak_y coordiate value
                peak_y, peak_x (float): Tuple containing peak_y and peak_x coordinates
        """

        if self.peaks:
            self.peaks = {}

        threshold *= (self.intensities.max() - self.intensities.min())
        peaks, _ = signal.find_peaks(self.intensities, height=threshold, width=min_width, distance=min_dist)
        peaks_coordinates = list(zip(self.wavelengths[peaks], self.intensities[peaks]))
        peaks_ids = [round(y_id, 1) for y_id in self.wavelengths[peaks]]
        for i, peak_id in enumerate(peaks_ids):
            self.peaks[peak_id] = {'coordinates': peaks_coordinates[i]}

        return peaks_ids

    def auto_integrate(self, error=None):
        """Calculate the area of all peaks
        
        Updates peaks attribute with peak width and area: {peak_id: {'width': (left_y, right_y), 'area': area}}
        where:
            peak_id (float): Rounded peak_y coordinate
            left_y, right_y (float): Tuple of y coordinates of left and right borders of interpolated peak peak_id
            area (float): Integral of the interpolated peak with left_y and right_y borders
        """

        if not self.peaks:
            self.find_peaks()

        if error is None:
            error = np.diff(self.wavelengths).mean()
        
        # Since scipy.signal.find_peaks is not very accurate and requires tweaking for
        # Every Raman spectrum, calculating the width of each peak
        # Will be done through the first derivative of the interpolated spectra
        sp = UnivariateSpline(self.wavelengths, self.intensities, k=4)
        roots = sp.derivative().roots()
        peak_position = []
        for peak in self.peaks.values():
            for j, m in enumerate(roots):
                if abs(peak['coordinates'][0]-m) < error:
                    peak_position.append(j)
        
        # Check if error value was enough and we found all the peaks
        # assert len(peak_position) == len(self.peaks), f'{len(peak_position)} peaks found, {len(self.peaks)} peaks were there' 
        if len(peak_position) < len(self.peaks):
            self.logger.warning(
                'INTERPOLATION ERROR: Inconsisten number of peaks calculated, %s - interpolated, %s - found\
                you may consider checking manually via tuning <find_peaks> method attributes',
                len(peak_position), len(self.peaks))
            new_peaks = list(zip(roots[peak_position], sp(roots[peak_position])))
            peaks_ids = [round(y_id, 1) for y_id in roots[peak_position]]
            self.peaks = {}
            for i, peak_id in enumerate(peaks_ids):
                self.peaks[peak_id] = {'coordinates': new_peaks[i]}

        if not peak_position:
            self.logger.warning('No peaks found')
            return

        peak_position = np.array(peak_position)
        
        # New peaks left and right borders
        try:
            lpb = roots[peak_position - 1]
            rpb = roots[peak_position + 1]
        except IndexError as E:
            self.logger.warning(
                'INTERPOLATION ERROR: Looks like you find more peaks than actual data points,\
                your spectrum a is most likely too noisy, consider increasing integration time,\
                also check the error message below: \n %s', E
            )

        # Writing widths and areas as a peaks attributes
        for i, peak in enumerate(self.peaks):
            self.peaks[peak].update({'width': (lpb[i], rpb[i])})
            self.peaks[peak].update({'area': sp.integral(lpb[i], rpb[i])})
        
    def load_spectrum(self, spectrum, timestamp, reference=False):
        """Loads the spectral data
        
        Args:
            spectrum (tuple): Tuple containing spectrum wavelengths and intensities as numpy arrays. 
                Example: (array(wavelengths), array(intensities))
            timestamp (float): time.time() for the measured spectra
            reference (bool, optional): True if the supplied spectra should be stored as a reference (background)
        """

        # If reference update is requested, dump all data to avoid confusion
        if reference:
            self._dump()
            self.reference = spectrum[1]

        # If reloading the spectrum without the data saved - save it!
        if self.intensities is not None:
            self.save_data(f'time-{self.timestamp}.json')

        self.wavelengths = spectrum[0]
        self.original = spectrum[1]
        self.intensities = spectrum[1]
        self.wavenumbers = _convert_wavelength_to_wavenumber(self.wavelengths)
        self.timestamp = timestamp

    def trim(self, xmin=MIN_X, xmax=MAX_X):
        """
        Trims the spectrum data to be within a specific wavelengths range

        Args:
            xmin (int): Minimum position on the X axis to start from
            xmax (int): Maximum position on the X axis to end from
        """

        # Creating the mask to map arrays
        above_ind = self.wavelengths > xmin
        below_ind = self.wavelengths < xmax
        full_mask = np.logical_and(above_ind, below_ind)

        # Mapping arrays if they are supplied
        self.wavelengths = self.wavelengths[full_mask]
        self.wavenumbers = self.wavenumbers[full_mask]
        self.intensities = self.intensities[full_mask]
        if self.reference is not None and self.reference.shape == full_mask.shape:
            self.reference = self.reference[full_mask]
        if self.baseline is not None and self.baseline.shape == full_mask.shape:
            self.baseline = self.baseline[full_mask]

    def subtract_reference(self):
        """Subtracts reference spectrum and updates the current one"""

        if self.reference is None:
            raise ValueError('Please upload the reference first')

        self.intensities = self.intensities - self.reference

    def subtract_baseline(self):
        """Subtracts the baseline and updates the current spectrum"""

        self._generate_baseline(lmbd=1e3, p=0.01, n_iter=10)

        self.intensities = self.intensities - self.baseline
    
    def show_spectrum(self, param='wvl'):
        """Plots the spectrum and shows it using matplotlib.pyplot"""

        if param == 'wvl':
            plt.plot(self.wavelengths, self.intensities, color='black', label=f'{self.timestamp}')
            plt.xlabel(WAVELENGTHS)
        elif param == 'wvn':
            plt.plot(self.wavenumbers, self.intensities, color='black', label=f'{self.timestamp}')
            plt.xlabel(WAVENUMBERS)
        else:
            raise ValueError('Select either "wvl" or "wvn" parameter to show either wavelenegths or wavenumbers')
        plt.ylabel(INTENSITIES)
        if self.peaks:
            plt.scatter(
                [peak['coordinates'][0] for peak in self.peaks.values()],
                [peak['coordinates'][1] for peak in self.peaks.values()],
                label='found peaks'
            )
        plt.legend()
        plt.show()

    def smooth_spectrum(self):
        """Smoothes the spectrum using Savitsky-Golay filter"""
        
        if self.smoothed:
            self.logger.info('Already smoothed')

        self.intensities = signal.savgol_filter(self.intensities, 15, 7)
        self.smoothed = True
        self.logger.debug('Smoothed')

    def save_data(self, filename=None):
        """Saves the spectrum and all supporting information as json file
        
        Args:
            path (str): Valid path for saving the data

        Returns:
            (Dict): Dictionary with spectral data if path is None
            (bool): True if path was provided and data was saved as .json file
        """
        filename += '.json'
        path = os.path.join(self.path, filename)

        # Handling missing properties
        if self.reference is None:
            self.reference = np.zeros(self.intensities.shape)
        if self.baseline is None:
            self.baseline = np.zeros(self.intensities.shape)
        if self.wavenumbers is None:
            self.wavenumbers = _convert_wavelength_to_wavenumber(self.wavelengths)

        data = {
            WAVELENGTHS: self.wavelengths.tolist(),
            ORIGINAL: self.original.tolist(),
            INTENSITIES: self.intensities.tolist(),
            WAVENUMBERS: self.wavenumbers.tolist(),
            REFERENCE: self.reference.tolist(),
            PEAKS: self.peaks,
            BASELINE: self.baseline.tolist(),
            TIMESTAMP: self.timestamp,
        }

        if filename is None:
            return data

        with open(path, 'w') as f:
            json.dump(data, f)

        # Flushing the data if saved
        self._dump()
        return True

    def load_data(self, path):
        """Loads the spectrum and all supporting information from json file
        
        Args:
            path (str): Valid path for loading the data
        """
        self._dump()

        with open(path, 'r') as f:
            data = json.load(f)
        
        # Not very elegant but allows to pass missing data without KeyError handling
        for key, value in data.items():
            if key in self.__dict__.keys():
                if isinstance(value, list):
                    value = np.array(value)
                self.__dict__.update({key: value})
    
    def default_process(self, path=None):
        """Default processing"""

        self.trim(810, 950)
        self.subtract_reference()
        self.subtract_baseline()
        self.find_peaks_iteratively()
        self.auto_integrate()
        return self.save_data(path)

# if __name__ == '__main__':
#     spec = RamanSpectrum()
#     spec.load_data('raman_data.json')
#     spec.trim(810, 950)
#     spec.subtract_baseline()
#     spec.show_spectrum()
