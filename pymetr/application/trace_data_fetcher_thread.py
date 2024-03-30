import logging
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

class TraceDataFetcherThread(QThread):
    trace_data_ready = Signal(object)  # Emits when trace data is ready
    fetch_error = Signal(str)  # Emits in case of a fetching error

    def __init__(self, instrument):
        super(TraceDataFetcherThread, self).__init__()
        self.instrument = instrument

    def run(self):
        try:
            trace_data = self.instrument.fetch_trace()
            self.trace_data_ready.emit(trace_data)
        except Exception as e:
            self.fetch_error.emit(str(e))
            logger.exception(f"Error fetching trace data: {e}")