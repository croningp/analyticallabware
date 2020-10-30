import time
import os
import logging


MAX_CMD_NO = 255


class HPLCController:
    def __init__(
        self, dir: str, cmd_file: str = "cmd", reply_file: str = "reply", logger=None
    ):
        """
        Initialize HPLC controller.  
        dir: Name of directory
        cmd_file: name of command file
        reply_file: name of reply file
        The macro must be loaded in the Chemstation software.
        dir and filenames must match those specified in the Macro.
        """
        self.cmd_file = os.path.join(dir, cmd_file)
        self.reply_file = os.path.join(dir, reply_file)
        self.cmd_no = 0

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
        Low-level execution primitive. Sends a command string to HPLC
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

        self.logger.info(f"Send command No. {cmd_no}: {cmd}.")

    def _receive(self, cmd_no: int, num_retries=20)-> str:
        """
        Low-level execution primitive.
        """
        for _ in range(num_retries):
            with open(self.reply_file, "r", encoding="utf_16") as reply_file:
                response = reply_file.read()

                if response:

                    first_line = response.splitlines()[0]
                    response_no = int(first_line.split()[0])

                    # check that response corresponds to sent command
                    if response_no == cmd_no:
                        self.logger.info(f"Reply: \n{response}")
                        return response

            time.sleep(0.5)
        raise IOError(f"Failed to read response to cmd_no {cmd_no}.")

    def send(self, cmd: str):
        if self.cmd_no == MAX_CMD_NO:
            self.reset_cmd_counter()

        self.cmd_no += 1
        self._send(cmd, self.cmd_no)

    def receive(self) -> str:
        return self._receive(self.cmd_no)

    def reset_cmd_counter(self):
        self._send("last_cmd_no = 0", cmd_no=MAX_CMD_NO + 1)
        self._receive(cmd_no=MAX_CMD_NO + 1)
        self.cmd_no = 0

        self.logger.debug("Reset command counter")

    def sleep(self, time: int):
        """
        Tells the HPLC to wait for specified amount of seconds.
        """
        self.send(f"SLEEP {time}")
        self.logger.debug("Sleep command sent.")

    def standby(self):
        """
        Switches all modules in standby mode.
        All lamps and pumps are switched off.
        """
        self.send(f"Standby")
        self.logger.debug("Standby command sent.")

    def preprun(self):
        """
        Prepares all modules for run.
        All lamps and pumps are switched on.
        """
        self.send(f"PrepRun")
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
        self.send("response$ = AcqStatus$")
        time.sleep(0.25)
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
        self.send("Stop")

    def switch_method(self, name: str = "AH_default"):
        """
        Allows the user to switch between pre-programmed methods.
        """
        self.send(f'LoadMethod "C:\\Chem32\\1\\Methods\\", "{name}.M"')
        time.sleep(1)
        self.send("response$ = _MethFile$")
        time.sleep(0.5)
        # check that method switched
        parsed_response = self.receive().splitlines()[1].split()[1:][0]
        assert parsed_response == f"{name}.M", "Switching Methods failed."

    def lamp_on(self):
        self.send("LampAll ON")

    def lamp_off(self):
        self.send("LampAll OFF")

    def pump_on(self):
        self.send("PumpAll ON")

    def pump_off(self):
        self.send("PumpAll OFF")

    def start_run(self):
        """
        This starts the currently selected method.
        Device must be ready. (status="PRERUN")
        """
        self.send("StartMethod")

    def run_method(self, data_dir: str, expt_name: str):
        """
        Starts the currently selected method, storing data
        under the <data_dir>/<expt_name>.D folder.
        Device must be ready. (status="PRERUN")
        """
        self.send(f'RunMethod "{data_dir}",,"{expt_name}"')

    def abort_run(self):
        """
        Stops the run. 
        A dialog window will pop up and manual intervention may be required.
        """
        self.send("StopMethod")


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    controller = HPLCController(os.path.dirname(sys.argv[-1]))

    controller.send('Print "Hi"')
