# src/pymetr/__main__.py
import sys
from .state import ApplicationState
from .views.windows.main_window import create_application

def main():
    # Create application state
    state = ApplicationState()
    
    # Create and run application
    app, window = create_application(state)
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()