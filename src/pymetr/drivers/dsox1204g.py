# dsox1204g.py
"""
Keysight DSOX1204G Oscilloscope Driver

Rewritten to use the new queue-based architecture:
 - Inherits from SCPIInstrument (async read/write/query).
 - Removes direct QThread/QTimer references.
 - Each method enqueues commands for the worker to process.
 - 'fetch_trace()' is turned into an asynchronous method that returns data 
   after an acquisition is complete, using a DataBlockProperty or a callback.

Usage in your scripts or UI code remains mostly the same, but be aware all 
communication is now asynchronous.
"""

import logging
import numpy as np

from scpi.core.scpi_instrument import SCPIInstrument
from scpi.core.subsystem import Subsystem
from scpi.core.sources import Sources
from scpi.core.trace import Trace
from scpi.core.properties import (
    SwitchProperty,
    SelectProperty,
    ValueProperty,
    DataProperty,
    DataBlockProperty
)

logger = logging.getLogger(__name__)


class Dsox1204g(SCPIInstrument):
    """
    Driver for Keysight DSOX1204G. Demonstrates:
     - Asynchronous SCPI commands
     - Subsystems for waveforms, triggers, timebase, etc.
     - fetch_trace() example using DataBlockProperty
    """

    def __init__(self, connection):
        """
        Args:
            connection: a ConnectionInterface object 
                        (PyVisaConnection, RawSocketConnection, etc.).
        """
        super().__init__(connection)

        self._format = "BYTE"  # Global data format
        self.sources = Sources(['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4'])
        self.sources.source = ["CHAN1"]

        # X-axis data caching for repeated fetches
        self.x_data = {}

        # Build subsystems
        self.waveform = Waveform.build(self, ':WAVeform')
        self.trigger  = Trigger.build(self, ':TRIGger')
        self.timebase = Timebase.build(self, ':TIMebase')
        self.wavegen  = WaveGen.build(self, ':WGEN')
        self.acquire  = Acquire.build(self, ':ACQuire')
        self.channel  = Channel.build(self, ':CHANnel', indices=4)

    # ------------------------------------------------
    # "format" property controlling global data format
    # ------------------------------------------------
    @property
    def format(self):
        return self._format

    @format.setter
    def format(self, new_fmt):
        if new_fmt not in ["ASCII", "BYTE", "WORD"]:
            raise ValueError("Invalid data format. Must be 'ASCII', 'BYTE', or 'WORD'.")
        self._format = new_fmt

    # ------------------------------------------------
    # GUI Commands (decorators)
    # ------------------------------------------------
    @SCPIInstrument.gui_command
    @Sources.source_command(":AUTOScale {}")
    def autoscale(self, *sources):
        """
        Autoscale the scope for given channels. 
        Because the decorator is used, the UI can auto-generate a button.
        """
        pass

    @SCPIInstrument.gui_command
    def digitize(self, *sources):
        """
        Calls fetch_trace() (async) to get a fresh trace from the scope.
        """
        logger.debug("Digitize command called.")
        self.fetch_trace()

    @SCPIInstrument.gui_command
    def single(self):
        """
        Performs a single acquisition:
         1) Stop
         2) *OPC? wait
         3) :SINGle
         4) Wait for armed + acquisition done
         5) fetch_trace()
        """
        logger.debug("Single trigger command received.")
        self.continuous_mode = False
        self.write(":STOP")
        self.query_operation_complete()   # async *OPC?
        self.write(":SINGle")
        self._enqueue_check_trigger_armed()

    @SCPIInstrument.gui_command
    def stop(self):
        logger.debug("Stop command received.")
        self.write(":STOP")
        self.continuous_mode = False

    @SCPIInstrument.gui_command
    def run(self):
        """
        Puts scope in continuous run mode, then starts checking triggers 
        in the background if desired. 
        """
        logger.debug("Run command received.")
        self.write(":RUN")
        self.continuous_mode = True
        # If you want to keep polling the scope in the background, 
        # you can do something like self._enqueue_check_trigger_armed() again.
        # but let's keep it minimal unless you need continuous data

    # ------------------------------------------------
    # Checking armed or acquisition done
    # ------------------------------------------------
    def _enqueue_check_trigger_armed(self):
        """
        We enqueue a command to query(":AER?"), then parse the response 
        in responseReceived to see if armed=1. 
        If not armed, we re-enqueue a short 'delay' or re-check. 
        Once armed, call wait_for_acquisition_complete.
        """
        logger.debug("Enqueue check_trigger_armed -> :AER?")
        self.query(":AER?")

    def _enqueue_check_acquisition_done(self):
        logger.debug("Enqueue check_acquisition_done -> :OPERegister:CONDition?")
        self.query(":OPERegister:CONDition?")

    # If you want to handle these in responseReceived, you can parse the value 
    # and re-enqueue if not done, or call fetch_trace when done.

    # ------------------------------------------------
    # Asynchronous fetch_trace
    # ------------------------------------------------
    @Sources.source_command(":DIGitize {}")
    def fetch_trace(self, *sources):
        """
        1) :DIGitize (enqueued by decorator).
        2) *OPC? wait or manual check (we can do query_operation_complete here).
        3) read the waveforms for each active channel, build a list of Trace objects, return them.

        Because of the @trace_thread decorator, the returning data 
        is automatically emitted to `traceDataReady` signal as well.
        """
        self.query_operation_complete()
        logger.debug(f"Fetching trace data from scope {self}")
        if not sources:
            sources = self.sources.source

        traces = []
        for source in sources:
            time_vals = self._fetch_time(source)
            data_vals = self._fetch_data(source)
            trace_obj = Trace(data_vals, x_data=time_vals, label=source)
            traces.append(trace_obj)

        return traces

    def _fetch_time(self, source=None):
        """
        Gets the horizontal scale info from the waveform preamble, builds time array.
        """
        if source:
            self.waveform.source = source

        try:
            preamble = self.waveform.preamble
            self._x_increment, self._x_origin, self._x_reference = preamble[4], preamble[5], int(preamble[6])
            self._y_increment, self._y_origin, self._y_reference = preamble[7], preamble[8], int(preamble[9])
            self.waveform.format = self._format

            count_points = self.waveform.points
            timestamps = (np.arange(count_points) - self._x_reference) * self._x_increment + self._x_origin
            return timestamps
        except Exception as e:
            raise ValueError(f"Issue fetching or parsing preamble: {e}")

    def _fetch_data(self, source=None):
        """
        Fetch raw data from self.waveform.data, convert if binary, etc.
        """
        if source:
            self.waveform.source = source

        self.waveform.format = self.format
        is_unsigned = self.waveform.unsigned

        if self._format in ["BYTE", "WORD"]:
            # e.g. 'B' vs 'b' for data_type
            data_type = 'B' if is_unsigned else 'b'
            self.data_type = data_type
            self.data_mode = "BINARY"
        else:
            self.data_type = 'B'
            self.data_mode = "ASCII"

        # read the raw data
        raw_data = self.waveform.data

        # Convert if binary:
        if self._format in ["BYTE", "WORD"]:
            voltages = (raw_data - self._y_reference) * self._y_increment + self._y_origin
        elif self._format == "ASCII":
            voltages = raw_data
        else:
            raise ValueError(f"Unsupported data format: {self.format}")

        return voltages


# ---------------------------------------------------------------------------
# Subsystems
# ---------------------------------------------------------------------------
class Acquire(Subsystem):
    mode         = SelectProperty(":MODE", ['RTIMe', 'SEGMmented'], "Acquisition mode")
    type         = SelectProperty(":TYPE", ['NORMal','AVERage','HRESolution','PEAK'], "Acq type")
    sample_rate  = ValueProperty(":SRATe",  type="float", range=[0.1, 1e9], units="S/s", doc_str="Sample rate")
    count        = ValueProperty(":COUNt", type="int",   range=[1, 10000],  doc_str="Averaging count / acquisitions")

class Channel(Subsystem):
    coupling = SelectProperty(":COUPling", ['AC', 'DC'], "Channel coupling")
    display  = SwitchProperty(":DISPlay",  "Channel on/off")
    scale    = ValueProperty(":SCALe",     type="float", range=[1e-3,1e3], units="V", doc_str="Vert scale")
    offset   = ValueProperty(":OFFSet",    type="float", range=[-1e2,1e2], units="V", doc_str="Vertical offset")
    probe    = ValueProperty(":PROBe",     type="float", doc_str="Probe attenuation")

class Timebase(Subsystem):
    mode       = SelectProperty(":MODE",       ['MAIN','WIND','XY','ROLL'], "Timebase mode")
    reference  = SelectProperty(":REFerence",  ['LEFT','CENTer','RIGHT'],   "Timebase ref")
    scale      = ValueProperty(":SCALe",       type="float", range=[1e-9,1.0],units="s", doc_str="Timebase scale")
    position   = ValueProperty(":POSition",    type="float", range=[-5.0,5.0],units="s", doc_str="Timebase pos")
    range      = ValueProperty(":RANGe",       type="float", range=[2e-9,50], units="s", doc_str="Timebase range")

class Trigger(Subsystem):
    mode   = SelectProperty(":MODe",   ['EDGE','GLITch','PATTern','SHOL','NONE'], "Trig mode")
    source = SelectProperty(":SOURce", ['CHAN1','CHAN2','CHAN3','CHAN4','EXT','LINE','WGEN'], "Trig source")
    slope  = SelectProperty(":SLOPe",  ['POSitive','NEGative'], "Trig slope")
    sweep  = SelectProperty(":SWEep",  ['AUTO','NORMAL'],       "Sweep mode")
    level  = ValueProperty(":LEVel",   type="float", range=[-5,5],units="V", doc_str="Trig level")

class WaveGen(Subsystem):
    function   = SelectProperty(":FUNC",  ['SIN','SQUare','RAMP','PULSe','NOISe','DC'], "Wavegen function")
    output     = SwitchProperty(":OUTP", "Wavegen output on/off")
    frequency  = ValueProperty(":FREQ",  type="float", range=[1e-3,1e8], units="Hz", doc_str="Wavegen freq")
    amplitude  = ValueProperty(":VOLT",  type="float", range=[1e-3,10],  units="V",  doc_str="Wavegen amplitude")
    offset     = ValueProperty(":VOLT:OFFS",type="float",range=[-5,5],   units="V",  doc_str="Wavegen offset")

class Waveform(Subsystem):
    source       = SelectProperty(":SOURce", ['CHAN1','CHAN2','CHAN3','CHAN4','FUNC','MATH','FFT','WMEM','BUS1','BUS2','EXT'], "Waveform src")
    format       = SelectProperty(":FORMat", ['ASCII','WORD','BYTE'],  "Waveform data fmt")
    points_mode  = SelectProperty(":POINts:MODE", ['NORMal','MAXimum','RAW'], "Points mode")
    byte_order   = SelectProperty(":BYTeorder", ['LSBFirst','MSBFirst'],      "Byte order")
    unsigned     = SwitchProperty(":UNSigned", "Data signed or unsigned")
    points       = ValueProperty(":POINts",  type="int", access='write', doc_str="Trace points to fetch")
    x_increment  = DataProperty(":XINCrement", doc_str="Waveform X incr")
    x_origin     = DataProperty(":XORigin",     doc_str="Waveform X origin")
    x_reference  = DataProperty(":XREFerence",  doc_str="Waveform X ref")
    y_increment  = DataProperty(":YINCrement", doc_str="Waveform Y incr")
    y_origin     = DataProperty(":YORigin",     doc_str="Waveform Y origin")
    y_reference  = DataProperty(":YREFerence",  doc_str="Waveform Y ref")
    preamble     = DataProperty(":PREamble", access='read', doc_str="Pre info")
    data         = DataBlockProperty(":DATa",   access='read', ieee_header=True, doc_str="Waveform data array")
