"""This module provides access and use of the Spinsolve NMR remote commands"""


def load_commands_from_file(protocol_options_file=None):
    """Loads NMR protocol commands and options from XML file.

    """
def load_commands_from_device(device=None):
    """Loads command list from the connected device"""

class ProtocolCommands:
    """Provides API for accessing NMR commands"""

    def generate_command(self, protocol_and_options):
        """Generates XML tree for the commnad
        """
        
    def get_command(self, protocol_name):
        """Obtains the command from XML with all available options
        """

class RequestCommands:
    """contains misc commands for NMR operation"""