# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   Year:               2025
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------

"""
Environment Setup Utility for TerraCover Modules

This module provides utilities to configure the system environment for proper
DLL loading when modules are executed directly (not from the launcher).

After reinstalling Anaconda, PyQt6 and other libraries may not find their DLLs
when modules are run directly. This utility ensures all necessary paths are
added to the system PATH before the GUI is launched.

IMPORTANT: This module automatically configures the environment when imported.
"""

import sys
import os

# Track if environment has been configured
_environment_configured = False


def setup_dll_paths():
    """
    Configure environment variables to ensure DLLs and data files are found.

    This function adds the following paths to the system PATH:
    - Anaconda Library\\bin (system DLLs like MSVCP, VCRUNTIME)
    - Python DLLs directory
    - PyQt6 Qt6\\bin directory (Qt DLLs)
    - Python executable directory

    It also configures:
    - QT_PLUGIN_PATH: Qt plugins directory
    - QT_QPA_PLATFORM_PLUGIN_PATH: Qt platform plugins
    - GDAL_DATA: GDAL data files (prevents "Cannot find gdalvrt.xsd" warnings)
    - PROJ_LIB: PROJ coordinate transformation data

    This is automatically called when importing the terracover package.

    Returns:
        None

    Example:
        >>> if __name__ == "__main__":
        ...     from terracover.core.setup_environment import setup_dll_paths
        ...     setup_dll_paths()
        ...     # Now safe to import and run GUI code
    """
    # Get Python directory
    python_dir = os.path.dirname(sys.executable)

    # Define all necessary DLL paths
    if sys.platform == "win32":
        # Windows paths
        dll_paths = [
            os.path.join(python_dir, "Library", "bin"),  # Anaconda system DLLs
            os.path.join(python_dir, "DLLs"),  # Python DLLs
            os.path.join(python_dir, "Lib", "site-packages", "PyQt6", "Qt6", "bin"),  # Qt DLLs
            python_dir  # Python executable directory
        ]
    else:
        # macOS/Linux paths
        dll_paths = [
            os.path.join(python_dir, "lib"),  # System libraries
            os.path.join(python_dir, "Lib", "site-packages", "PyQt6", "Qt6", "lib"),  # Qt libraries
            python_dir  # Python executable directory
        ]

    # Get current PATH
    current_path = os.environ.get('PATH', '')

    # Add each DLL path to PATH if it exists and isn't already there
    for dll_path in dll_paths:
        if os.path.exists(dll_path) and dll_path not in current_path:
            os.environ['PATH'] = dll_path + os.pathsep + current_path
            current_path = os.environ['PATH']

    # Set Qt plugin path
    if sys.platform == "win32":
        pyqt6_plugins = os.path.join(python_dir, "Lib", "site-packages", "PyQt6", "Qt6", "plugins")
    else:
        # macOS/Linux paths
        pyqt6_plugins = os.path.join(python_dir, "lib", "python3.11", "site-packages", "PyQt6", "Qt6", "plugins")
        
    if os.path.exists(pyqt6_plugins):
        os.environ['QT_PLUGIN_PATH'] = pyqt6_plugins
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(pyqt6_plugins, "platforms")

    # Set GDAL_DATA path to prevent "Cannot find gdalvrt.xsd" warnings
    if sys.platform == "win32":
        gdal_data = os.path.join(python_dir, "Library", "share", "gdal")
        proj_lib = os.path.join(python_dir, "Library", "share", "proj")
    else:
        # macOS/Linux paths
        gdal_data = os.path.join(python_dir, "share", "gdal")
        proj_lib = os.path.join(python_dir, "share", "proj")
        
    if os.path.exists(gdal_data):
        os.environ['GDAL_DATA'] = gdal_data

    # Set PROJ_LIB path for PROJ coordinate transformations
    if os.path.exists(proj_lib):
        os.environ['PROJ_LIB'] = proj_lib


def is_environment_configured():
    """
    Check if the environment is already configured with necessary DLL paths.

    Returns:
        bool: True if PyQt6 bin/lib directory is in PATH, False otherwise
    """
    python_dir = os.path.dirname(sys.executable)
    if sys.platform == "win32":
        pyqt6_lib = os.path.join(python_dir, "Lib", "site-packages", "PyQt6", "Qt6", "bin")
    else:
        pyqt6_lib = os.path.join(python_dir, "lib", "python3.11", "site-packages", "PyQt6", "Qt6", "lib")
    
    current_path = os.environ.get('PATH', '')
    return pyqt6_lib in current_path


# NOTE: Auto-configuration on import has been disabled to prevent crashes when
# importing this module. Modules should explicitly call setup_dll_paths() in their
# if __name__ == "__main__" block before importing PyQt6.
#
# Old behavior (disabled):
# if not _environment_configured and not is_environment_configured():
#     setup_dll_paths()
#     _environment_configured = True
