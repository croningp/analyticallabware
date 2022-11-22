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
3) Setup `pre-commit` to automatically lint code and apply formatting where applicable on each commit:
```bash
pre-commit install
```
4) Install AnalyticalLabware with the extra dependencies needed for your instrument, i.e.
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
- nmrglue (python library for nmr data processing, [git][nmrglue-git]/[docs][nmrglue-docs])

### Device specific
- Advion bindings require .NET Framework 4.0 or later ([download link][dotnetfx]) and Advion API 6.4 (x64) or later.
- Ocean Optics spectrometers require a `seabreeze` library for a hardware control: [git][seabreeze-git]/[docs][seabreeze-docs]. *Note*: to build a seabreeze library for python 3.9 a Microsoft Visual Studio is required.
- Magritek Spinsolve NMR spectrometer requires `nmrglue` library for processing of the nmr spectra: [git][nmrglue-git]/[docs][nmrglue-docs].

#### _Chemputer specific_
- ChemputerAPI
- SerialLabware


# Usage guides

## Spinsolve NMR
```python
from AnalyticalLabware.devices import SpinsolveNMR

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
from AnalyticalLabware.devices import OceanOpticsRaman

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

## Agilent HPLC System
The following instructions are only valid for Agilent HPLC systems running with Agilent Chemstation v1.X.X software. The instrument control is achieved using the special macro in the Agilent Chemstation software.
1. To activate the macro, copy the corresponding file `hplctalk.mac` from the [AnalyticalLabware](./AnalyticalLabware/devices/Agilent/hplctalk.mac) to the core folder of the Chemstation installation (`C:\Chem32\CORE` by default).
2. Then activate it by typing the following commands in the Chemstation command line:
    1. `macro hplctalk.mac` -> activate the macro.
    2. `HPLCTalk_Run` -> start command monitoring.

**Alternatively** after copying the macro file you can add the commands to the `user.mac` macro file (or create it if does not exist). The `user.mac` macro is executed every time the Chemstation software starts, so your script will run by default. Example of new `user.mac` file below:
```
macro hplctalk.mac
HPLCTalk_Run
```

The following methods are available for the use from AnalyticalLabware HPLC module:
```python
from AnalyticalLabware.devices.agilent.hplc import HPLCController

# Ensure path exists
# Otherwise change the path in the macro file and restart the macro in chemstation
default_command_path = "C:\\Users\\group\\Code\\analyticallabware\\AnalyticalLabware\\test"

hplc = HPLCController(comm_dir=default_command_path)

# Check the status
hplc.status()

# Prepare for running
hplc.preprun()

# Switch the method
# ".M" is appended to the method name by default
hplc.switch_method(method_name="my_method")

# Execute the method and save the data in the target folder
# Under experiment name
hplc.run_method(
    data_dir="path_to_target_folder",
    experiment_name="name_of_your_experiment"
)

# Switch all modules into standby mode
hplc.standby()

# Obtain the last measure spectrum and store it in self.spectra collection
# Channels A, B, C and D are read by default
hplc.get_spectrum()

# When spectra are loaded, use can access the collection by the channel name
# And perform basic processing and analysis operations
chrom = hplc.spectra['A']  # Chromatogram at channel A of the detector
chrom.find_peaks()  # Find peaks
chrom.show_spectrum()  # Display the chromatogram
```

## Chemputer specific
AnalyticalLabware devices can be used in chempiler enironment if added to the corresponding graph with the correct set of parameters.

Example of the Spinsolve NMR object on the graph:
```json
{
    "id": "nmr",
    "type": "custom",
    "x": 240,
    "y": 240,
    "customProperties": {
        "name": {
            "name": "name",
            "id": "name",
            "units": "",
            "type": "str"
        }
    },
    "internalId": 24,
    "label": "nmr",
    "current_volume": 0,
    "class": "ChemputerNMR",
    "name": "nmr"
}
```
To instantiate chempiler, simply import `chemputer_devices` module from `AnalyticalLabware` and supply as a `device_modules` argument during Chempiler instantiation, e.g.
```python
from AnalyticalLabware.devices import chemputer_devices
from chempiler import Chempiler
import ChemputerAPI

c = Chempiler(
    'procedure', 'graph.json', 'output',
    simulation=True,
    device_modules=[ChemputerAPI, chemputer_devices]
)
```
# Contribution
If you wish to contribute, branch off master, use the general style of the device classes and your common sense. `AbstractSpectrum` class is there for you to provide &#0177;unified API for the spectral data, feel free to rewrite the parent processing methods and add your own. When done - submit a merge request.

[dotnetfx]: https://dotnet.microsoft.com/download/dotnet
[nmrglue-docs]: https://nmrglue.readthedocs.io/en/latest/index.html
[nmrglue-git]: https://github.com/jjhelmus/nmrglue
[seabreeze-docs]: https://python-seabreeze.readthedocs.io/en/latest/index.html
[seabreeze-git]: https://github.com/ap--/python-seabreeze
[pythonnet-python39-support]: https://github.com/pythonnet/pythonnet/issues/1389
