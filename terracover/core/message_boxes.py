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


import logging
import threading

# Global batch mode flag - when True, messageboxes are suppressed and errors are logged
_BATCH_MODE = False

# Configure logging for batch mode
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Lazy import cache for PyQt6 - only imported when actually needed
_PYQT_IMPORTS = None

def _get_pyqt_imports():
    """
    Lazy import of PyQt6 modules.
    Only imports PyQt6 when actually needed (when a messagebox is displayed).
    This prevents DLL loading issues when modules are imported but not used.

    Returns:
        dict: Dictionary with PyQt6 classes and PYQT_AVAILABLE flag
    """
    global _PYQT_IMPORTS

    if _PYQT_IMPORTS is None:
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            from PyQt6.QtCore import QThread, QTimer, QObject, pyqtSignal
            _PYQT_IMPORTS = {
                'QApplication': QApplication,
                'QMessageBox': QMessageBox,
                'QThread': QThread,
                'QTimer': QTimer,
                'QObject': QObject,
                'pyqtSignal': pyqtSignal,
                'available': True
            }
        except ImportError:
            # Fallback to tkinter if PyQt6 is not available
            from tkinter import messagebox
            _PYQT_IMPORTS = {
                'tkinter_messagebox': messagebox,
                'available': False
            }

    return _PYQT_IMPORTS


def _is_main_thread():
    """Check if we're running in the main thread"""
    pyqt = _get_pyqt_imports()

    if pyqt['available']:
        try:
            QApplication = pyqt['QApplication']
            QThread = pyqt['QThread']
            app = QApplication.instance()
            if app:
                current_thread = QThread.currentThread()
                app_thread = app.thread()
                is_main_qt = current_thread == app_thread
                return is_main_qt
        except Exception:
            pass

    # Fallback to Python threading
    current_py_thread = threading.current_thread()
    main_py_thread = threading.main_thread()
    is_main_py = current_py_thread == main_py_thread
    return is_main_py




# ------------------------------------------------------------------------


def set_batch_mode(enabled: bool):
    """
    Enable or disable batch mode.
    When batch mode is enabled:
    - Error messageboxes are suppressed and logged instead
    - Confirmation dialogs automatically return True (proceed)
    - Info/warning dialogs are logged instead of displayed
    
    Args:
        enabled (bool): True to enable batch mode, False to disable
    """
    global _BATCH_MODE
    _BATCH_MODE = enabled
    if enabled:
        logger.info("Batch mode enabled - messageboxes will be suppressed and logged")
    else:
        logger.info("Batch mode disabled - messageboxes will be displayed normally")


def is_batch_mode() -> bool:
    """
    Check if batch mode is currently enabled.
    
    Returns:
        bool: True if batch mode is enabled, False otherwise
    """
    return _BATCH_MODE


def _show_error_messagebox(errors):
    spaced_errors = []
    for i, error in enumerate(errors):
        spaced_errors.append(error)
        if i < len(errors) - 1:
            spaced_errors.append("")  # Add empty string

    error_message = "\n".join(spaced_errors)
    
    if _BATCH_MODE:
        # In batch mode, log errors instead of showing messagebox
        logger.error(f"Validation errors occurred:\n{error_message}")
    else:
        # Normal mode - show messagebox
        # Use thread-safe dialog system
        pyqt = _get_pyqt_imports()
        if pyqt['available']:
            try:
                from ..gui_src.core.thread_safe_dialogs import show_error_from_thread
                show_error_from_thread("Errors", error_message)
                return
            except Exception:
                pass

        # Fallback to tkinter
        from tkinter import messagebox
        messagebox.showerror("Errors", error_message)


# ------------------------------------------------------------------------


def _ask_yes_no_messagebox(question):
    """
    Displays a yes/no message box with the given question(s).
    In batch mode, automatically returns True (proceed) and logs the question.
    
    Args:
        question (str or List[str]): Single question string or list of question strings
        
    Returns:
        bool: True for Yes, False for No. 
              If input is a list, questions are combined into one message box.
              In batch mode, always returns True (proceed).
    """
    # Handle both single string and list inputs
    if isinstance(question, str):
        # Single question
        message = question
    elif isinstance(question, list):
        # Multiple questions - combine into one message
        if not question:
            return False
        
        # Validate all items are strings
        for q in question:
            if not isinstance(q, str):
                raise ValueError(f"All questions must be strings, got: {type(q)}")
        
        # Combine questions with line breaks and add continuation question
        message = "\n\n".join(question) + "\n\nDo you want to continue?"
    else:
        raise ValueError("Question must be a string or list of strings")
    
    if _BATCH_MODE:
        # In batch mode, log the question and automatically proceed (return True)
        logger.info(f"Batch mode: Auto-confirming dialog - {message}")
        return True
    else:
        # Normal mode - show messagebox
        # Use thread-safe dialog system
        pyqt = _get_pyqt_imports()
        if pyqt['available']:
            try:
                from ..gui_src.core.thread_safe_dialogs import show_question_from_thread
                result = show_question_from_thread("Confirmation", message)
                return result
            except Exception:
                pass

        # Fallback to tkinter
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # Show single message box
        result = messagebox.askyesno("Confirmation", message)
        root.destroy()
        return result



