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
Dialog theming utilities for consistent dark theme across all dialogs
Provides functions to apply dark theme to QMessageBox and other dialogs
"""

import sys
from PyQt6.QtWidgets import QMessageBox, QDialog, QInputDialog, QApplication, QFileDialog
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QMetaObject, Q_ARG, QThread, QMutex, QWaitCondition
from PyQt6.QtGui import QPalette, QColor


class ThreadSafeDialogManager(QObject):
    """Thread-safe dialog manager using Qt signals"""
    
    # Signals for different dialog types
    show_error_signal = pyqtSignal(str, str)  # title, message
    show_question_signal = pyqtSignal(str, str)  # title, message
    
    def __init__(self):
        super().__init__()
        self._question_result = False
        self._question_mutex = QMutex()
        self._question_condition = QWaitCondition()
        self._question_answered = False
        
        # Connect signals to slots
        self.show_error_signal.connect(self._show_error_slot)
        self.show_question_signal.connect(self._show_question_slot)
    
    def _show_error_slot(self, title, message):
        """Slot to show error dialog in main thread"""
        try:
            create_dark_messagebox(
                None, 
                QMessageBox.Icon.Critical, 
                title, 
                message, 
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            pass
    
    def _show_question_slot(self, title, message):
        """Slot to show question dialog in main thread"""
        try:
            result = create_dark_messagebox(
                None, 
                QMessageBox.Icon.Question, 
                title, 
                message, 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            # Store result and notify waiting thread
            self._question_mutex.lock()
            try:
                self._question_result = (result == QMessageBox.StandardButton.Yes)
                self._question_answered = True
                self._question_condition.wakeAll()
            finally:
                self._question_mutex.unlock()
                
        except Exception as e:
            # Wake up waiting thread with default result
            self._question_mutex.lock()
            try:
                self._question_result = False
                self._question_answered = True
                self._question_condition.wakeAll()
            finally:
                self._question_mutex.unlock()
    
    def show_error_threadsafe(self, title, message):
        """Show error dialog from any thread"""
        if QThread.currentThread() == QApplication.instance().thread():
            # We're in the main thread, show directly
            self._show_error_slot(title, message)
        else:
            # We're in a worker thread, use signal
            self.show_error_signal.emit(title, message)
    
    def show_question_threadsafe(self, title, message):
        """Show question dialog from any thread and return result"""
        if QThread.currentThread() == QApplication.instance().thread():
            # We're in the main thread, show directly
            self._show_question_slot(title, message)
            return self._question_result
        else:
            # We're in a worker thread, use signal and wait for result
            self._question_mutex.lock()
            try:
                self._question_answered = False
                self.show_question_signal.emit(title, message)
                
                # Wait for the dialog to be answered
                while not self._question_answered:
                    self._question_condition.wait(self._question_mutex)
                
                return self._question_result
            finally:
                self._question_mutex.unlock()


# Global instance
_dialog_manager = None


def get_dialog_manager():
    """Get or create the global dialog manager"""
    global _dialog_manager
    if _dialog_manager is None:
        _dialog_manager = ThreadSafeDialogManager()
        # Move to main thread
        app = QApplication.instance()
        if app:
            _dialog_manager.moveToThread(app.thread())
    return _dialog_manager

def apply_dark_theme_to_dialog(dialog):
    """
    Apply dark theme to any dialog window
    
    Args:
        dialog: QDialog, QMessageBox, or any QWidget-based dialog
    """
    try:
        # Set dark stylesheet for the dialog matching the main theme exactly
        dialog_style = """
            QDialog, QMessageBox, QFileDialog {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
            }
            
            QLabel {
                color: #ffffff;
                background-color: transparent;
                padding: 4px;
            }
            
            QPushButton {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 12px;
                min-height: 24px;
                max-height: 32px;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                min-width: 80px;
            }
            
            QPushButton:hover {
                background-color: #4a90e2;
                border-color: #6ba3e6;
            }
            
            QPushButton:pressed {
                background-color: #357abd;
                border-color: #5a9dd8;
            }
            
            QPushButton:default {
                background-color: #4a90e2;
                border-color: #6ba3e6;
            }
            
            QPushButton:focus {
                outline: none;
                border: 2px solid #6ba3e6;
            }
            
            /* Cancel and No button styling - same as danger buttons */
            QPushButton[text="Cancel"], QPushButton[text="&Cancel"],
            QPushButton[text="No"], QPushButton[text="&No"] {
                background-color: #c53c3c;
                border-color: #d95656;
            }
            
            QPushButton[text="Cancel"]:hover, QPushButton[text="&Cancel"]:hover,
            QPushButton[text="No"]:hover, QPushButton[text="&No"]:hover {
                background-color: #d94545;
                border-color: #e66767;
            }
            
            QPushButton[text="Cancel"]:pressed, QPushButton[text="&Cancel"]:pressed,
            QPushButton[text="No"]:pressed, QPushButton[text="&No"]:pressed {
                background-color: #8b0000;
                border-color: #a01010;
            }
            
            QTextEdit, QPlainTextEdit {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                selection-background-color: #4a90e2;
            }
            
            QLineEdit {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 6px;
                color: #ffffff;
                selection-background-color: #4a90e2;
            }
            
            QLineEdit:focus {
                border-color: #4a90e2;
                background-color: #454545;
            }
        """
        
        dialog.setStyleSheet(dialog_style)
        
        # Force dark title bar on Windows
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(dialog.winId())
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass
                
    except Exception as e:
        pass


def create_dark_messagebox(parent, icon, title, text, buttons=QMessageBox.StandardButton.Ok):
    """
    Create a QMessageBox with dark theme applied
    
    Args:
        parent: Parent widget (can be None)
        icon: QMessageBox.Icon (Information, Warning, Critical, Question)
        title: Dialog title
        text: Dialog text
        buttons: Standard buttons to show
        
    Returns:
        QMessageBox.StandardButton: The button that was clicked
    """
    # Get the main application window as parent if none provided
    if parent is None:
        app = QApplication.instance()
        if app:
            # Try to find a main window
            for widget in app.topLevelWidgets():
                if widget.isWindow() and widget.isVisible():
                    parent = widget
                    break
    
    msg_box = QMessageBox(parent)
    msg_box.setIcon(icon)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStandardButtons(buttons)
    
    # Make sure dialog stays on top and is modal
    msg_box.setModal(True)
    msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    
    # Apply dark theme
    apply_dark_theme_to_dialog(msg_box)
    
    # Center the dialog on screen if no parent
    if parent is None:
        try:
            screen = QApplication.primaryScreen()
            if screen:
                screen_center = screen.geometry().center()
                msg_box.move(screen_center.x() - msg_box.width()//2, 
                           screen_center.y() - msg_box.height()//2)
        except Exception:
            pass  # If centering fails, just use default position
    
    return msg_box.exec()


def show_info_dialog(parent, title, message):
    """Show information dialog with dark theme"""
    return create_dark_messagebox(
        parent, 
        QMessageBox.Icon.Information, 
        title, 
        message, 
        QMessageBox.StandardButton.Ok
    )


def show_warning_dialog(parent, title, message):
    """Show warning dialog with dark theme"""
    return create_dark_messagebox(
        parent, 
        QMessageBox.Icon.Warning, 
        title, 
        message, 
        QMessageBox.StandardButton.Ok
    )


def show_error_dialog(parent, title, message):
    """Show error dialog with dark theme"""
    return create_dark_messagebox(
        parent, 
        QMessageBox.Icon.Critical, 
        title, 
        message, 
        QMessageBox.StandardButton.Ok
    )


def show_question_dialog(parent, title, message):
    """
    Show question dialog with dark theme
    
    Returns:
        bool: True if Yes was clicked, False if No was clicked
    """
    result = create_dark_messagebox(
        parent, 
        QMessageBox.Icon.Question, 
        title, 
        message, 
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    return result == QMessageBox.StandardButton.Yes


def show_confirmation_dialog(parent, title, message):
    """
    Show confirmation dialog with dark theme
    
    Returns:
        bool: True if OK was clicked, False if Cancel was clicked
    """
    result = create_dark_messagebox(
        parent, 
        QMessageBox.Icon.Question, 
        title, 
        message, 
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
    )
    return result == QMessageBox.StandardButton.Ok


# Simple approach - don't use monkey patching to avoid issues
def initialize_dark_dialogs():
    """
    Initialize dark theme for dialogs (simplified approach)
    Just ensure our helper functions are available
    """
    # No monkey patching - just make sure our functions are available
    pass


def _configure_dialog_layout(dialog):
    """Configure dialog with system drives and common locations in sidebar"""
    try:
        from PyQt6.QtCore import QStandardPaths, QUrl
        from PyQt6.QtWidgets import QListView, QTreeView
        import os

        sidebar_urls = []

        # Add system drives (C:, D:, etc.)
        if os.name == 'nt':  # Windows
            import string
            for drive in string.ascii_uppercase:
                drive_path = f"{drive}:\\"
                if os.path.exists(drive_path):
                    sidebar_urls.append(QUrl.fromLocalFile(drive_path))

        # Add common user directories
        locations = [
            QStandardPaths.StandardLocation.DesktopLocation,
            QStandardPaths.StandardLocation.DocumentsLocation,
            QStandardPaths.StandardLocation.DownloadLocation
        ]

        for location in locations:
            try:
                path = QStandardPaths.writableLocation(location)
                if path:
                    sidebar_urls.append(QUrl.fromLocalFile(path))
            except:
                continue

        if sidebar_urls:
            dialog.setSidebarUrls(sidebar_urls)

        # Disable context menus in file dialog to prevent native OS dialogs
        for child in dialog.findChildren(QListView) + dialog.findChildren(QTreeView):
            child.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    except:
        pass


# File Dialog Helper Functions with Dark Theme
def get_open_filename(parent=None, caption="Select File", directory="", filter="All Files (*)"):
    """Open file dialog with dark theme"""
    dialog = QFileDialog(parent)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.setWindowTitle(caption)
    if directory:
        dialog.setDirectory(directory)
    if filter:
        dialog.setNameFilter(filter)
    
    # Force Qt's non-native dialog to ensure theming works
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    
    # Configure tree view in sidebar
    _configure_dialog_layout(dialog)
    
    # Apply dark theme
    apply_dark_theme_to_dialog(dialog)
    
    if dialog.exec():
        selected_files = dialog.selectedFiles()
        if selected_files:
            return selected_files[0], dialog.selectedNameFilter()
    return "", ""


def get_open_filenames(parent=None, caption="Select Files", directory="", filter="All Files (*)"):
    """Open multiple files dialog with dark theme"""
    dialog = QFileDialog(parent)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
    dialog.setWindowTitle(caption)
    if directory:
        dialog.setDirectory(directory)
    if filter:
        dialog.setNameFilter(filter)
    
    # Force Qt's non-native dialog to ensure theming works
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    
    # Configure tree view in sidebar
    _configure_dialog_layout(dialog)
    
    # Apply dark theme
    apply_dark_theme_to_dialog(dialog)
    
    if dialog.exec():
        return dialog.selectedFiles(), dialog.selectedNameFilter()
    return [], ""


def get_save_filename(parent=None, caption="Save File", directory="", filter="All Files (*)"):
    """Save file dialog with dark theme"""
    import re
    import os
    
    dialog = QFileDialog(parent)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setWindowTitle(caption)
    if directory:
        dialog.setDirectory(directory)
    if filter:
        dialog.setNameFilter(filter)
    
    # Set default suffix to ensure file extension is added
    # Only for specific file types, not for "All Files"
    is_all_files_filter = (filter == "All Files (*)" or 
                          filter == "All Files (*.*)" or 
                          "All files" in filter.lower() or
                          filter.strip() == "")
    
    if filter and not is_all_files_filter:
        # Extract the first extension from the filter
        match = re.search(r'\*\.(\w+)', filter)
        if match:
            default_suffix = match.group(1)
            dialog.setDefaultSuffix(default_suffix)
    
    # Force Qt's non-native dialog to ensure theming works
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    
    # Disable the native confirmation dialog - we'll handle it ourselves
    dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, True)
    
    # Configure tree view in sidebar
    _configure_dialog_layout(dialog)
    
    # Apply dark theme
    apply_dark_theme_to_dialog(dialog)
    
    while True:
        if dialog.exec():
            selected_files = dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                
                # If using "All Files" filter, ensure user provided an extension
                if is_all_files_filter:
                    filename = os.path.basename(file_path)
                    if '.' not in filename or filename.endswith('.'):
                        # Show error and retry
                        show_warning_dialog(
                            parent,
                            "Extension Required",
                            "Please specify a file extension (e.g., .txt, .json, .csv)"
                        )
                        continue
                
                # Check if file exists and show our own confirmation dialog
                if os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    result = show_question_dialog(
                        parent,
                        "File Exists",
                        f"The file '{filename}' already exists.\nDo you want to replace it?"
                    )
                    if not result:
                        # User chose No, re-apply dark theme and continue dialog
                        apply_dark_theme_to_dialog(dialog)
                        continue
                
                return file_path, dialog.selectedNameFilter()
        else:
            # User cancelled
            break
    
    return "", ""


def get_existing_directory(parent=None, caption="Select Directory", directory=""):
    """Directory selection dialog with dark theme"""
    dialog = QFileDialog(parent)
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    # Force Qt's non-native dialog to ensure theming works
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setWindowTitle(caption)
    if directory:
        dialog.setDirectory(directory)
    
    # Configure tree view in sidebar
    _configure_dialog_layout(dialog)
    
    # Apply dark theme
    apply_dark_theme_to_dialog(dialog)
    
    if dialog.exec():
        selected_dirs = dialog.selectedFiles()
        if selected_dirs:
            return selected_dirs[0]
    return ""