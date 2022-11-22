"""
Python module to parse the xml messages received from Spinsolve NMR.
"""
import logging

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from .exceptions import RequestError, HardwareError, ShimmingError, NMRError
from .constants import (
    CURRENT_SPINSOLVE_VERSION,
    USER_DATA_TAG,
)


class ReplyParser:
    """Parses usefull information from the xml reply"""

    ### Response tags for easier handling ###
    HARDWARE_RESPONSE_TAG = "HardwareResponse"
    AVAILABLE_PROTOCOL_OPTIONS_RESPONSE_TAG = "AvailableProtocolOptionsResponse"
    STATUS_TAG = "StatusNotification"
    ESTIMATE_DURATION_RESPONSE_TAG = "EstimateDurationResponse"
    CHECK_SHIM_RESPONSE_TAG = "CheckShimResponse"
    QUICK_SHIM_RESPONSE_TAG = "QuickShimResponse"
    POWER_SHIM_RESPONSE_TAG = "PowerShimResponse"
    COMPLETED_NOTIFICATION_TAG = "CompletedNotificationType"
    GET_RESPONSE_TAG = "GetResponse"

    def __init__(self, device_ready_flag, data_folder_queue):
        """
        Args:
            device_ready_flag (:obj: "threading.Event"): The threading event indicating
                that the instrument is ready for the next commands
            data_folder_queue (:obj: "queue.Queue"): A queue object to store the data folder information
                for subsequent access with Spectrum class
        """

        self.device_ready_flag = device_ready_flag
        self.data_folder_queue = data_folder_queue
        self.connected_tag = None  # String to indicate if the instrument is connected, updated with HardwareRequest

        self.logger = logging.getLogger("spinsolve.parser")

        # For shimming validation
        self.shimming_line_width_threshold = 1
        self.shimming_base_width_threshold = 40

    def parse(self, message):
        """Parses the message into valuable XML element

        Depending on the element tag, invokes various parsing methods

        Args:
            message (bytes): The message received from the instrument
        """

        self.logger.debug("Obtained the message: \n%s", message)

        # Checking the obtained message
        try:
            msg_root = ET.fromstring(message)
        except ParseError:
            self.logger.error(
                "ParseError: invalid XML message received, check the full message \n <%s>",
                message.decode(),
            )
            raise ParseError(
                "Invalid XML message received from the instrument, please check the log for the full message"
            ) from None
        if msg_root.tag != "Message" or len(msg_root) > 1:
            self.logger.error(
                "ParseError: incorrect message received, check the full message \n <%s>",
                message.decode(),
            )
            raise ParseError(
                "Incorrect message received from the instrument, please check the log for the full message"
            )

        # Main message element
        msg_element = msg_root[0]

        # Invoking specific methods for specific responds
        if msg_element.tag == self.HARDWARE_RESPONSE_TAG:
            return self.hardware_processing(msg_element)
        elif msg_element.tag == self.AVAILABLE_PROTOCOL_OPTIONS_RESPONSE_TAG:
            return message
        elif msg_element.tag in [
            self.CHECK_SHIM_RESPONSE_TAG,
            self.QUICK_SHIM_RESPONSE_TAG,
            self.POWER_SHIM_RESPONSE_TAG,
        ]:
            return self.shimming_processing(msg_element)
        elif (
            msg_element.tag == self.STATUS_TAG
            or msg_element.tag == self.COMPLETED_NOTIFICATION_TAG
        ):
            return self.status_processing(msg_element)
        elif msg_element.tag == self.ESTIMATE_DURATION_RESPONSE_TAG:
            return self.estimate_duration_processing(msg_element)
        elif msg_element.tag == self.GET_RESPONSE_TAG:
            return self.data_response_processing(msg_element)
        else:
            self.logger.info(
                "No specific parser requested, returning full decoded message"
            )
            return message.decode()

    def hardware_processing(self, element):
        """Process the message if the Hardware tag is present

        Args:
            element (:obj: xml.etree.ElementTree.Element): An element containing all
                usefull information regarding Hardware response from the instrument

        Returns:
            dict: Dictionary with usefull hardware information

        Raises:
            HardwareError: In case the instrument is not connected
        """

        # Checking if the instrument is physically connected
        self.logger.debug("Parsing message with <%s> tag", element.tag)
        self.connected_tag = element.find(".//ConnectedToHardware").text
        if self.connected_tag == "false":
            raise HardwareError("The instrument is not connected!")

        software_tag = element.find(".//SpinsolveSoftware").text

        spinsolve_tag = element.find(".//SpinsolveType").text

        self.logger.info(
            "The %s NMR instrument is successfully connected \nRunning under %s Spinsolve software version",
            spinsolve_tag,
            software_tag,
        )
        if software_tag[:6] != CURRENT_SPINSOLVE_VERSION:
            self.logger.warning(
                "The current software version <%s> was not tested, please update or use at your own risk",
                software_tag,
            )

        # If the instrument is connected, setting the ready flag
        self.device_ready_flag.set()

        usefull_information_dict = {
            "Connected": f"{self.connected_tag}",
            "SoftwareVersion": f"{software_tag}",
            "InstrumentType": f"{spinsolve_tag}",
        }

        return usefull_information_dict

    def data_response_processing(self, element):
        """Process the message if the user parameters response is present.

        Args:
            element (:obj: xml.etree.ElementTree.Element): An element containing
                all usefull information regarding Hardware response from the
                instrument.

        Returns:
            Dict: Dictionary with user/experiment specific parameter, e.g.
                userdata, solvent or sample.
        """

        self.logger.debug("Parsing message with <%s> tag", element.tag)
        # messages with GetResponse have only one child
        if len(element) > 1:
            raise RequestError(
                "Returned response for user data is incorrect, \
check log files for details!"
            )

        chelement = element[0]

        # special case for user data
        if chelement.tag == USER_DATA_TAG:
            return {
                subel.attrib["key"]: subel.attrib["value"]
                for subel in chelement  # iterating over subelements
            }

        return chelement.text

    def shimming_processing(self, element):
        """Process the message if the Shim tag is present

        Args:
            element (:obj: xml.etree.ElementTree.Element): An element containing all
                usefull information regarding shimming response from the instrument

        Returns:
            True if shimming was successfull

        Raises:
            ShimmingError: If the shimming process failed
        """

        self.logger.debug("Parsing message with <%s> tag", element.tag)

        self.device_ready_flag.set()

        error_text = element.get("error")
        if error_text:
            self.logger.error(
                "ShimmingError: check the error message below\
\n%s",
                error_text,
            )
            if (
                self.shimming_base_width_threshold == 40
                and self.shimming_line_width_threshold == 1
            ):
                # only raise error if default line widths were used as the
                # reference point
                raise ShimmingError(f"Shimming error: {error_text}")

        for child in element:
            self.logger.info("%s - %s", child.tag, child.text)

        # Obtaining shimming parameters
        line_width = round(float(element.find(".//LineWidth").text), 2)
        base_width = round(float(element.find(".//BaseWidth").text), 2)
        system_ready = element.find(".//SystemIsReady").text

        # Checking shimming criteria
        if line_width > self.shimming_line_width_threshold:
            self.logger.critical(
                "Shimming line width <%.2f> is above requested threshold <%.2f>, consider running another shimming method",
                line_width,
                self.shimming_line_width_threshold,
            )
        if base_width > self.shimming_base_width_threshold:
            self.logger.critical(
                "Shimming line width <%.2f> is above requested threshold <%.2f>, consider running another shimming method",
                line_width,
                self.shimming_line_width_threshold,
            )
        if system_ready != "true":
            self.logger.critical(
                "System is not ready after shimming, consider running another shimming method"
            )
            return False
        else:
            return True

    def status_processing(self, element):
        """Process the message if the Status tag is present

        Logs the incoming messages and manages device_ready_flag

        Args:
            element (:obj: xml.etree.ElementTree.Element): An element containing all
                usefull information regarding status response from the instrument

        Returns:
            str: String containing the path to the saved NMR data

        Raises:
            NMRError: in case of the protocol errors
        """

        self.logger.debug("Parsing message with <%s> tag", element.tag)

        # Valuable data from the message
        state_tag = element[0].tag
        state_elem = element[0]
        protocol_attrib = state_elem.get("protocol")

        # Checking for errors first
        error_attrib = state_elem.get("error")

        # No error is actually raised, since the instrument
        # Continues with protocol execution even if an error was returned
        # TODO add an option to handle the error and stop the execution
        if error_attrib:
            self.logger.error(
                "NMRError: <%s>, check the log for the full message", error_attrib
            )
            # raise NMRError(f"Error running the protocol <{protocol_attrib}>: {error_attrib}")

        status_attrib = state_elem.get("status")
        percentage_attrib = state_elem.get("percentage")
        seconds_remaining_attrib = state_elem.get("secondsRemaining")

        # Logging the data
        if state_tag == "State":
            # Resetting the event to False to block the incoming msg
            if status_attrib == "Running":
                self.logger.debug("Device in operation, blocking the incoming messages")
            self.device_ready_flag.clear()
            self.logger.info("%s the <%s> protocol", status_attrib, protocol_attrib)
            if status_attrib == "Ready":
                # When device is ready, setting the event to True for the next protocol to be executed
                # Delay the flag setting for the SHIM protocol
                if protocol_attrib != "SHIM":
                    self.device_ready_flag.set()
                data_folder = state_elem.get("dataFolder")
                self.logger.info(
                    "The protocol <%s> is complete, the NMR data is saved in <%s>",
                    protocol_attrib,
                    data_folder,
                )
                self.data_folder_queue.put(data_folder)
                return data_folder

        if state_tag == "Progress":
            self.logger.info(
                "The protocol <%s> is performing, %s%% completed, %s seconds remain",
                protocol_attrib,
                percentage_attrib,
                seconds_remaining_attrib,
            )

    def estimate_duration_processing(self, element):
        """Process the message if protocol duration was requested

        Args:
            element (:obj: xml.etree.ElementTree.Element): An element containing all
                usefull information regarding duration estimation from the instrument

        Returns:
            int: Estimated duration for the requested protocol in seconds

        Raises:
            RequestError: In case the instrument returns an error attribute
        """

        self.logger.debug("Parsing message with <%s> tag", element.tag)

        error_text = element.get("error")
        if error_text:
            self.logger.error("RequestError: check the log for the full message")
            raise RequestError(f"Duration request error: {error_text}")

        duration_in_seconds = element.get("durationInSeconds")

        return int(duration_in_seconds)
