import os
import time

import numpy as np
import nmrglue as ng
import scipy

from AnalyticalLabware import SpinsolveNMRSpectrum

from .utils import find_nearest_value_index

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

    Peak regions are filtered to remove potential false positives (e.g. noise
        spikes).

    Args:
        x_data (:obj:np.array): X data points, needed to pick up the data
            resolution and map the region indexes to the corresponding data
            points.
        y_data (:obj:np.array): Y data points, needed to validate if the peaks
            are actually present in the region and remove invalid regions.
        peaks_regions (:obj:np.array): 2D Nx2 array with peak regions indexes
            (rows) as left and right borders (columns).

    Returns:
        :obj:np.array: 2D Mx2 array with filtered peak regions indexes(rows) as
            left and right borders (columns).
    """

    # filter peaks where region is smaller than spectrum resolution
    # like single spikes, e.g. noise
    # compute the regions first
    x_data_regions = np.copy(x_data[peaks_regions])

    # get arguments where absolute difference is greater than data resolution
    resolution = np.absolute(np.mean(np.diff(x_data)))

    # (N, 1) array!
    valid_regions_map = np.absolute(np.diff(x_data_regions)) > resolution

    # get their indexes, mind the flattening of all arrays!
    valid_regions_indexes = np.argwhere(valid_regions_map.flatten()).flatten()

    # filtering!
    peaks_regions = peaks_regions[valid_regions_indexes]

    return peaks_regions

def filter_noisy_regions(y_data, peaks_regions):
    """ Remove noisy regions from given regions array.

    Peak regions are filtered to remove false positive noise regions, e.g.
        incorrectly assigned due to curvy baseline. Filtering is performed by
        computing average peak points/data points ratio.

    Args:
        y_data (:obj:np.array): Y data points, needed to validate if the peaks
            are actually present in the region and remove invalid regions.
        peaks_regions (:obj:np.array): 2D Nx2 array with peak regions indexes
            (rows) as left and right borders (columns).

    Returns:
        :obj:np.array: 2D Mx2 array with filtered peak regions indexes(rows) as
            left and right borders (columns).
    """

    # compute the actual regions data points
    y_data_regions = []
    for region in peaks_regions:
        y_data_regions.append(
            y_data[region[0]:region[-1]]
        )

    # compute noise data regions, i.e. in between peak regions
    noise_data_regions = []
    for row, _ in enumerate(peaks_regions):
        try:
            noise_data_regions.append(
                y_data[peaks_regions[row][1]:peaks_regions[row+1][0]]
            )
        except IndexError:
            # exception for the last row -> discard
            pass

    # compute average peaks/data points ratio for noisy regions
    noise_peaks_ratio = []
    for region in noise_data_regions:
        # minimum height is pretty low to ensure enough noise is picked
        peaks, _ = scipy.signal.find_peaks(region, height=region.max()*0.2)
        noise_peaks_ratio.append(peaks.size/region.size)

    # compute average with weights equal to the region length
    noise_peaks_ratio = np.average(
        noise_peaks_ratio,
        weights=[region.size for region in noise_data_regions]
    )

    # filtering!
    valid_regions_indexes = []
    for row, region in enumerate(y_data_regions):
        peaks, _ = scipy.signal.find_peaks(region, height=region.max()*0.2)
        if peaks.size != 0 and peaks.size/region.size < noise_peaks_ratio:
            valid_regions_indexes.append(row)

    peaks_regions = peaks_regions[np.array(valid_regions_indexes)]

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
        :obj:np.array: 2D Mx2 array with peak regions indexes (rows) as left and
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
    """ Expand the peak regions by the desired value.

    Args:
        x_data (:obj:np.array): X data points.
        peaks_regions (:obj:np.array): 2D Nx2 array with peak regions indexes
            (rows) as left and right borders (columns).
        d_expand (float): Value to expand borders to (in X data scale).

    Returns:
        :obj:np.array: 2D Nx2 array with expanded peak regions indexes (rows) as
            left and right borders (columns).
    """

    data_regions = np.copy(x_data[peaks_regions])

    # determine scale orientation, i.e. decreasing (e.g. ppm on NMR spectrum)
    # or increasing (e.g. wavelength on UV spectrum)
    if (data_regions[:, 0] - data_regions[:, 1]).mean() > 0:
        # ppm-like scale
        data_regions[:, 0] += d_expand
        data_regions[:, -1] -= d_expand
    else:
        # wavelength-like scale
        data_regions[:, 0] -= d_expand
        data_regions[:, -1] += d_expand

    # converting new values to new indexes
    for index_, value in np.ndenumerate(data_regions):
        data_regions[index_] = find_nearest_value_index(x_data, value)[1]

    return data_regions.astype(int)

#TODO method for validating peak regions

def phase_region(y_data, region, space=20, n_iter=3):
    """ Phase individual region of spectral points.

    Optimal phase is found iteratively by minimizing the area under the baseline
    for the corresponding region.

    Args:
        y_data (:obj:np.array): 1D array of spectral data points.
        region (Union[List, :obj:np.array]): Indexes of left and right border of
            region of interest.
        space (int, optional): Number of evenly spaced phase values to iterate
            through.
        n_iter (int, optional): Number of iterations.

    Returns:
        List[int, float, :obj:np.array]:
            - peak position (index) on the y data or averaged value in case of
                several peaks in the region;
            - optimal phase for the region;
            - height(s) of the found peak(s) in the region.
    """
    # slicing the region of interest
    data_region = y_data[region[0]:region[-1]]

    # initial coarse adjustment space
    phases = np.linspace(-180, 180, space)

    for _ in range(n_iter):
        sum_vals = []
        for phase in phases:
            # phasing the region
            phased = ng.proc_base.ps(data_region, phase)
            # building baseline as linspace between region edge points
            baseline = np.linspace(
                data_region[0], data_region[-1], len(data_region))
            # mapping the points under the baseline
            points_below = np.ma.less(phased, baseline)
            # original paper was calculating area under the curve
            # but simple number of points give sufficient results
            # or even better for really noisy spectra
            sum_points = np.sum(points_below)
            sum_vals.append(sum_points)
        min_sum = np.argmin(sum_vals)
        # building new adjustment space within found minimum
        phases = np.linspace(phases[min_sum-1], phases[min_sum+1], space)

    # 0.3 height was chosen arbitrary to catch all peaks in the region
    # and at the same time skip noise spikes
    peak_id, peak_dic = scipy.signal.find_peaks(
        phased, height=data_region.max()*0.3)

    # calculate relative region position if several peaks found in the region
    if len(peak_id) > 1:
        # converting to int to use as index
        peak_id = np.around(peak_id.mean()).astype(int)
        peak_dic['peak_heights'] = peak_dic['peak_heights'].sum()
    else:
        # just peak up the value
        peak_id = peak_id[0]
        peak_dic['peak_heights'] = peak_dic['peak_heights'][0]

    return [region[0] + peak_id, phases[9], peak_dic['peak_heights']]

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