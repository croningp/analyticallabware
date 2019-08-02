"""Module provide API for the remote control of the Magritek SpinSolve NMR"""
class ReplyParser:
    """Parses usefull information from the xml reply"""

    def __init__(self):
        pass
    
    def parse(self, message):
        """Parses the message into valuable XML element"""
    
    def hardware_processing(self, element):
        """Process the message if the Hardware tag is present"""
    
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
