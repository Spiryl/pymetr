from pymetr.instruments.dsox1204g import Oscilloscope
from pymetr import Instrument
import logging

logging.basicConfig(level=logging.INFO)

# Select an instrument
resource = Instrument.select_instrument("TCPIP?*::INSTR")

# Create an instance using the selected resource string
oscope = Oscilloscope(resource)

# Open a connection to the instrument
oscope.open()

# Verify the identity and connection is good.
print(oscope.identity())

# Loop through and turn on the channels. 
for channel in range (0,4):
    print(f"Turning on channel {channel+1} display.\n")
    oscope.channel[channel].display = 'On'

# Call a different parameter
print(f"Channel 1 offset: {oscope.channel[0].offset}\n")

# Loop through and turn off on the channels. 
for channel in range (0,4):
    print(f"Turning off channel {channel+1} display.\n")
    oscope.channel[channel].display = 'Off'

# See if they are off.
for channel in range (0,4):
    print(f"Checking channel {channel+1} display {oscope.channel[channel].display}\n")

oscope.close()