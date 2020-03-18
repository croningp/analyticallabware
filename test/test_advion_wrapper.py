import advion_wrapper as av
from advion_wrapper.enums import ErrorCode
from advion_wrapper.errors import AdvionCMSError
from os.path import dirname, join

instrument = av.SimulatedInstrument(dirname(__file__))
inst_ctrl = av.InstrumentController(instrument)
script_dir = dirname(__file__)
manager = av.AcquisitionManager(
    join(script_dir, "default.method"),
    join(script_dir, "negativeESI.ion"),
    join(script_dir, "defaultNegative.tune"),
    "abcd",
    script_dir,
)


def test_start_controller():
    inst_ctrl.start_controller()


def test_standby():
    try:
        inst_ctrl.standby()
    except AdvionCMSError as e:
        if e.args[0] != ErrorCode.CMS_STANDBY_NOT_ALLOWED:
            raise e


def test_get_state():
    print(manager.state)
