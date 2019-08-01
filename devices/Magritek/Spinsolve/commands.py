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

    def __init__(self, protocols_path=None, device=None):
        """Initialiser for the protocol commands
        """

        # Obtaining the file path
        protocol_options_file = os.path.join(protocols_path, 'ProtocolOptions.xml')

        #TODO If device is supplied load the commands from it
        if device is not None:
            self._protocols = load_commands_from_device(device)
        else:
            self._protocols = load_commands_from_file(protocol_options_file)
    def generate_command(self, protocol_and_options):
        """Generates XML tree for the commnad
        """

        # Checking supplied argument types
        if not isinstance(protocol_and_options, tuple) or len(protocol_and_options) != 2:
            raise TypeError('Supplied argument must be a tuple with exactly two items: protocol name and protocol options as dict')
        try:
            full_command = self.get_command(protocol_and_options[0]) # Loading the full command dictionary for future validation
        except KeyError:
            raise ProtocolError('Supplied protocol <{}> is not a valid protocol'.format(protocol_and_options[0])) from None
        try:
            for key, value in protocol_and_options[1].items():
                if value not in full_command[1].get(key):
                    raise ProtocolOptionsError('Supplied value <{}> is not valid for the option <{}>'.format(value, key))
        except AttributeError:
            raise TypeError('Supplied options should be packed into dictionary') from None
        except ProtocolOptionsError:
            raise
        except (KeyError, TypeError):
            raise ProtocolOptionsError('Supplied option <{}> is not valid for the selected protocol <{}>'.format(key, protocol_and_options[0])) from None
        # Creating an empty bytes object to write the future XML message
        msg = BytesIO()
        # First element of the XML message
        msg_root = ET.Element("Message")
        # First subelement of the message root as <"command"/> 
        # with attributes as "command_option_key"="command_option_value"
        msg_root_command = ET.SubElement(msg_root, "Protocol", {"protocol": f"{protocol_and_options[0]}"})
        # If additional options required
        for key, value in protocol_and_options[1].items():
            _ = ET.SubElement(msg_root_command, "Option", {"name": f"{key}", "value": f"{value}"})
        # Growing a message XML tree with the <Message /> root
        msg_tree = ET.ElementTree(msg_root)
        # Writing the message tree to msg object
        msg_tree.write(msg, encoding='utf-8', xml_declaration=True)

        return msg.getvalue()
        
    def get_command(self, protocol_name):
        """Obtains the command from XML with all available options
        """

class RequestCommands:
    """contains misc commands for NMR operation"""