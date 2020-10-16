import logging
import time

import numpy as np

from ChemputerAPI import ChemputerDevice

from AnalyticalLabware import IDEXMXIIValve, SpinsolveNMR, OceanOpticsRaman, HPLCController

from ..analysis.base_spectrum import AbstractSpectrum

### Physical devices ###

class ChemputerIDEX(IDEXMXIIValve, ChemputerDevice):
    def __init__(self, name, address, mode="ethernet", port=5000):
        ChemputerDevice.__init__(self, name)
        IDEXMXIIValve.__init__(
            self,
            mode=mode,
            address=address,
            connect_on_instantiation=True,
        )

    @property
    def capabilities(self):
        return [("sink", 0)]
    
    def wait_until_ready(self):
        pass

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

    def default_processing(self, *args, **kwargs):
        return self.x, self.y, 42.0

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

class SimChemputerIDEX(IDEXMXIIValve, ChemputerDevice):
    def __init__(self, name, address, port=5000):
        ChemputerDevice.__init__(self, name)

    @property
    def capabilities(self):
        return [("sink", 0)]

    def open_connection(self):
        self.logger.info("Opening connection!")

    def wait_until_ready(self):
        pass

    def sample(self, time):
        self.logger.info("Valving sampling!")

# Generator to simulate change of HPLC status
def alternate():
    while True:
        yield ["PRERUN"]
        yield ["NOTREADY"]

class SimHPLCController(HPLCController, ChemputerDevice):

    alternator = alternate()
    
    def __init__(self, name):
        ChemputerDevice.__init__(self, name)
        self.spectrum = _SimulatedSpectrum()

    def switch_method(self, name):
        pass

    def send(self):
        pass
    
    def receive(self):
        pass

    def standby(self):
        pass

    def preprun(self):
        pass

    def sleep(self):
        pass

    def status(self, alternator=alternator):
        return next(alternator)

    def get_spectrum(self, *args, **kwargs):
        self.spectrum.load_spectrum()
