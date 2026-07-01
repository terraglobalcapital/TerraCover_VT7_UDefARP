# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   GDAL version:       3.10.3
#   Year:               2025
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------

"""
VT7 Utility Functions

This module contains utility functions for raster/vector processing used throughout the VT7 workflow.
Includes functions for:
- Array/raster conversions
- Masking operations
- Vector to raster conversion
- Raster calculations
- Distance calculations
"""

import os
import numpy as np
from osgeo import gdal, ogr
import tempfile
import shutil
import re

# Enable GDAL/OGR exceptions for better error handling
gdal.UseExceptions()
ogr.UseExceptions()


def image_to_array(image):
    """Read raster image and return as numpy array."""
    # Set up a GDAL dataset
    in_ds = gdal.Open(image)
    # Set up a GDAL band
    in_band = in_ds.GetRasterBand(1)
    # Create Numpy Array1
    arr = in_band.ReadAsArray()
    return arr


def array_to_image(in_fn, out_fn, data, data_type, nodata=None, compress='lzw'):
    '''
    Create image from array with compression
    :param in_fn: datasource to copy projection and geotransform from
    :param out_fn: path to the file to create
    :param data: NumPy array containing data to write
    :param data_type: output data type
    :param nodata: optional NoData value
    :param compress: compression method for GeoTIFF ('lzw', 'deflate', 'packbits', 'none'). Default: 'lzw'
    :return:
    '''
    in_ds = gdal.Open(in_fn)
    output_format = out_fn.split('.')[-1].upper()
    if (output_format == 'TIF'):
        output_format = 'GTIFF'
    elif (output_format == 'RST'):
        output_format = 'rst'

    driver = gdal.GetDriverByName(output_format)

    # Build creation options
    creation_options = ["BigTIFF=YES"]

    # Add compression options for GeoTIFF
    if output_format == 'GTIFF' and compress.lower() != 'none':
        creation_options.append(f"COMPRESS={compress.upper()}")
        creation_options.append("TILED=YES")
        creation_options.append("BLOCKXSIZE=512")
        creation_options.append("BLOCKYSIZE=512")

        # Add predictor for better compression based on data type
        if compress.lower() in ['lzw', 'deflate']:
            # Check if data type is floating point
            if data_type in [gdal.GDT_Float32, gdal.GDT_Float64]:
                creation_options.append("PREDICTOR=3")  # Floating point predictor
            else:
                creation_options.append("PREDICTOR=2")  # Horizontal differencing

    out_ds = driver.Create(out_fn, in_ds.RasterXSize, in_ds.RasterYSize, 1, data_type, options=creation_options)
    out_ds.SetProjection(in_ds.GetProjection().encode('utf-8', 'backslashreplace').decode('utf-8'))
    out_ds.SetGeoTransform(in_ds.GetGeoTransform())
    out_band = out_ds.GetRasterBand(1)
    if nodata is not None:
        out_band.SetNoDataValue(nodata)
    out_band.WriteArray(data)
    out_band.FlushCache()
    out_ds.FlushCache()
    return


def apply_mask_to_raster(target_raster, mask_raster, outside_value='auto'):
    """
    Apply mask from one raster to another raster array.
    Where mask_raster has valid data (not nodata), keep target_raster values.
    Where mask_raster has nodata, set target_raster to specified value.

    :param target_raster: Path to raster that will be masked (can be file path or already loaded array)
    :param mask_raster: Path to raster used as mask
    :param outside_value: Value to use outside the mask. Options:
                         - 'auto' (default): Use target's nodata if available, else 0
                         - 'nodata': Use target's nodata value (or 0 if not defined)
                         - numeric value (e.g., 0, -9999): Use this specific value
    :return: Masked array
    """
    # Read target raster array if it's a file path
    if isinstance(target_raster, str):
        target_arr = image_to_array(target_raster)
        # Get nodata value from file
        target_ds = gdal.Open(target_raster)
        target_band = target_ds.GetRasterBand(1)
        target_nodata = target_band.GetNoDataValue()
        target_ds = None
        target_band = None
    else:
        # Already an array
        target_arr = target_raster
        target_nodata = None

    # Read mask raster
    mask_arr = image_to_array(mask_raster)

    # Get nodata value from mask
    mask_ds = gdal.Open(mask_raster)
    mask_band = mask_ds.GetRasterBand(1)
    mask_nodata = mask_band.GetNoDataValue()
    mask_ds = None
    mask_band = None

    # Determine the value to use outside the mask
    if outside_value == 'auto' or outside_value == 'nodata':
        fill_value = target_nodata if target_nodata is not None else 0
    else:
        # Use the specified numeric value
        fill_value = outside_value

    # Apply mask
    # If mask != nodata, keep target value, otherwise set to fill_value
    if mask_nodata is not None:
        masked_arr = np.where(mask_arr != mask_nodata, target_arr, fill_value)
    else:
        # If mask has no nodata defined, assume 0 is nodata
        masked_arr = np.where(mask_arr != 0, target_arr, fill_value)

    return masked_arr


def vector_to_raster(vector_fn, in_fn, raster_fn, data_type, attribute, nodata=None, compress='lzw', background_value=None):
    '''
    Create raster image from vector file with compression
    :param vector_fn: vector datasource
    :param in_fn: datasource to copy projection and geotransform from
    :param raster_fn: path to create raster file
    :param data_type: output data type
    :param attribute: attribute field name to use for rasterization
    :param nodata: optional NoData value
    :param compress: compression method for GeoTIFF ('lzw', 'deflate', 'packbits', 'none'). Default: 'lzw'
    :param background_value: optional background value for areas without polygons (if None, uses nodata or 0)
    :return:
    '''
    # Open the vector data source
    source_ds = ogr.Open(vector_fn)
    source_layer = source_ds.GetLayer()

    in_ds = gdal.Open(in_fn)
    output_format = raster_fn.split('.')[-1].upper()
    if (output_format == 'TIF'):
        output_format = 'GTIFF'
    elif (output_format == 'RST'):
        output_format = 'rst'

    driver = gdal.GetDriverByName(output_format)

    # Build creation options
    creation_options = ["BigTIFF=YES"]

    # Add compression options for GeoTIFF
    if output_format == 'GTIFF' and compress.lower() != 'none':
        creation_options.append(f"COMPRESS={compress.upper()}")
        creation_options.append("TILED=YES")
        creation_options.append("BLOCKXSIZE=512")
        creation_options.append("BLOCKYSIZE=512")

        # Add predictor for better compression based on data type
        if compress.lower() in ['lzw', 'deflate']:
            # Check if data type is floating point
            if data_type in [gdal.GDT_Float32, gdal.GDT_Float64]:
                creation_options.append("PREDICTOR=3")  # Floating point predictor
            else:
                creation_options.append("PREDICTOR=2")  # Horizontal differencing

    out_ds = driver.Create(raster_fn, in_ds.RasterXSize, in_ds.RasterYSize, 1, data_type, options=creation_options)
    out_band = out_ds.GetRasterBand(1)
    out_ds.SetGeoTransform(in_ds.GetGeoTransform())

    out_ds.SetProjection(in_ds.GetProjection().encode('utf-8', 'backslashreplace').decode('utf-8'))

    if nodata is not None:
        out_band.SetNoDataValue(nodata)

    # Initialize raster with background value if specified
    if background_value is not None:
        out_band.Fill(background_value)

    # Rasterize
    gdal.RasterizeLayer(out_ds, [1], source_layer, options=[f"ATTRIBUTE={attribute}"])

    # Cleanup - flush and close all datasets
    out_band.FlushCache()
    out_ds.FlushCache()
    out_band = None
    out_ds = None
    in_ds = None
    source_ds = None
    return


def admin_divisions_to_raster(shapefile_fn, in_fn, raster_fn, data_type=gdal.GDT_UInt16, id_field='ID', mask_file=None, nodata=None, compress='lzw'):
    '''
    Convert shapefile to raster with consecutive integer IDs starting from 2
    :param shapefile_fn: input shapefile path
    :param in_fn: datasource to copy projection and geotransform from
    :param raster_fn: path to create raster file
    :param data_type: output data type (default: UInt16)
    :param id_field: name of the ID field to create (default: 'ID')
    :param mask_file: optional mask raster - keeps values inside mask, sets outside to nodata, fills nodata inside mask with 1
    :param nodata: optional NoData value
    :param compress: compression method for GeoTIFF ('lzw', 'deflate', 'packbits', 'none'). Default: 'lzw'
    :return:
    '''
    # Open the original shapefile (read-only)
    source_ds = ogr.Open(shapefile_fn, 0)
    source_layer = source_ds.GetLayer()

    # Create a temporary in-memory shapefile with only the ID field
    mem_driver = ogr.GetDriverByName('Memory')
    mem_ds = mem_driver.CreateDataSource('memData')

    # Create memory layer with same spatial reference
    mem_layer = mem_ds.CreateLayer('temp', source_layer.GetSpatialRef(), source_layer.GetGeomType())

    # Create only the ID field (integer with sufficient width)
    field_defn = ogr.FieldDefn(id_field, ogr.OFTInteger)
    mem_layer.CreateField(field_defn)

    # Copy geometries and assign consecutive IDs starting from 2
    feature_id = 2
    source_layer.ResetReading()
    for src_feature in source_layer:
        # Create new feature in memory layer
        mem_feature = ogr.Feature(mem_layer.GetLayerDefn())
        mem_feature.SetGeometry(src_feature.GetGeometryRef())
        mem_feature.SetField(id_field, feature_id)
        mem_layer.CreateFeature(mem_feature)
        mem_feature = None
        feature_id += 1

    # Close source
    source_layer = None
    source_ds = None

    # Create temporary directory for shapefile
    temp_dir = tempfile.mkdtemp()
    temp_shp_path = os.path.join(temp_dir, 'temp_admin.shp')

    # Write to temporary shapefile
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    temp_ds = shp_driver.CreateDataSource(temp_shp_path)
    temp_layer = temp_ds.CreateLayer('temp_admin', mem_layer.GetSpatialRef(), mem_layer.GetGeomType())

    # Copy field definition
    temp_layer.CreateField(field_defn)

    # Copy features
    mem_layer.ResetReading()
    for mem_feature in mem_layer:
        temp_layer.CreateFeature(mem_feature)

    # Flush and close
    temp_ds.FlushCache()
    temp_layer = None
    temp_ds = None
    mem_layer = None
    mem_ds = None

    # Use the existing vector_to_raster method to rasterize
    # Set background_value=1 so areas without polygons are 1 instead of nodata
    vector_to_raster(temp_shp_path, in_fn, raster_fn, data_type, id_field, nodata, compress, background_value=1)

    # Clean up temporary directory and all files
    try:
        shutil.rmtree(temp_dir)
    except:
        pass

    # Apply mask if provided
    if mask_file is not None:
        # Read the rasterized output
        raster_arr = image_to_array(raster_fn)

        # Get raster nodata value
        ds = gdal.Open(raster_fn)
        band = ds.GetRasterBand(1)
        raster_nodata = band.GetNoDataValue()
        ds = None
        band = None

        # Step 1: Apply mask - outside mask becomes nodata
        masked_arr = apply_mask_to_raster(raster_arr, mask_file, outside_value=nodata if nodata is not None else 0)

        # Step 2: Special logic - inside mask with nodata values should be set to 1
        # Read mask array to identify inside/outside
        mask_arr = image_to_array(mask_file)

        # Get mask nodata value
        mask_ds = gdal.Open(mask_file)
        mask_band = mask_ds.GetRasterBand(1)
        mask_nodata = mask_band.GetNoDataValue()
        mask_ds = None
        mask_band = None

        # Define what "inside mask" means
        if mask_nodata is not None:
            inside_mask = mask_arr != mask_nodata
        else:
            inside_mask = mask_arr != 0

        # Where we're inside mask AND original raster had nodata, set to 1
        if raster_nodata is not None:
            has_nodata = raster_arr == raster_nodata
            masked_arr[inside_mask & has_nodata] = 1

        # Write back the masked result
        array_to_image(in_fn, raster_fn, masked_arr, data_type, nodata, compress)

    return


def convert_expression_to_numpy(expression):
    """
    Convert a user-friendly map algebra expression to a valid numpy expression.

    Args:
        expression (str): The map algebra expression using map1[1], map2[1], etc.

    Returns:
        str: The expression converted to numpy syntax for use with arrays
    """
    # Remove spaces
    if " " in expression:
        expression = expression.replace(" ", "")

    # Convert function names to numpy equivalents
    replacements = {
        "if": "np.where",
        "ln": "np.log",
        "log10": "np.log10",
        "sqrt": "np.sqrt",
        "square": "np.square",
        "min": "np.min",
        "max": "np.max",
        "sin": "np.sin",
        "cos": "np.cos",
        "tan": "np.tan",
        "arcsin": "np.arcsin",
        "arccos": "np.arccos",
        "arctan": "np.arctan",
        "abs": "np.abs",
        "round_up": "np.ceil",
        "round_down": "np.floor"
    }

    for old, new in replacements.items():
        if old in expression:
            expression = expression.replace(old, new)

    # Handle no_data comparisons
    if "==no_data" in expression:
        b1 = re.findall(r'map+\d+\[.*?\]', expression)
        b1a = [i + "==no_data" for i in b1]
        b1b = ["np.isnan(" + i + ")" for i in b1]
        for i, j in zip(b1a, b1b):
            if i in expression:
                expression = expression.replace(i, j)

    if "!=no_data" in expression:
        b1 = re.findall(r'map+\d+\[.*?\]', expression)
        b1a = [i + "!=no_data" for i in b1]
        b1b = ["~np.isnan(" + i + ")" for i in b1]
        for i, j in zip(b1a, b1b):
            if i in expression:
                expression = expression.replace(i, j)

    if ",no_data" in expression:
        expression = expression.replace(",no_data", ",np.nan")

    # Convert band numbers from 1-based to 0-based
    def convert_band_number(match):
        map_name = match.group(1)
        band_num = int(match.group(2))
        zero_based_band = band_num - 1
        return f"{map_name}[{zero_based_band}]"

    expression = re.sub(r'(map\d+)\[(\d+)\]', convert_band_number, expression)

    return expression


def raster_calculator(input_files, output_file, expression, out_dtype="uint8"):
    """
    Simplified raster calculator for VT7 operations.
    Uses the proven expression converter from raster_calculator.py

    Args:
        input_files: Single file path or list of file paths
        output_file: Path to output file
        expression: Expression string (e.g., "if(map1[1] == 1, map2[1], no_data)")
        out_dtype: Output data type ("uint8", "float32", etc.)
    """
    # Ensure input_files is a list
    if isinstance(input_files, str):
        input_files = [input_files]

    # Convert expression to numpy format
    numpy_expr = convert_expression_to_numpy(expression)

    # Replace map references with array references (map1 -> array[0], map2 -> array[1], etc.)
    # Find all map references like map1[, map2[, etc.
    map_refs = re.findall(r'map(\d+)\[', numpy_expr)
    unique_map_nums = sorted(set(int(m) for m in map_refs), reverse=True)  # Process from highest to lowest

    for map_num in unique_map_nums:
        array_index = map_num - 1  # Convert map1 -> array[0], map2 -> array[1], etc.
        numpy_expr = numpy_expr.replace(f'map{map_num}[', f'array[{array_index}][')

    # Open input datasets and read arrays
    array = []  # array[map_index][band_index]
    for file_path in input_files:
        ds = gdal.Open(file_path)
        bands = []
        for band_idx in range(ds.RasterCount):
            band = ds.GetRasterBand(band_idx + 1)
            arr = band.ReadAsArray().astype(float)
            nodata = band.GetNoDataValue()
            if nodata is not None:
                arr[arr == nodata] = np.nan
            bands.append(arr)
        array.append(bands)
        ds = None

    # Evaluate expression
    with np.errstate(divide='ignore', invalid='ignore'):
        result = eval(numpy_expr)

    # Handle inf values
    if isinstance(result, np.ndarray):
        result = np.where(np.isinf(result), np.nan, result)

    # Convert dtype
    dtype_map = {
        'uint8': gdal.GDT_Byte,
        'float32': gdal.GDT_Float32,
        'float64': gdal.GDT_Float64,
        'int16': gdal.GDT_Int16,
        'int32': gdal.GDT_Int32
    }
    gdal_dtype = dtype_map.get(out_dtype.lower(), gdal.GDT_Byte)

    # Determine output nodata
    if out_dtype == 'uint8':
        out_nodata = 255
    elif 'float' in out_dtype:
        out_nodata = -9999.0
    else:
        out_nodata = -9999

    # Replace NaN with nodata value
    result_output = result.copy()
    result_output[np.isnan(result)] = out_nodata

    # Write output
    array_to_image(input_files[0], output_file, result_output, gdal_dtype, nodata=out_nodata)

    # Cleanup
    array = None


def euclidean_distance(input_file, output_file, raster_value=1):
    """
    Calculate Euclidean distance from cells with specified value.
    Uses GDAL's ComputeProximity for compatibility with the official module.

    Args:
        input_file: Input raster file path
        output_file: Output distance raster file path
        raster_value: Value to calculate distance from (default: 1)
    """
    # Open source raster
    src_ds = gdal.Open(input_file, gdal.GA_ReadOnly)
    if src_ds is None:
        raise RuntimeError(f"Could not open {input_file}")

    src_band = src_ds.GetRasterBand(1)

    # Create output raster with same dimensions
    driver = gdal.GetDriverByName('GTiff')
    dst_ds = driver.Create(
        output_file,
        src_ds.RasterXSize,
        src_ds.RasterYSize,
        1,
        gdal.GDT_Float32,
        options=['COMPRESS=LZW', 'TILED=YES', 'BIGTIFF=YES']
    )

    if dst_ds is None:
        raise RuntimeError(f"Could not create {output_file}")

    # Copy spatial reference
    dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
    dst_ds.SetProjection(src_ds.GetProjection())

    dst_band = dst_ds.GetRasterBand(1)
    dst_band.SetNoDataValue(-9999.0)

    # Calculate proximity using GDAL's optimized algorithm
    # OPTIONS: VALUES=value_list (which pixel values to calculate distance from)
    #          DISTUNITS=GEO (use georeferenced coordinates instead of pixel units)
    options = [f'VALUES={raster_value}', 'DISTUNITS=GEO']

    gdal.ComputeProximity(src_band, dst_band, options)

    # Flush and close
    dst_band.FlushCache()
    dst_ds.FlushCache()

    # Cleanup
    src_band = None
    src_ds = None
    dst_band = None
    dst_ds = None


def replace_ref_system(in_fn, out_fn):
    '''
        RST raster format: correct reference system name in rdc file
        :param in_fn: datasource to copy correct projection name
        :param out_fn: rst raster file
    '''
    if out_fn.split('.')[-1] == 'rst':
        read_file_name, _ = os.path.splitext(in_fn)
        write_file_name, _ = os.path.splitext(out_fn)
        temp_file_path = 'rdc_temp.rdc'
        write_file = write_file_name + '.rdc'
        read_file = read_file_name + '.rdc'

        # Read in the file
        with open(read_file, 'r') as file:
            filedata = file.read()

        # Write the file out again
        with open(temp_file_path, 'w') as file:
            file.write(filedata)

        os.remove(write_file)
        os.rename(temp_file_path, write_file)


def read_nrt_value(nrt_txt_file):
    """
    Read NRT (Negligible Risk Threshold) value from text file.

    This function reads the NRT value from the text file created by nrt_calculation().
    The file has a specific format with the NRT value on a line starting with "NRT value:".

    :param nrt_txt_file: Path to the NRT text file (e.g., "03_BCM_NRT_value.txt")
    :return: NRT value in meters (as integer)
    :raises FileNotFoundError: If the file does not exist
    :raises ValueError: If the NRT value cannot be extracted from the file

    Example:
        >>> nrt_file = "path/to/03_BCM_NRT_value.txt"
        >>> nrt = read_nrt_value(nrt_file)
        >>> print(f"NRT: {nrt} meters")
        NRT: 450 meters

    Expected file format:
        Negligible Risk Threshold (NRT)
        ==================================================

        The NRT is defined as the distance from forest edge at which
        99.5 percent of the deforestation experienced over the HRP has occurred.

        NRT value: 450 meters
        NRT bin range: 420.00 - 480.00 meters
        Cumulative proportion at NRT: 0.9951
    """
    # Check if file exists
    if not os.path.exists(nrt_txt_file):
        raise FileNotFoundError(f"NRT file not found: {nrt_txt_file}")

    # Read the file and extract NRT value
    nrt_value = None
    with open(nrt_txt_file, 'r') as f:
        for line in f:
            # Look for the line that starts with "NRT value:"
            if line.strip().startswith("NRT value:"):
                # Extract the numeric value
                # Format: "NRT value: 450 meters"
                parts = line.split(':')
                if len(parts) >= 2:
                    # Get the part after the colon and extract the number
                    value_str = parts[1].strip().split()[0]  # Get first word after colon (the number)
                    try:
                        nrt_value = int(value_str)
                        break
                    except ValueError:
                        raise ValueError(f"Could not parse NRT value from line: {line.strip()}")

    if nrt_value is None:
        raise ValueError(f"NRT value not found in file: {nrt_txt_file}")

    return nrt_value


def build_filename(base_name, project_name=None, version=None):
    """
    Build filename with project_name and version.

    For files starting with numbers (e.g., "01_BCM_..."), project_name goes AFTER the number.
    For files without leading numbers (e.g., "T1_forest.tif"), project_name goes at the start.

    Parameters
    ----------
    base_name : str
        Base filename (e.g., "T1_forest.tif" or "01_BCM_Histogram_deforestation_distance.png")
    project_name : str, optional
        Project name to insert after leading number or at start (default: None)
    version : str, optional
        Version identifier to insert before extension (default: None)

    Returns
    -------
    str
        Formatted filename with project_name and version applied

    Examples
    --------
    >>> build_filename("T1_forest.tif", project_name="MyProject", version="1")
    'MyProject_T1_forest_v1.tif'

    >>> build_filename("01_BCM_Histogram_deforestation_distance.png", project_name="MyProject", version="2")
    '01_MyProject_BCM_Histogram_deforestation_distance_v2.png'

    >>> build_filename("T1_forest.tif", project_name=None, version="1")
    'T1_forest_v1.tif'

    >>> build_filename("T1_forest.tif", project_name="MyProject", version=None)
    'MyProject_T1_forest.tif'

    >>> build_filename("T1_forest.tif")
    'T1_forest.tif'
    """
    # Split base_name into name and extension
    if '.' in base_name:
        name_parts = base_name.rsplit('.', 1)
        name = name_parts[0]
        ext = '.' + name_parts[1]
    else:
        name = base_name
        ext = ''

    # Check if filename starts with a number pattern (e.g., "01_", "02_", etc.)
    import re
    number_prefix_match = re.match(r'^(\d+)_(.+)$', name)

    if number_prefix_match:
        # File starts with number (e.g., "01_BCM_Histogram...")
        # Format: NUMBER_[PROJECT_]REST[_vVERSION].ext
        number = number_prefix_match.group(1)
        rest = number_prefix_match.group(2)

        parts = [number]
        if project_name:
            parts.append(project_name)
        parts.append(rest)

        result = '_'.join(parts)
    else:
        # File does NOT start with number (e.g., "T1_forest.tif")
        # Format: [PROJECT_]NAME[_vVERSION].ext
        parts = []
        if project_name:
            parts.append(project_name)
        parts.append(name)

        result = '_'.join(parts)

    # Add version suffix before extension if provided
    if version:
        result = result + '_v' + str(version)

    # Add extension
    result = result + ext

    return result
