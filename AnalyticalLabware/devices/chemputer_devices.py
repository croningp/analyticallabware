import logging
import time

import numpy as np

from ChemputerAPI import ChemputerDevice

from .Magritek.Spinsolve.spinsolve import SpinsolveNMR
from .OceanOptics.Raman.raman_control import OceanOpticsRaman
from ..analysis.base_spectrum import AbstractSpectrum

### Physical devices ###

class ChemputerNMR(SpinsolveNMR, ChemputerDevice):
    def __init__(self, name):
        ChemputerDevice.__init__(self, name)
        SpinsolveNMR.__init__(self)

    @property
    def capabilities(self):
        return [("sink", 0)]

### Simulated devices ###

class _SimulatedSpectrum(AbstractSpectrum):

    def __init__(self, *args, **kwargs):
        super().__init__(save_path=False)

    def load_spectrum(self, *args, **kwargs):
        x = np.linspace(-100, 100, 1000)
        y = 1/(1 + x**2)
        super().load_spectrum(x=x, y=y, timestamp=time.time())

    def save_data(self, *args, **kwargs):
        pass

class SimChemputerNMR(ChemputerDevice):
    def __init__(self, name):
        ChemputerDevice.__init__(self, name)
        self.spectrum = _SimulatedSpectrum()

    def get_spectrum(self, *args, **kwargs):
        self.spectrum.load_spectrum()

    @property
    def capabilities(self):
        return [("sink", 0)]

class SimOceanOpticsRaman():

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('simulated.oceanopticsraman')
        self.spectrum = _SimulatedSpectrum()

    def get_spectrum(self):
        self.spectrum.load_spectrum()

    def obtain_reference_spectrum(self):
        pass
