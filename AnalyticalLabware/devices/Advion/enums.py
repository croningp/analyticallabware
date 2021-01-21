from enum import IntEnum


class AcquisitionState(IntEnum):
    Prevented = 0
    Ready = 1
    Waiting = 2
    Underway = 3
    Paused = 4


class InstrumentState(IntEnum):
    Fault = 0
    Initializing = 1
    Vented = 2
    PumpingDown = 3
    Standby = 4
    Operate = 5


class OperationMode(IntEnum):
    Idle = 0
    Tuning = 1
    AutoTuning = 2
    Acquiring = 3


class SourceType(IntEnum):
    NO_SOURCE = 0
    ESI_SOURCE = 1
    APCI_SOURCE = 2
    DART_SOURCE = 3
    VAPCI_SOURCE = 4


class InstrumentSwitch(IntEnum):
    PositiveIon = 0
    FullNebulizationGas = 1
    StandbyNebulizationGas = 2
    SourceGas = 3
    CapillaryHeater = 4
    SourceGasHeater = 5
    TransferLineHeater = 6
    PositiveCalibrant = 7
    NegativeCalibrant = 8
    UsingHelium = 9
    NumInstrumentSwitches = 10


class ErrorCode(IntEnum):
    CMS_OK = 0

    # USB
    CMS_NO_USB_CONNECTION = 1
    CMS_USB_CONNECTED = 2
    CMS_LOST_USB_CONNECTION = 3

    # Instrument condition
    CMS_HIVOLT_OFF_BAD_VACUUM = 10
    CMS_STANDBY_IONSOURCE_REMOVED = 11
    CMS_STANDBY_IONSOURCE_UNPLUGGED = 12
    CMS_VACUUM_TOO_LOW = 13
    CMS_VACUUM_OK = 14

    # Acquisition errors
    CMS_ALREADY_ACQUIRING = 20
    CMS_ALREADY_PAUSED = 21
    CMS_NOT_ACQUIRING = 22
    CMS_NOT_PAUSED = 23
    CMS_NOT_WRITING_DATA = 24
    CMS_WRITE_FAILED = 25
    CMS_SWITCHING_NOT_ALLOWED = 26
    CMS_SEGMENTS_NOT_ALLOWED = 27
    CMS_SCAN_MODE_OUT_OF_RANGE = 28

    # Tune scanning errors
    CMS_TUNE_INDEX_OUT_OF_RANGE = 30

    # Instrument controller errors
    CMS_CONTROLLER_ALREADY_STARTED = 40
    CMS_CONTROLLER_NOT_STARTED = 41
    CMS_INSTRUMENT_IS_OPERATING = 42
    CMS_PUMP_ALREADY_ON = 43
    CMS_OPERATING_NOT_ALLOWED = 44
    CMS_STANDBY_NOT_ALLOWED = 45
    CMS_INSTRUMENT_NOT_OPERATING = 46
    CMS_PARSING_FAILED = 47
    CMS_INDEX_OUT_OF_RANGE = 48
    CMS_INSTRUMENT_TYPE_UNKNOWN = 49

    # AutoTune and Calibration Errors
    CMS_ALREADY_AUTO_TUNING = 50
    CMS_CANCELLED = 51
    CMS_PEAKS_NOT_FOUND = 52
    CMS_COULD_NOT_AUTOTUNE = 53
    CMS_NOT_ENOUGH_TUNING_MASSES = 54

    # Acquisition limitations
    CMS_RANGE_SCAN_TIME_TOO_LOW = 60
    CMS_RANGE_SCAN_TIME_TOO_HIGH = 61
    CMS_SIM_DWELL_TIME_TOO_LOW = 62
    CMS_SIM_DWELL_TIME_TOO_HIGH = 63
    CMS_SCAN_SPEED_TOO_HIGH = 64
    CMS_SIM_NO_MASSES = 65

    # Data processing
    CMS_DATA_READ_FAIL = 70
    CMS_INVALID_FILTER_PARAMS = 71

    # General
    CMS_PARAMETER_OUT_OF_RANGE = 80
    CMS_DATASET_FOLDER_LOCKED = 81
    CMS_PATH_TOO_LONG = 82


class DataErrorCode(IntEnum):
    ADVIONDATA_OK = 0
    ADVIONDATA_FILE_OPEN_FAILED = 1
    ADVIONDATA_FILE_WRITE_FAILED = 2
    ADVIONDATA_OUT_OF_MEMORY = 3
    ADVIONDATA_CREATE_DATX_FAILED = 4
    ADVIONDATA_OPEN_DATX_FAILED = 5
    ADVIONDATA_CHANNEL_NOT_DEFINED = 6
    ADVIONDATA_AUX_FILE_NOT_DEFINED = 7
    ADVIONDATA_DATA_VERSION_TOO_HIGH = 8
    ADVIONDATA_DATA_PARAMETER_IS_NULL = 9
    ADVIONDATA_PARSING_FAILED = 10
    ADVIONDATA_INDEX_OUT_OF_RANGE = 11
    ADVIONDATA_PARAMETER_OUT_OF_RANGE = 12
    ADVIONDATA_NO_SPECTRA = 13
    ADVIONDATA_CHANNEL_HEADER_CLOSED = 14
    ADVIONDATA_DATASET_FOLDER_LOCKED = 15
    ADVIONDATA_PATH_TOO_LONG = 16


class NumberReadback(IntEnum):
    PiraniPressureRB = 0  # Chamber pressure, in Torr.
    TurboSpeedRB = 1  # Internal pump speed, in percent of maximum.
    CapillaryTemperatureRB = 2  # Capillary temperature, in degrees C.
    SourceGasTemperatureRB = 3  # Ion source gas temperature, in degrees C.
    TransferLineTemperatureRB = (
        4  # Ion source transfer line temperature, in degrees C, for vAPCI source.
    )
    CapillaryVoltageRB = 5  # Capillary voltage, in V.
    SourceVoltageRB = 6  # Ion source voltage, in V.
    ExtractionElectrodeRB = 7  # Extraction electrode voltage, in V.
    HexapoleBiasRB = 8  # Hexapole bias voltage, in V.
    PoleBiasRB = 9  # Pole bias voltage, in V.
    HexapoleRFRB = 10  # Hexapole RF voltage, in V.
    RectifiedRFRB = 11  # Rectified RF voltage, in V.
    ESIVoltageRB = 12  # ESI ion source voltage, in kV.
    APCICurrentRB = 13  # APCI ion source current, in uA.
    DetectorVoltageRB = 14  # Detector voltage, in kV.
    DynodeVoltageRB = 15  # Dynode voltage, in kV.
    DC1RB = 16  # DC 1 voltage, in V.
    DC2RB = 17  # DC 2 voltage, in V.

    NumNumberReadbacks = (
        18  # Utility definition - number of real number read-backs for CMS.
    )


class BinaryReadback(IntEnum):
    # Read-backs only
    CommunicationOK = 0  # USB communication is working.
    PumpSpeedOK = 1  # Internal pump speed is sufficient.
    VacuumOK = 2  # Chamber vacuum is sufficient.
    SafetySwitchOK = 3  # Ion source is seated in the housing.

    FIASignal = 4  # Flow Injection Analysis (FIA) contact is closed.
    DigitalInput1 = 5  # Digital input 1 is closed.
    DigitalInput2 = 6  # Digital input 2 is closed.
    DigitalInput3 = 7  # Digital input 3 is closed.
    DigitalInput4 = 8  # Digital input 4 is closed.

    # Set internally only
    PumpPowerRB = 9  # Internal pump is turned on.
    HighVoltagesRB = 10  # High voltages are being applied to the instrument.

    # Set via public API
    PositiveIonRB = 11  # Ion source polarity is positive.
    FullNebulizationGasRB = 12  # Nebulization gas is flowing at full level.
    StandbyNebulizationGasRB = 13  # Nebulization gas is flowing at standby level.
    SourceGasRB = 14  # Ion source gas is flowing.
    CapillaryHeaterRB = 15  # Capillary heater is on.
    SourceGasHeaterRB = 16  # Ion source gas heater is on.
    TransferLineHeaterRB = (
        17  # Ion source transfer line heater is on, for vAPCI source.
    )
    PositiveCalibrantRB = 18  # Positive (left) calibrant vial is flowing.
    NegativeCalibrantRB = 19  # Negative (right) calibrant vial is flowing.
    UsingHeliumRB = 20  # Source gas is helium.

    NumBinaryReadbacks = 21  # Utility definition - number of binary read-backs for CMS.
