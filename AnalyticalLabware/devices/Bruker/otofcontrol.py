from ctypes import c_buffer, c_double, c_int, c_long, pointer
from comtypes import CoInitialize, CoUninitialize
from comtypes.client import CreateObject
from .enums import AcquisitionStatus, BusyStatus, InstrumentMode, GeneralError


class BrukerMS:
    def __init__(self):
        CoInitialize()
        self.handle = CreateObject("BDal.OtofControl.RemoteCustom")

    def close(self):
        self.handle.ExitMSConnection()
        self.handle = None
        CoUninitialize()

    def init_ms_connection(self):
        return GeneralError.check_return(self.handle.InitMSConnection(0))

    def exit_ms_connnection(self):
        return GeneralError.check_return(self.handle.ExitMSConnection(0))

    def show_application(self):
        return GeneralError.check_return(self.handle.ShowApplication)

    @property
    def busy_status(self) -> BusyStatus:
        status = pointer(c_int())
        GeneralError.check_return(self.handle.CheckBusyStatus(status))
        return BusyStatus(status.contents.value)

    def get_last_error_code(self, clear_error_flag=False) -> int:
        return self.handle.GetLastErrorCode(c_long(clear_error_flag))

    def get_last_error_text(self, clear_error_flag=False) -> str:
        buff = pointer(c_buffer(0, 128))
        GeneralError.check_return(
            self.handle.GetLastErrorText(c_long(clear_error_flag), buff)
        )
        return buff.contents.value.decode()

    @property
    def instrument_mode(self) -> InstrumentMode:
        mode = pointer(c_int())
        GeneralError.check_return(self.handle.GetInstrumentMode(mode))
        return InstrumentMode(mode.contents.value)

    @instrument_mode.setter
    def instrument_mode(self, mode: InstrumentMode):
        GeneralError.check_return(self.handle.SetInstrumentMode(mode.value))

    def reset_chromatogram(self):
        GeneralError.check_return(self.handle.ResetChromatogram(0))

    def load_method(self, method_path: str):
        GeneralError.check_return(self.handle.LoadMethod(method_path.encode(), 0))

    def save_method(self, method_path: str):
        GeneralError.check_return(self.handle.SaveMethod(method_path.encode(), 0))

    @property
    def acquisition_status(self) -> AcquisitionStatus:
        status = pointer(c_int())
        GeneralError.check_return(self.handle.GetAcquisitionStatus(status))
        return AcquisitionStatus(status.contents.value)

    def prepare_acquisiton(self, data_path: str):
        GeneralError.check_return(self.handle.PrepareAcquisiton(data_path.encode()))

    def start_acquisition(self, delay_time: float):
        GeneralError.check_return(self.handle.StartAcquisition(0, c_double(delay_time)))

    def set_acquisition_pause(self, pause: int):
        GeneralError.check_return(self.handle.SetAcquisitionPause(pause))

    def stop_acquisition(self, delay_time: float):
        GeneralError.check_return(self.handle.StopAcquisition(0, c_double(delay_time)))

    def start_postprocessing(self, data_path: str):
        GeneralError.check_return(self.handle.StartPostprocessing(data_path.encode()))

    def load_calibration(self, analysis_path: str):
        GeneralError.check_return(
            self.handle.LoadCalibration(analysis_path.encode(), 0)
        )


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
