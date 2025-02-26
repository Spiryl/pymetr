import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication

from pymetr.ui.main_window import MainWindow
from pymetr.core.state import ApplicationState
from pymetr.core.logging import setup_logging, setup_status_logging
from pymetr.services.theme_service import ThemeService

def main():
    """Application entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting PyMetr")
    
    # Create application
    # Enable high DPI support
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("PyMetr")
    app.setOrganizationName("PyMetr")
    
    # Set application style
    app.setStyle("Fusion")

    try:
        # Create state and set it as the global state.
        state = ApplicationState()
        
        # Initialize theme service (will be used by MainWindow)
        theme_service = ThemeService.get_instance()
        
        # Create and show main window
        window = MainWindow(state)
        
        # Set up status bar logging AFTER window is created
        # This ensures the status bar exists to receive log messages
        status_logger = setup_status_logging(state)
        
        # Show the window
        window.show()
        
        # Handle command line arguments
        if len(sys.argv) > 1:
            script_path = Path(sys.argv[1])
            if script_path.exists() and script_path.suffix == '.py':
                state.open_script(script_path)
        
        # Start event loop
        return app.exec()
        
    except Exception as e:
        logger.exception("Fatal error during startup")
        return 1

if __name__ == '__main__':
    sys.exit(main())