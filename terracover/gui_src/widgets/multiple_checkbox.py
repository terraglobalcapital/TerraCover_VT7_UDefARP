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
Multiple Checkbox Widget for PyQt6 GUI Framework
Creates multiple checkboxes based on labels_list configuration
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
                             QScrollArea, QGridLayout)
from PyQt6.QtCore import pyqtSignal
import json
from typing import List, Dict, Any


class NoScrollScrollArea(QScrollArea):
    """QScrollArea that doesn't propagate wheel events to parent.

    This prevents the main window scroll from being affected when
    the mouse is over this scroll area.
    """

    def wheelEvent(self, event):
        """Handle wheel events locally without propagating to parent."""
        scrollbar = self.verticalScrollBar()
        if scrollbar.maximum() > 0:
            # Handle scroll locally
            super().wheelEvent(event)
            # Always accept to prevent propagation to parent (even at scroll limits)
            event.accept()
        else:
            # No scrollable content, ignore the event
            event.ignore()


class MultipleCheckboxWidget(QWidget):
    """Widget for displaying multiple checkboxes based on labels_list"""
    
    value_changed = pyqtSignal()
    
    def __init__(self, parent=None, labels_list: List[str] = None, default_value: str = ""):
        super().__init__(parent)
        
        self.labels_list = labels_list or []
        self.checkboxes = {}  # Dictionary to store checkbox widgets
        
        # Set up layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area for checkboxes (NoScrollScrollArea prevents parent scroll)
        scroll_area = NoScrollScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)  # Limit height for long lists
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #555555;
                border-radius: 6px;
                background-color: #353535;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #353535;
            }
        """)
        
        # Create widget to hold checkboxes
        checkbox_widget = QWidget()
        checkbox_layout = QGridLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create checkboxes based on labels_list
        self._create_checkboxes(checkbox_layout)
        
        # Set up scroll area
        scroll_area.setWidget(checkbox_widget)
        
        # Add scroll area to main layout
        layout.addWidget(scroll_area)
        
        # Set default values
        if default_value:
            self.set_value(default_value)
    
    def _create_checkboxes(self, layout):
        """Create checkboxes based on labels_list in two columns"""
        for i, label in enumerate(self.labels_list):
            checkbox = QCheckBox(label)
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #ffffff;
                    background-color: #353535;
                    spacing: 8px;
                    font-size: 11px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #555555;
                    background-color: #404040;
                }
                QCheckBox::indicator:checked {
                    background-color: #4a90e2;
                    border-color: #6ba3e6;
                }
                QCheckBox::indicator:checked:pressed {
                    background-color: #357abd;
                    border-color: #5a9dd8;
                }
                QCheckBox::indicator:unchecked:hover {
                    border-color: #6ba3e6;
                }
            """)
            
            # Connect signal
            checkbox.stateChanged.connect(self._on_checkbox_changed)
            
            # Store checkbox
            self.checkboxes[label] = checkbox
            
            # Add to grid layout in two columns
            row = i // 2
            col = i % 2
            layout.addWidget(checkbox, row, col)
    
    def _on_checkbox_changed(self):
        """Handle checkbox state change"""
        self.value_changed.emit()
    
    def get_value(self) -> str:
        """Get current selected values as JSON string"""
        selected = []
        for label, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.append(label)
        return json.dumps(selected)
    
    def set_value(self, value: str):
        """Set checkbox states from JSON string or list"""
        try:
            if isinstance(value, str):
                if value.strip():
                    selected = json.loads(value)
                else:
                    selected = []
            elif isinstance(value, list):
                selected = value
            else:
                selected = []
            
            # Update checkbox states
            for label, checkbox in self.checkboxes.items():
                checkbox.setChecked(label in selected)
                
        except (json.JSONDecodeError, Exception):
            # If parsing fails, clear all checkboxes
            for checkbox in self.checkboxes.values():
                checkbox.setChecked(False)
    
    def get_selected_labels(self) -> List[str]:
        """Get list of selected labels"""
        selected = []
        for label, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.append(label)
        return selected
    
    def set_selected_labels(self, labels: List[str]):
        """Set selected labels from list"""
        for label, checkbox in self.checkboxes.items():
            checkbox.setChecked(label in labels)
    
    def clear_all(self):
        """Clear all checkbox selections"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)
    
    def select_all(self):
        """Select all checkboxes"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)