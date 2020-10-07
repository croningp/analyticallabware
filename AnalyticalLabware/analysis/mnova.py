import os
import time

import numpy as np

from AnalyticalLabware import SpinsolveNMRSpectrum

def create_binary_peak_map(data):
    """ Return binary map of the peaks within data points.

    True value is assigned to potential peak points, False - to baseline.
    """
    # copying array
    data_c = np.copy(data)

    # placeholder for the peak mapping
    peak_map = np.full_like(data_c, False, dtype=bool)

    for _ in range(100500): # shouldn't take more iterations

        # looking for peaks
        peaks_found = np.logical_or(
            data_c > np.mean(data_c) + np.std(data_c)*3,
            data_c < np.mean(data_c) - np.std(data_c)*3
        )

        # merging with peak mapping
        np.logical_or(peak_map, peaks_found, out=peak_map)

        # if no peaks found - break
        if not peaks_found.any():
            break

        # setting values to 0 and iterating again
        data_c[peaks_found] = 0

    return peak_map

def combine_map_to_regions(mapping):
    """ Combine Falses and Trues values into their indexes arrays. """

    # region borders
    region_borders = np.diff(mapping)

    # corresponding indexes
    border_indexes = np.argwhere(region_borders)

    lefts = border_indexes[::2]+1 # because diff was used to get the index

    # edge case, where first peak doesn't have left border
    if mapping[border_indexes][0]:
        # just preppend 0 as first left border
        # mind the vstack, as np.argwhere produces a vector array
        lefts = np.vstack((0, lefts))

    rights = border_indexes[1::2]

    # another edge case, where last peak doesn't have a right border
    if mapping[-1]: # True if last point identified as potential peak
        # just append -1 as last peak right border
        rights.vstack((rights, -1))

    # columns as borders, rows as regions, i.e.
    # :output:[0] -> first peak region
    return np.hstack((lefts, rights))

def filter_regions(x_data, peaks_regions):
    """ Filter peak regions. """

    # filter peaks where region is smaller than spectrum resolution
    # like single spikes, e.g. noise
    # compute the regions first
    data_regions = np.copy(x_data[peaks_regions])

    # get arguments where absolute difference is greater than data resolution
    resolution = np.absolute(np.mean(np.diff(x_data)))
    valid_regions_map = np.absolute(np.diff(data_regions)) > resolution

    # get their indexes, mind the flattening of all arrays!
    valid_regions_indexes = np.argwhere(valid_regions_map.flatten()).flatten()

    # filtering!
    peaks_regions = peaks_regions[valid_regions_indexes]

    return peaks_regions

def merge_regions(x_data, peaks_regions, d_merge):
    """ Merge peak regions if distance between is less than delta. """

def expand_regions(x_data, peaks_regions, d_expand):
    """ Expand the peak regions by the desired value. """

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import scipy

    plt.ion()
    fig, ax = plt.subplots()
    HERE = os.path.abspath(os.path.dirname(__file__))
    DATA = os.path.join(HERE, 'data.1d')
    ACQU_PARS = os.path.join(HERE, 'acqu.par')

    spec = SpinsolveNMRSpectrum(False)
    spec.load_spectrum(HERE)
    spec.fft()

    x, y = spec.x, spec.y
    params = spec.extract_parameters(ACQU_PARS)

    # switching to magnitude mode
    y_m = np.sqrt(y.real**2 + y.imag**2)

    # derivative for further calculation
    y_m_der = np.gradient(y_m)

    # Gussian filtered
    y_m_g = scipy.ndimage.gaussian_filter1d(y_m, 3)