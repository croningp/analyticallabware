import os
import time

import numpy as np

from AnalyticalLabware import SpinsolveNMRSpectrum

def create_binary_peak_map(data):
    """ Return binary map of the peaks within data points.

    True values are assigned to potential peak points, False - to baseline.

    Args:
        data (:obj:np.array): 1D array with data points.

    Returns:
        :obj:np.array, dtype=bool: Mapping of data points, where True is
            potential peak region point, False - baseline.
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
    """ Combine True values into their indexes arrays.

    Args:
        mapping (:obj:np.array): Boolean mapping array to extract the indexes
            from.

    Returns:
        :obj:np.array: 2D array with left and right borders of regions, where
            mapping is True.

    Example:
        >>> combine_map_to_regions(np.array([True, True, False, True, False]))
        array([[0, 1],
                [3, 3]])
    """

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
    """ Filter peak regions.

    Peak regions are filtered to removed potential false positives (e.g. noise
        spikes).

    Args:
        x_data (:obj:np.array): X data points, needed to pick up the data
            resolution and map the region indexes to the corresponding data
            points.
        peaks_regions (:obj:np.array): 2D Nx2 array with peak regions indexes
            (rows) as left and right borders (columns).

    Returns:
        :obj:np.array: 2D Mx2 array with filtered peak regions indexes(rows) as
            left and right borders (columns).
    """

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

def merge_regions(x_data, peaks_regions, d_merge, recursively=True):
    """ Merge peak regions if distance between is less than delta.

    Args:
        x_data (:obj:np.array): X data points.
        peaks_regions (:obj:np.array): 2D Nx2 array with peak regions indexes
            (rows) as left and right borders (columns).
        d_merge (float): Minimum distance in X data points to merge two or more
            regions together.
        recursively (bool, optional): If True - will repeat the procedure until
            all regions with distance < than d_merge will merge.

    Returns:
        :obj:np.array: 2D Nx2 array with peak regions indexes (rows) as left and
            right borders (columns), merged according to predefined minimal
            distance.

    Example:
        >>> regions = np.array([
                [1, 10],
                [11, 20],
                [25, 45],
                [50, 75],
                [100, 120],
                [122, 134]
            ])
        >>> data = np.ones_like(regions) # ones as example
        >>> merge_regions(data, regions, 1)
        array([[  1,  20],
               [ 25,  45],
               [ 50,  75],
               [100, 120],
               [122, 134]])
        >>> merge_regions(data, regions, 20, True)
        array([[  1,  75],
               [100, 134]])
    """
    # the code is pretty ugly but works
    merged_regions = []

    # converting to list to drop the data of the fly
    regions = peaks_regions.tolist()

    for i, _ in enumerate(regions):
        try:
            # check left border of i regions with right of i+1
            if abs(x_data[regions[i][-1]] - x_data[regions[i+1][0]]) <= d_merge:
                # if lower append merge the regions
                merged_regions.append([regions[i][0], regions[i+1][-1]])
                # drop the merged one
                regions.pop(i+1)
            else:
                # if nothing to merge, just append the current region
                merged_regions.append(regions[i])
        except IndexError:
            # last row
            merged_regions.append(regions[i])

    merged_regions = np.array(merged_regions)

    if not recursively:
        return merged_regions

    # if recursively, check for the difference
    if (merged_regions == regions).all():
        # done
        return merged_regions

    return merge_regions(x_data, merged_regions, d_merge, recursively=True)

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