import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication, QFile, QTextStream

from pymetr.ui.main_window import MainWindow
from pymetr.core.state import ApplicationState
from pymetr.core.logging import setup_logging

def main():
    """Application entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting PyMetr")
    
    # Create application
    # QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    # QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setApplicationName("PyMetr")
    app.setOrganizationName("PyMetr")
    
    # Set application style
    app.setStyle("Fusion")

    style_path = Path(__file__).parent / "core" / "styles.qss"
    styleSheetFile = QFile(str(style_path))
    if styleSheetFile.open(QFile.ReadOnly | QFile.Text):
        textStream = QTextStream(styleSheetFile)
        app.setStyleSheet(textStream.readAll())

    try:
        # Create state and set it as the global state.
        state = ApplicationState()
        
        # Create and show main window
        window = MainWindow(state)
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
