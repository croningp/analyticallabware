"""Module for interfacing with OceanOptics Raman spectrometer

.. moduleauthor:: Artem Leonov, Graham Keenan
"""
import time
import logging

from ..oceanoptics import OceanOpticsSpectrometer
from .raman_spectrum import RamanSpectrum

class OceanOpticsRaman(OceanOpticsSpectrometer):
    """Operational class for interfacing with the OceanOptics Raman spectrometer

    Inherits:
        OceanOpticsSpectrometer: Base Spectrometer class
    """

    def __init__(self, name=None, path=None, integration_time=2.0):
        super().__init__('RAMAN', name)
        self.last_spectrum = None
        self.spectrum = RamanSpectrum(path)
        self.start_time = time.time()
        self.spectrum.start_time = self.start_time
        self.logger = logging.getLogger('oceanoptics.spectrometer.raman')
        self.set_integration_time(integration_time)

    def get_spectrum(self):
        """Obtains spectrum and performs basic processing"""

        spec = self.scan()
        timestamp = round(time.time(), 2)
        self.logger.debug('Spectrum obtained at %s', timestamp)
        self.spectrum.load_spectrum(spec, timestamp, reference=False)
        # self.last_spectrum = self.spectrum.default_process()
        # return np.array(
        #     [
        #         self.last_spectrum['wavelengths'],
        #         self.last_spectrum['intensities']
        #     ]
        # )

    def obtain_reference_spectrum(self):
        """Obtains the reference spectrum for further use"""

        spec = self.scan()
        self.start_time = time.time()
        self.spectrum.load_spectrum(spec, self.start_time, reference=True)
