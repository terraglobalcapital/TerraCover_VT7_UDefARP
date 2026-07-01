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
Progress reporting utilities for TerraCove modules.

This module provides shared progress reporting functionality to avoid code duplication
across modules that don't inherit from _RasterTemplate.
"""

from datetime import datetime
from typing import Callable, Optional


def safe_update_progress(
    message: str,
    percent: float,
    progress_callback: Optional[Callable[[str, float], None]],
    console_output: bool = True
) -> None:
    """
    Safely update progress if callback is available.
    Also logs progress to console for monitoring/debugging.

    This is the same robust progress reporting pattern used in the framework's
    _RasterTemplate class, made available as a standalone utility function.

    Args:
        message (str): Descriptive status message
        percent (float): Progress as decimal (0.0 to 1.0)
        progress_callback (Callable, optional): Progress callback function
        console_output (bool): Whether to print to console (default: True)

    Usage:
        Instead of duplicating progress methods in each class, simply call:

        >>> class MyProcessor:
        ...     def __init__(self, progress_callback=None):
        ...         self.progress_callback = progress_callback
        ...
        ...     def run(self):
        ...         safe_update_progress("Starting...", 0.0, self.progress_callback)
        ...         # ... processing ...
        ...         safe_update_progress("Completed", 1.0, self.progress_callback)

        Or create a simple helper method:
        >>> def _update_progress(self, message, percent):
        ...     safe_update_progress(message, percent, self.progress_callback)
    """
    # Log to console if requested
    if console_output:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] Progress: {percent*100:.1f}% - {message}")
    
    # Also call GUI callback if available
    if progress_callback:
        try:
            progress_callback(message, percent)
        except Exception as e:
            print(f"[PROGRESS ERROR] Callback failed: {e}")


