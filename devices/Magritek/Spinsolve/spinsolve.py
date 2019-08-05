"""Module provide API for the remote control of the Magritek SpinSolve NMR"""
import logging
import queue
import socket
import threading
import time

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from socket import gaierror
from queue import Empty
from .exceptions import NMRError, ShimmingError, HardwareError
from .commands import ProtocolCommands, RequestCommands

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
        self.connected_tag = None # String to indicate if the instrument is connected, updated with HardwareRequest
    
    def parse(self, message):
        """Parses the message into valuable XML element
        
        Depending on the element tag, invokes various parsing methods
        
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

        # Main message element
        msg_element = msg_root[0]

        # Invocing specific methods for specific responds
        if msg_element.tag == self.HARDWARE_RESPONSE_TAG:
            return self.hardware_processing(msg_element)
        elif msg_element.tag == self.AVAILABLE_PROTOCOL_OPTIONS_RESPONSE_TAG:
            # TODO
            raise NotImplementedError
        elif msg_element.tag in [self.CHECK_SHIM_RESPONSE_TAG, self.QUICK_SHIM_RESPONSE_TAG, self.POWER_SHIM_RESPONSE_TAG]:
            return self.shimming_processing(msg_element)
        elif msg_element.tag == self.STATUS_TAG or msg_element.tag == self.COMPLETED_NOTIFICATION_TAG:
            return self.status_processing(msg_element)
        else:
            # TODO logging.info here
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
        self.connected_tag = element.find(".//ConnectedToHardware").text
        if self.connected_tag == "false":
            raise HardwareError("The instrument is not connected!")
        
        software_tag = element.find(".//SpinsolveSoftware").text

        spinsolve_tag = element.find(".//SpinsolveType").text
        
        # TODO logging.info here
        if software_tag[:4] != "1.15":
            # TODO logging.warning here 'Current software version {} was not tested, use at your own risk'.format(software_tag))
            pass
        
        # If the instrument is connected, setting the ready flag
        self.device_ready_flag.set()
        
        usefull_information_dict = {"Connected": f"{self.connected_tag}", "SoftwareVersion": f"{software_tag}", "InstrumentType": f"{spinsolve_tag}"}

        return usefull_information_dict
    
    def shimming_processing(self, element, line_width_threshold=1, base_width_threshold=40):
        """Process the message if the Shim tag is present
        
        Args:
            element (:obj: xml.etree.ElementTree.Element): An element containing all 
                usefull information regarding shimming response from the instrument
            line_width_threshold (int, optional): Line width threshold to judge the shimming quality
            base_width_threshold (int, optional): Base width threshold to judge the shimming quality
        
        Returns:
            True if shimming was successfull

        Raises:
            ShimmingError: If the shimming process falied
        """

        error_text = element.get("error")
        if error_text:
            # TODO logging.debug here to output full message
            raise ShimmingError(f"Shimming error: {error_text}")
        
        # TODO logging.info the shimming results
        # for child in element:
        #    self.logger.info(f'{child.tag} - {child.text}')
        
        # Obtaining shimming parameters
        line_width = round(float(element.find(".//LineWidth").text), 2)
        base_width = round(float(element.find(".//BaseWidth").text), 2)
        system_ready = element.find(".//SystemIsReady").text
        
        # Checking shimming criteria
        if line_width > line_width_threshold:
            # TODO logging.critical here
            pass
        if base_width > base_width_threshold:
            # TODO logging.critical here
            pass
        if system_ready != "true":
            # TODO logging.critical here
            pass
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

        # Valuable data from the message
        state_tag = element[0].tag
        state_elem = element[0]
        protocol_attrib = state_elem.get("protocol")

        # Checking for errors first
        error_attrib = state_elem.get("error")
        if error_attrib:
            raise NMRError(f"Error running the protocol <{protocol_attrib}>: {error_attrib}")

        status_attrib = state_elem.get("status")
        percentage_attrib = state_elem.get("percentage")
        seconds_remaining_attrib = state_elem.get("secondsRemaining")
        
        # Logging the data
        if state_tag == "State":
            # Resetting the event to False to block the incomming msg
            self.device_ready_flag.clear()
            # TODO logging.info(f'{status_attrib} the {protocol_attrib} protocol')
            if status_attrib == "Ready":
                # When device is ready, setting the event to True for the next protocol to be executed
                self.device_ready_flag.set()
                data_folder = state_elem.get("dataFolder")
                # TODO logging.info(f'the protocol {protocol_attrib} is complete, the nmr is saved in {data_folder}')
                return data_folder
        
        if state_tag == "Progress":
            # TODO logging.info(f'the protocol {protocol_attrib} is performed, {percentage_attrib}% completed, {seconds_remaining_attrib} seconds remain') 
            pass

class SpinsolveConnection:
    """Provides API for the socket connection to the Spinsolve NMR instrument"""

    def __init__(self, device_ready_flag, HOST=None, PORT=13000):
        """
        Args:
            device_ready_flag (:obj: threading.Event): an internal flag to indicate if the
                instrument is ready for next operation
            HOST (str, optional): TCP/IP address of the local host
            PORT (int, optional): TCP/IP listening port for Spinsolve software, 13000 by defualt
                must be changed in the software if necessary
        """

        # Getting the localhost IP address if not provided by instantiation
        # refer to socket module manual for details

        try:
            CURR_HOST = socket.gethostbyname(socket.getfqdn())
        except gaierror:
            CURR_HOST = socket.gethostbyname(socket.gethostname())

        # Connection parameters
        if HOST is not None:
            self.HOST = CURR_HOST
        else: 
            self.HOST = HOST
        self.PORT = PORT
        self.BUFSIZE = 8192

        # Connection object, thread and lock
        self._listener = None
        self._connection = None
        self._connection_lock = threading.Lock()

        # Response queue for inter threading commincation
        self.response_queue = queue.Queue()

    def open_connection(self):
        """Open a socket connection to the Spinsolve software"""

        if self._connection is not None:
            # TODO logging.warning open opened connection
            return

        # Creating socket
        self._connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # TODO check the blocking socket timeout
        self._connection.settimeout(0.1)

        # Connecting and spawning listening thread
        self._connection.connect((self.HOST, self.PORT))
        self._listener = threading.Thread(target=self.connection_listener, name="{}_listener".format(__name__), daemon=False)
        self._listener.start()
        # TODO logging.info here

    def connection_listener(self):
        """Checks for the new data and output it into receive buffer"""

        # TODO logging.info here
        while True:
            with self._connection_lock:
                try:
                    # Receiving data
                    chunk = self._connection.recv(self.BUFSIZE)
                    if chunk:
                        try:
                            # Checking if anything was already in the queue
                            last_reply = self.response_queue.get_nowait()
                            # TODO logging.warning here
                        except queue.Empty:
                            pass
                        try:
                            # In case the message is larger then self.BUFSIZE
                            reply = b""
                            while chunk:
                                reply += chunk
                                # TODO logging.debug here
                                chunk = self._connection.recv(self.BUFSIZE)
                        # If nothing else has been received
                        except socket.timeout:
                            pass
                        # Put the received data in the receive buffer for further processing
                        self.response_queue.put(reply)
                # When no more data is coming
                except socket.timeout:
                    pass
                except OSError:
                    # TODO logging.critical here
                    return
            # Releasing lock
            time.sleep(0.05)

    def transmit(self, msg):
        """Sends the message to the socket
        
        Args:
            msg (bytes): encoded message to be sent to the instrument
        """

        # TODO logger.debug here
        self._device_ready_flag.wait()
        # TODO logger.debug here
        with self._connection_lock:
            self._connection.send(msg)
        # TODO logger.debug here

    def receive(self):
        """Grabs the message from receive buffer and invoke parser to process it"""

        with self._connection_lock:
            # TODO logger.debug here
            try:
                reply = self.response_queue.get_nowait()
                # TODO logger.debug here
            except Empty:
                # TODO logger.critical ("Response Queue was empty, something wrong")
                pass
            
            return reply

    def close_connection(self):
        """Closes connection"""

        # TODO logging.info here
        if self._connection is not None:
            self._connection.close()
            self._connection.shutdown()
            self._listener.join(timeout=3)
        else:
            pass

    def is_connection_open(self):
        """Checks if the connection to the instrument is still alive"""
        raise NotImplementedError

class SpinsolveNMR:
    """ Python class to handle Magritek Spinsolve NMR instrument """

    def __init__(self, nmr_dir=None, address=None, port=13000):
        """
        Args:
            nmr_dir (str, optional): directory to save NMR data, will be created at 
                ./NMR_data if not provided
            address (str, optional): IP address of the local host
            host (int, optional): host for the TCP/IP connection to the Spinsolve software
        """
        self._device_ready_flag = threading.Event()
        self._parser = ReplyParser(self._device_ready_flag)
        self._connection = SpinsolveConnection(self._device_ready_flag, HOST=address, PORT=port)
        self._cmd = ProtocolCommands()
        self._req = RequestCommands()

    def connect(self):
        """Connects to the instrument"""
        self._connection.open_connection()

    def initialise(self):
        """Initialises the instrument"""
        cmd = self._req.request_hardware()
        self._connection.transmit(cmd)
        reply = self._connection.receive()
        return self._parser.parse(reply)

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

    def wait_until_ready(self):
        """Blocks until the instrument is ready"""
