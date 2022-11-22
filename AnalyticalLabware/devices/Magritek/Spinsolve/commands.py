"""This module provides access and use of the Spinsolve NMR remote commands"""

import os
import logging
from io import BytesIO

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from .utils.exceptions import ProtocolError, ProtocolOptionsError, RequestError
from .utils.constants import (
    SAMPLE_TAG,
    SOLVENT_TAG,
    USER_DATA_TAG,
)


def load_commands_from_file(protocols_path=None):
    """Loads NMR protocol commands and options from XML file.

    If the file is not provided, will search for it in the default Margitek folder

    Args:
        protocol_options_file (str, optional): An external file containing XML commands
            for Spinsolve NMR. Usually 'ProtocolOptions.xml'

    Returns:
        dict: A dictionary containing protocol name as a key and XML element as a value
            For example:

            {'1D PROTON': <Element 'Protocol'>, '1D CARBON': <Element 'Protocol'>}

    Raises:
        ProtocolError: In case the XML command file wasn't found or the supplied file is not
            a valid XML file
    """
    # If the xml wasn't provided check for it in the standard Magritek folder
    # where it is created by default, <current_user>/Documents/Magritek/Spinsolve
    if protocols_path is None:
        current_user = os.getlogin()
        spinsolve_folder = os.path.join(
            "C:\\", "Users", current_user, "Documents", "Magritek", "Spinsolve"
        )
        spinsolve_commands_file = os.path.join(spinsolve_folder, "ProtocolOptions.xml")
        try:
            commands_tree = ET.parse(spinsolve_commands_file)
        except FileNotFoundError:
            raise ProtocolError(
                "The ProtocolOptions file wasn't found in the original folder \n Please check or supply the file manually"
            ) from None
    else:
        protocol_options_file = os.path.join(protocols_path, "ProtocolOptions.xml")
        try:
            commands_tree = ET.parse(protocol_options_file)
        except ParseError:
            raise ProtocolError("Supply file is not a valid XML document") from None
    commands_root = commands_tree.getroot()
    protocols = {
        element.get("protocol"): element for element in commands_root.iter("Protocol")
    }
    return protocols


def load_commands_from_device(device_message):
    """Loads command list from the connected device

    Args:
        device_message (bytes): A message from the instrument containing all possible
            protocols and their options

    Returns:
        dict: A dictionary containing protocol name as a key and XML element as a value
            For example:

            {'1D PROTON': <Element 'Protocol'>, '1D CARBON': <Element 'Protocol'>}
    """

    commands_root = ET.fromstring(device_message)
    protocols = {
        element.get("protocol"): element for element in commands_root.iter("Protocol")
    }
    return protocols


class ProtocolCommands:
    """Provides API for accessing NMR commands"""

    # Short list of most commonly used NMR protocols for easier maintenance

    PROTON = "1D PROTON"
    CARBON = "1D CARBON"
    FLUORINE = "1D FLUORINE"

    PROTON_EXTENDED = "1D EXTENDED+"
    CARBON_EXTENDED = "1D CARBON+"
    FLUORINE_EXTENDED = "1D FLUORINE+"

    SHIM_ON_SAMPLE_PROTOCOL = "SHIM 1H SAMPLE"
    SHIM_PROTOCOL = "SHIM"

    # Although this is a request and should be in RequestCommands
    # The XML message syntax is similar to "Start protocol"
    ESTIMATE_DURATION_REQUEST = "EstimateDurationRequest"

    def __init__(self, protocols_path=None):
        """Initialiser for the protocol commands

        Loads the commands from the supplied file or directly from the NMR
        instrument and stores them as an internal dictionary. Also provides
        methods to access specific commands and generate valid XML strings
        from supplied command tuple

        Args:
            protocol_path (str, optional): Optional path to the location of the
                ProtocolOptions.xml file
            device (Any, optional): Reserved for future use to load command list from the
                instrument
        """

        self.logger = logging.getLogger("spinsolve.commandsapi")

        self._protocols = load_commands_from_file(protocols_path)

    def __iter__(self):
        """Yields every protocol name"""

        for protocol in self._protocols.keys():
            yield protocol

    def generate_command(self, protocol_and_options, custom_tag="Start"):
        """Generates XML message for the command to execute the requested protocol with requested options

        Args:
            protocol_and_options (tuple): Tuple with protocol name and dictionary with protocol
                option names and values. Example: ('1D PROTON', {'Scan': 'QuickScan'})

        Returns:
            bytes: encoded to 'utf-8' string containing the valid XML message to be sent to the
                NMR instrument to start the requested protocol

        Raises:
            ProtocolError: If the supplied protocol is not a valid command
            ProtocolOptionsError: If the supplied option or its value are not validated in a protocol
                command

        Example:
            >>> generate_command(
                    ('valid_protocol_name',
                    {'valid_protocol_option_name': 'valid_protocol_option_value'}))
            b'<?xml version=\'1.0\' encoding=\'utf-8\'?>
                <Message>
                    <Start protocol="valid_protocol_name">
                        <Option name="valid_protocol_option_name" value="valid_protocol_option_value" />
                    </Protocol>
                </Message>'
        """

        # Checking supplied argument types
        self.logger.debug(
            "Checking the supplied attributes for the protocol <%s> - <%s>",
            protocol_and_options[0],
            protocol_and_options[1],
        )
        if (
            not isinstance(protocol_and_options, tuple)
            or len(protocol_and_options) != 2
        ):
            raise TypeError(
                "Supplied argument must be a tuple with exactly two items: protocol name and protocol options as dict"
            )
        try:
            full_command = self.get_protocol(
                protocol_and_options[0]
            )  # Loading the full command dictionary for future validation
        except KeyError:
            raise ProtocolError(
                "Supplied protocol <{}> is not a valid protocol".format(
                    protocol_and_options[0]
                )
            ) from None
        try:
            for key, value in protocol_and_options[1].items():
                # Casting the value to string, as all stored values are strings
                value = str(value)
                # If the value list is empty but the value is expected, e.g. SHIM 1H SAMPLE - SampleReference
                # All value checks should be performed when the method called
                if value not in full_command[1].get(key) and full_command[1].get(key):
                    raise ProtocolOptionsError(
                        "Supplied value <{}> is not valid for the option <{}>".format(
                            value, key
                        )
                    )
        except AttributeError:
            raise TypeError(
                "Supplied options should be packed into dictionary"
            ) from None
        except ProtocolOptionsError:
            raise
        except (KeyError, TypeError):
            raise ProtocolOptionsError(
                "Supplied option <{}> is not valid for the selected protocol <{}>".format(
                    key, protocol_and_options[0]
                )
            ) from None

        # Creating an empty bytes object to write the future XML message
        msg = BytesIO()
        # First element of the XML message
        msg_root = ET.Element("Message")
        # First subelement of the message root as <"command"/>
        # with attributes as "command_option_key"="command_option_value"
        msg_root_command = ET.SubElement(
            msg_root, custom_tag, {"protocol": f"{protocol_and_options[0]}"}
        )
        # If additional options required
        for key, value in protocol_and_options[1].items():
            _ = ET.SubElement(
                msg_root_command, "Option", {"name": f"{key}", "value": f"{value}"}
            )
        # Growing a message XML tree with the <Message /> root
        msg_tree = ET.ElementTree(msg_root)
        # Writing the message tree to msg object
        msg_tree.write(msg, encoding="utf-8", xml_declaration=True)

        self.logger.debug("Message built: <%s>", msg.getvalue())

        return msg.getvalue()

    def get_protocol(self, protocol_name):
        """Obtains the command from XML with all available options

        Args:
            protocol_name (str): Valid protocol name

        Returns:
            tuple: Containing protocol name and protocol options with all possible
                values packed as dictionary, as required by generate_command method

        Raises:
            ProtocolError
        """

        protocol_options = {}
        try:
            for option_element in self._protocols[protocol_name].findall(".//Option"):
                option = option_element.get("name")
                option_values = []
                for value_element in option_element:
                    if value_element.text is not None:
                        option_values.append(value_element.text)
                protocol_options[option] = option_values
        except KeyError:
            raise ProtocolError(
                "Supplied protocol <{}> is not a valid protocol".format(protocol_name)
            ) from None
        return (protocol_name, protocol_options)

    def reload_commands(self, data):
        """Reload the protocols from the supplied data

        Args:
            data (bytes): A valid XML file, usually acquired from the instrument
        """

        self.logger.debug("Requested protocols update")
        self._protocols = load_commands_from_device(data)
        self.logger.info("Protocols dictionary updated")

    ### For easier access the following properties are added ###

    def shim_on_sample(self, reference_peak, option):
        """Generates the command for shimming on sample

        Args:
            reference_peak (float): Largest peak of the supplied sample used for shimming
                and scale calibration
            option (str): Shimming method
        """
        # Validation the supplied peak value
        if isinstance(reference_peak, float):
            reference_peak = str(round(reference_peak, 2))
        else:
            raise ProtocolOptionsError("Supplied reference peak must be float!")

        return self.generate_command(
            (
                self.SHIM_ON_SAMPLE_PROTOCOL,
                {"SampleReference": f"{reference_peak}", "Shim": f"{option}"},
            )
        )

    @property
    def proton_protocol(self):
        """Gets protocol name and available options for simple 1D Proton experiment"""
        return self.get_protocol("1D PROTON")

    @property
    def proton_extended_protocol(self):
        """Gets protocol name and available options for extended 1D Proton experiment"""
        return self.get_protocol("1D EXTENDED+")

    @property
    def carbon_protocol(self):
        """Gets protocol name and available options for simple 1D Carbon experiment"""
        return self.get_protocol("1D CARBON")

    @property
    def carbon_extended_protocol(self):
        """Gets protocol name and available options for extended 1D Carbon experiment"""
        return self.get_protocol("1D CARBON+")

    @property
    def fluorine_protocol(self):
        """Gets protocol name and available options for simple 1D Fluorine experiment"""
        return self.get_protocol("1D FLUORINE")

    @property
    def fluorine_extended_protocol(self):
        """Gets protocol name and available options for extended 1D Fluorine experiment"""
        return self.get_protocol("1D FLUORINE+")

    @property
    def reaction_monitoring_protocol(self):
        """Gets protocol name and available options for reaction monitoring experiment"""
        return self.get_protocol("RM")


class RequestCommands:
    """Contains misc commands for NMR operation"""

    ### List of supported requests for easier maintenance ###
    HARDWARE_REQUEST = "HardwareRequest"
    AVAILABLE_PROTOCOL_OPTIONS_REQUEST = "AvailableProtocolOptionsRequest"
    GET_REQUEST = "GetRequest"
    CHECK_SHIM_REQUEST = "CheckShimRequest"
    QUICK_SHIM_REQUEST = "QuickShimRequest"
    POWER_SHIM_REQUEST = "PowerShimRequest"
    ABORT_REQUEST = "Abort"

    # Tags for setting user specific information
    SET_TAG = "Set"
    DATA_FOLDER_TAG = "DataFolder"
    DATA_FOLDER_METHODS = ["UserFolder", "TimeStamp", "TimeStampTree"]

    def __init__(self):

        self.logger = logging.getLogger("spinsolve.requestsapi")

    def generate_request(self, tag, options=None):
        """Generate the XML request message

        The syntax for the request commands is slightly different from
        protocol commands, so this separate method is present

        Args:
            tag (str): The main message tag for the request command
            options (dict, optional): Request options to be supplied to the request message

        Returns:
            bytes: encoded to 'utf-8' string containing the valid XML request message
            to be sent to the NMR instrument
        """

        self.logger.debug(
            "Generating request from the supplied attributes: tag - <%s>; options - <%s>",
            tag,
            options,
        )

        # Creating an empty bytes object to write the future XML message
        msg = BytesIO()
        # First element of the XML message
        msg_root = ET.Element("Message")
        # First subelement of the message root as <"command"/>
        # with attributes as "command_option_key"="command_option_value"
        msg_root_element = ET.SubElement(msg_root, f"{tag}")
        # Special case - UserData
        if options is not None and USER_DATA_TAG in options:
            # Removing the appended key
            options.pop(USER_DATA_TAG)
            # Creating new subelement
            user_data_subelement = ET.SubElement(msg_root_element, USER_DATA_TAG)
            for key, value in options.items():
                subelem = ET.SubElement(
                    user_data_subelement, "Data", {"key": f"{key}", "value": f"{value}"}
                )
        elif options is not None:
            for key, value in options.items():
                subelem = ET.SubElement(msg_root_element, f"{key}")
                subelem.text = value
        # Growing a message XML tree with the <Message /> root
        msg_tree = ET.ElementTree(msg_root)
        # Writing the message tree to msg object
        msg_tree.write(msg, encoding="utf-8", xml_declaration=True)

        self.logger.debug("Request generated: <%s>", msg.getvalue())

        return msg.getvalue()

    def request_shim(self, shim_request_option):
        """Returns the message for shimming the instrument"""

        if shim_request_option not in [
            self.CHECK_SHIM_REQUEST,
            self.POWER_SHIM_REQUEST,
            self.QUICK_SHIM_REQUEST,
        ]:
            raise RequestError("Supplied shimming option is not valid")

        return self.generate_request(shim_request_option)

    def request_hardware(self):
        """Returns the message for the hardware request"""

        return self.generate_request(self.HARDWARE_REQUEST)

    def request_available_protocol_options(self):
        """Returns the message to request full list of available protocols and their options"""

        return self.generate_request(self.AVAILABLE_PROTOCOL_OPTIONS_REQUEST)

    def set_solvent_data(self, solvent):
        """Returns the message to set the solvent data.

        Args:
            solvent (str): Solvent name to be saved with the spectrum data.
        """

        return self.generate_request(self.SET_TAG, {SOLVENT_TAG: f"{solvent}"})

    def set_sample_data(self, sample):
        """Returns the message to set the solvent data.

        Args:
            sample (str): Sample name to be saved with the spectrum data.
        """

        return self.generate_request(self.SET_TAG, {SAMPLE_TAG: f"{sample}"})

    def set_data_folder(self, data_folder_path, data_folder_method):
        """Returns the message to set the data saving method and path

        Args:
            data_folder_path (str): valid path to save the spectral data
            data_folder_method (str): one of three methods according to the manual:
                'UserFolder' - data is saved directly in the provided path
                'TimeStamp' - data is saved in newly created folder in format
                    yyyymmddhhmmss in the provided path
                'TimeStampTree' - data is saved in the newly created folders in format
                    yyyy/mm/dd/hh/mm/ss in the provided path
        """
        # Just to avoid errors from the device
        if data_folder_method not in self.DATA_FOLDER_METHODS:
            raise RequestError("Please use valid data folder method")

        return self.generate_request(
            self.DATA_FOLDER_TAG, {data_folder_method: data_folder_path}
        )

    def set_user_data(self, user_data):
        """Returns the message for setting the user data

        Args:
            user_data (dict): Dictionary contaning user specific data, will be saved
                in the "acq.par" file together with spectral data
        """
        # appending "UserData" key to allow custom message creation
        user_data.update({USER_DATA_TAG: ""})
        return self.generate_request(self.SET_TAG, user_data)

    def abort(self):
        """Returns the message to abort the current operation"""

        return self.generate_request(self.ABORT_REQUEST)

    def get_user_data(self):
        """
        Returns the message for querying the user data from the instrument.
        """

        return self.generate_request(self.GET_REQUEST, {USER_DATA_TAG: ""})

    def get_solvent(self):
        """
        Returns the message for querying the solvent data from the instrument.
        """

        return self.generate_request(self.GET_REQUEST, {SOLVENT_TAG: ""})

    def get_sample(self):
        """
        Returns the message for querying the sample data from the instrument.
        """

        return self.generate_request(self.GET_REQUEST, {SAMPLE_TAG: ""})
