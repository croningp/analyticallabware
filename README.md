# AnalyticalLabware
This repository contains python interface for analytical instruments to be used exclusively with Chemputer or any other platform developed in Cronin Group.

# Installation
1) Clone the repo and change your working directory
```bash
git clone git@gitlab.com:croningroup/chemputer/analyticallabware.git

cd analyticallabware
```
2) Install chemputer related packages unless installed already
```bash
pip install -r requirements.txt
```
3) Install AnalyticalLabware with the extra dependencies needed for your instrument, i.e.
```bash
# For the Magritek Spinsolve NMR
pip install -e .[spinsolve]
# For the AdvionMS
pip install -e .[advion]
# For the Ocean Optics Spectrometers
pip install -e .[oceanoptics]
# For the Agilent HPLC
pip install -e .[agilent]

# Or install all dependencies with
pip install -e .[all]
```
If you need to use Advion MS instrument, please contact @hessammehr for the installation guidelines.
## Note for python 3.9 users
Since pythonnet is not supported in python 3.9 ([yet][pythonnet-python39-support]), users who want to use Advion instruments should use python 3.8 instead.

## Requirements
### Python libraries
- scipy
- matplotlib
- numpy
- seabreeze (python wrapper for OceanOptics Seabreeze library, [git][seabreeze-git]/[docs][seabreeze-docs])
- nmrglue (python library for nmr data processing, [git][nmrglue-git]/[docs][nmrglue-docs])

### Device specific
- Advion bindings require .NET Framework 4.0 or later ([download link][dotnetfx]) and Advion API 6.4 (x64) or later.

#### _Chemputer specific_
- ChemputerAPI
- SerialLabware


# Usage guides

## Spinsolve NMR
```python
from AnalyticalLabware import SpinsolveNMR

# Make sure that Spinsolve software is running and
# the Remote Control option is turned on
s = SpinsolveNMR()

# create a data folder to save spectra to
s.user_folder('path_to_folder') # check available saving options in method doc

# set experiment specific data
s.solvent = 'methanol'
s.sample = 'TEST-1'
s.user_data = {'comment': 'test experiment 1'}

s.protocols_list() # yields list of all available protocols

# get available protocol options
# where 'protocol_name' is the name of the protocol
s.cmd.get_protocol('protocol_name')

# shim on sample
# check available shimming options in the manual
s.shim_on_sample(
    reference_peak=<reference_peak_float_number>,
    option=<option_parameter>
)

# simple proton experiment
# where 'option' is a valid option for simple proton protocol ('1D PROTON')
s.proton(option='option')

### Basic spectrum processing is available through s.spectrum class ###
# loads last measured spectrum if any, else runs default protocol
s.get_spectrum()

# now ppm and spectral data are available as s.spectrum.x and s.spectrum.y
# hint: to obtain raw FID data use the following public method for the 'data.1d' file
time_axis, fid_real, fid_imag = s.spectrum.extract_data(<path_to_fid_file>)
```

## OceanOptics Raman spectrometer
```python
from AnalyticalLabware import OceanOpticsRaman

# make sure your instrument is connected and you've
# installed all required hardware drivers
r = OceanOpticsRaman()

# set the integration time in seconds!
r.set_integration_time(<time_in_seconds>)

# obtain raw spectroscopic data
# will return tuple of wavelength and intensities arrays
# as np.array objects
r.scan(<n_scans>)
```

The module also supports basic spectrum processing.

```python
# load the spectrum data to internal Spectrum class
r.get_spectrum()

# the spectrum is now available via r.spectrum
# you can use the following methods for processing
r.spectrum.correct_baseline() # subtracting the baseline
r.spectrum.smooth_spectrum() # smoothing the spectrum
r.spectrum.trim(xmin, xmax) # trimming the spectrum on X axis

# finding the peaks, please refer to method documentation for
# attribute assignment
r.spectrum.find_peaks(threshold, min_width, min_dist)
# alternative method
# r.spectrum.find_peaks_iteratively(threshold, steps)

# integration
r.spectrum.integrate_area(area)
r.spectrum.integrate_peak(peak)

# saving the data as .pickle file
r.spectrum.save_data(filename) # !filename without .pickle extension!
```

## Advion CMS mass spectrometers
Before
1. You will need to do a one-time setup at the beginning.
```python
import time
from AnalyticalLabware.devices.Advion import (
    AdvionData, SimulatedInstrument, USBInstrument, InstrumentController, AcquisitionManager
)

instrument = USBInstrument() # SimulatedInstrument() if not connected to physical spectrometer
controller = InstrumentController(instrument)

controller.start_controller()
controller.operate() # starts N2 flow
```

2. For each experiment, create an acquisition manager, which allows you to control the run.
```python
manager = AcquisitionManager(
    MS_METHOD, # path to method XML
    [MS_ION_SOURCE_P, MS_ION_SOURCE_N],
    [MS_TUNE_P, MS_TUNE_N],
    self.experiment_name,
    self.experiment_dir,
)

# wait until manager ready before starting a run
while manager.state != advion_wrapper.AcquisitionState.Ready:
    time.sleep(2)
manager.start()

# wait until acquisition actually underway
while manager.state != advion_wrapper.AcquisitionState.Underway:
    time.sleep(2)

# wait until done
while manager.state != advion_wrapper.AcquisitionState.Ready:
    time.sleep(2)

# export output .datx files to npz/csv
data = AdvionData("my_data.datx")
data.write_npz("my_data.npz") # more space-efficient
data.write_csv("my_data.csv")
```

# Contribution
If you wish to contribute, branch off master, use the general style of the device classes and your common sense. `AbstractSpectrum` class is there for you to provide &#0177;unified API for the spectral data, feel free to rewrite the parent processing methods and add your own. When done - submit a merge request.

[dotnetfx]: https://dotnet.microsoft.com/download/dotnet
[nmrglue-docs]: https://nmrglue.readthedocs.io/en/latest/index.html
[nmrglue-git]: https://github.com/jjhelmus/nmrglue
[seabreeze-docs]: https://python-seabreeze.readthedocs.io/en/latest/index.html
[seabreeze-git]: https://github.com/ap--/python-seabreeze
[pythonnet-python39-support]: https://github.com/pythonnet/pythonnet/issues/1389