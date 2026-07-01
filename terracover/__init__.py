# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:      © Terra Global Capital. All rights reserved.
#   Author:         david.montoya@terraglobalcapital.com
#   Python version: >=3.9
#   Year:           2025
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------

# Configure environment BEFORE any imports that need DLLs
# This ensures PyQt6, GDAL, rasterio, etc. can find their DLLs
import sys
import os
import importlib.util

# Load setup_environment directly without importing it as a module
# to avoid circular imports
_setup_env_path = os.path.join(os.path.dirname(__file__), 'core', 'setup_environment.py')
_spec = importlib.util.spec_from_file_location("_setup_environment", _setup_env_path)
_setup_env_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_setup_env_module)

# Configure DLL paths if not already configured
if not _setup_env_module.is_environment_configured():
    _setup_env_module.setup_dll_paths()

# Clean up temporary variables
del _setup_env_path, _spec, _setup_env_module


# Lazy import mechanism - imports modules only when accessed
# This prevents circular imports when modules are run directly as __main__
_LAZY_IMPORTS = {
    # VT0007 UDef-ARP (standalone only includes this module)
    "udef_arp": ("modules.udef_arp", "udef_arp"),
}

def __getattr__(name):
    """
    Lazy import mechanism for terracover modules.

    This function is called when an attribute is accessed on the terracover package
    but hasn't been imported yet. It allows us to defer imports until they're actually
    needed, which prevents circular import issues when modules are run directly.

    Args:
        name: The name of the attribute being accessed

    Returns:
        The requested module function

    Raises:
        AttributeError: If the requested attribute doesn't exist
    """
    if name in _LAZY_IMPORTS:
        module_path, func_name = _LAZY_IMPORTS[name]
        from importlib import import_module
        module = import_module(f".{module_path}", package="terracover")
        func = getattr(module, func_name)
        # Cache the imported function in the module's namespace
        globals()[name] = func
        return func
    raise AttributeError(f"module 'terracover' has no attribute '{name}'")

# Version information
__version__ = "1.0.0"
__author__ = "David Montoya <david.montoya@terraglobalcapital.com>"

# Define public API (standalone only includes udef_arp)
__all__ = [
    "udef_arp",
    "__version__",
    "__author__"
]