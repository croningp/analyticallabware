import time
from os import path

MAX_CMD_NO = 256


class HPLCController:
    def __init__(self, dir: str, cmd_file: str = "cmd", reply_file: str = "reply"):
        """
        Initialize HPLC controller.
        """
        self.cmd_file = path.join(dir, cmd_file)
        self.reply_file = path.join(dir, reply_file)
        self.cmd_no = 0

        # TODO: Create cmd_file if it doesn't exist

        self.reset_cmd_counter()

    def _send(self, cmd: str, cmd_no: int):
        """
        Low-level execution primitive. Sends a command string to HPLC
        """
        # override cmd_no if explicitly given

        with open(self.cmd_file, "w", encoding="utf8") as cmd_file:
            cmd_file.write(f"{cmd_no} {cmd}")

    def _receive(self, cmd_no: int) -> str:
        """
        Low-level execution primitive.
        """
        while True:
            with open(self.reply_file, "r", encoding="utf_16") as reply_file:
                response = reply_file.read()

            first_line = response.splitlines()[0]
            response_no = int(first_line.split()[0])

            if response_no == cmd_no:
                return response

            time.sleep(0.25)

    def send(self, cmd: str):
        if self.cmd_no > MAX_CMD_NO:
            self.reset_cmd_counter()

        self.cmd_no += 1
        self._send(cmd, self.cmd_no)

    def receive(self) -> str:
        return self._receive(self.cmd_no)

    def reset_cmd_counter(self):
        self._send("last_cmd_no = 0", cmd_no=MAX_CMD_NO)
        self._receive(cmd_no=MAX_CMD_NO)
        self.cmd_no = 0


if __name__ == "__main__":
    import sys

    controller = HPLCController(sys.argv[-1])

    controller.send('Print "Hi"')
