from SerialLabware.controllers import AbstractDistributionValve

class IDEXMXIIValve(AbstractDistributionValve):
    """Two-position IDEX MX Series II HPLC valve."""
    def move_home(self):
        """Move valve to home position.
        This is supposed to correspond to the idle position of the valve, i.e.
        any injected sample will go to the sample loop and HPLC eluent is
        route to the waste."""
        self.send_message("P01")
    
    def move_to_position(self, position: int):
        """Move value to specified position.
        Position 1 corresponds to the home position, i.e. injected sample goes
        to the loop and eluent to waste.
        Position 2 corresponds usually represents the beginning of acquisition
        where sample in the loop goes to analysis."""
        if position == 1:
            self.send_message("P01")
        elif position == 2:
            self.send_message("P02")
        # TODO: Implement multi-position valves.
        else:
            raise ValueError("Position has to be one of 1 or 2.")