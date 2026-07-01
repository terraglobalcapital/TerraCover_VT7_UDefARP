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
Main application creator for PyQt6 GUI framework
Creates applications with the same interface as the tkinter version
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QScrollArea, QTextEdit, QTextBrowser,
                             QProgressBar, QPushButton, QGroupBox, QLabel, QMessageBox,
                             QFileDialog, QSplitter, QFrame, QTabWidget)
from PyQt6.QtCore import Qt, QTimer, QEvent, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPixmap, QIcon
from typing import Dict, List, Callable
import os
import re
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import base64

from .dark_theme import apply_dark_theme, get_button_style
from .section_processor import SectionProcessor
from .worker_thread import WorkerThread

# Global variable to store spatial viewer instance for module communication
_global_spatial_viewer = None

def get_global_spatial_viewer():
    """
    Get the global spatial viewer instance.
    
    This function allows modules to access the spatial viewer that's integrated
    into the main GUI application.
    
    Returns:
        SpatialViewer or None: The spatial viewer instance if available, None otherwise
    """
    return _global_spatial_viewer

def update_spatial_viewer_files(files_dict):
    """
    Update the global spatial viewer with module files information.
    
    This function provides a convenient way for modules to update the spatial viewer
    with their input and output file information.
    
    Args:
        files_dict (dict): Dictionary with 'inputs' and 'outputs' keys containing file path lists
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    global _global_spatial_viewer
    
    
    if _global_spatial_viewer is not None:
        try:
            _global_spatial_viewer.set_module_files(files_dict)
            return True
        except Exception:
            return False
    else:
        return False


class OutputRedirector(QObject):
    """Redirector to capture stdout/stderr and send to GUI console"""
    
    output_received = pyqtSignal(str, str)  # message, level
    
    def __init__(self, stream_type="stdout"):
        super().__init__()
        self.stream_type = stream_type
        self.original_stream = getattr(sys, stream_type)
        
    def write(self, message):
        """Write method called by print statements"""
        if message.strip():  # Only process non-empty messages
            level = "error" if self.stream_type == "stderr" else "info"
            # Don't strip the message - preserve newlines for multi-line output
            self.output_received.emit(message, level)

        # Also write to original stream
        self.original_stream.write(message)
        
    def flush(self):
        """Flush method required by stdout/stderr interface"""
        self.original_stream.flush()


class DocumentationWidget(QTextBrowser):
    """Widget for displaying formatted documentation with image support"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenExternalLinks(False)  # Prevent opening links in browser
        self.setStyleSheet("""
            QTextBrowser {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                color: #ffffff;
                padding: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                line-height: 1.4;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 14px;
                border-radius: 0px;
                margin: 0;
                border: none;
            }
            QScrollBar::groove:vertical {
                background-color: #2b2b2b;
                width: 14px;
                border-radius: 0px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #404040;
                border-radius: 3px;
                min-height: 30px;
                margin: 0px;
                border: none;
                width: 14px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #505050;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                width: 0px;
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: #2b2b2b;
                border: none;
            }
            QScrollBar:horizontal {
                background-color: #2b2b2b;
                height: 14px;
                border-radius: 0px;
                margin: 0;
                border: none;
            }
            QScrollBar::groove:horizontal {
                background-color: #2b2b2b;
                height: 14px;
                border-radius: 0px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #404040;
                border-radius: 3px;
                min-width: 30px;
                margin: 0px;
                border: none;
                height: 14px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #505050;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
                border: none;
            }
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                width: 0px;
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background-color: #2b2b2b;
                border: none;
            }
        """)
    
    def set_documentation(self, doc_text: str):
        """Set documentation text with image placeholder processing"""
        # First, extract and replace images with temporary markers
        images_html = {}
        image_counter = [0]  # Use list to allow modification in nested function

        def extract_image(match):
            marker = f"___IMAGE_PLACEHOLDER_{image_counter[0]}___"
            images_html[marker] = self._create_image_html(match)
            image_counter[0] += 1
            return marker

        # Pattern: {{IMAGE:filename:width:height:caption}}
        image_pattern = r'\{\{IMAGE:([^:]+):(\d+):(\d+):([^}]+)\}\}'
        text_with_markers = re.sub(image_pattern, extract_image, doc_text)

        # Convert to HTML with basic formatting (this will escape regular HTML but not our markers)
        html_text = self._convert_to_html(text_with_markers)

        # Replace markers with actual image HTML
        for marker, image_html in images_html.items():
            html_text = html_text.replace(marker, image_html)

        self.setHtml(html_text)
    
    def _create_image_html(self, match) -> str:
        """Create HTML for an image from a regex match object"""
        filename = match.group(1)
        width = match.group(2)
        height = match.group(3)
        caption = match.group(4)

        # Use the same logic as icon detection for consistency
        base_path = _find_terracover_root()

        # Try to find the image in various locations
        possible_paths = [
            os.path.join(base_path, "images", "test", filename),
            os.path.join(base_path, "images", filename),
            os.path.join("terracover", "images", "test", filename),
            os.path.join("terracover", "images", filename),
            os.path.join("images", "test", filename),
            os.path.join("images", filename),
            filename
        ]

        found_path = None
        for path in possible_paths:
            if os.path.exists(path):
                found_path = path
                break

        if found_path:
            ext = os.path.splitext(filename)[1].lower()
            mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.bmp': 'image/bmp'}
            mime = mime_map.get(ext, 'image/png')
            with open(found_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            return f'<div style="text-align: center; margin: 10px 0;"><img src="data:{mime};base64,{b64}" width="{width}" height="{height}" style="border: 1px solid #555555; border-radius: 4px;"><br><i style="color: #888888; font-size: 10px;">{caption}</i></div>'
        else:
            searched_info = f"Searched paths: {'; '.join([p for p in possible_paths if not os.path.isabs(p) or len(p) < 100])}"
            return f'<div style="text-align: center; margin: 10px 0; color: #ff6666; font-style: italic;">[IMAGE NOT FOUND: {filename}]<br><i style="color: #888888; font-size: 9px;">{caption}</i><br><i style="color: #666666; font-size: 8px;">{searched_info}</i></div>'
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#39;'))

    def _convert_to_html(self, text: str) -> str:
        """Convert text to HTML with basic formatting"""
        # Split into lines for processing
        lines = text.strip().split('\n')
        html_lines = []
        current_indent = 0  # Track current indentation level
        in_code_block = False  # Track if we're inside a code block
        code_lines = []  # Store code block lines

        for line in lines:
            original_line = line
            line = line.strip()

            # Check for code block markers
            if line == '(CODE)':
                in_code_block = True
                code_lines = []
                continue
            elif line == '(/CODE)':
                in_code_block = False
                # Render accumulated code block with preserved spacing
                code_content = '\n'.join(code_lines)
                html_lines.append(f'<pre style="background-color: #353535; color: #d4d4d4; padding: 10px; border-radius: 4px; border: 1px solid #555555; font-family: \'Consolas\', \'Monaco\', monospace; font-size: 11px; margin: 10px 0; overflow-x: auto;">{self._escape_html(code_content)}</pre>')
                code_lines = []
                continue

            # If inside code block, accumulate lines without processing
            if in_code_block:
                code_lines.append(original_line.rstrip())
                continue

            if not line:
                # Use a paragraph with minimal margin for single line spacing
                html_lines.append('<p style="margin: 0; line-height: 0.5em;">&nbsp;</p>')
                # Reset indent on empty lines
                current_indent = 0
            elif line.startswith('(HD1)'):
                # Main headers marked with (HD1) - always reset indent
                content = self._escape_html(line[5:].strip()).upper()  # Remove (HD1) marker, escape HTML, convert to uppercase
                html_lines.append(f'<h3 style="color: #4a90e2; margin: 15px 0 10px 0;">{content}</h3>')
                current_indent = 0  # Reset indent after header
            elif line.startswith('(HD2)'):
                # Sub headers marked with (HD2) - always reset indent
                content = self._escape_html(line[5:].strip()).upper()  # Remove (HD2) marker, escape HTML, convert to uppercase
                html_lines.append(f'<h4 style="color: #ffffff; font-weight: bold; margin: 10px 0 5px 0;">{content}</h4>')
                current_indent = 0  # Reset indent after header
            elif line.startswith('(HD3)'):
                # Sub-subsection headers marked with (HD3) - always reset indent
                content = self._escape_html(line[5:].strip())  # Remove (HD3) marker and escape HTML
                html_lines.append(f'<h4 style="color: #cccccc; font-style: italic; margin: 8px 0 4px 0;">{content}</h4>')
                current_indent = 0  # Reset indent after header
            elif line.startswith('*'):
                # Handle asterisks as tab indentation
                asterisk_count = 0
                for char in line:
                    if char == '*':
                        asterisk_count += 1
                    else:
                        break

                content = self._escape_html(line[asterisk_count:].strip())
                indent_px = asterisk_count * 20  # 20px per asterisk/tab
                html_lines.append(f'<p style="margin: 3px 0 3px {indent_px}px;">{content}</p>')
                current_indent = indent_px  # Track indent level
            elif line.startswith('•') or line.startswith('-'):
                # Regular bullet points - use current indent or default
                content = self._escape_html(line[1:].strip())
                # Only apply current_indent if it's from asterisks, otherwise use default 20px
                base_indent = 20
                html_lines.append(f'<p style="margin: 3px 0 3px {base_indent}px;">• {content}</p>')
            elif line.startswith('[IMAGE:'):
                # Image placeholders
                html_lines.append(f'<p style="color: #888888; font-style: italic; margin: 10px 0;">{line}</p>')
            elif '___IMAGE_PLACEHOLDER_' in line:
                # Don't escape image placeholder markers - they will be replaced with HTML later
                html_lines.append(line)
                current_indent = 0
            else:
                # Regular text
                content = self._escape_html(line)
                html_lines.append(f'<p style="margin: 5px 0;">{content}</p>')
                # Reset indent on regular text
                current_indent = 0

        return ''.join(html_lines)


class ConsoleWidget(QTextEdit):
    """Console widget for displaying progress and log messages"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        
        # Setup output redirectors for stdout and stderr
        self.stdout_redirector = OutputRedirector("stdout")
        self.stderr_redirector = OutputRedirector("stderr")
        
        # Connect redirectors to console
        self.stdout_redirector.output_received.connect(self.add_backend_output)
        self.stderr_redirector.output_received.connect(self.add_backend_output)
        
        # Redirect system streams
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector
        self.setStyleSheet("""
            QTextEdit {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 6px;
                color: #90ee90;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 8px;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 14px;
                border-radius: 0px;
                margin: 0;
                border: none;
            }
            QScrollBar::groove:vertical {
                background-color: #2b2b2b;
                width: 14px;
                border-radius: 0px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #404040;
                border-radius: 3px;
                min-height: 30px;
                margin: 0px;
                border: none;
                width: 14px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #505050;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                width: 0px;
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: #2b2b2b;
                border: none;
            }
            QScrollBar:horizontal {
                background-color: #2b2b2b;
                height: 14px;
                border-radius: 0px;
                margin: 0;
                border: none;
            }
            QScrollBar::groove:horizontal {
                background-color: #2b2b2b;
                height: 14px;
                border-radius: 0px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #404040;
                border-radius: 3px;
                min-width: 30px;
                margin: 0px;
                border: none;
                height: 14px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #505050;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
                border: none;
            }
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                width: 0px;
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background-color: #2b2b2b;
                border: none;
            }
        """)
        
        # Add initial message
        self.add_log("Application started. Ready for input.")
        self.add_log("Console capturing backend output (stdout/stderr).", "info")
    
    def add_log(self, message: str, level: str = "info"):
        """Add a log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding based on level
        colors = {
            "info": "#90ee90",
            "warning": "#ffff00", 
            "error": "#ff0000",
            "success": "#00ffff"
        }
        color = colors.get(level, "#90ee90")
        
        formatted_message = f'<span style="color: {color};">[{timestamp}] {message}</span><br>'
        self.insertHtml(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """Clear the console"""
        self.clear()
        self.add_log("Console cleared.")
    
    def add_backend_output(self, message: str, level: str = "info"):
        """Add backend output (stdout/stderr) to console with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color coding based on level
        colors = {
            "info": "#ffffff",      # White for normal output
            "warning": "#ffff00",
            "error": "#ff0000",     # Red for stderr
            "success": "#00ffff"
        }
        color = colors.get(level, "#ffffff")

        # Replace newlines with HTML line breaks to preserve formatting
        # Split by newlines and handle each line
        lines = message.rstrip('\n').split('\n')

        # For multi-line messages, only add timestamp to first line
        if len(lines) > 1:
            # First line with timestamp
            formatted_message = f'<span style="color: {color};">[{timestamp}] {lines[0]}</span><br>'
            self.insertHtml(formatted_message)

            # Remaining lines without timestamp (indented to align with first line content)
            for line in lines[1:]:
                # Add spacing to align with content after timestamp
                formatted_line = f'<span style="color: {color};">           {line}</span><br>'
                self.insertHtml(formatted_line)
        else:
            # Single line - original behavior
            formatted_message = f'<span style="color: {color};">[{timestamp}] {message.rstrip()}</span><br>'
            self.insertHtml(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def restore_streams(self):
        """Restore original stdout/stderr when console is destroyed"""
        if hasattr(self, 'stdout_redirector'):
            sys.stdout = self.stdout_redirector.original_stream
        if hasattr(self, 'stderr_redirector'):
            sys.stderr = self.stderr_redirector.original_stream


class MainApplication(QMainWindow):
    """Main application window"""
    
    def __init__(self, title: str, documentation: str, run_function: Callable = None,
                 validate_function: Callable = None, num_columns: int = 3, sections: Dict = None,
                 include_spatial_viewer: bool = True, include_console_tab: bool = True,
                 include_control_buttons: bool = True, include_progress_bar: bool = True):
        super().__init__()

        self.title = title
        self.documentation = documentation
        self.run_function = run_function
        self.validate_function = validate_function
        self.num_columns = num_columns
        self.sections = sections or {}
        self.include_spatial_viewer = include_spatial_viewer
        self.include_console_tab = include_console_tab
        self.include_control_buttons = include_control_buttons
        self.include_progress_bar = include_progress_bar
        
        self.section_processor = None
        self.worker_thread = None
        self._error_dialog_open = False  # Flag to prevent multiple error dialogs

        # Set up the UI
        self.setup_ui()
        
        # Apply theme
        apply_dark_theme(QApplication.instance())
        
        # Initialize thread-safe dialog manager
        try:
            from .thread_safe_dialogs import get_global_dialog_manager
            get_global_dialog_manager()
        except Exception:
            pass  # Silent fail - fallback to tkinter will work
        
        # Force dark window frame (Windows specific)
        try:
            # Try to set dark title bar on Windows
            if sys.platform == "win32":
                import ctypes
                from ctypes import wintypes
                
                # Get window handle with basic validation
                hwnd = int(self.winId())
                if hwnd != 0:  # Only check for non-zero handle
                    # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                    )
        except Exception:
            pass  # Ignore if unable to set dark title bar
    
    def _calculate_dynamic_window_size(self):
        """Calculate window size based on content to avoid excessive spacing"""
        # Count total fields across all sections
        total_fields = 0
        section_count = len(self.sections)
        total_height = 0

        # Base height for window frame, title, tabs, buttons, etc.
        base_height = 220

        # Height per section header
        section_header_height = 40 * section_count
        total_height += base_height + section_header_height

        # Calculate height per field based on type
        for section_name, fields_list in self.sections.items():
            for field_dict in fields_list:
                total_fields += len(field_dict)
                # Check each field's type for specific height requirements
                for param_name, param_config in field_dict.items():
                    entry_type = param_config.get('entry_type', '')

                    # Assign specific heights for different widget types
                    if entry_type == 'class_definition_table':
                        total_height += 650  # Large height for class definition table
                    elif entry_type == 'transition_table':
                        total_height += 450  # Medium-large height for transition table
                    elif entry_type == 'code editor':
                        total_height += 400  # Large height for code editor widget
                    elif entry_type == 'code_editor_with_console':
                        total_height += 450  # Large height for code editor with buttons
                    elif entry_type == 'interactive_console':
                        total_height += 350  # Height for interactive console
                    elif entry_type in {'dynamic rows', 'dynamic rows with file'}:
                        total_height += 200  # Medium height for dynamic rows
                    elif entry_type in {'browse multiple', 'multiple checkbox'}:
                        total_height += 150  # Medium height for multiple selections
                    else:
                        total_height += 55  # Standard height for simple fields

        # Get available screen geometry to ensure window fits
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            # Use 90% of available screen height to leave space for taskbar/dock
            available_height = int(screen_geometry.height() * 0.9)
            available_width = int(screen_geometry.width() * 0.9)
        else:
            # Fallback if screen info not available
            available_height = 900
            available_width = 1200

        # Base dimensions
        min_width = 800
        max_width = min(800, available_width)  # Adjust to screen width
        min_height = 400
        max_height = min(900, available_height)  # Adjust to screen height

        # Apply limits
        final_height = max(min_height, min(total_height, max_height))
        final_width = min_width  # Keep width constant for consistency

        return final_width, final_height
    
    def _apply_dark_theme_to_messagebox(self, msg_box):
        """Apply dark theme to a QMessageBox using centralized theming"""
        try:
            from .dialog_theming import apply_dark_theme_to_dialog
            apply_dark_theme_to_dialog(msg_box)
        except Exception:
            pass  # Ignore styling errors
    
    
    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle(self.title)
        
        # Calculate dynamic window size based on content
        window_width, window_height = self._calculate_dynamic_window_size()
        self.setGeometry(100, 100, window_width, window_height)
        
        # Ensure clean window title (especially important for Docker environments)
        self.setObjectName("MainApplicationWindow")
        
        # Set X11 window class properties to control how VcXsrv shows the title
        try:
            # Force window class and instance names (X11 specific)
            clean_title = self.title.replace(' ', '_').replace('-', '_')
            self.setProperty("_q_xcb_wm_class", f"{clean_title}\0TerraCove")
            
            # Additional X11 window manager properties
            self.setProperty("WM_CLASS", clean_title)
            self.setProperty("WM_NAME", self.title)
            self.setProperty("_NET_WM_NAME", self.title)
            
        except Exception as e:
            pass  # Silently ignore X11 property errors
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Add centered module title
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #4a90e2;
                margin: 10px 0;
                padding: 8px;
                background-color: transparent;
                border: none;
            }
        """)
        main_layout.addWidget(title_label)
        
        # Create main tab widget with Analysis, Documentation, and Console tabs
        self.create_main_tab_widget(main_layout)
        
        # Hide status bar
        self.statusBar().hide()
    
    
    def create_main_tab_widget(self, parent_layout):
        """Create main tab widget with Analysis, Documentation, and Console tabs"""
        # Create main tab widget
        self.main_tab_widget = QTabWidget()
        
        # Platform-specific tab styling
        import sys
        if sys.platform == "darwin":
            # macOS specific styling - wider tabs, left aligned
            tab_style = """
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #353535;
                    border-radius: 6px;
                }
                QTabBar::tab {
                    background-color: #404040;
                    border: 1px solid #555555;
                    padding: 8px 20px;
                    color: #ffffff;
                    margin-right: 2px;
                    border-radius: 4px 4px 0px 0px;
                    font-size: 11px;
                    font-weight: bold;
                    min-width: 100px;
                    text-align: left;
                }
                QTabBar::tab:selected {
                    background-color: #4a90e2;
                    border-color: #4a90e2;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #505050;
                }
                QTabBar {
                    alignment: left;
                }
            """
        else:
            # Default styling for Windows/Linux
            tab_style = """
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #353535;
                    border-radius: 6px;
                }
                QTabBar::tab {
                    background-color: #404040;
                    border: 1px solid #555555;
                    padding: 6px 12px;
                    color: #ffffff;
                    margin-right: 2px;
                    border-radius: 4px 4px 0px 0px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QTabBar::tab:selected {
                    background-color: #4a90e2;
                    border-color: #4a90e2;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #505050;
                }
            """
        
        self.main_tab_widget.setStyleSheet(tab_style)
        
        # Create Analysis tab (main form)
        self.create_analysis_tab()
        
        # Create Documentation tab
        if self.documentation:
            self.create_documentation_tab()

        # Create Console tab (only if requested)
        if self.include_console_tab:
            self.create_console_tab()

        # Create Spatial Viewer tab (only if requested)
        if self.include_spatial_viewer:
            self.create_spatial_viewer_tab()

        # Add main tab widget to parent layout
        parent_layout.addWidget(self.main_tab_widget)
    
    def create_analysis_tab(self):
        """Create the Analysis tab with the main form"""
        analysis_widget = QWidget()
        analysis_layout = QVBoxLayout(analysis_widget)
        analysis_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create scroll area for form fields
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.form_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.form_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #2b2b2b;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #2b2b2b;
            }
        """)
        
        # Create form content widget
        self.form_content = QWidget()
        self.form_content.setStyleSheet("QWidget { background-color: #2b2b2b; }")
        self.form_content_layout = QVBoxLayout(self.form_content)
        self.form_content_layout.setContentsMargins(5, 5, 5, 5)
        
        self.form_scroll.setWidget(self.form_content)
        analysis_layout.addWidget(self.form_scroll)

        # Create progress section (only if requested)
        if self.include_progress_bar:
            self.create_progress_section(analysis_layout)

        # Create buttons section (only if requested)
        if self.include_control_buttons:
            self.create_buttons_section(analysis_layout)
        
        # Add Analysis tab
        self.main_tab_widget.addTab(analysis_widget, "Analysis")
    
    def create_documentation_tab(self):
        """Create the Documentation tab"""
        doc_widget = QWidget()
        doc_layout = QVBoxLayout(doc_widget)
        doc_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create documentation widget
        self.doc_widget = DocumentationWidget()
        self.doc_widget.set_documentation(self.documentation)
        doc_layout.addWidget(self.doc_widget)
        
        # Add Documentation tab
        self.main_tab_widget.addTab(doc_widget, "Documentation")
    
    def create_console_tab(self):
        """Create the Console tab"""
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)
        console_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create console
        self.console = ConsoleWidget()
        console_layout.addWidget(self.console)
        
        # Console controls
        console_controls = QHBoxLayout()
        
        clear_console_btn = QPushButton("Clear Console")
        clear_console_btn.clicked.connect(self.console.clear_log)
        clear_console_btn.setStyleSheet("""
            QPushButton {
                background-color: #c53c3c;
                border: 1px solid #d95656;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                max-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover:enabled {
                background-color: #d94545;
            }
            QPushButton:disabled {
                background-color: #666666;
                border: 1px solid #777777;
                color: #aaaaaa;
            }
        """)
        console_controls.addWidget(clear_console_btn)
        
        copy_console_btn = QPushButton("Copy Console")
        copy_console_btn.clicked.connect(self.copy_console)
        copy_console_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff8c00;
                border: 1px solid #ffa533;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                max-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ff9f33;
            }
        """)
        console_controls.addWidget(copy_console_btn)
        
        save_console_btn = QPushButton("Save Console")
        save_console_btn.clicked.connect(self.save_console)
        save_console_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                border: 1px solid #6ba3e6;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                max-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #6ba3e6;
            }
        """)
        console_controls.addWidget(save_console_btn)
        
        console_controls.addStretch()
        console_layout.addLayout(console_controls)
        
        # Add Console tab
        self.main_tab_widget.addTab(console_widget, "Console")
    
    def create_spatial_viewer_tab(self):
        """Create the Spatial Viewer tab - Not available in standalone version"""
        global _global_spatial_viewer
        # Spatial viewer is not available in standalone version
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_label = QLabel("Spatial Viewer not available in standalone version")
        error_label.setStyleSheet("color: #ffaaaa; font-size: 14px; padding: 20px;")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.addWidget(error_label)
        self.main_tab_widget.addTab(error_widget, "Spatial Viewer")
        _global_spatial_viewer = None
    
    def create_progress_section(self, parent_layout):
        """Create progress section"""
        progress_group = QGroupBox("")
        progress_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: none;
                font-weight: bold;
                margin-top: 5px;
            }
            QGroupBox::title {
                color: #ffffff;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_label = QLabel("Ready to start analysis")
        self.progress_label.setStyleSheet("QLabel { color: #ffffff; }")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)  # Make it taller
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #404040;
                color: #ffffff;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                border-radius: 3px;
                background-color: #4a90e2;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        parent_layout.addWidget(progress_group)
    
    def create_buttons_section(self, parent_layout):
        """Create control buttons section"""
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(2, 5, 2, 2)
        
        # Save configuration button
        self.save_btn = QPushButton("Save Arguments")
        self.save_btn.clicked.connect(self.save_arguments)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                border: 1px solid #6ba3e6;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                max-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #6ba3e6;
            }
        """)
        button_layout.addWidget(self.save_btn)
        
        # Load configuration button
        self.load_btn = QPushButton("Load Arguments")
        self.load_btn.clicked.connect(self.load_arguments)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                border: 1px solid #6ba3e6;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                max-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #6ba3e6;
            }
        """)
        button_layout.addWidget(self.load_btn)
        
        # Reset defaults button
        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.clicked.connect(self.reset_defaults)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #c53c3c;
                border: 1px solid #d95656;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                max-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover:enabled {
                background-color: #d94545;
            }
            QPushButton:disabled {
                background-color: #666666;
                border: 1px solid #777777;
                color: #aaaaaa;
            }
        """)
        button_layout.addWidget(self.reset_btn)
        
        # Add stretch
        button_layout.addStretch()
        
        # Validate inputs button
        if self.validate_function:
            self.validate_btn = QPushButton("Validate Inputs")
            self.validate_btn.clicked.connect(self.validate_inputs)
            self.validate_btn.setStyleSheet(get_button_style("warning"))
            button_layout.addWidget(self.validate_btn)
        
        # Run analysis button
        if self.run_function:
            self.run_btn = QPushButton("Run Analysis")
            self.run_btn.clicked.connect(self.run_analysis)
            self.run_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d8b47;
                    border: 1px solid #3ba55a;
                    color: white;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 4px;
                    max-height: 30px;
                    font-size: 11px;
                }
                QPushButton:hover:enabled {
                    background-color: #3ba55a;
                    border: 1px solid #4fc269;
                }
                QPushButton:disabled {
                    background-color: #666666;
                    border: 1px solid #777777;
                    color: #aaaaaa;
                }
            """)
            button_layout.addWidget(self.run_btn)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_analysis)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #c53c3c;
                border: 1px solid #d95656;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                max-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover:enabled {
                background-color: #d94545;
            }
            QPushButton:disabled {
                background-color: #666666;
                border: 1px solid #777777;
                color: #aaaaaa;
            }
        """)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)
        
        parent_layout.addWidget(button_frame)
    
    def set_section_processor(self, processor: SectionProcessor):
        """Set the section processor"""
        self.section_processor = processor
        
        # Connect signals
        processor.values_changed.connect(self.on_values_changed)
        
        # Add processor to form content
        self.form_content_layout.addWidget(processor)
        
        # Apply any default values after a short delay
        QTimer.singleShot(100, self.apply_default_values)
    
    def apply_default_values(self):
        """Apply default values to all fields"""
        if self.section_processor:
            # Reset to defaults and then apply them
            for param_name, config in self.section_processor.field_configs.items():
                if param_name in self.section_processor.field_widgets:
                    widget = self.section_processor.field_widgets[param_name]
                    if hasattr(widget, 'set_value') and config.default_value:
                        try:
                            widget.set_value(config.default_value)
                        except Exception as e:
                            pass
    
    def on_values_changed(self):
        """Handle when field values change"""
        # Status bar is hidden, so no need to update it
        pass
    
    def save_arguments(self):
        """Save current arguments to file"""
        if not self.section_processor:
            return
        
        from .dialog_theming import get_save_filename
        file_path, _ = get_save_filename(
            self, "Save Arguments", 
            f"{self.title}_config.json", 
            "JSON files (*.json)"
        )
        
        if file_path:
            if self.section_processor.save_configuration(file_path):
                self.console.add_log(f"Configuration saved to: {file_path}", "success")
                msg = QMessageBox(QMessageBox.Icon.Information, "Success", "Configuration saved successfully!", QMessageBox.StandardButton.Ok, self)
                self._apply_dark_theme_to_messagebox(msg)
                msg.exec()
            else:
                self.console.add_log("Failed to save configuration", "error")
                msg = QMessageBox(QMessageBox.Icon.Critical, "Error", "Failed to save configuration!", QMessageBox.StandardButton.Ok, self)
                self._apply_dark_theme_to_messagebox(msg)
                msg.exec()
    
    def load_arguments(self):
        """Load arguments from file"""
        if not self.section_processor:
            return
        
        from .dialog_theming import get_open_filename
        file_path, _ = get_open_filename(
            self, "Load Arguments", 
            "", "JSON files (*.json)"
        )
        
        if file_path:
            if self.section_processor.load_configuration(file_path):
                self.console.add_log(f"Configuration loaded from: {file_path}", "success")
                msg = QMessageBox(QMessageBox.Icon.Information, "Success", "Configuration loaded successfully!", QMessageBox.StandardButton.Ok, self)
                self._apply_dark_theme_to_messagebox(msg)
                msg.exec()
            else:
                self.console.add_log("Failed to load configuration", "error")
                msg = QMessageBox(QMessageBox.Icon.Critical, "Error", "Failed to load configuration!", QMessageBox.StandardButton.Ok, self)
                self._apply_dark_theme_to_messagebox(msg)
                msg.exec()
    
    def reset_defaults(self):
        """Reset all fields to default values"""
        msg = QMessageBox(QMessageBox.Icon.Question, "Reset Defaults", 
                         "Are you sure you want to reset all fields to their default values?",
                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        self._apply_dark_theme_to_messagebox(msg)
        reply = msg.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.section_processor:
                self.section_processor.reset_to_defaults()
                self.console.add_log("All fields reset to default values", "info")
    
    def validate_inputs(self):
        """Validate all inputs"""
        if not self.section_processor:
            return
        
        self.console.add_log("Validating inputs...", "info")
        
        # Check required fields
        errors = self.section_processor.validate_required_fields()
        
        # Run custom validation if provided
        if self.validate_function:
            try:
                values = self.section_processor.get_all_values()
                custom_result = self.validate_function(**values)
                if isinstance(custom_result, list):
                    errors.extend(custom_result)
                elif custom_result is False:
                    errors.append("Custom validation failed")
            except Exception as e:
                errors.append(f"Validation error: {str(e)}")
        
        if errors:
            error_msg = "Validation errors found:\n\n" + "\n".join(f"• {error}" for error in errors)
            self.console.add_log("Validation failed", "error")
            for error in errors:
                self.console.add_log(f"  • {error}", "error")
            msg = QMessageBox(QMessageBox.Icon.Warning, "Validation Errors", error_msg, QMessageBox.StandardButton.Ok, self)
            self._apply_dark_theme_to_messagebox(msg)
            msg.exec()
        else:
            self.console.add_log("Validation successful", "success")
            msg = QMessageBox(QMessageBox.Icon.Information, "Validation Success", "All inputs are valid!", QMessageBox.StandardButton.Ok, self)
            self._apply_dark_theme_to_messagebox(msg)
            msg.exec()
    
    def run_analysis(self):
        """Run the analysis function"""
        if not self.run_function or not self.section_processor:
            return
        
        # Validate first
        errors = self.section_processor.validate_required_fields()
        if errors:
            self.validate_inputs()
            return
        
        # Get all values
        values = self.section_processor.get_all_values()
        
        self.console.add_log("Starting analysis...", "info")
        self.console.add_log(f"Parameters: {len(values)} fields configured", "info")
        
        # Start worker thread
        self.worker_thread = WorkerThread(self.run_function, **values)
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.finished.connect(self.analysis_finished)
        
        # Update UI for running state
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting analysis...")
        
        self.worker_thread.start()
    
    def cancel_analysis(self):
        """Cancel the running analysis"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.console.add_log("Cancelling analysis...", "warning")
            self.worker_thread.cancel()
            self.worker_thread.wait()
    
    def update_progress(self, message: str, percent: float):
        """Update progress bar and message"""
        self.progress_label.setText(message)
        self.progress_bar.setValue(int(percent * 100))
        self.console.add_log(f"Progress: {message} ({int(percent * 100)}%)", "info")
    
    def analysis_finished(self, success: bool, message: str):
        """Handle analysis completion"""
        # Reset UI
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        if success:
            self.progress_label.setText("Analysis completed successfully!")
            self.console.add_log("Analysis completed successfully!", "success")
            msg = QMessageBox(QMessageBox.Icon.Information, "Success", "Analysis completed successfully!", QMessageBox.StandardButton.Ok, self)
            self._apply_dark_theme_to_messagebox(msg)
            msg.exec()
        else:
            self.progress_label.setText("Analysis failed or was cancelled")
            self.console.add_log(f"Analysis failed: {message}", "error")

            # Don't show "Analysis Failed" dialog for validation errors,
            # as validation errors are already shown by the thread-safe dialog system
            # Also prevent multiple dialogs from opening simultaneously
            if "validation errors" not in message.lower() and not self._error_dialog_open:
                self._error_dialog_open = True
                msg = QMessageBox(QMessageBox.Icon.Critical, "Analysis Failed", message, QMessageBox.StandardButton.Ok, self)
                self._apply_dark_theme_to_messagebox(msg)
                msg.exec()
                self._error_dialog_open = False
            else:
                # For validation errors, just log them - the specific errors were already shown
                if "validation errors" in message.lower():
                    self.console.add_log("Validation errors were already displayed", "info")

        self.worker_thread = None
    
    def copy_console(self):
        """Copy console content to clipboard"""
        try:
            # Get plain text from console
            console_text = self.console.toPlainText()
            
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(console_text)
            
            self.console.add_log("Console content copied to clipboard", "success")
            msg = QMessageBox(QMessageBox.Icon.Information, "Copy Console", "Console content has been copied to clipboard!", QMessageBox.StandardButton.Ok, self)
            self._apply_dark_theme_to_messagebox(msg)
            msg.exec()
            
        except Exception as e:
            self.console.add_log(f"Failed to copy console: {str(e)}", "error")
            msg = QMessageBox(QMessageBox.Icon.Critical, "Copy Failed", f"Failed to copy console content: {str(e)}", QMessageBox.StandardButton.Ok, self)
            self._apply_dark_theme_to_messagebox(msg)
            msg.exec()
    
    def save_console(self):
        """Save console content to a text file"""
        try:
            # Get plain text from console
            console_text = self.console.toPlainText()
            
            # Open save dialog
            from .dialog_theming import get_save_filename
            file_path, _ = get_save_filename(
                self, "Save Console Output", 
                f"console_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 
                "Text files (*.txt);;All files (*.*)"
            )
            
            if file_path:
                # Save to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Console Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("="*50 + "\n\n")
                    f.write(console_text)
                
                self.console.add_log(f"Console saved to: {file_path}", "success")
                msg = QMessageBox(QMessageBox.Icon.Information, "Save Console", f"Console content has been saved to:\n{file_path}", QMessageBox.StandardButton.Ok, self)
                self._apply_dark_theme_to_messagebox(msg)
                msg.exec()
            
        except Exception as e:
            self.console.add_log(f"Failed to save console: {str(e)}", "error")
            msg = QMessageBox(QMessageBox.Icon.Critical, "Save Failed", f"Failed to save console content: {str(e)}", QMessageBox.StandardButton.Ok, self)
            self._apply_dark_theme_to_messagebox(msg)
            msg.exec()
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Restore original stdout/stderr streams
        if hasattr(self, 'console'):
            self.console.restore_streams()
        
        # Accept the close event
        event.accept()


def _find_terracover_root():
    """Find the terracover root directory dynamically"""
    # Get the current script directory and find terracover root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Navigate up to find the terracover root directory
    terracover_root = current_dir
    while terracover_root and not os.path.basename(terracover_root) == 'terracover':
        parent_dir = os.path.dirname(terracover_root)
        if parent_dir == terracover_root:  # Reached root
            break
        terracover_root = parent_dir
    
    # If we found terracover directory, use it as base
    if os.path.basename(terracover_root) == 'terracover':
        return terracover_root
    else:
        # Fallback to current working directory
        base_path = os.getcwd()
        # Try to find terracover in current working directory
        if os.path.exists(os.path.join(base_path, 'terracover')):
            return os.path.join(base_path, 'terracover')
        elif os.path.exists(os.path.join(base_path, 'TerraCover', 'terracover')):
            return os.path.join(base_path, 'TerraCover', 'terracover')
        return base_path


def _find_icon_path():
    """Find the application icon using dynamic path detection"""
    base_path = _find_terracover_root()
    
    # Try to find the icon in various locations, prioritizing .ico over .png
    possible_paths = [
        os.path.join(base_path, "images", "logo.ico"),
        os.path.join(base_path, "images", "logo.png"),
        os.path.join("terracover", "images", "logo.ico"),
        os.path.join("terracover", "images", "logo.png"),
        os.path.join("images", "logo.ico"),
        os.path.join("images", "logo.png"),
        "logo.ico",
        "logo.png"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    
    return None


def create_application(title: str, documentation: str, sections: Dict[str, List[Dict]],
                      run_function: Callable = None, validate_function: Callable = None,
                      section_defaults: Dict[str, bool] = None, num_columns: int = 3,
                      include_spatial_viewer: bool = True, include_console_tab: bool = True,
                      include_control_buttons: bool = True, include_progress_bar: bool = True) -> None:
    """Create and run a complete PyQt6 application

    Args:
        include_spatial_viewer (bool): If True, includes Spatial Viewer tab. Default True.
        include_console_tab (bool): If True, includes Console tab. Default True.
        include_control_buttons (bool): If True, includes Save/Load/Run/Cancel buttons. Default True.
        include_progress_bar (bool): If True, includes progress bar. Default True.
    """
    
    # Platform-specific Qt environment setup
    import platform
    system = platform.system().lower()
    
    if system == 'linux' and os.environ.get('DISPLAY'):
        # Docker/Linux specific Qt environment setup
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
        os.environ['QT_X11_NO_MITSHM'] = '1'
        os.environ['QT_ASSUME_STDERR_HAS_CONSOLE'] = '1'
    elif system == 'darwin':
        # macOS specific Qt environment setup
        os.environ['QT_QPA_PLATFORM'] = 'cocoa'
        
        # Additional X11/VcXsrv specific settings to control window title
        os.environ['QT_XCB_GL_INTEGRATION'] = 'none'
        os.environ['QT_LOGGING_RULES'] = 'qt.qpa.xcb.info=false'
        
        # Force clean window class and resource names
        os.environ['RESOURCE_NAME'] = title.replace(' ', '_').replace('-', '_')
        os.environ['RESOURCE_CLASS'] = 'TerraCove'
    elif system == 'windows':
        # Windows-specific settings
        if 'QT_QPA_PLATFORM' in os.environ:
            del os.environ['QT_QPA_PLATFORM']  # Let Qt auto-detect on Windows
    
    # Create QApplication if it doesn't exist
    app = QApplication.instance()
    if app is None:
        # Use clean application arguments for Docker
        clean_argv = [title]  # Use title as application name
        app = QApplication(clean_argv)
    
    # Set application properties (more explicit for Docker environments)
    app.setApplicationName(title)
    app.setOrganizationName("TerraCove")
    app.setApplicationDisplayName(title)
    app.setApplicationVersion("1.0")
    
    # Force dark theme for application
    try:
        if system == 'windows':
            # Windows-specific dark mode settings
            app.setStyleSheet("QApplication { background-color: #2b2b2b; }")
            # Set palette for dark theme
            from PyQt6.QtGui import QPalette, QColor
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Base, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(64, 64, 64))
            app.setPalette(palette)
    except Exception:
        pass
    
    # Set application icon using dynamic path detection
    icon_path = _find_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    
    # Create main window
    window = MainApplication(title, documentation, run_function, validate_function, num_columns, sections,
                            include_spatial_viewer, include_console_tab, include_control_buttons, include_progress_bar)
    
    # Also set the window icon for the main window using dynamic path detection
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))
    
    # Convert section_defaults keys to uppercase if provided
    if section_defaults:
        section_defaults = {key.upper(): value for key, value in section_defaults.items()}
    
    # Create and set up section processor
    processor = SectionProcessor(sections, window, section_defaults, module_title=title)
    processor.create_gui_elements(processor)  # Create elements within processor
    window.set_section_processor(processor)
    
    # Force clean window title (important for Docker)
    window.setWindowTitle(title)
    
    # Show window
    window.show()
    
    # Final title setting for Docker compatibility
    QTimer.singleShot(100, lambda: window.setWindowTitle(title))
    
    # Start event loop if not already running
    if not app.closingDown():
        sys.exit(app.exec())