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

        with open(self.cmd_file, "w", encoding="utf8") as cmd_file:
            cmd_file.write(f"{cmd_no} {cmd}")

        self.logger.info(f"Send command No. {cmd_no}: {cmd}.")

    def _receive(self, cmd_no: int) -> str:
        """
        Low-level execution primitive.
        """
        while True:
            with open(self.reply_file, "r", encoding="utf_16") as reply_file:
                response = reply_file.read()

                if response:

                    first_line = response.splitlines()[0]
                    response_no = int(first_line.split()[0])

                    # check that response corresponds to sent command
                    if response_no == cmd_no:
                        self.logger.info(f"Reply: \n{response}")
                        return response

            time.sleep(0.25)

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
        self.send(f'SLEEP {time}')
        self.logger.debug("Sleep command sent.")

    def standby(self):
        # TODO Standby cmd
        pass

    def preprun(self):
        # TODO PrepRun cmd
        pass

    def status(self):
        # TODO print Print AcqStatus$
        pass

    def stop_macro(self):
        # TODO Stop cmd
        pass

    def switch_method(self, name: str = "default"):
        # TODO change _MethFile$
        pass

    def lamp_on(self):
        pass

    def lamp_off(self):
        pass

    def pump_on(self):
        pass

    def pump_off(self):
        pass

# TODO: What else needs to be implemented? CONTINJECT, StartMethod, StopMethod, LCInjReset, On Error


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    controller = HPLCController(os.path.dirname(sys.argv[-1]))

    controller.send('Print "Hi"')
