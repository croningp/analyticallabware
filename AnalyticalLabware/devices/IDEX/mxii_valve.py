from SerialLabware.controllers import AbstractDistributionValve
from SerialLabware.controllers import LabDeviceCommands

class IDEXMXIIValveCommands(LabDeviceCommands):
    MOVE_TO_1 = {"name": "P01"}
    MOVE_TO_2 = {"name": "P02"}

class IDEXMXIIValve(AbstractDistributionValve):
    """Two-position IDEX MX Series II HPLC valve."""
    def __init__(self, *params, **kwargs):
        super().__init__(*params, **kwargs)
        self.cmd = IDEXMXIIValveCommands
        self.command_terminator = "\r"
        self.reply_terminator = "\r"

    def initialise_device(self):
        super().initialise_device()

    def is_connected(self):
        pass

    def is_ready(self):
        pass

    def move_home(self):
        """Move valve to home position.
        This is supposed to correspond to the idle position of the valve, i.e.
        any injected sample will go to the sample loop and HPLC eluent is
        route to the waste."""
        self.send_message(self.cmd.MOVE_TO_1)
        self.receive_reply()

    def move_to_position(self, position: int):
        """Move value to specified position.
        Position 1 corresponds to the home position, i.e. injected sample goes
        to the loop and eluent to waste.
        Position 2 corresponds usually represents the beginning of acquisition
        where sample in the loop goes to analysis."""
        if position == 1:
            self.send_message(self.cmd.MOVE_TO_1)
        elif position == 2:
            self.send_message(self.cmd.MOVE_TO_2)
        # TODO: Implement multi-position valves.
        else:
            raise ValueError("Position has to be one of 1 or 2.")
        self.receive_reply()