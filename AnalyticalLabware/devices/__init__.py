# physical instruments
from .IDEX.mxii_valve import IDEXMXIIValve
from .Magritek.Spinsolve.spinsolve import SpinsolveNMR
from .OceanOptics.Raman.raman_control import OceanOpticsRaman
from .OceanOptics.UV.QEPro2192 import QEPro2192
from .OceanOptics.IR.NIRQuest512 import NIRQuest512
from .DrDAQ.pH_module import DrDaqPHModule
from .Agilent.hplc import HPLCController

# chemputer-related instruments
from .chemputer_devices import *

# classes for spectra processing
from .OceanOptics.Raman.raman_spectrum import RamanSpectrum
from .Magritek.Spinsolve.spectrum import SpinsolveNMRSpectrum
from .Agilent.chromatogram import AgilentHPLCChromatogram
