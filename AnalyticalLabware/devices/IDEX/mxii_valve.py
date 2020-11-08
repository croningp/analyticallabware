import SerialLabware

try:
    # running SerialLabware 2
    from SerialLabware import IDEXMXIIValve
except ImportError:
    from .mxii_valve_sl1 import IDEXMXIIValve
