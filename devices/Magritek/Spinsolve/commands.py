"""This module provides access and use of the Spinsolve NMR remote commands"""


def load_commands_from_file(protocol_options_file=None):
    """Loads NMR protocol commands and options from XML file.

    """
    # If the xml wasn't provided check for it in the standard Magritek folder
    # where it is created by default, <current_user>/Documents/Magritek/Spinsolve
    if protocol_options_file is None:
        current_user = os.getlogin()
        spinsolve_folder = os.path.join("C:", "Users", current_user, "Documents", "Magritek", "Spinsolve")
        spinsolve_commands_file = os.path.join(spinsolve_folder, "ProtocolOptions.xml")
        try:
            commands_tree = ET.parse(spinsolve_commands_file)
        except FileNotFoundError:
            raise ProtocolError("The ProtocolOptions file wasn't found in the original folder \n Please check or supply the file manually") from None
    else:
        spinsolve_commands_file = protocol_options_file
        try:
            commands_tree = ET.parse(spinsolve_commands_file)
        except ParseError:
            raise ProtocolError("Supply file is not a valid XML document") from None
    commands_root = commands_tree.getroot()
    protocols = {element.get("protocol"):element for element in commands_root.iter("Protocol")}
    return protocols

def load_commands_from_device(device=None):
    """Loads command list from the connected device"""
    raise NotImplementedError

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