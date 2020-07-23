import threading
import time

from SerialLabware.serial_labware import SerialDevice, command
from SerialLabware import IKARCTDigital


class IDEXMXIIValve(SerialDevice):
    """Two-position IDEX MX Series II HPLC valve."""
    def __init__(self, *params, **kwargs):
        super().__init__(*params, **kwargs)
        self.cmd = {
            "MOVE_TO_1":    "P01\r",
            "MOVE_TO_2":    "P02\r",
            "READ_STATUS":  "S00\r"}
        self.status_codes = {
            44: "Data CRC error",
            55: "Data integrity error",
            66: "Valve positioning error",
            77: "Valve configuration error or command error",
            88: "Non-volatile memory error",
            99: "Valve cannot be homed"}

    @property
    @command
    def is_connected(self) -> bool:
        try:
            self.send_message(self.cmd["READ_STATUS"], get_return=True)
        except:
            return False
        return True

    @property
    @command
    def status(self) -> int:
        status = self.send_message(self.cmd["READ_STATUS"], get_return=True)
        # Look up error code; status is okay if no error.
        self.logger.debug("IDEX valve :: OK - status = %s (%s).", status,
                          self.status_codes.get(status, "OK"))
        return int(status.strip())

    def is_ready(self) -> bool:
        return self.status not in self.status_codes

    @property
    def current_position(self):
        status = self.status
        if status not in self.status_codes:
            # status is position
            return status
        else:
            # status is error code
            error = self.status_codes[status]
            raise Exception(f"IDEX valve :: Error {status} ({error}).")

    @command
    def move_home(self):
        """Move valve to home position.
        This is supposed to correspond to the idle position of the valve, i.e.
        any injected sample will go to the sample loop and HPLC eluent is
        route to the waste."""
        value = self.move_to_position(1)
        return value

    @command
    def move_to_position(self, position: int):
        """Move value to specified position.
        Position 1 corresponds to the home position, i.e. injected sample goes
        to the loop and eluent to waste.
        Position 2 corresponds usually represents the beginning of acquisition
        where sample in the loop goes to analysis.

        Args:
            position (int): Valve position to move to."""
        # do nothing if already in requested position
        if position == self.current_position:
            return position

        if position == 1:
            value = self.send_message(self.cmd["MOVE_TO_1"], get_return=True)
        elif position == 2:
            value = self.send_message(self.cmd["MOVE_TO_2"], get_return=True)
        # TODO: Implement multi-position valves.
        else:
            raise ValueError("Position has to be one of 1 or 2.")
        return value

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