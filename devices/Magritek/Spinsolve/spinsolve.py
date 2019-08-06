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
            self.logger.error("ParseError: invalid XML message received, check the full message \n <%s>", message.decode())
            raise ParseError("Invalid XML message received from the instrument, please check the log for the full message") from None
        if msg_root.tag != "Message" or len(msg_root) > 1:
            self.logger.error("ParseError: incorrect message received, check the full message \n <%s>", message.decode())
            raise ParseError("Incorrect message received from the instrument, please check the log for the full message")

        # Main message element
        msg_element = msg_root[0]

        # Invocing specific methods for specific responds
        if msg_element.tag == self.HARDWARE_RESPONSE_TAG:
            return self.hardware_processing(msg_element)
        elif msg_element.tag == self.AVAILABLE_PROTOCOL_OPTIONS_RESPONSE_TAG:
            return message()
        elif msg_element.tag in [self.CHECK_SHIM_RESPONSE_TAG, self.QUICK_SHIM_RESPONSE_TAG, self.POWER_SHIM_RESPONSE_TAG]:
            return self.shimming_processing(msg_element)
        elif msg_element.tag == self.STATUS_TAG or msg_element.tag == self.COMPLETED_NOTIFICATION_TAG:
            return self.status_processing(msg_element)
        else:
            self.logger.info("No specific parser requested, returning full decoded message")
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
        
        self.logger.info("The %s NMR instrument is successfully connected \nRunning under %s Spinsolve software version", spinsolve_tag, software_tag)
        if software_tag[:4] != "1.15":
            self.logger.warning("The current software version <%s> was not tested, please update or use at your own risk", software_tag)
        
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
        
        self.logger.debug("Parsing message with <%s> tag", element.tag)

        error_text = element.get("error")
        if error_text:
            self.logger.error("ShimmingError: check the log for the full message")
            raise ShimmingError(f"Shimming error: {error_text}")
        
        for child in element:
            self.logger.info("%s - %s", child.tag, child.text)
        
        # Obtaining shimming parameters
        line_width = round(float(element.find(".//LineWidth").text), 2)
        base_width = round(float(element.find(".//BaseWidth").text), 2)
        system_ready = element.find(".//SystemIsReady").text
        
        # Checking shimming criteria
        if line_width > self.shimming_line_width_threshold:
            self.logger.critical("Shimming line width <%s> is above requested threshold <%s>, consider running another shimming method", line_width, self.shimming_line_width_threshold)
        if base_width > self.shimming_base_width_threshold:
            self.logger.critical("Shimming line width <%s> is above requested threshold <%s>, consider running another shimming method", line_width, self.shimming_line_width_threshold)
        if system_ready != "true":
            self.logger.critical("System is not ready after shimming, consider running another shimming method")
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
        if error_attrib:
            self.logger.error("NMRError: <%s>, check the log for the full message", error_attrib)
            raise NMRError(f"Error running the protocol <{protocol_attrib}>: {error_attrib}")

        status_attrib = state_elem.get("status")
        percentage_attrib = state_elem.get("percentage")
        seconds_remaining_attrib = state_elem.get("secondsRemaining")
        
        # Logging the data
        if state_tag == "State":
            # Resetting the event to False to block the incomming msg
            self.device_ready_flag.clear()
            self.logger.info("%s the <%s> protocol", status_attrib, protocol_attrib)
            if status_attrib == "Ready":
                # When device is ready, setting the event to True for the next protocol to be executed
                self.device_ready_flag.set()
                data_folder = state_elem.get("dataFolder")
                self.logger.info("The protocol <%s> is complete, the NMR data is saved in <%s>", protocol_attrib, data_folder)
                return data_folder
        
        if state_tag == "Progress":
            self.logger.info("The protocol <%s> is performing, %s%% completed, %s seconds remain", protocol_attrib, percentage_attrib, seconds_remaining_attrib)

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

        # Connection object, thread, lock and disconnection request tag
        self._listener = None
        self._connection = None
        self._connection_lock = threading.Lock()
        self._connection_close_requested = threading.Event()

        # Response queue for inter threading commincation
        self.response_queue = queue.Queue()

        self.logger = logging.getLogger("spinsolve.connection")

    def open_connection(self):
        """Open a socket connection to the Spinsolve software"""

        if self._connection is not None:
            self.logger.warning("You are trying to open connection that is already open")
            return

        # Creating socket
        self._connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._connection.settimeout(0.1)

        # Connecting and spawning listening thread
        self._connection.connect((self.HOST, self.PORT))
        self.logger.debug("Connection at %s:%s is opened", self.HOST, self.PORT)
        self._listener = threading.Thread(target=self.connection_listener, name="{}_listener".format(__name__), daemon=False)
        self._listener.start()
        self.logger.info("Connection created")

    def connection_listener(self):
        """Checks for the new data and output it into receive buffer"""

        self.logger.info("Connection listener thread is starting")

        while True:
            if self._connection_close_requested.is_set():
                self._connection_close_requested.clear()
                self.logger.info("Connection listener finished")
                return
            with self._connection_lock:
                try:
                    # Receiving data
                    chunk = self._connection.recv(self.BUFSIZE)
                    if chunk:
                        try:
                            # Checking if anything was already in the queue
                            last_reply = self.response_queue.get_nowait()
                            self.logger.warning("Unprocessed message in queue: \n%s", last_reply.decode())
                        except queue.Empty:
                            pass
                        try:
                            # In case the message is larger then self.BUFSIZE
                            reply = b""
                            while chunk:
                                reply += chunk
                                chunk = self._connection.recv(self.BUFSIZE)
                                self.logger.debug("Keep receiving the big message")
                        # If nothing else has been received
                        except socket.timeout:
                            pass
                        # Put the received data in the receive buffer for further processing
                        self.response_queue.put(reply)
                        self.logger.debug("Message added to the response queue")
                # When no more data is coming
                except socket.timeout:
                    pass
            # Releasing lock
            time.sleep(0.05)
        
    def transmit(self, msg):
        """Sends the message to the socket
        
        Args:
            msg (bytes): encoded message to be sent to the instrument
        """

        with self._connection_lock:
            self.logger.debug("Sending the message")
            self._connection.send(msg)
            self.logger.debug("Message sent")

    def receive(self):
        """Grabs the message from receive buffer"""

        self.logger.debug("Receiving the message from the responce queue")
        try:
            reply = self.response_queue.get(timeout=1)
            self.response_queue.task_done()
            self.logger.debug("Message obtained from the queue")
        except queue.Empty:
            self.logger.error("Queue was empty")
            raise
            
        return reply

    def close_connection(self):
        """Closes connection"""

        self.logger.debug("Socket connection closure requested")
        self._connection_close_requested.set()
        if self._listener is not None and self._listener.is_alive():
            self._listener.join(timeout=3)
        if self._connection is not None:
            self._connection.close()
            self._connection = None # To avaiable subsequent calls to open_connection after connection was once closed
            self._connection_close_requested.clear()
            self.logger.info("Socket connection closed")
        else:
            self.logger.warning("You are trying to close nonexistent connection")

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

        self.logger = logging.getLogger("spinsolve")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            "%(asctime)s ; %(module)s ; %(name)s ; %(message)s")
        ch.setFormatter(console_formatter)
        self.logger.addHandler(ch)

        if auto_connect:
            self.connect()
            self.initialise()

    def __del__(self):
        self.disconnect()

    def connect(self):
        """Connects to the instrument"""

        self.logger.debug("Connection requested")
        self._connection.open_connection()

    def disconnect(self):
        """Closes the socket connection"""

        self.logger.info("Request to close the connection received")
        self._connection.close_connection()
        self.logger.info("The instrument is disconnected")

    def send_message(self, msg):
        """Sends the message to the instrument"""

        if self._parser.connected_tag != "true":
            raise HardwareError("The instrument is not connected, check the Spinsolve software")
        self.logger.debug("Waiting for the device to be ready")
        self._device_ready_flag.wait()
        self.logger.debug("Sending the message \n%s", msg)
        self._connection.transmit(msg)
        self.logger.debug("Message sent")

    def receive_reply(self, parse=True):
        """Receives the reply from the intrument and parses it if necessary"""

        self.logger.debug("Reply requested from the connection")
        reply = self._connection.receive()
        self.logger.debug("Reply received")
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

    def load_commands(self):
        """Requests the available commands from the instrument"""

        cmd = self.req_cmd.request_available_protocol_options()
        self.send_message(cmd)
        reply = self.receive_reply()
        self.cmd.reload_commands(reply)
        self.logger.info("Commands updated, see available protocols \n <%s>", list(self.cmd._protocols.keys())) # pylint: disable=protected-access

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
        raise NotImplementedError

    def proton(self, option="QuickScan"):
        """Initialise simple 1D Proton experiment"""

        cmd = self.cmd.generate_command((self.cmd.PROTON, {"Scan": f"{option}"}))
        self.send_message(cmd)
        return self.receive_reply()
    
    def proton_extended(self, options):
        """Initialise extended 1D Proton experiment"""

        cmd = self.cmd.generate_command((self.cmd.PROTON_EXTENDED, options))
        self.send_message(cmd)
        return self.receive_reply()

    def carbon(self, options=None):
        """Initialise simple 1D Carbon experiment"""

        if options is None:
            options = {"Number": "128", "RepetitionTime": "2"}
        cmd = self.cmd.generate_command((self.cmd.CARBON, options))
        self.send_message(cmd)
        return self.receive_reply()

    def carbon_extended(self, options):
        """Initialise extended 1D Carbon experiment"""

        cmd = self.cmd.generate_command((self.cmd.CARBON_EXTENDED, options))
        self.send_message(cmd)
        return self.receive_reply()

    def fluorine(self, option="QuickScan"):
        """Initialise simple 1D Fluorine experiment"""

        cmd = self.cmd.generate_command((self.cmd.FLUORINE, option))
        self.send_message(cmd)
        return self.receive_reply()

    def fluorine_extended(self, options):
        """Initialise extended 1D Fluorine experiment"""

        cmd = self.cmd.generate_command((self.cmd.FLUORINE_EXTENDED, options))
        self.send_message(cmd)
        return self.receive_reply()

    def wait_until_ready(self):
        """Blocks until the instrument is ready"""

        self._device_ready_flag.wait()

    def calibrate(self, reference_peak, option="LockAndCalibrateOnly"):
        """Performs shimming on sample protocol"""
        
        self.logger.warning("DEPRECATION WARNING: use shim_on_sample() method instead")
        return self.shim_on_sample(reference_peak, option)
