# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   GDAL version:       3.10.3
#   GeoPandas version:  1.1.1
#   PyQt6 version:      6.7.1
#   Year:               2025
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------


"""
Thread-safe dialog system for TerraCover GUI
Uses Qt signals to communicate between worker threads and main thread
"""

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox
import logging

logger = logging.getLogger(__name__)

class DialogManager(QObject):
    """Global dialog manager that runs in the main thread"""

    # Define signals for different dialog types
    show_error_signal = pyqtSignal(str, str, object)  # title, message, result_callback
    show_question_signal = pyqtSignal(str, str, object)  # title, message, result_callback
    
    def __init__(self):
        super().__init__()
        self.result_storage = {}
        
        # Connect signals to slots
        self.show_error_signal.connect(self._show_error_dialog)
        self.show_question_signal.connect(self._show_question_dialog)
        
    
    def _show_error_dialog(self, title, message, result_callback=None):
        """Show error dialog in main thread"""
        try:
            from .dialog_theming import create_dark_messagebox
            create_dark_messagebox(
                None,
                QMessageBox.Icon.Critical,
                title,
                message,
                QMessageBox.StandardButton.Ok
            )
            # Call callback to signal completion
            if result_callback:
                result_callback(True)
        except Exception as e:
            logger.error(f"Error showing dialog: {e}")
            # Call callback even on error
            if result_callback:
                result_callback(False)
    
    def _show_question_dialog(self, title, message, result_callback):
        """Show question dialog in main thread and call callback with result"""
        try:
            from .dialog_theming import create_dark_messagebox
            result = create_dark_messagebox(
                None,
                QMessageBox.Icon.Question,
                title,
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            # Convert result to boolean
            answer = (result == QMessageBox.StandardButton.Yes)
            
            # Call the callback with the result
            if result_callback:
                result_callback(answer)
                
        except Exception as e:
            logger.error(f"Error showing question dialog: {e}")
            # Call callback with default result
            if result_callback:
                result_callback(False)
    
    def show_error_threadsafe(self, title, message, callback=None):
        """Show error dialog from any thread"""
        self.show_error_signal.emit(title, message, callback)

    def show_question_threadsafe(self, title, message, callback):
        """Show question dialog from any thread"""
        self.show_question_signal.emit(title, message, callback)


# Global instance
_dialog_manager = None

def get_global_dialog_manager():
    """Get or create the global dialog manager"""
    global _dialog_manager
    
    if _dialog_manager is None:
        app = QApplication.instance()
        if app is None:
            logger.warning("No QApplication instance found")
            return None
            
        _dialog_manager = DialogManager()
        
        # Make sure it runs in the main thread
        main_thread = app.thread()
        if _dialog_manager.thread() != main_thread:
            _dialog_manager.moveToThread(main_thread)
    
    return _dialog_manager

def show_error_from_thread(title, message):
    """
    Show error dialog from any thread (thread-safe)

    Note: This is a synchronous function that will block until user closes the dialog
    """
    import time

    manager = get_global_dialog_manager()
    if not manager:
        return

    # Create a storage mechanism for the result
    result_container = {'completed': False}

    def result_callback(success):
        result_container['completed'] = True

    # Show the dialog
    manager.show_error_threadsafe(title, message, result_callback)

    # Wait for the result (with timeout to prevent infinite blocking)
    timeout = 30  # 30 seconds timeout
    start_time = time.time()

    while not result_container['completed']:
        time.sleep(0.1)  # Sleep for 100ms
        if time.time() - start_time > timeout:
            return

    return

def show_question_from_thread(title, message):
    """
    Show question dialog from any thread (thread-safe)
    Returns True for Yes, False for No
    
    Note: This is a synchronous function that will block until user responds
    """
    import threading
    import time
    
    manager = get_global_dialog_manager()
    if not manager:
        return False
    
    # Create a storage mechanism for the result
    result_container = {'result': None, 'completed': False}
    
    def result_callback(answer):
        result_container['result'] = answer
        result_container['completed'] = True
    
    # Show the dialog
    manager.show_question_threadsafe(title, message, result_callback)
    
    # Wait for the result (with timeout to prevent infinite blocking)
    timeout = 30  # 30 seconds timeout
    start_time = time.time()
    
    while not result_container['completed']:
        time.sleep(0.1)  # Sleep for 100ms
        if time.time() - start_time > timeout:
            return False
    
    return result_container['result']