import logging
from pymetr.drivers.base import SCPIInstrument
from pymetr.drivers.base import Subsystem
from pymetr.drivers.base import (
    ValueProperty, SelectProperty, SwitchProperty
)

logger = logging.getLogger(__name__)

class HS9000(SCPIInstrument):
    """
    HSX Series Synthesizer Driver

    Features:
    - Multiple channels (CH1..CHn) for freq/power/phase control
    - Reference clock selection and monitoring
    - Built-in diagnostics
    - Network configuration
    - Temperature monitoring

    Usage:
        synth = HS9000(connection, channels=4)
        synth.ch[1].frequency = "2105MHz"
        synth.ch[2].output = True
        synth.ref.source = "EXT:10MHz"
        synth.diag.start()
    """

    def __init__(self, connection):
        super().__init__(connection)
        
        # Build subsystems
        self.channel = Channel.build(self, ":CH", indices=4)
        self.reference = Reference.build(self, ":REF")
        self.ip = IP.build(self, ":IP")
        self.communication = Communication.build(self, ":COMM")

        # Set response mode based on read_after_write flag
        if self.read_after_write:
            self.communication.respond = True

class Channel(Subsystem):
    """
    Represents a single synthesizer channel (n) with properties and methods.
    Commands use the pattern :CHn:<command>
    """
    # Frequency settings with unit suffixes
    frequency = ValueProperty(":FREQ", type="float", range=[10e6, 6e9], units="Hz", doc_str="Channel output frequency", join_char=":")

    # Power settings
    power = ValueProperty(":PWR", type="float", range=[-20, 20], units="dBm",doc_str="Channel output power", join_char=":")
    output = SwitchProperty(":PWR:RF", doc_str="RF output state", join_char=":")

    # Phase settings
    phase = ValueProperty(":PHASE", type="float", range=[0, 360], units="deg",doc_str="Phase offset", join_char=":")


class Reference(Subsystem):
    """
    Reference clock subsystem.
    Commands use pattern :REF:<command>
    """
    source = SelectProperty("", ["EXT:10MHz", "INT:100MHz"], doc_str="Reference clock source", join_char=":")

class IP(Subsystem):
    """
    IP address configuration subsystem.
    Commands use pattern :IP:<command>
    """
    mode = SelectProperty(":STATUS", ["STATIC", "DHCP"], doc_str="IP address mode", join_char=":")
    address = ValueProperty(":ADDR", doc_str="Static IP address", join_char=":")
    subnet = ValueProperty(":SUBNET", doc_str="Subnet mask", join_char=":")
    gateway = ValueProperty(":GATEWAY", doc_str="Gateway address", join_char=":")

class Communication(Subsystem):
    """
    Communication settings subsystem.
    Commands use pattern :COMM:<command>
    """
    respond = SwitchProperty(":RESPOND", doc_str="Enable responses for all commands", join_char=":")
