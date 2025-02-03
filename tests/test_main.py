# tests/test_main.py
import pytest
from unittest.mock import Mock, patch
from pymetr.__main__ import main

def test_main():
    with patch('pymetr.__main__.create_application') as mock_create:
        with patch('sys.exit') as mock_exit:
            # Create mock app and window
            mock_app = Mock()
            mock_window = Mock()
            mock_create.return_value = (mock_app, mock_window)
            
            main()
            
            # Verify application was created and executed
            mock_create.assert_called_once()
            mock_app.exec.assert_called_once()
            mock_exit.assert_called_once()