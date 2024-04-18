# test_instrument.py
import unittest
from unittest.mock import patch, MagicMock
from pymetr.core import Instrument

class TestInstrument(unittest.TestCase):

    @patch('pymetr.base.pyvisa.ResourceManager')
    def setUp(self, MockResourceManager):
        # Mocking the ResourceManager and the open_resource return value
        self.mock_rm = MockResourceManager.return_value
        self.mock_inst = MagicMock()
        self.mock_rm.open_resource.return_value = self.mock_inst
        # Creating an instance of Instrument for testing
        self.resource_string = "GPIB0::1::INSTR"
        self.instrument = Instrument(self.resource_string)

    def test_init(self):
        """Test initializing an instrument."""
        self.assertEqual(self.instrument.resource_string, self.resource_string)
        self.assertIsNotNone(self.instrument.rm)

    def test_open(self):
        """Test opening a connection to the instrument."""
        self.instrument.open()
        self.mock_rm.open_resource.assert_called_once_with(self.resource_string)
        self.assertEqual(self.instrument.handle, self.mock_inst)

    def test_close(self):
        """Test closing the connection to the instrument."""
        self.instrument.open() # Make sure the instrument is open
        self.instrument.close()
        self.mock_inst.close.assert_called_once()

    @patch('pymetr.base.Instrument.write')
    def test_clear_status(self, mock_write):
        """Test clearing the instrument status."""
        self.instrument.clear_status()
        mock_write.assert_called_once_with('*CLS')

    @patch('pymetr.base.Instrument.query')
    def test_query(self, mock_query):
        query_command = "*IDN?"
        mock_query.return_value = 'Instrument ID'
        response = self.instrument.query(query_command)
        mock_query.assert_called_once_with(query_command)
        self.assertEqual(response, 'Instrument ID')

    @patch('pymetr.base.Instrument.read')
    def test_read(self, mock_read):
        mock_read.return_value = 'Read response'
        response = self.instrument.read()
        mock_read.assert_called_once()
        self.assertEqual(response, 'Read response')

    def test_identity(self):
        """Test querying the instrument for its identity."""
        # Mocking the query method directly since identity calls query
        with patch.object(self.instrument, 'query', return_value='Fake Instrument ID') as mock_query:
            response = self.instrument.identity()
            mock_query.assert_called_once_with('*IDN?')
            self.assertEqual(response, 'Fake Instrument ID')

if __name__ == '__main__':
    unittest.main()
