# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   Year:               2025
#
#   VT0007 UDef-ARP Standalone Version
#   Simplified JSON formatter with only required entry types
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------


"""
JSON formatter utility for configuration files - VT7 Standalone Version
Creates human-readable JSON files for saving/loading configurations
"""

import json
from typing import Dict, Any, List
from datetime import datetime


class ConfigJsonFormatter:
    """
    Formats configuration data for saving and loading - VT7 Standalone Version
    Supports only entry types used by VT7: browse file, save folder, text entry, multiple checkbox
    """

    def __init__(self, field_configs: Dict[str, Any] = None, sections: Dict[str, List[Dict]] = None):
        """
        Initialize the formatter with field configurations and sections.

        Args:
            field_configs: Dictionary mapping field names to their configurations
            sections: Dictionary mapping section names to their field lists
        """
        self.field_configs = field_configs or {}
        self.sections = sections or {}

    def format_config_data(self, module_title: str, values: Dict[str, Any], comments: str = "") -> Dict[str, Any]:
        """
        Format configuration data into the readable structure.

        Args:
            module_title: Title of the module
            values: Raw configuration values
            comments: Optional comments about this configuration

        Returns:
            Formatted configuration dictionary
        """
        formatted_arguments = {}

        for field_name, value in values.items():
            field_config = self.field_configs.get(field_name, None)
            if field_config and hasattr(field_config, 'entry_type'):
                entry_type = getattr(field_config, 'entry_type', 'text entry')
            elif isinstance(field_config, dict):
                entry_type = field_config.get('entry_type', 'text entry')
            else:
                entry_type = 'text entry'

            formatted_value = self._format_value_by_type(value, entry_type)
            formatted_arguments[field_name] = formatted_value

        config_data = {
            "module": module_title,
            "saved_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "comments": comments,
            "arguments": formatted_arguments
        }

        return config_data

    def _format_value_by_type(self, value: Any, entry_type: str) -> Any:
        """
        Format a value based on its widget type.

        Args:
            value: The raw value to format
            entry_type: Type of the input widget

        Returns:
            Formatted value appropriate for the widget type
        """
        if value is None or value == "":
            return ""

        try:
            if entry_type in ["browse file", "browse folder", "browse file/folder",
                             "save file", "save folder", "save file/folder"]:
                # File/folder paths - keep as strings
                return str(value) if value else ""

            elif entry_type == "dropdown":
                # Dropdown - keep as string
                return str(value)

            elif entry_type == "checkbox":
                # Checkbox - format as "1" or "0" string
                if isinstance(value, bool):
                    return "1" if value else "0"
                elif isinstance(value, str):
                    if value.lower() in ['true', '1', 'yes', 'on']:
                        return "1"
                    else:
                        return "0"
                elif isinstance(value, (int, float)):
                    return "1" if bool(value) else "0"
                return "1" if bool(value) else "0"

            elif entry_type == "text entry":
                # Text entry - keep as string
                return str(value) if value else ""

            elif entry_type in ["multiple checkbox", "grouped_checkbox"]:
                # Multiple checkbox / Grouped checkbox - format as list of selected items
                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)
                        if isinstance(parsed_value, list):
                            return parsed_value
                    except (json.JSONDecodeError, ValueError):
                        # Handle comma-separated string
                        return [item.strip() for item in value.split(',') if item.strip()]
                elif isinstance(value, list):
                    return value
                return []

            else:
                # Default formatting
                return str(value)

        except Exception:
            # Fallback to string representation if formatting fails
            return str(value)

    def restore_filenames_from_json(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore values when loading from JSON.
        For VT7 standalone, this is a pass-through since no complex widget types need restoration.

        Args:
            values: The loaded JSON values

        Returns:
            Values (unchanged for VT7 standalone)
        """
        return values.copy()


def create_formatted_json(module_title: str, values: Dict[str, Any],
                         field_configs: Dict[str, Any] = None,
                         sections: Dict[str, List[Dict]] = None,
                         comments: str = "") -> str:
    """
    Create a formatted JSON string for configuration data.

    Args:
        module_title: Title of the module
        values: Configuration values to format
        field_configs: Field configurations for context
        sections: Section organization information
        comments: Optional comments about this configuration

    Returns:
        Formatted JSON string
    """
    formatter = ConfigJsonFormatter(field_configs, sections)
    config_data = formatter.format_config_data(module_title, values, comments=comments)

    return json.dumps(config_data, indent=2, ensure_ascii=False, separators=(',', ': '))
