import inspect
import ctypes

from .enums import ErrorCode, DataErrorCode


def check_return(return_code, adviondata: bool = False):
    if adviondata:
        # ErrorCode from AdvionData
        if return_code != DataErrorCode.ADVIONDATA_OK:
            raise AdvionCMSError(DataErrorCode(return_code))
    elif return_code != ErrorCode.CMS_OK:
        # ErrorCode from AdvionCMS
        raise AdvionCMSError(ErrorCode(return_code))


class AdvionCMSError(Exception):
    pass
