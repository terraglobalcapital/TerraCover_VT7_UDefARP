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
Enhanced tooltip implementation for PyQt6
"""

from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont


class ToolTip(QLabel):
    """Custom tooltip widget with dark theme styling"""
    
    def __init__(self, parent=None, text=""):
        super().__init__(parent)
        self.setText(text)
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Set up styling
        self.setStyleSheet("""
            QLabel {
                background-color: #353535;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }
        """)
        
        import sys
        if sys.platform == "darwin":
            self.setFont(QFont("Helvetica Neue", 10))
        else:
            self.setFont(QFont("Arial", 10))
        self.setWordWrap(True)
        self.setMaximumWidth(400)
        
    def show_tooltip(self, pos):
        """Show tooltip at specified position"""
        self.move(pos)
        self.show()
        
        # Auto-hide after 10 seconds
        QTimer.singleShot(10000, self.hide)


class ToolTipManager:
    """Manager for handling tooltips on widgets"""
    
    @staticmethod
    def add_tooltip(widget: QWidget, text: str):
        """Add a tooltip to a widget"""
        if not text:
            return
            
        tooltip = None
        
        def show_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.close()
            
            tooltip = ToolTip(None, text)
            pos = event.globalPosition().toPoint() + QPoint(10, 10)
            tooltip.show_tooltip(pos)
        
        def hide_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.close()
                tooltip = None
        
        # Connect events
        widget.enterEvent = show_tooltip
        widget.leaveEvent = hide_tooltip