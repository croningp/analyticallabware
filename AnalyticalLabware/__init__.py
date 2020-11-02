# physical instruments
from .devices.IDEX.mxii_valve import IDEXMXIIValve
from .devices.Magritek.Spinsolve.spinsolve import SpinsolveNMR
from .devices.OceanOptics.Raman.raman_control import OceanOpticsRaman
from .devices.OceanOptics.UV.QEPro2192 import QEPro2192
from .devices.OceanOptics.IR.NIRQuest512 import NIRQuest512
from .devices.DrDAQ.pH_module import DrDaqPHModule
from .devices.Agilent.hplc import HPLCController

# chemputer-related instruments
from .devices.chemputer_devices import *

# classes for spectra processing
from .devices.OceanOptics.Raman.raman_spectrum import RamanSpectrum
from .devices.Magritek.Spinsolve.spectrum import SpinsolveNMRSpectrum
from .devices.Agilent.chromatogram import AgilentHPLCChromatogram
