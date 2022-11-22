"""Module containts general SpinSolve errors"""


class HardwareError(Exception):
    """Generic error in hardware operation"""


class NMRError(Exception):
    """Generic error in NMR operation"""


class ProtocolError(NMRError):
    """Generic error in Protocol handling"""


class ProtocolOptionsError(KeyError):
    """Error in selecting correct options for chosen protocol"""


class ShimmingError(HardwareError):
    """Specific error in case of poor instrument shimming"""


class RequestError(KeyError):
    """Specific error in case of wrong request type"""
