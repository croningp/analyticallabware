"""
.. module:: QEPro2192
    :synopsis: Module representing the UV QEPro2192 spectrometer
    :platforms: Unix, Windows

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

.. note:: Feel free to edit. This is a skeleton for minimal functionality.

"""

from .uv_spectrum import UVSpectrum
from ..oceanoptics import OceanOpticsSpectrometer

class NoReferenceException(Exception):
    """Exception for calling spectrum without a reference
    """

class QEPro2192(OceanOpticsSpectrometer):
    """Class representing the QEPro2192 spectrometer

    Inherits:
        OceanOpticsSpectrometer
    """

    def __init__(self):
        super().__init__("UV", name="QEPro2192 UV Spectrometer")
        self.reference = {}
        self.__ref_called = False

    def obtain_reference_spectrum(self) -> UVSpectrum:
        """Obtain a reference spectrum.

        Returns:
            UVSpectrum: Reference UV spectrum
        """

        wavelengths, intensities = self.scan()
        self.reference["wavelength"] = wavelengths
        self.reference["intensities"] = intensities
        self.__ref_called = True

        return UVSpectrum(wavelengths, intensities)

    def obtain_spectrum(self) -> UVSpectrum:
        """Obtain a UV spectrum of a sample.

        Raises:
            NoReferenceException: Attempting to measure a sample without
            a reference

        Returns:
            UVSpectrum: Sample UV spectrum.
        """

        if not self.__ref_called:
            raise NoReferenceException(
                "Attempting to call a spectrum without a valid reference\
                spectrum"
            )

        wavelengths, intensities = self.scan()
        return UVSpectrum(wavelengths, intensities, ref=self.reference)
