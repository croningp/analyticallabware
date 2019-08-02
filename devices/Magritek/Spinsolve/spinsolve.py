"""Module provide API for the remote control of the Magritek SpinSolve NMR"""

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from socket import gaierror

from .exceptions import NMRError, ShimmingError, HardwareError

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
    
    def __init__(self, device_ready_flag):
        """
        Args:
            device_ready_flag (:obj: "threading.Event"): The threading event indicating
                that the instrument is ready for the next commands
        """
        self.device_ready_flag = device_ready_flag
    
    def parse(self, message):
        """Parses the message into valuable XML element
        
        Args:
            message (bytes): The message received from the instrument
        """

        # Checking the obtained message
        try:
            msg_root = ET.fromstring(message)
        except ParseError:
            # TODO logging.debug here
            raise ParseError("Invalid XML message received from the instrument, please check the log for the full message") from None
        if msg_root.tag != "Message" or len(msg_root) > 1:
            # TODO logging.debug here
            raise ParseError("Incorrect message received from the instrument, please check the log for the full message")

        msg_element = msg_root[0]

        # Invocing specific methods for specific responds
        if msg_element.tag == self.HARDWARE_RESPONSE_TAG:
            self.hardware_processing(msg_element)
        elif msg_element.tag == self.AVAILABLE_PROTOCOL_OPTIONS_RESPONSE_TAG:
            raise NotImplementedError
        elif msg_element.tag in [self.CHECK_SHIM_RESPONSE_TAG, self.QUICK_SHIM_RESPONSE_TAG, self.POWER_SHIM_RESPONSE_TAG]:
            self.shimming_processing(msg_element)
        elif msg_element.tag == self.STATUS_TAG or msg_element.tag == self.COMPLETED_NOTIFICATION_TAG:
            self.status_processing(msg_element)
        else:
            # TODO logging.info here
            pass
    
    def hardware_processing(self, element):
        """Process the message if the Hardware tag is present
        
        Args:
            element (:obj: xml.etree.ElementTree.Element): an element containing all 
                usefull information regarding Hardware response from the instrument

        Returns:
            dict: dictionary with usefull hardware information

        Raises:
            HardwareError: in case the instrument is not connected
        """

        # Checking if the instrument is physically connected
        connected_tag = element.find(".//ConnectedToHardware").text
        if connected_tag == "false":
            raise HardwareError("The instrument is not connected!")
        
        software_tag = main_element.find(".//SpinsolveSoftware").text

        spinsolve_tag = main_element.find(".//SpinsolveType").text
        
        # TODO logging.info here
        if software_tag[:4] != "1.13":
            # TODO logging.warning here 'Current software version {} was not tested, use at your own risk'.format(software_tag))
            pass
        
        usefull_information_dict = {"Connected": f"{connected_tag}", "SoftwareVersion": f"{software_tag}", "InstrumentType": f"{spinsolve_tag}"}

        return usefull_information_dict
    
    def shimming_processing(self, element):
        """Process the message if the Shim tag is present"""
        
    
    def status_processing(self, element):
        """Process the message if the Status tag is present"""

class SpinsolveConnection:
    """Provides API for the socket connection to the instrument"""

    def open_connection(self):
        """Open a socket connection to the Spinsolve software"""

    def connection_listener(self):
        """Checks for the new data and output it into receive buffer"""

    def transmit(self, message):
        """Sends the message to the socket"""

    def receive(self):
        """Grabs the message from receive buffer and invoke parser to process it"""

    def close_connection(self):
        """Closes connection"""

    def is_connection_open(self):
        """Checks if the connection to the instrument is still alive"""

class SpinsolveNMR:
    """ Python class to handle Magritek Spinsolve NMR instrument """

    def __init__(self):
        pass

    def connect(self):
        """Connects to the instrument"""

    def initialise(self):
        """Initialises the instrument"""

    def is_instrument_ready(self):
        """Checks if the instrument is ready for the next command"""

    def shim(self):
        """Initialise shimming protocol"""

    def shim_on_sample(self, reference_peak):
        """Initialise shimming on sample protocol"""

    def user_folder(self, path, method):
        """Indicate the path and the method for saving NMR data"""

    def user_data(self, data=None, *, solvent, sample):
        """Loads the user data to be saved with the NMR data"""

    def get_duration(self, protocol):
        """Requests for an approximate duration of a specific protocol"""

    def proton(self, options):
        """Initialise simple 1D Proton experiment"""
    
    def proton_extended(self, options):
        """Initialise extended 1D Proton experiment"""

    def carbon(self, options):
        """Initialise simple 1D Carbon experiment"""

    def carbon_extended(self, options):
        """Initialise extended 1D Carbon experiment"""

    def fluorine(self, options):
        """Initialise simple 1D Fluorine experiment"""

    def fluorine_extended(self, options):
        """Initialise extended 1D Fluorine experiment"""
