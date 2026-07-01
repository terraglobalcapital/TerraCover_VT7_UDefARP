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

"""
Core module for TerraCover GUI4.

This module contains internal utilities for spatial data processing,
validation, and I/O operations. All functions and classes should be
imported directly from their respective modules:

- from .in_out import _ReadRaster, _SaveTable, etc.
- from .validations import _SpatialFileValidator, etc.  
- from .checks import _gdal_type_max_min, etc.
- from .map_template import _RasterTemplate
- from .base_processor import BaseProcessor, BaseFileProcessor
"""

# No public API - all imports should be direct from submodules
__all__ = []