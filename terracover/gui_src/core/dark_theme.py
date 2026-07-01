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
Dark theme stylesheet for PyQt6 GUI framework
Based on the leakage.py layout with enhanced dark mode styling
"""

DARK_THEME_STYLESHEET = """
QMainWindow {
    background-color: #2b2b2b;
    color: #ffffff;
}

/* Title Bar Styling */
QMainWindow::title {
    background-color: #353535;
    color: #ffffff;
    padding: 5px;
}

/* Title Bar Buttons */  
QMainWindow::close-button, QMainWindow::minimize-button, QMainWindow::maximize-button {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 2px;
}

QMainWindow::close-button:hover {
    background-color: #c53c3c;
}

QMainWindow::minimize-button:hover, QMainWindow::maximize-button:hover {
    background-color: #4a90e2;
}

QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
    selection-background-color: #4a90e2;
}

/* Ensure all content areas have consistent background */
QWidget[class="content"] {
    background-color: #2b2b2b;
}

/* Group Boxes */
QGroupBox {
    font-weight: bold;
    border: 1px solid #555555;
    border-radius: 6px;
    margin-top: 1ex;
    padding-top: 8px;
    background-color: #353535;
    color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px 0 8px;
    color: #ffffff;
    background-color: #2b2b2b;
}

/* Buttons */
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
}

QPushButton:hover {
    background-color: #4a90e2;
    border-color: #6ba3e6;
}

QPushButton:pressed {
    background-color: #357abd;
    border-color: #5a9dd8;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    border-color: #404040;
    color: #888888;
}

/* Success Button (Run Analysis) */
QPushButton[class="success"] {
    background-color: #2d8b47;
    border-color: #3ba55a;
}

QPushButton[class="success"]:hover {
    background-color: #35a253;
    border-color: #4bb866;
}

QPushButton[class="success"]:pressed {
    background-color: #1e5f32;
    border-color: #2a7a42;
}

/* Warning Button (Validate) */
QPushButton[class="warning"] {
    background-color: #ff8c00;
    border-color: #ffa533;
}

QPushButton[class="warning"]:hover {
    background-color: #ff9f33;
    border-color: #ffb366;
}

QPushButton[class="warning"]:pressed {
    background-color: #e67c00;
    border-color: #ff8f1a;
}

/* Danger Button (Cancel/Clear) */
QPushButton[class="danger"] {
    background-color: #c53c3c;
    border-color: #d95656;
}

QPushButton[class="danger"]:hover {
    background-color: #d94545;
    border-color: #e66767;
}

QPushButton[class="danger"]:pressed {
    background-color: #8b0000;
    border-color: #a01010;
}

/* Line Edits */
QLineEdit {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 6px;
    color: #ffffff;
    selection-background-color: #4a90e2;
    max-height: 30px;
}

QLineEdit:focus {
    border-color: #4a90e2;
    background-color: #454545;
}

QLineEdit:disabled {
    background-color: #2a2a2a;
    border-color: #404040;
    color: #888888;
}

/* Combo Boxes */
QComboBox {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 6px;
    color: #ffffff;
    min-width: 100px;
    max-height: 30px;
}

QComboBox:hover {
    border-color: #4a90e2;
}

QComboBox:focus {
    border-color: #4a90e2;
    background-color: #454545;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #555555;
    background-color: #404040;
    border-radius: 0px 4px 4px 0px;
}

QComboBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #ffffff;
}

QComboBox QAbstractItemView {
    background-color: #353535;
    border: 1px solid #555555;
    border-radius: 4px;
    color: #ffffff;
    selection-background-color: #4a90e2;
    outline: none;
}

/* Spin Boxes */
QSpinBox {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 8px;
    color: #ffffff;
}

QSpinBox:focus {
    border-color: #4a90e2;
    background-color: #454545;
}

QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #555555;
    background-color: #404040;
    border-radius: 0px 4px 0px 0px;
}

QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid #555555;
    background-color: #404040;
    border-radius: 0px 0px 4px 0px;
}

/* Check Boxes */
QCheckBox {
    color: #ffffff;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #555555;
    border-radius: 3px;
    background-color: #404040;
}

QCheckBox::indicator:hover {
    border-color: #4a90e2;
}

QCheckBox::indicator:checked {
    background-color: #4a90e2;
    border-color: #4a90e2;
}

QCheckBox::indicator:checked:hover {
    background-color: #6ba3e6;
    border-color: #6ba3e6;
}

/* Progress Bars */
QProgressBar {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #4a90e2;
    border-radius: 4px;
}

/* Text Edits */
QTextEdit {
    background-color: #353535;
    border: 1px solid #555555;
    border-radius: 4px;
    color: #ffffff;
    selection-background-color: #4a90e2;
}

QTextEdit:focus {
    border-color: #4a90e2;
}

/* Scroll Areas */
QScrollArea {
    background-color: #2b2b2b;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #2b2b2b;
}

QScrollArea QWidget {
    background-color: #2b2b2b;
}

QScrollArea::viewport {
    background-color: #2b2b2b;
}

/* Scroll Bars */
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

/* Labels */
QLabel {
    color: #ffffff;
    background-color: transparent;
}

/* Tool Tips */
QToolTip {
    background-color: #353535;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px;
}

/* Menu Bars */
QMenuBar {
    background-color: #353535;
    border-bottom: 1px solid #555555;
    color: #ffffff;
}

QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
}

QMenuBar::item:selected {
    background-color: #4a90e2;
}

QMenu {
    background-color: #353535;
    border: 1px solid #555555;
    color: #ffffff;
}

QMenu::item {
    padding: 6px 20px;
}

QMenu::item:selected {
    background-color: #4a90e2;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #555555;
    background-color: #353535;
}

QTabBar::tab {
    background-color: #404040;
    border: 1px solid #555555;
    padding: 8px 16px;
    color: #ffffff;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #4a90e2;
    border-color: #4a90e2;
}

QTabBar::tab:hover {
    background-color: #505050;
}

/* Headers */
QHeaderView::section {
    background-color: #404040;
    color: #ffffff;
    padding: 6px;
    border: 1px solid #555555;
    font-weight: bold;
}

/* Table Views */
QTableView {
    background-color: #353535;
    alternate-background-color: #3a3a3a;
    color: #ffffff;
    gridline-color: #555555;
    selection-background-color: #4a90e2;
}

QTableView::item {
    padding: 4px;
    border: none;
}

QTableView::item:selected {
    background-color: #4a90e2;
}

/* File Dialogs */
QFileDialog {
    background-color: #2b2b2b;
    color: #ffffff;
    border: 1px solid #555555;
}

QFileDialog QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
}

QFileDialog QListView {
    background-color: #353535;
    color: #ffffff;
    selection-background-color: #4a90e2;
    border: 1px solid #555555;
    outline: none;
}

QFileDialog QListView::item {
    padding: 4px;
    border: none;
}

QFileDialog QListView::item:selected {
    background-color: #4a90e2;
    color: #ffffff;
}

QFileDialog QListView::item:hover {
    background-color: #404040;
}

QFileDialog QTreeView {
    background-color: #353535;
    color: #ffffff;
    selection-background-color: #4a90e2;
    border: 1px solid #555555;
    outline: none;
}

QFileDialog QTreeView::item {
    padding: 4px;
    border: none;
}

QFileDialog QTreeView::item:selected {
    background-color: #4a90e2;
    color: #ffffff;
}

QFileDialog QTreeView::item:hover {
    background-color: #404040;
}

QFileDialog QTreeView::branch {
    background-color: transparent;
}

QFileDialog QTreeView::branch:selected {
    background-color: #4a90e2;
}

/* File Dialog Toolbar */
QFileDialog QToolBar {
    background-color: #353535;
    border: 1px solid #555555;
    spacing: 2px;
}

QFileDialog QToolButton {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px;
    color: #ffffff;
    min-width: 20px;
    min-height: 20px;
}

QFileDialog QToolButton:hover {
    background-color: #4a90e2;
    border-color: #6ba3e6;
}

QFileDialog QToolButton:pressed {
    background-color: #357abd;
    border-color: #5a9dd8;
}

/* File Dialog Side Panel */
QFileDialog QSplitter {
    background-color: #2b2b2b;
}

QFileDialog QSplitter::handle {
    background-color: #555555;
}

QFileDialog QSplitter::handle:horizontal {
    width: 3px;
}

QFileDialog QSplitter::handle:vertical {
    height: 3px;
}
"""

def apply_dark_theme(app):
    """Apply the dark theme to the application"""
    import sys
    
    # Base dark theme
    stylesheet = DARK_THEME_STYLESHEET
    
    # Add platform-specific tab styling for macOS
    if sys.platform == "darwin":
        macos_tab_styles = """
        /* macOS specific tab styling */
        QTabBar::tab {
            background-color: #404040;
            border: 1px solid #555555;
            padding: 8px 20px;
            color: #ffffff;
            margin-right: 2px;
            border-radius: 4px 4px 0px 0px;
            min-width: 100px;
            text-align: left;
        }
        
        QTabBar::tab:selected {
            background-color: #4a90e2;
            border-color: #4a90e2;
        }
        
        QTabBar::tab:hover {
            background-color: #505050;
        }
        
        QTabBar {
            alignment: left;
        }
        """
        stylesheet += macos_tab_styles
    else:
        # Default tab styling for Windows/Linux
        default_tab_styles = """
        /* Default tab styling */
        QTabBar::tab {
            background-color: #404040;
            border: 1px solid #555555;
            padding: 8px 16px;
            color: #ffffff;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #4a90e2;
            border-color: #4a90e2;
        }
        
        QTabBar::tab:hover {
            background-color: #505050;
        }
        """
        stylesheet += default_tab_styles
    
    app.setStyleSheet(stylesheet)

def get_button_style(button_type="default"):
    """Get specific button style"""
    styles = {
        "default": """QPushButton { 
            background-color: #404040;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 4px 12px;
            min-height: 24px;
            max-height: 32px;
            color: #ffffff;
            font-weight: bold;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #4a90e2;
            border-color: #6ba3e6;
        }
        QPushButton:pressed {
            background-color: #357abd;
            border-color: #5a9dd8;
        }""",
        "success": "QPushButton { background-color: #2d8b47; border-color: #3ba55a; }",
        "warning": "QPushButton { background-color: #ff8c00; border-color: #ffa533; }",
        "danger": "QPushButton { background-color: #c53c3c; border-color: #d95656; }"
    }
    return styles.get(button_type, "")