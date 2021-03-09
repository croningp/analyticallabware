from ctypes import c_double, c_int, c_long, byref
from comtypes import BSTR, CoInitialize, CoUninitialize
from comtypes.client import CreateObject

try:
    from .enums import AcquisitionStatus, BusyStatus, InstrumentMode, GeneralError
except (ImportError, SystemError):
    from enums import AcquisitionStatus, BusyStatus, InstrumentMode, GeneralError


class BrukerMS:
    def __init__(self, rpc=False):
        """
        Args:
            rpc (bool): Whether otofControl will be accessed using
                a remote procedure call (RPC) system
        """
        self.handle = _BrukerMS(rpc)

    def __enter__(self):
        self.handle.init_ms_connection()
        return self.handle

    def __exit__(self, type, value, traceback):
        self.handle.close()


class _BrukerMS:
    def __init__(self, rpc=False):
        self.rpc = rpc
        CoInitialize()
        self.handle = CreateObject("BDal.OtofControl.RemoteCustom")

    def close(self):
        self.exit_ms_connection()

    def init_ms_connection(self):
        return GeneralError.check_return(self.handle.InitMSConnection(0))

    def exit_ms_connection(self):
        return GeneralError.check_return(self.handle.ExitMSConnection(0))

    def show_application(self):
        return GeneralError.check_return(self.handle.ShowApplication)

    def get_busy_status(self) -> BusyStatus:
        status = c_int()
        GeneralError.check_return(self.handle.CheckBusyStatus(byref(status)))
        return status.value if self.rpc else BusyStatus(status.value)

    def get_last_error_code(self, clear_error_flag=False) -> int:
        return self.handle.GetLastErrorCode(c_long(clear_error_flag))

    def get_last_error_text(self, clear_error_flag=False) -> str:
        buff = BSTR()
        self.handle.GetLastErrorText(c_long(clear_error_flag), byref(buff))
        return buff.value

    def get_instrument_mode(self) -> InstrumentMode:
        mode = c_int()
        GeneralError.check_return(self.handle.GetInstrumentMode(byref(mode)))
        return mode.value if self.rpc else InstrumentMode(mode.value)

    def set_instrument_mode(self, mode: InstrumentMode):
        GeneralError.check_return(self.handle.SetInstrumentMode(int(mode)))

    def reset_chromatogram(self):
        GeneralError.check_return(self.handle.ResetChromatogram(0))

    def load_method(self, method_path: str):
        GeneralError.check_return(self.handle.LoadMethod(method_path, 0))

    def save_method(self, method_path: str):
        GeneralError.check_return(self.handle.SaveMethod(method_path, 0))

    def get_acquisition_status(self) -> AcquisitionStatus:
        status = c_int()
        GeneralError.check_return(self.handle.GetAcquisitionStatus(byref(status)))
        return status.value if self.rpc else AcquisitionStatus(status.value)

    def prepare_acquisition(self, data_path: str):
        GeneralError.check_return(self.handle.PrepareAcquisition(data_path))

    def start_acquisition(self, delay_time: float):
        GeneralError.check_return(self.handle.StartAcquisition(0, c_double(delay_time)))

    def set_acquisition_pause(self, pause: int):
        GeneralError.check_return(self.handle.SetAcquisitionPause(pause))

    def stop_acquisition(self, delay_time: float):
        GeneralError.check_return(self.handle.StopAcquisition(0, c_double(delay_time)))

    def start_postprocessing(self, data_path: str):
        GeneralError.check_return(self.handle.StartPostprocessing(data_path))

    def load_calibration(self, analysis_path: str):
        GeneralError.check_return(self.handle.LoadCalibration(analysis_path, 0))


# TODO:
# [id(3)] long GetAboutText([out] BSTR* AboutText
# );
#
# [id(8)] long SetUser(    BSTR UserName,
# BSTR Password,
# long UserMode
# );
#
# [id(20)] long LoadCalibration(  BSTR szAnalysisPath,
# long lOption
# );
