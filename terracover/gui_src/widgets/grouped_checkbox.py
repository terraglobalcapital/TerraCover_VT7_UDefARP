# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          (c) Terra Global Capital. All rights reserved.
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
Grouped Checkbox Widget for PyQt6 GUI Framework

Creates grouped checkboxes with section headers and group labels.
Designed for workflow stages with hierarchical organization.

Example structure:
{
    "section1": {
        "label": "Section 1 Label",
        "items": ["Item 1", "Item 2"]  # Simple items without groups
    },
    "section2": {
        "label": "Section 2 Label",
        "groups": {
            "Group A": ["Item A1", "Item A2"],
            "Group B": ["Item B1", "Item B2"]
        }
    }
}
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
    QLabel, QFrame, QGridLayout
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
import json
from typing import List, Dict, Any, Optional


class GroupedCheckboxWidget(QWidget):
    """
    Widget for displaying grouped checkboxes with section headers.

    Supports two types of sections:
    1. Simple sections with a list of items
    2. Grouped sections with sub-groups and items
    """

    value_changed = pyqtSignal()

    def __init__(self, parent=None, structure: Dict[str, Any] = None, default_value: str = ""):
        """
        Initialize the grouped checkbox widget.

        Args:
            parent: Parent widget
            structure: Dictionary defining sections, groups, and items
            default_value: JSON string of initially selected items
        """
        super().__init__(parent)

        self.structure = structure or {}
        self.checkboxes = {}  # Maps item label to checkbox widget
        self.section_frames = {}  # Maps section key to frame widget

        self._setup_ui()

        if default_value:
            self.set_value(default_value)

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create container frame (no scroll area - auto-size to content)
        container_frame = QFrame()
        container_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #555555;
                border-radius: 6px;
                background-color: #353535;
            }
        """)

        # Create content layout
        content_layout = QVBoxLayout(container_frame)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(15)

        # Build sections
        for section_key, section_data in self.structure.items():
            section_frame = self._create_section(section_key, section_data)
            content_layout.addWidget(section_frame)
            self.section_frames[section_key] = section_frame

        layout.addWidget(container_frame)

    def _create_section(self, section_key: str, section_data: Dict) -> QFrame:
        """Create a section frame with header and content."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Section header
        header_label = QLabel(section_data.get('label', section_key))
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(10)
        header_label.setFont(header_font)
        header_label.setStyleSheet("color: #4a90e2; background-color: transparent;")
        layout.addWidget(header_label)

        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #555555;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        # Simple items (no groups)
        if 'items' in section_data:
            items_layout = QVBoxLayout()
            items_layout.setSpacing(4)
            for item in section_data['items']:
                checkbox = self._create_checkbox(item)
                items_layout.addWidget(checkbox)
            layout.addLayout(items_layout)

        # Grouped items
        if 'groups' in section_data:
            for group_name, items in section_data['groups'].items():
                group_widget = self._create_group(group_name, items)
                layout.addWidget(group_widget)

        return frame

    def _create_group(self, group_name: str, items: List[str]) -> QWidget:
        """Create a group widget with label and checkboxes."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(4)

        # Group label
        group_label = QLabel(group_name)
        group_font = QFont()
        group_font.setItalic(True)
        group_font.setPointSize(9)
        group_label.setFont(group_font)
        group_label.setStyleSheet("color: #aaaaaa; background-color: transparent; padding-left: 5px;")
        layout.addWidget(group_label)

        # Checkboxes in grid (2 columns)
        checkbox_widget = QWidget()
        checkbox_layout = QGridLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(15, 0, 0, 0)
        checkbox_layout.setSpacing(4)
        checkbox_layout.setHorizontalSpacing(20)

        num_columns = 2
        for i, item in enumerate(items):
            checkbox = self._create_checkbox(item)
            row = i // num_columns
            col = i % num_columns
            checkbox_layout.addWidget(checkbox, row, col)

        layout.addWidget(checkbox_widget)

        return widget

    def _create_checkbox(self, label: str) -> QCheckBox:
        """Create a styled checkbox."""
        checkbox = QCheckBox(label)
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                background-color: transparent;
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

        checkbox.stateChanged.connect(self._on_checkbox_changed)
        self.checkboxes[label] = checkbox

        return checkbox

    def _on_checkbox_changed(self):
        """Handle checkbox state change."""
        self.value_changed.emit()

    def get_value(self) -> str:
        """Get current selected values as JSON string."""
        selected = []
        for label, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.append(label)
        return json.dumps(selected)

    def set_value(self, value: str):
        """Set checkbox states from JSON string or list."""
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

            for label, checkbox in self.checkboxes.items():
                checkbox.setChecked(label in selected)

        except (json.JSONDecodeError, Exception):
            for checkbox in self.checkboxes.values():
                checkbox.setChecked(False)

    def get_selected_labels(self) -> List[str]:
        """Get list of selected labels."""
        return [label for label, cb in self.checkboxes.items() if cb.isChecked()]

    def set_selected_labels(self, labels: List[str]):
        """Set selected labels from list."""
        for label, checkbox in self.checkboxes.items():
            checkbox.setChecked(label in labels)

    def clear_all(self):
        """Clear all checkbox selections."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def select_all(self):
        """Select all checkboxes."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def select_section(self, section_key: str):
        """Select all checkboxes in a section."""
        if section_key not in self.structure:
            return

        section_data = self.structure[section_key]
        items_to_select = []

        if 'items' in section_data:
            items_to_select.extend(section_data['items'])
        if 'groups' in section_data:
            for items in section_data['groups'].values():
                items_to_select.extend(items)

        for label in items_to_select:
            if label in self.checkboxes:
                self.checkboxes[label].setChecked(True)

    def deselect_section(self, section_key: str):
        """Deselect all checkboxes in a section."""
        if section_key not in self.structure:
            return

        section_data = self.structure[section_key]
        items_to_deselect = []

        if 'items' in section_data:
            items_to_deselect.extend(section_data['items'])
        if 'groups' in section_data:
            for items in section_data['groups'].values():
                items_to_deselect.extend(items)

        for label in items_to_deselect:
            if label in self.checkboxes:
                self.checkboxes[label].setChecked(False)

    def is_item_selected(self, label: str) -> bool:
        """Check if a specific item is selected."""
        if label in self.checkboxes:
            return self.checkboxes[label].isChecked()
        return False

    def set_item_enabled(self, label: str, enabled: bool):
        """Enable or disable a specific checkbox."""
        if label in self.checkboxes:
            self.checkboxes[label].setEnabled(enabled)

    def get_section_selected(self, section_key: str) -> List[str]:
        """Get selected items in a specific section."""
        if section_key not in self.structure:
            return []

        section_data = self.structure[section_key]
        section_items = []

        if 'items' in section_data:
            section_items.extend(section_data['items'])
        if 'groups' in section_data:
            for items in section_data['groups'].values():
                section_items.extend(items)

        return [label for label in section_items if self.is_item_selected(label)]
