"""Module provide API for the remote control of the Magritek SpinSolve NMR"""
import logging
import queue
import socket
import threading
import time

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

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

        # For shimming validation
        self.shimming_line_width_threshold = 1
        self.shimming_base_width_threshold = 40
    
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
    
    def shimming_processing(self, element):
        """Process the message if the Shim tag is present
        
        Args:
            element (:obj: xml.etree.ElementTree.Element): An element containing all 
                usefull information regarding shimming response from the instrument
        
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
        if line_width > self.shimming_line_width_threshold:
            # TODO logging.critical here
            pass
        if base_width > self.shimming_base_width_threshold:
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

    def __init__(self, HOST=None, PORT=13000):
        """
        Args:
            HOST (str, optional): TCP/IP address of the local host
            PORT (int, optional): TCP/IP listening port for Spinsolve software, 13000 by defualt
                must be changed in the software if necessary
        """

        # Getting the localhost IP address if not provided by instantiation
        # refer to socket module manual for details
        try:
            CURR_HOST = socket.gethostbyname(socket.getfqdn())
        except socket.gaierror:
            CURR_HOST = socket.gethostbyname(socket.gethostname())

        # Connection parameters
        if HOST is not None:
            self.HOST = HOST
        else: 
            self.HOST = CURR_HOST
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
        with self._connection_lock:
            self._connection.send(msg)
        # TODO logger.debug here

    def receive(self):
        """Grabs the message from receive buffer"""

        # TODO logger.debug here
        try:
            reply = self.response_queue.get(timeout=1)
            self.response_queue.task_done()
            # TODO logger.debug here
        except queue.Empty:
            # TODO logger.critical ("Response Queue was empty, something wrong")
            raise
            
        return reply

    def close_connection(self):
        """Closes connection"""

        # TODO logging.info here
        if self._connection is not None:
            self._connection.close()
            self._listener.join(timeout=3)
        else:
            # TODO logging.warning here
            pass

    def is_connection_open(self):
        """Checks if the connection to the instrument is still alive"""
        # TODO
        raise NotImplementedError

class SpinsolveNMR:
    """ Python class to handle Magritek Spinsolve NMR instrument """

    def __init__(self, spinsolve_options_path, address=None, port=13000, auto_connect=True):
        """
        Args:
            address (str, optional): IP address of the local host
            host (int, optional): host for the TCP/IP connection to the Spinsolve software
            auto_connect (bool, optional): If you need to connect to the instrument immediately
                after instantiation
        """

        # Flag for check the instrument status
        self._device_ready_flag = threading.Event()

        # Instantiating submodules
        self._parser = ReplyParser(self._device_ready_flag)
        self._connection = SpinsolveConnection(HOST=address, PORT=port)
        self.cmd = ProtocolCommands(spinsolve_options_path)
        self.req_cmd = RequestCommands()

        if auto_connect:
            self.connect()
            self.initialise()

    def __del__(self):
        self._connection.close_connection()

    def connect(self):
        """Connects to the instrument"""

        self._connection.open_connection()
        # TODO logging.info here

    def send_message(self, msg):
        """Sends the message to the instrument"""

        # TODO logger.debug here
        self._device_ready_flag.wait()
        self._connection.transmit(msg)
        # TODO logger.debug here

    def receive_reply(self, parse=True):
        """Receives the reply from the intrument and parses it if necessary"""

        # TODO logging.debug here
        reply = self._connection.receive()
        if parse:
            reply = self._parser.parse(reply)
        return reply

    def initialise(self):
        """Initialises the instrument by sending HardwareRequest"""

        cmd = self.req_cmd.request_hardware()
        self._connection.transmit(cmd)
        return self.receive_reply()

    def is_instrument_ready(self):
        """Checks if the instrument is ready for the next command"""

        if self._parser.connected_tag == "true" and self._device_ready_flag.is_set():
            return True
        else:
            return False

    def shim(self, option="CheckShimRequest"):
        """Initialise shimming protocol
        
        Consider checking <Spinsolve>.cmd.get_protocol(<Spinsolve>.cmd.SHIM_PROTOCOL) for available options

        Args:
            option (str, optinal): A name of the instrument shimming method
        """

        cmd = self.req_cmd.request_shim(option)
        self.send_message(cmd)
        return self.receive_reply()

    def shim_on_sample(self, reference_peak, option="LockAndCalibrateOnly", *, line_width_threshold=1, base_width_threshold=40):
        """Initialise shimming on sample protocol

        Consider checking <Spinsolve>.cmd.get_protocol(<Spinsolve>.cmd.SHIM_ON_SAMPLE_PROTOCOL) for available options
        
        Args:
            reference_peak (float): A reference peak to shim and calibrate on
            option (str, optinla): A name of the instrument shimming method
            line_width_threshold (int, optional): Spectrum line width at 50%, should be below 1 
                for good quality spectrums
            base_width_threshold (int, optional): Spectrum line width at 0.55%, should be below 40 
                for good quality spectrums
        """

        self._parser.shimming_line_width_threshold = line_width_threshold
        self._parser.shimming_base_width_threshold = base_width_threshold
        cmd = self.cmd.shim_on_sample(reference_peak, option)
        self.send_message(cmd)
        return self.receive_reply()

    def user_folder(self, data_path, data_folder_method="TimeStamp"):
        """Indicate the path and the method for saving NMR data

        Args:
            data_folder_path (str): Valid path to save the spectral data
            data_folder_method (str, optinal): One of three methods according to the manual:
                'UserFolder' - Data is saved directly in the provided path
                'TimeStamp' (default) - Data is saved in newly created folder in format
                    yyyymmddhhmmss in the provided path
                'TimeStampTree' - Data is saved in the newly created folders in format
                    yyyy/mm/dd/hh/mm/ss in the provided path

        Returns:
            bool: True if successfull
        """

        cmd = self.req_cmd.set_data_folder(data_path, data_folder_method)
        self.send_message(cmd)
        return True

    def user_data(self, data=None, *, solvent, sample):
        """Loads the user data to be saved with the NMR data
        
        Args:
            data (dict, optinal): Any user data that needs to be saved with the spectal
                data in form of {'key': 'value'}.
            solvent (str): Name of the solvent to be saved with the spectral data
            sample (str): Sample name to be saved with the spectral data

        Returns:
            bool: True if successfull
        """
        if data is not None:
            user_data_cmd = self.req_cmd.set_user_data(data)
            self.send_message(user_data_cmd)
        experiment_data_cmd = self.req_cmd.set_experiment_data(solvent=solvent, sample=sample)
        self.send_message(experiment_data_cmd)
        return True

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
