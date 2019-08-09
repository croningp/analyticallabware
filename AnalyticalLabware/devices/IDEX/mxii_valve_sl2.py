import threading
import time

from SerialLabware.controllers import AbstractDistributionValve
from SerialLabware.controllers import LabDeviceCommands
from SerialLabware.exceptions import SLDeviceError

class IDEXMXIIValveCommands(LabDeviceCommands):
    MOVE_TO_1 = {"name": "P01"}
    MOVE_TO_2 = {"name": "P02"}
    READ_STATUS = {"name": "S00", "parse": {"type": int}}
    STATUS_CODES = {44: "Data CRC error",
                    55: "Data integrity error",
                    66: "Valve positioning error",
                    77: "Valve configuration error or command error",
                    88: "Non-volatile memory error",
                    99: "Valve cannot be homed"}


class IDEXMXIIValve(AbstractDistributionValve):
    """Two-position IDEX MX Series II HPLC valve."""
    def __init__(self, *params, **kwargs):
        super().__init__(*params, **kwargs)
        self.cmd = IDEXMXIIValveCommands
        self.command_terminator = "\r"
        self.reply_terminator = "\r"

    def initialise_device(self):
        super().initialise_device()

    def is_connected(self) -> bool:
        try:
            self.send_message(self.cmd.READ_STATUS)
            self.receive_reply()
        except:
            return False
        return True

    @property
    def status(self) -> int:
        self.send_message(self.cmd.READ_STATUS)
        reply = self.receive_reply()
        # Look up error code; status is okay if no error.
        self.logger.debug("IDEX valve :: OK - status = %s (%s).", reply,
                          self.cmd.STATUS_CODES.get(reply, "OK"))
        return reply

    def is_ready(self) -> bool:
        return self.status not in self.cmd.STATUS_CODES

    @property
    def current_position(self):
        status = self.status
        if status not in self.cmd.STATUS_CODES:
            # status is position
            return status
        else:
            # status is error code
            error = self.cmd.STATUS_CODES[status]
            raise SLDeviceError(f"IDEX valve :: Error {status} ({error}).",
                                status, self.cmd.STATUS_CODES[status])

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
        where sample in the loop goes to analysis.

        Args:
            position (int): Valve position to move to."""
        if position == 1:
            self.send_message(self.cmd.MOVE_TO_1)
        elif position == 2:
            self.send_message(self.cmd.MOVE_TO_2)
        # TODO: Implement multi-position valves.
        else:
            raise ValueError("Position has to be one of 1 or 2.")
        self.receive_reply()

    def sample(self, seconds: int, sync=False):
        """Move valve to position 2 for `seconds`, then switch back to 1.

        Args:
            seconds (int): Number of seconds to stay in position 2.
            sync (bool): Whether to block the thread during sampling.
        """
        if sync:
            self.move_to_position(2)
            time.sleep(seconds)
            self.move_to_position(1)
        else:
            self.move_to_position(2)
            threading.Timer(seconds, lambda: self.move_to_position(1)).start()