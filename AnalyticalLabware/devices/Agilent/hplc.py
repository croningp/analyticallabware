"""
Module to provide API for the remote control of the Agilent HPLC systems.

HPLCController sends commands to Chemstation software via a command file.
Answers are received via reply file. On the Chemstation side, a custom
Macro monitors the command file, executes commands and writes to the reply file.
Each command is given a number (cmd_no) to keep track of which commands have
been processed.

.. moduleauthor:: Alexander Hammer, Hessam Mehr
"""

import time
import os
import logging

from .chromatogram import AgilentHPLCChromatogram, TIME_FORMAT

# maximum command number
MAX_CMD_NO = 255

# Default Chemstation data directory
DEFAULT_DATA_DIR = r"C:\Chem32\1\Data"

# Default Chemstation methods directory
DEFAULT_METHOD_DIR = 'C:\\Chem32\\1\\Methods\\'

# Commands sent to the Chemstation Macro
# See https://www.agilent.com/cs/library/usermanuals/Public/MACROS.PDF
RESET_COUNTER_CMD = "last_cmd_no = 0"
GET_STATUS_CMD = "response$ = AcqStatus$"
SLEEP_CMD = "Sleep {seconds}"
STANDBY_CMD = "Standby"
STOP_MACRO_CMD = "Stop"
PREPRUN_CMD = "PrepRun"
LAMP_ON_CMD = "LampAll ON"
LAMP_OFF_CMD = "LampAll OFF"
PUMP_ON_CMD = "PumpAll ON"
PUMP_OFF_CMD = "PumpAll OFF"
GET_METHOD_CMD = "response$ = _MethFile$"
SWITCH_METHOD_CMD = 'LoadMethod "{method_dir}", "{method_name}.M"'
START_METHOD_CMD = "StartMethod"
RUN_METHOD_CMD = 'RunMethod "{data_dir}",,"{experiment_name}_{timestamp}"'
STOP_METHOD_CMD = "StopMethod"

class HPLCController:
    """
    Class to control Agilent HPLC systems via Chemstation Macros.
    """
    def __init__(
            self,
            comm_dir: str,
            data_dir: str = None,
            cmd_file: str = "cmd",
            reply_file: str = "reply",
            logger=None
        ):
        """
        Initialize HPLC controller.
        comm_dir: Name of directory for communication.
        data_dir: path to where chemstation will save the data.
                    If None, data will be saved in default folder Chem32\\1\\Data
        cmd_file: name of command file
        reply_file: name of reply file
        The macro must be loaded in the Chemstation software.
        dir and filenames must match those specified in the Macro.
        """
        self.cmd_file = os.path.join(comm_dir, cmd_file)
        self.reply_file = os.path.join(comm_dir, reply_file)
        self.cmd_no = 0

        if data_dir is None:
            if os.path.isdir(DEFAULT_DATA_DIR):
                self.data_dir = DEFAULT_DATA_DIR
            else:
                raise FileNotFoundError(f"Default data_dir {DEFAULT_DATA_DIR} not found.")
        else:
            self.data_dir = data_dir

        self.spectra = {
            'channel_A': AgilentHPLCChromatogram(self.data_dir, channel='A'),
            'channel_B': AgilentHPLCChromatogram(self.data_dir, channel='B'),
            'channel_C': AgilentHPLCChromatogram(self.data_dir, channel='C'),
            'channel_D': AgilentHPLCChromatogram(self.data_dir, channel='D'),
        }

        self.data_files = []

        # Create files if needed
        open(self.cmd_file, "a").close()
        open(self.reply_file, "a").close()

        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger("hplc_logger")
            self.logger.addHandler(logging.NullHandler())

        self.reset_cmd_counter()

        self.logger.info("HPLC Controller initialized.")

    def _send(self, cmd: str, cmd_no: int):
        """
        Low-level execution primitive. Sends a command string to HPLC.

        Args:
            cmd: Command string to be sent
            cmd_no: Command number
        """
        # override cmd_no if explicitly given
        while True:
            try:
                with open(self.cmd_file, "w", encoding="utf8") as cmd_file:
                    cmd_file.write(f"{cmd_no} {cmd}")
            except PermissionError:
                self.logger.warning("Failed sending command, trying again...")
                continue
            break

        cmd_file = None

        # Crude way of resolving conflicts where the command file is
        # held by the other side.
        while cmd_file is None:
            try:
                cmd_file = open(self.cmd_file, "w", encoding="utf8")
            except PermissionError:
                self.logger.warning("Failed to open command file for writing - trying again.")
                time.sleep(0.5)
                continue

        with cmd_file:
            cmd_file.write(f"{cmd_no} {cmd}")

        # wait one second to make sure command is processed by hplc
        time.sleep(1)

        self.logger.info("Send command No. %d: %s.", cmd_no, cmd)

    def _receive(self, cmd_no: int, num_retries=20)-> str:
        """
        Low-level execution primitive.

        Args:
            cmd_no: Command number
            num_retries: Number of retries to open reply file

        Raises:
            IOError: Could not read reply file.
        """
        for _ in range(num_retries):
            with open(self.reply_file, "r", encoding="utf_16") as reply_file:
                response = reply_file.read()

                if response:

                    first_line = response.splitlines()[0]
                    response_no = int(first_line.split()[0])

                    # check that response corresponds to sent command
                    if response_no == cmd_no:
                        self.logger.info("Reply: \n%s", response)
                        return response

            time.sleep(0.5)
        raise IOError(f"Failed to read response to cmd_no {cmd_no}.")

    def send(self, cmd: str):
        """
        Sends a command to Chemstation.

        Args:
            cmd: Command to be sent
        """
        if self.cmd_no == MAX_CMD_NO:
            self.reset_cmd_counter()

        self.cmd_no += 1
        self._send(cmd, self.cmd_no)

    def receive(self) -> str:
        """
        Returns messages received in reply file.
        """
        return self._receive(self.cmd_no)

    def reset_cmd_counter(self):
        """
        Resets the command counter.
        """
        self._send(RESET_COUNTER_CMD, cmd_no=MAX_CMD_NO + 1)
        self._receive(cmd_no=MAX_CMD_NO + 1)
        self.cmd_no = 0

        self.logger.debug("Reset command counter")

    def sleep(self, seconds: int):
        """
        Tells the HPLC to wait for a specified number of seconds.

        Args:
            seconds: number of seconds to wait
        """
        self.send(SLEEP_CMD.format(seconds=seconds))
        self.logger.debug("Sleep command sent.")

    def standby(self):
        """
        Switches all modules in standby mode.
        All lamps and pumps are switched off.
        """
        self.send(STANDBY_CMD)
        self.logger.debug("Standby command sent.")

    def preprun(self):
        """
        Prepares all modules for run.
        All lamps and pumps are switched on.
        """
        self.send(PREPRUN_CMD)
        self.logger.debug("PrepRun command sent.")

    def status(self):
        """
        Returns a list with the device status. It can be:
        INITIALIZING    Set during initialization
        NOMODULE        No module configured
        OFFLINE         Currently in offline mode
        STANDBY         All modules in standby mode. Lamps/pumps switched off
        PRERUN          Ready to start run
        INJECTING       Injecting
        PREPARING       Run is being prepared. For example, doing a balance
        RUN             Run is in progress
        POSTRUN         Postrun is in progress
        RAWDATA         Rawdata are still being processed following a run
        NOTREADY        Run cannot be started
        ERROR           Error occurred
        BREAK           Injection paused
        NORESPONSE
        MALFORMED
        """
        self.send(GET_STATUS_CMD)
        time.sleep(1)

        try:
            parsed_response = self.receive().splitlines()[1].split()[1:]
        except IOError:
            return ["NORESPONSE"]
        except IndexError:
            return ["MALFORMED"]
        return parsed_response

    def stop_macro(self):
        """
        Stops Macro execution. Connection will be lost.
        """
        self.send(STOP_MACRO_CMD)

    def switch_method(self, method_name: str = "AH_default"):
        """
        Allows the user to switch between pre-programmed methods.

        Args:
            method_name: any available method in Chemstation method directory

        Raises:
            IndexError: Response did not have expected format. Try again.
            AssertionError: The desired method is not selected. Try again.
        """
        self.send(
            SWITCH_METHOD_CMD.format(
                method_dir=DEFAULT_METHOD_DIR, method_name=method_name
            )
        )

        time.sleep(1)
        self.send(GET_METHOD_CMD)
        time.sleep(1)
        # check that method switched
        try:
            parsed_response = self.receive().splitlines()[1].split()[1:][0]
        except:
            raise IndexError("Switching Methods failed.")

        assert parsed_response == f"{method_name}.M", "Switching Methods failed."

    def lamp_on(self):
        """
        Turns the UV lamp on.
        """
        self.send(LAMP_ON_CMD)

    def lamp_off(self):
        """
        Turns the UV lamp off.
        """
        self.send(LAMP_OFF_CMD)

    def pump_on(self):
        """
        Turns on the pump on.
        """
        self.send(PUMP_ON_CMD)

    def pump_off(self):
        """
        Turns the pump off.
        """
        self.send(PUMP_OFF_CMD)

    def start_method(self):
        """
        Starts and executes a method to run according to Run Time Checklist.
        Device must be ready. (status="PRERUN")
        """
        self.send(START_METHOD_CMD)

    def run_method(self, data_dir: str, experiment_name: str):
        """
        This is the preferred method to trigger a run.
        Starts the currently selected method, storing data
        under the <data_dir>/<experiment_name>.D folder.
        The should <experiment_name> end with a timestamp in the '%Y-%m-%d-%H-%M' format.
        Device must be ready. (status="PRERUN")

        Args:
            data_dir: Directory where to save the data
            experiment_name: Name of the experiment
        """
        timestamp = time.strftime(TIME_FORMAT)

        self.send(
            RUN_METHOD_CMD.format(
                data_dir=data_dir,
                experiment_name=experiment_name,
                timestamp=timestamp
            )
        )

        folder_name = f"{experiment_name}_{timestamp}.D"
        self.data_files.append(os.path.join(data_dir, folder_name))
        self.logger.info("Started HPLC run:  %s.", folder_name)

    def stop_method(self):
        """
        Stops the run.
        A dialog window will pop up and manual intervention may be required.
        """
        self.send(STOP_METHOD_CMD)

    def get_spectrum(self):
        """
        Load last chromatogram for any channel in spectra dictionary.
        """
        # will block if spectrum is measuring
        last_file = self.data_files[-1]

        for channel, spec in self.spectra.items():
            spec.load_spectrum(last_file)
            self.logger.info("%s chromatogram loaded.", channel)

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    controller = HPLCController(os.path.dirname(sys.argv[-1]))

    controller.send('Print "Hi"')
