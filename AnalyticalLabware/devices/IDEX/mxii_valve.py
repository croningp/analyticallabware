import SerialLabware

try:
    from SerialLabware.controllers import AbstractDistributionValve
    # running SerialLabware 2
    from .mxii_valve_sl2 import IDEXMXIIValve
except ImportError:
    from .mxii_valve_sl1 import IDEXMXIIValve
