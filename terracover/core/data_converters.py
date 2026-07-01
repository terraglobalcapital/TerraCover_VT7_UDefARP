# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   Year:               2025
#
#   VT0007 UDef-ARP Standalone Version
#   Simplified data converters with only required classes
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------


"""
Data Conversion Utilities for TerraCover GUI Widgets - VT7 Standalone Version

This module provides utilities for converting data between different formats,
particularly for handling widget input/output transformations.

Classes:
    TextEntryConverter: Handles conversions for text entry widgets
"""

from typing import Optional, Union, Any


class TextEntryConverter:
    """
    Utility class for converting data to/from text entry widget format.

    Text entry widgets in the GUI return string values that need to be converted
    to appropriate Python data types for processing. This class provides methods
    for handling these conversions safely with proper validation and error handling.

    Example:
        converter = TextEntryConverter()

        # Convert from GUI string to int
        gui_string = "123"
        int_value = converter.to_int(gui_string)
        # Result: 123

        # Convert with default value
        float_value = converter.to_float("", default_value=0.5)
        # Result: 0.5

        # Convert back to string for GUI
        string_result = converter.to_string(123)
        # Result: "123"
    """

    def to_int(self, value: Union[str, int, float], default_value: Optional[int] = None) -> Optional[int]:
        """
        Convert string input to integer with optional default value.

        Handles empty strings, whitespace, and invalid input gracefully.
        Converts float values to int by truncating (not rounding).

        Args:
            value (Union[str, int, float]): Input value to convert
            default_value (int, optional): Value to return if conversion fails or input is empty

        Returns:
            Optional[int]: Converted integer value, default_value, or None

        Examples:
            >>> converter = TextEntryConverter()
            >>> converter.to_int("123")
            123

            >>> converter.to_int("", default_value=0)
            0

            >>> converter.to_int("123.7")
            123

            >>> converter.to_int("invalid")
            None

            >>> converter.to_int("  42  ")
            42
        """
        # Handle None input
        if value is None:
            return default_value

        # Handle empty or whitespace-only strings
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return default_value

        try:
            # Convert to int, handling float strings by truncating
            if isinstance(value, str):
                # Try direct int conversion first
                try:
                    return int(value)
                except ValueError:
                    # Try float conversion then int (for decimal strings)
                    return int(float(value))
            elif isinstance(value, (int, float)):
                return int(value)
            else:
                return default_value
        except (ValueError, TypeError, OverflowError):
            return default_value

    def to_float(self, value: Union[str, int, float], default_value: Optional[float] = None) -> Optional[float]:
        """
        Convert string input to float with optional default value.

        Handles empty strings, whitespace, and invalid input gracefully.

        Args:
            value (Union[str, int, float]): Input value to convert
            default_value (float, optional): Value to return if conversion fails or input is empty

        Returns:
            Optional[float]: Converted float value, default_value, or None

        Examples:
            >>> converter = TextEntryConverter()
            >>> converter.to_float("123.45")
            123.45

            >>> converter.to_float("", default_value=0.0)
            0.0

            >>> converter.to_float("123")
            123.0

            >>> converter.to_float("invalid")
            None

            >>> converter.to_float("  3.14  ")
            3.14
        """
        # Handle None input
        if value is None:
            return default_value

        # Handle empty or whitespace-only strings
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return default_value

        try:
            return float(value)
        except (ValueError, TypeError, OverflowError):
            return default_value

    def to_string(self, value: Any, default_value: Optional[str] = None) -> Optional[str]:
        """
        Convert input to string with optional default value.

        Handles None values and provides consistent string conversion.

        Args:
            value (Any): Input value to convert
            default_value (str, optional): Value to return if input is None

        Returns:
            Optional[str]: Converted string value, default_value, or None

        Examples:
            >>> converter = TextEntryConverter()
            >>> converter.to_string(123)
            "123"

            >>> converter.to_string(None, default_value="")
            ""

            >>> converter.to_string(3.14159)
            "3.14159"

            >>> converter.to_string("")
            ""
        """
        if value is None:
            return default_value

        try:
            return str(value)
        except (ValueError, TypeError):
            return default_value
