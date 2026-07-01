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
VT7 Model Evaluation

This module contains the ModelEvaluation class and evaluation methods for VT7 models.
Includes:
- ModelEvaluation class for analyzing model performance
- Voronoi-based sampling and evaluation
- Statistical analysis and visualization
"""

import os
import sys
import numpy as np
from osgeo import gdal, ogr, osr
from osgeo.gdalconst import GA_ReadOnly
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import scipy.stats as stats
from scipy.spatial import Voronoi
import geopandas as gpd
import shapely
import seaborn as sns
from shapely.geometry import Point
from geopandas import GeoDataFrame
import shutil

# Enable GDAL/OGR exceptions for better error handling
gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()

try:
    from .utils import image_to_array, array_to_image, replace_ref_system, vector_to_raster
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from terracover.modules.vt7.utils import image_to_array, array_to_image, replace_ref_system, vector_to_raster


class ModelEvaluation:
    """
    Model Evaluation class for VT7 Benchmark Model validation.

    This class provides methods to evaluate model performance using Thiessen polygons
    and residual analysis, following Verra VT7 methodology.
    """

    def __init__(self):
        self.data_folder = None

    def set_working_directory(self, directory: object) -> object:
        '''
        Set up the working directory
        :param directory: your local directory with all data files
        '''
        self.data_folder = directory
        os.chdir(self.data_folder)

    def replace_legend(self, out_fn):
        '''
         RST raster format: correct legend in rdc file of Combined Deforestation Review Map
         :param out_fn: rst raster file
        '''
        if out_fn.split('.')[-1] == 'rst':
            base_name, _ = os.path.splitext(out_fn)
            temp_file_path = 'rdc_temp.rdc'

            with open(base_name + '.rdc', 'r') as read_file, open(temp_file_path, 'w') as write_file:
                for line in read_file:
                    if line.startswith("legend cats :"):
                        write_file.write("legend cats : " + '3'+'\n')
                        # Write the three new lines
                        write_file.write("code 1      : "+"Forest at the start of HRP"+"\n")
                        write_file.write("code 2      : "+"Deforestation within CAL"+"\n")
                        write_file.write("code 3      : "+"Deforestation within CNF"+"\n")
                    else:
                        write_file.write(line)
            shutil.move(temp_file_path, base_name + '.rdc')

    def create_mask_polygon(self, mask):
        '''
        Create municipality mask polygon
        :param mask: mask of the jurisdiction (binary map)
        :return:
        '''
        in_ds = gdal.Open(mask)
        in_band = in_ds.GetRasterBand(1)

        # Set up osr spatial reference
        projection = in_ds.GetProjection().encode('utf-8', 'backslashreplace').decode('utf-8')
        spatial_ref = osr.SpatialReference()
        spatial_ref.ImportFromWkt(projection)

        # Create a temporary shapefile to store all polygons
        temp_layername = "POLYGONIZED_MASK"
        driver = ogr.GetDriverByName("ESRI Shapefile")
        temp_ds = driver.CreateDataSource(temp_layername + ".shp")
        temp_layer = temp_ds.CreateLayer(temp_layername, srs=spatial_ref)
        gdal.Polygonize(in_band, in_band, temp_layer, -1, [], callback=None)

        # Close all datasets to release file handles
        temp_layer = None
        temp_ds = None
        in_band = None
        in_ds = None
        return

    def bbox_to_pixel_offsets(self,gt, bbox):
        '''
        https://gist.github.com/perrygeo/5667173
        '''
        originX = gt[0]
        originY = gt[3]
        pixel_width = gt[1]
        pixel_height = gt[5]
        x1 = int((bbox[0] - originX) / pixel_width)
        x2 = int((bbox[1] - originX) / pixel_width) + 1

        y1 = int((bbox[3] - originY) / pixel_height)
        y2 = int((bbox[2] - originY) / pixel_height) + 1

        xsize = x2 - x1
        ysize = y2 - y1
        return (x1, y1, xsize, ysize)

    def zonal_stats(self, vector_path, raster_path, nodata_value=None, global_src_extent=False):
        '''
        https://gist.github.com/perrygeo/5667173
        '''
        rds = gdal.Open(raster_path, GA_ReadOnly)
        assert (rds)
        rb = rds.GetRasterBand(1)
        rgt = rds.GetGeoTransform()

        # Read native nodata from raster before any override
        native_nodata = rb.GetNoDataValue()

        if nodata_value:
            nodata_value = float(nodata_value)
            rb.SetNoDataValue(nodata_value)

        vds = ogr.Open(vector_path, GA_ReadOnly)  # TODO maybe open update if we want to write stats
        assert (vds)
        vlyr = vds.GetLayer(0)

        # Get spatial reference from the vector layer
        vector_srs = vlyr.GetSpatialRef()

        # create an in-memory numpy array of the source raster data
        # covering the whole extent of the vector layer
        if global_src_extent:
            # use global source extent
            # useful only when disk IO or raster scanning inefficiencies are your limiting factor
            # advantage: reads raster data in one pass
            # disadvantage: large vector extents may have big memory requirements
            src_offset = self.bbox_to_pixel_offsets(rgt, vlyr.GetExtent())
            src_array = rb.ReadAsArray(*src_offset)

            # calculate new geotransform of the layer subset
            new_gt = (
                (rgt[0] + (src_offset[0] * rgt[1])),
                rgt[1],
                0.0,
                (rgt[3] + (src_offset[1] * rgt[5])),
                0.0,
                rgt[5]
            )

        mem_drv = ogr.GetDriverByName('Memory')
        driver = gdal.GetDriverByName('MEM')

        # Loop through vectors
        stats = []
        feat = vlyr.GetNextFeature()
        while feat is not None:

            if not global_src_extent:
                # use local source extent
                # fastest option when you have fast disks and well indexed raster (ie tiled Geotiff)
                # advantage: each feature uses the smallest raster chunk
                # disadvantage: lots of reads on the source raster
                src_offset = self.bbox_to_pixel_offsets(rgt, feat.geometry().GetEnvelope())
                src_array = rb.ReadAsArray(*src_offset)

                # calculate new geotransform of the feature subset
                new_gt = (
                    (rgt[0] + (src_offset[0] * rgt[1])),
                    rgt[1],
                    0.0,
                    (rgt[3] + (src_offset[1] * rgt[5])),
                    0.0,
                    rgt[5]
                )

            # Create a temporary vector layer in memory with proper spatial reference
            mem_ds = mem_drv.CreateDataSource('out')
            mem_layer = mem_ds.CreateLayer('poly', vector_srs, ogr.wkbPolygon)
            mem_layer.CreateFeature(feat.Clone())

            # Rasterize it
            rvds = driver.Create('', src_offset[2], src_offset[3], 1, gdal.GDT_Byte)
            rvds.SetGeoTransform(new_gt)
            gdal.RasterizeLayer(rvds, [1], mem_layer, burn_values=[1])
            rv_array = rvds.ReadAsArray()

            # Mask the source data array with our current feature
            # we take the logical_not to flip 0<->1 to get the correct mask effect
            # we also mask out nodata values explicitly (both user-provided and native raster nodata)
            mask_condition = np.logical_not(rv_array)
            if nodata_value is not None:
                mask_condition = np.logical_or(mask_condition, src_array == nodata_value)
            if native_nodata is not None and native_nodata != nodata_value:
                mask_condition = np.logical_or(mask_condition, src_array == native_nodata)
            masked = np.ma.MaskedArray(src_array, mask=mask_condition)

            # Suppress UserWarning about converting masked elements to nan
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='.*converting a masked element to nan.*')
                feature_stats = {
                    'sum': float(masked.sum())}

            stats.append(feature_stats)

            rvds = None
            mem_ds = None
            feat = vlyr.GetNextFeature()

        vds = None
        rds = None
        return stats

    def remove_edge_cells(self, full_voronoi_grid: GeoDataFrame, area_mask: GeoDataFrame,
                          area_percentile_threshold: float) -> GeoDataFrame:
        '''
        Ensure thiessen polygon cells retain percentile threshold of maximum size after intersection with mask of the jurisdiction
         :param full_voronoi_grid: thiessen polygon dataframe
         :param area_mask: mask of the jurisdiction
         :param area_percentile_threshold: area percentile threshold
         :return  thiessen_gdf: result dataframe
        '''
        # Use keep_geom_type=False to prevent warnings about dropped geometries
        thiessen_gdf = gpd.overlay(full_voronoi_grid, area_mask, how="intersection", keep_geom_type=False)

        # Filter to keep only Polygon and MultiPolygon geometries
        thiessen_gdf = thiessen_gdf[thiessen_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]

        # Get area of each polygon
        thiessen_gdf["area"] = thiessen_gdf.area

        # Calculate size of cell compared to max
        thiessen_gdf["percentcell"] = thiessen_gdf["area"] / thiessen_gdf["area"].max()

        # Select cells with more than thresh% of their area within the mask
        thiessen_gdf = thiessen_gdf[thiessen_gdf["percentcell"] > area_percentile_threshold]

        return thiessen_gdf

    def create_thiessen_polygon(self, grid_area, mask_voronoi, mask_exclusions, density, deforestation, out_fn, raster_fn):
        '''
          Create thiessen polygon with improved methodology for handling exclusions.

          IMPORTANT: This method uses a two-mask approach to properly handle exclusions:
          1. mask_voronoi: Full jurisdictional area (jnr_value only, no exclusions) used to generate
             complete Voronoi polygons without fragmentation
          2. mask_exclusions: JNR area with exclusions applied (jnr_with_exclusions_mask) used to
             calculate final statistics after filtering

          This ensures that:
          - Voronoi polygons are generated over a continuous area (not fragmented by exclusions)
          - The 0.999 threshold filter works correctly to remove only edge polygons
          - Exclusions are applied AFTER filtering, affecting only final statistics

         :param grid_area: assessment grid cell area in hectares
         :param mask_voronoi: Full jurisdictional mask for Voronoi generation (no exclusions)
         :param mask_exclusions: Jurisdictional mask with exclusions for final statistics
         :param density: adjusted prediction density map
         :param deforestation: Deforestation Map during the HRP
         :param out_fn: Output filename for thiessen polygons
         :param raster_fn: Output filename for residuals raster
         :return  clipped_gdf: thiessen polygon dataframe
        '''
        import tempfile

        print("=" * 60)
        print("Creating Thiessen Polygon Grid")
        print("=" * 60)
        print(f"Grid area: {grid_area:,} ha ({grid_area/100:.0f} km²)")

        ## Polygonize VORONOI mask (full jurisdictional area, no exclusions)
        print("Polygonizing Voronoi mask...")
        self.create_mask_polygon(mask_voronoi)
        mask_voronoi_df = gpd.GeoDataFrame.from_file('POLYGONIZED_MASK.shp')

        ## Polygonize EXCLUSIONS mask (with exclusions applied)
        print("Polygonizing exclusions mask...")
        self.create_mask_polygon(mask_exclusions)
        mask_exclusions_df = gpd.GeoDataFrame.from_file('POLYGONIZED_MASK.shp')

        # Get raster dimensions and geotransform for grid calculations
        in_ds = gdal.Open(mask_voronoi)
        pixel_size = int(in_ds.GetGeoTransform()[1])
        raster_y_size = in_ds.RasterYSize
        raster_x_size = in_ds.RasterXSize
        geotransform = in_ds.GetGeoTransform()
        in_ds = None  # Close the dataset to release file handle

        # Calculate grid size from grid area
        grid_size = int(np.sqrt(grid_area * 10000)) // pixel_size
        print(f"Grid cell size: {grid_size} pixels")

        # Systematic Sampling
        sample_points = []
        for y in range(-1 * grid_size, raster_y_size + 1 * grid_size, grid_size):
            for x in range(-1 * grid_size, raster_x_size + 1 * grid_size, grid_size):
                # Convert raster coordinates to geographic coordinates
                geo_x = geotransform[0] + x * geotransform[1]
                geo_y = geotransform[3] + y * geotransform[5]
                sample_points.append((geo_x, geo_y))

        ## Generate Voronoi polygons
        # Convert sample_points list to DataFrame
        df = pd.DataFrame(sample_points, columns=['geo_x', 'geo_y'])
        df['coords'] = list(zip(df['geo_x'], df['geo_y']))
        df['coords_P'] = df['coords'].apply(Point)
        points_df = gpd.GeoDataFrame(df, geometry='coords_P', crs=mask_voronoi_df.crs)

        # Convert the 'coords' column to a numpy array
        coords = np.array(points_df['coords'].tolist())

        # Create thiessen polygon
        print(f"Generating Voronoi tessellation from {len(coords):,} sample points...")
        vor = Voronoi(points=coords)

        # Polygonize the line ridge is not infinity
        lines = [shapely.geometry.LineString(vor.vertices[line]) for line in
                 vor.ridge_vertices if -1 not in line]

        polys = shapely.ops.polygonize(lines)

        # Convert Voronoi polygons (polys) into a GeoDataFrame.
        voronois = gpd.GeoDataFrame(geometry=gpd.GeoSeries(polys), crs=mask_voronoi_df.crs)
        print(f"Generated {len(voronois)} Voronoi polygons")

        ## Filter edge polygons using Voronoi mask (no exclusions)
        print("Filtering edge polygons (99.9% threshold)...")
        clipped_gdf = self.remove_edge_cells(voronois, mask_voronoi_df, 0.999)
        print(f"Retained {len(clipped_gdf)} polygons after edge filtering")

        ## Apply exclusions mask to filtered polygons
        if len(clipped_gdf) > 0:
            print("Applying exclusions to grid...")

            # Assign original polygon IDs BEFORE applying exclusions overlay
            # This preserves the identity of each Voronoi cell so that fragments
            # (islands) created by exclusion removal can be dissolved back together
            clipped_gdf = clipped_gdf.copy()
            clipped_gdf['_voronoi_id'] = range(1, len(clipped_gdf) + 1)

            # Overlay filtered polygons with exclusions mask to remove excluded areas
            thiessen_with_exclusions = gpd.overlay(clipped_gdf, mask_exclusions_df,
                                                    how="intersection", keep_geom_type=False)

            # Extract polygons and multipolygons from GeometryCollections
            extracted_geoms = thiessen_with_exclusions['geometry'].apply(
                lambda geom: [g for g in geom.geoms if
                              g.geom_type in ['Polygon', 'MultiPolygon']] if geom.geom_type == 'GeometryCollection' else [
                    geom]
            )
            # Explode while preserving the original index to maintain _voronoi_id mapping
            extracted_series = extracted_geoms.explode()
            clipped_gdf = gpd.GeoDataFrame({
                'geometry': extracted_series.values,
                '_voronoi_id': thiessen_with_exclusions.loc[extracted_series.index, '_voronoi_id'].values
            }, crs=thiessen_with_exclusions.crs)

            # Filter out any non-polygon geometries (LineString, MultiLineString, Point, etc.)
            # This can occur when overlay operations produce degenerate geometries
            polygon_mask = clipped_gdf['geometry'].apply(lambda geom: geom.geom_type in ['Polygon', 'MultiPolygon'])
            clipped_gdf = clipped_gdf[polygon_mask].copy()

            # Dissolve fragments back to their original Voronoi polygon IDs
            # This merges islands created by exclusion removal back into a single
            # MultiPolygon per original Voronoi cell, preserving the correct polygon count
            clipped_gdf = clipped_gdf.dissolve(by='_voronoi_id').reset_index()

            # Calculate area in hectares (this is now the area AFTER exclusions)
            clipped_gdf['Area_ha'] = clipped_gdf['geometry'].area / 10000

        print(f"Final grid: {len(clipped_gdf)} polygons")

        # Check if we have any polygons at all
        if len(clipped_gdf) == 0:
            print(f"\n[ERROR] No polygons generated. Skipping evaluation.")
            # Create placeholder image with error message
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5,
                    f'Evaluation skipped:\nNo polygons could be generated\n\n'
                    f'Check your input masks and grid parameters',
                    horizontalalignment='center',
                    verticalalignment='center',
                    fontsize=14,
                    color='red',
                    weight='bold',
                    transform=plt.gca().transAxes)
            plt.axis('off')
            plt.savefig(out_fn, dpi=100, bbox_inches='tight')
            plt.close()
            return None
        ## Calculate zonal statistics
        print("Calculating zonal statistics...")

        # Use tempfile for temporary vector file
        with tempfile.NamedTemporaryFile(suffix='.shp', delete=False, dir=tempfile.gettempdir()) as tmp_vector:
            vector_temp_path = tmp_vector.name

        try:
            ## Convert clipped_gdf to shapefile (geometry only, avoids column name truncation warnings)
            clipped_gdf[['geometry']].to_file(vector_temp_path)

            # Actual Deforestation(ha)
            stats = self.zonal_stats(vector_temp_path, deforestation, nodata_value=0)

            # Calculate areal_resolution_of_map_pixels
            in_ds4 = gdal.Open(density)
            P1 = in_ds4.GetGeoTransform()[1]
            P2 = abs(in_ds4.GetGeoTransform()[5])
            areal_resolution_of_map_pixels = P1 * P2 / 10000
            in_ds4 = None  # Close dataset to release file handle

            # Add the results back to the GeoDataFrame
            clipped_gdf['Actual Deforestation(ha)'] = [(item['sum'] if item['sum'] is not None else 0) * areal_resolution_of_map_pixels for item in stats]

            # Predicted Deforestation(ha)
            stats1 = self.zonal_stats(vector_temp_path, density, nodata_value=0)

            clipped_gdf['Predicted Deforestation(ha)'] = [(item['sum'] if item['sum'] is not None else 0) for item in stats1]

        finally:
            # Clean up temp shapefile and associated files
            for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
                temp_file = vector_temp_path.replace('.shp', ext)
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass

        # Drop auxiliary column and assign sequential IDs
        clipped_gdf = clipped_gdf.drop(columns=['_voronoi_id'], errors='ignore')
        clipped_gdf['ID'] = range(1, len(clipped_gdf) + 1)

        # Replace NaN or blank values with '0'
        columns_to_fill = ['Actual Deforestation(ha)', 'Predicted Deforestation(ha)']
        for column in columns_to_fill:
            clipped_gdf[column] = clipped_gdf[column].fillna(0)

        # Calculate residuals
        clipped_gdf['Residuals(ha)'] = clipped_gdf['Predicted Deforestation(ha)'] - clipped_gdf['Actual Deforestation(ha)']

        # Export to Excel with formatting (use os.path.splitext to properly handle file extensions)
        excel_file_path = os.path.splitext(out_fn)[0] + '.xlsx'
        print(f"Saving grid statistics Excel: {os.path.basename(excel_file_path)}")

        # Prepare data for export
        export_df = clipped_gdf.drop('geometry', axis=1)[['ID', 'Actual Deforestation(ha)', 'Predicted Deforestation(ha)', 'Residuals(ha)']]

        # Create Excel writer with openpyxl engine for formatting
        with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
            export_df.to_excel(writer, sheet_name='Evaluation Grid', index=False)

            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Evaluation Grid']

            # Import openpyxl styles for formatting
            from openpyxl.styles import numbers

            # Apply number format to numeric columns (B, C, D) with 2 decimals and thousands separator
            for row in worksheet.iter_rows(min_row=2, min_col=2, max_col=4):
                for cell in row:
                    cell.number_format = '#,##0.00'

            # Set column widths
            worksheet.column_dimensions['A'].width = 10
            worksheet.column_dimensions['B'].width = 25
            worksheet.column_dimensions['C'].width = 25
            worksheet.column_dimensions['D'].width = 20

        # Rename columns (both for shapefile export and return value)
        clipped_gdf = clipped_gdf.rename(columns={'Predicted Deforestation(ha)': 'PredDef',
                                                   'Actual Deforestation(ha)': 'ActualDef',
                                                   'Residuals(ha)':'Residuals'})

        # Export residuals shapefile with same information as Excel
        # raster_fn parameter now used for shapefile output (change extension from .tif to .shp)
        shapefile_fn = os.path.splitext(raster_fn)[0] + '.shp'
        print(f"Creating residuals shapefile: {os.path.basename(shapefile_fn)}")

        # Prepare columns for shapefile export (same as Excel plus geometry)
        # Shapefile field names limited to 10 characters, so use abbreviated names
        export_gdf = clipped_gdf[['ID', 'Area_ha', 'ActualDef', 'PredDef', 'Residuals', 'geometry']].copy()
        export_gdf.to_file(shapefile_fn)

        print("=" * 60 + "\n")
        # Clean up temporary shapefiles
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            # Clean up POLYGONIZED_MASK
            temp_file = f'POLYGONIZED_MASK{ext}'
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

        return clipped_gdf

    def create_deforestation_map(self, fmask, deforestation_cal, deforestation_cnf, out_fn_def):
        '''
        Create combined deforestation map showing forest, deforestation in CAL, and deforestation in CNF

        :param fmask: Forest mask at the start of HRP
        :param deforestation_cal: Deforestation map during CAL period
        :param deforestation_cnf: Deforestation map during CNF period
        :param out_fn_def: Output path for combined deforestation map
        :return: None
        '''
        arr_fmask = image_to_array(fmask)
        arr_def_cal = image_to_array(deforestation_cal)
        arr_def_cnf = image_to_array(deforestation_cnf)

        deforestation_arr = np.copy(arr_fmask)

        deforestation_arr[arr_def_cnf == 1] = 3
        deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 1)] = 2
        deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (arr_fmask == 1)] = 1

        # Write deforestation map
        array_to_image(fmask, out_fn_def, deforestation_arr, gdal.GDT_Int16, -1)
        replace_ref_system(fmask, out_fn_def)

        return

    def create_plot(self, grid_area, clipped_gdf, title, out_fn, xmax=None, ymax=None):
        '''
        Create plot and save to local directory
        :param grid_area: assessment grid cell area or 100,000 (ha)
        :param clipped_gdf: thiessen_polygon geo-dataframe
        :param title: plot title
        :param out_fn: plot path
        :param xmax: maximum x-axis value
        :param ymax: maximum y-axis value
        :return: None
        '''
        # Set Seaborn Style
        sns.set_theme()

        # Filter out cells where BOTH ActualDef and PredDef are zero or near-zero
        # This prevents division by zero and improves regression quality
        # Keep cells where at least one value is greater than a small threshold (0.01 ha)
        threshold = 0.01
        valid_mask = (clipped_gdf['ActualDef'] > threshold) | (clipped_gdf['PredDef'] > threshold)
        clipped_gdf_filtered = clipped_gdf[valid_mask].copy()

        # Check if we have enough data points BEFORE filtering
        if len(clipped_gdf) < 2:
            error_msg = (
                f"\n{'='*80}\n"
                f"ERROR: Insufficient Thiessen Polygons for Regression Analysis\n"
                f"{'='*80}\n\n"
                f"Only {len(clipped_gdf)} Thiessen polygon(s) were generated.\n"
                f"Regression analysis requires at least 2 polygons to calculate slope and intercept.\n\n"
                f"CAUSE:\n"
                f"  - The evaluation grid area ({grid_area} ha) is too large for your study area\n"
                f"  - This creates grid cells larger than the masked area\n"
                f"  - Result: Only 1 or 0 polygons intersect with the area of interest\n\n"
                f"SOLUTION:\n"
                f"  1. Reduce the 'evaluation_grid_area' parameter in your model configuration\n"
                f"  2. Recommended: Try 25,000 ha or 10,000 ha instead of {grid_area} ha\n"
                f"  3. Verify your mask raster covers the expected area\n"
                f"  4. Check that your input data has sufficient spatial coverage\n\n"
                f"Current Status:\n"
                f"  - Total polygons generated: {len(clipped_gdf)}\n"
                f"  - Minimum required: 2\n"
                f"{'='*80}\n"
                f"\nSKIPPING plot generation and continuing with workflow...\n"
            )
            print(error_msg)

            # Create a placeholder image with error message instead of returning None
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5,
                    f'Plot generation skipped:\nInsufficient polygons ({len(clipped_gdf)})\n\n'
                    f'Reduce evaluation_grid_area\nfrom {grid_area} ha to 25,000 or 10,000 ha',
                    horizontalalignment='center',
                    verticalalignment='center',
                    fontsize=14,
                    color='red',
                    weight='bold',
                    transform=plt.gca().transAxes)
            plt.axis('off')
            plt.savefig(out_fn, dpi=100, bbox_inches='tight')
            plt.close()

            # Return early without creating the regression plot
            return None

        # Check if we have enough data points AFTER filtering
        if len(clipped_gdf_filtered) < 2:
            print(f"[WARNING] Only {len(clipped_gdf_filtered)} valid data points after filtering. Need at least 2 for regression.")
            print(f"[WARNING] Total polygons: {len(clipped_gdf)}, Filtered out: {len(clipped_gdf) - len(clipped_gdf_filtered)}")
            # Use original data if filtering removes too many points
            clipped_gdf_filtered = clipped_gdf.copy()

        # prepare the X/Y data
        X = np.array(clipped_gdf_filtered['ActualDef'], dtype=np.float64)
        Y = np.array(clipped_gdf_filtered['PredDef'], dtype=np.float64)

        ## Perform linear regression
        slope, intercept, _, _, _ = stats.linregress(X, Y)

        # Create the equation string
        equation = f'Y = {slope:.4f} * X + {intercept:.2f}'

        # Calculate the trend line
        trend_line = slope * X + intercept

        ## Calculate R square
        # Get the correlation coefficient
        r = np.corrcoef(X, Y)[0, 1]
        # Square the correlation coefficient
        r_squared = r ** 2

        ##Calculate MedAE
        distance_arr = [abs(X[i] - Y[i]) for i in range(len(X))]
        MedAE = np.median(distance_arr)

        ## Calculate MedAE percent
        MedAE_percent = (MedAE / int(grid_area)) * 100

        # Set the figure size
        plt.figure(figsize=(8, 6))

        # Create a scatter plot using filtered data
        plt.scatter(X, Y, color='steelblue', alpha=0.5, linewidth=1.0, s=50)

        # Add labels and title
        plt.xlabel('Actual Deforestation (ha)', color='black', fontweight='bold', labelpad=10)
        plt.ylabel('Predicted Deforestation (ha)', color='black', fontweight='bold', labelpad=10)
        plt.title(title, color='firebrick', fontweight='bold', fontsize=20, pad=20)

        # Plot the trend line
        plt.plot(X, trend_line, color='mediumseagreen', linestyle='-', label='OLS Line')

        # Plot a 1-to-1 line (using filtered data)
        max_val = max(X.max(), Y.max())
        plt.plot([0, max_val], [0, max_val], color='crimson', linestyle='--',
                 label='1:1 Line')

        ## Theil-Sen Regressor
        # Fit Theil-Sen Regressor
        # Compute Theil-Sen estimator
        ts_slope, ts_intercept, _, _ = stats.theilslopes(Y, X)

        # Generate predictions
        y_pred = ts_slope * X + ts_intercept

        # Equation of the line
        ts_equation = f'Y = {ts_slope:.4f} * X + {ts_intercept:.2f}'

        # Plot Theil-Sen Line
        plt.plot(X, y_pred, color='orange', linestyle='-', label='Theil-Sen Line')

        # Add a legend in the bottom right position
        plt.legend(loc='lower right')

        # Set a proportion to extend the limits
        extension_f = 0.1

        # Check if lim is string and "default"
        if isinstance(xmax, str) and xmax.lower() == "default":
            xmax = max(X) * (1 + extension_f)
        else:
            xmax = float(xmax)

        if isinstance(ymax, str) and ymax.lower() == "default":
            ymax = max(Y) * (1 + extension_f)
        else:
            ymax = float(ymax)

        plt.xlim([0, xmax])
        plt.ylim([0, ymax])

        text_x_pos = ymax * 0.05
        text_y_start_pos = ymax * 0.9
        text_y_gap = ymax * 0.05

        # Adjust plt texts with the new calculated positions
        plt.text(text_x_pos, text_y_start_pos, f'Theil-Sen : {ts_equation}', fontsize=11,
                 color='black')
        plt.text(text_x_pos, text_y_start_pos - text_y_gap, f'OLS : {equation}', fontsize=11, color='black')
        plt.text(text_x_pos, text_y_start_pos - 2 * text_y_gap, f'Samples = {len(X)}', fontsize=11, color='black')
        plt.text(text_x_pos, text_y_start_pos - 3 * text_y_gap, f'R^2 = {r_squared:.4f}', fontsize=11, color='black')
        plt.text(text_x_pos, text_y_start_pos - 4 * text_y_gap, f'MedAE = {MedAE:.2f} ({MedAE_percent:.2f}%)',
                 fontsize=11, color='black')

        # x, yticks
        plt.yticks(fontsize=10, color='dimgrey')
        plt.xticks(fontsize=10, color='dimgrey')

        # Save the plot
        # Ensure output directory exists
        out_dir = os.path.dirname(out_fn)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # Save plot with error handling for network drives and permission issues
        try:
            plt.savefig(out_fn, dpi=100, bbox_inches='tight')
        except (PermissionError, OSError) as e:
            print(f"[WARNING] Failed to save directly to {out_fn}")
            print(f"[WARNING] Error: {e}")
            # Try saving to temp directory first, then copy
            import tempfile
            import shutil
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_path = temp_file.name
            temp_file.close()

            print(f"[INFO] Attempting to save to temporary file: {temp_path}")
            plt.savefig(temp_path, dpi=100, bbox_inches='tight')
            print(f"[INFO] Copying from temp to final destination...")
            shutil.copy2(temp_path, out_fn)
            os.remove(temp_path)
            print(f"[SUCCESS] Plot saved successfully to {out_fn}")

        plt.close()  # Close the figure to free memory and release file handles

        # Save statistics to text file
        stats_txt = os.path.splitext(out_fn)[0] + '_statistics.txt'
        with open(stats_txt, 'w', encoding='utf-8') as f:
            f.write("Model Evaluation Statistics\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Title: {title}\n")
            f.write(f"Grid Area: {grid_area:,} ha\n\n")

            f.write("Regression Analysis\n")
            f.write("-" * 60 + "\n")
            f.write(f"Theil-Sen Regression: {ts_equation}\n")
            f.write(f"OLS Regression:       {equation}\n\n")

            f.write("Statistical Metrics\n")
            f.write("-" * 60 + "\n")
            f.write(f"Number of Samples:    {len(X)}\n")
            f.write(f"R-squared (R²):       {r_squared:.4f}\n")
            f.write(f"Median Absolute Error (MedAE): {MedAE:.2f} ha ({MedAE_percent:.2f}%)\n\n")

            f.write("Data Range\n")
            f.write("-" * 60 + "\n")
            f.write(f"Actual Deforestation:\n")
            f.write(f"  Minimum:  {X.min():.2f} ha\n")
            f.write(f"  Maximum:  {X.max():.2f} ha\n")
            f.write(f"  Mean:     {X.mean():.2f} ha\n")
            f.write(f"  Std Dev:  {X.std():.2f} ha\n\n")
            f.write(f"Predicted Deforestation:\n")
            f.write(f"  Minimum:  {Y.min():.2f} ha\n")
            f.write(f"  Maximum:  {Y.max():.2f} ha\n")
            f.write(f"  Mean:     {Y.mean():.2f} ha\n")
            f.write(f"  Std Dev:  {Y.std():.2f} ha\n")

        return

    def remove_temp_files(self):
        '''
        Remove temporary files created during model evaluation
        :return: None
        '''
        # Files to check for and delete
        mask_file = 'mask'
        shapefiles_to_delete = ["TEMP_POLYGONIZED", "POLYGONIZED_MASK", "thiessen_polygon_temp", "temp_vector"]

        # Shapefile associated extensions
        mask_file_extensions = [".tif", ".rst", ".rdc", ".RST", ".RST.aux.xml", ".ref"]
        shapefile_extensions = [".shp", ".shx", ".dbf", ".prj", ".sbn", ".sbx", ".cpg", ".shp.xml"]

        # Delete mask files
        for mask_ext in mask_file_extensions:
            mask_filename = f"{mask_file}{mask_ext}"
            if os.path.exists(mask_filename):
                os.remove(mask_filename)

        # Delete shapefiles with associated extensions
        for shp_base in shapefiles_to_delete:
            for ext in shapefile_extensions:
                full_filename = f"{shp_base}{ext}"
                if os.path.exists(full_filename):
                    os.remove(full_filename)
        return

    def create_voronoi_mask(self, jnr_lb_full_areas, jnr_value, output_path):
        """
        Create a binary Voronoi mask containing only the analysis area (no exclusions).

        This mask is used for generating complete Voronoi polygons without fragmentation
        from exclusion zones. It extracts the analysis area value from the area of interest raster.

        Args:
            jnr_lb_full_areas: Path to area of interest binary mask raster
            jnr_value: Integer value representing analysis area in the raster (default: 1 for binary mask)
            output_path: Path where the binary Voronoi mask will be saved

        Returns:
            str: Path to created Voronoi mask

        Example:
            evaluator = ModelEvaluation()
            mask_path = evaluator.create_voronoi_mask(
                jnr_lb_full_areas="path/to/area_of_interest.tif",
                jnr_value=1,
                output_path="path/to/Voronoi_Mask.tif"
            )
        """
        from osgeo import gdal
        import numpy as np

        # Open the JNR/LB full areas raster
        ds = gdal.Open(jnr_lb_full_areas)
        if ds is None:
            raise ValueError(f"Could not open JNR/LB raster: {jnr_lb_full_areas}")

        band = ds.GetRasterBand(1)
        data = band.ReadAsArray()

        # Create mask: 1 where jnr_value, 0 elsewhere
        voronoi_mask_data = np.where(data == jnr_value, 1, 0).astype(np.uint8)

        # Create output raster
        driver = gdal.GetDriverByName('GTiff')
        out_ds = driver.Create(output_path, ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Byte)
        out_ds.SetGeoTransform(ds.GetGeoTransform())
        out_ds.SetProjection(ds.GetProjection())
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(voronoi_mask_data)
        out_band.FlushCache()

        # Close datasets to release file handles
        out_band = None
        out_ds = None
        band = None
        ds = None

        return output_path

    def run_evaluation(self, grid_area, density_map, deforestation_map, mask_voronoi, mask_exclusions, title, out_fn,
                       xmax="default", ymax="default"):
        """
        Run model evaluation for Testing Stage CAL or CNF phases.

        This saves all outputs in the same location as the PNG:
        - Evaluation plot (PNG + statistics TXT)
        - Thiessen polygon grid (Excel file)
        - Residuals map (GeoTIFF)

        Args:
            grid_area: Assessment grid cell area in hectares (e.g., 50000 for 50km²)
            density_map: Path to density map (fitting or adjusted prediction density)
            deforestation_map: Path to deforestation map (CAL: T1-T2, CNF: T2-T3)
            mask_voronoi: Full jurisdictional mask for Voronoi generation (no exclusions)
            mask_exclusions: Jurisdictional mask with exclusions for final statistics
            title: Title for the evaluation plot
            out_fn: Output path for the plot PNG file
            xmax: Maximum x-axis value (default: "default" for auto-scale)
            ymax: Maximum y-axis value (default: "default" for auto-scale)

        Returns:
            None
        """
        # Get output directory and set as working directory
        output_dir = os.path.dirname(out_fn)

        # Ensure output directory exists before changing to it
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        original_dir = os.getcwd()
        os.chdir(output_dir)

        try:
            # Create Thiessen polygons using two-mask approach
            base_name = os.path.splitext(os.path.basename(out_fn))[0]
            residuals_map = os.path.join(output_dir, f"{base_name}_residuals.tif")
            grid_excel = os.path.join(output_dir, f"{base_name}_grid.xlsx")

            thiessen_gdf = self.create_thiessen_polygon(
                grid_area=grid_area,
                mask_voronoi=mask_voronoi,
                mask_exclusions=mask_exclusions,
                density=density_map,
                deforestation=deforestation_map,
                out_fn=grid_excel,
                raster_fn=residuals_map
            )

            # Create the evaluation plot
            self.create_plot(
                grid_area=grid_area,
                clipped_gdf=thiessen_gdf,
                title=title,
                out_fn=out_fn,
                xmax=xmax,
                ymax=ymax
            )

            # Cleanup
            del thiessen_gdf
            import gc
            gc.collect()

        finally:
            # Return to original directory
            os.chdir(original_dir)

# ======================================
# Evaluate Testing Stage - Benchmark Model/Alternative Model
# ======================================

def evaluate_testing_stage(folders, fcbm_file, jnr_lb_full_areas, jnr_with_exclusions_mask,
                           jnr_value=1, model_type='benchmark', evaluation_grid_area=100000,
                           evaluation_xmax="default", evaluation_ymax="default",
                           project_name=None, version=None,
                           run_eval_cal=True, run_eval_cnf=True,
                           cancel_flag=None):
    """
    Run model evaluation for Fitting (CAL) and/or Prediction (CNF) phases of the Testing Stage.

    This function evaluates the model performance by comparing predicted density maps
    against actual deforestation maps using grid-based analysis. It automatically locates
    the required files based on the VT7 folder structure and model type.

    Args:
        folders: VT7FolderStructure object with testing model folders created
        fcbm_file: Path to FCBM output file (used to generate deforestation maps on-demand)
        jnr_lb_full_areas: Path to area of interest binary mask (for Voronoi generation)
        jnr_with_exclusions_mask: Path to JNR mask with exclusions applied
        jnr_value: Value representing analysis area in the mask raster (default: 1 for binary mask)
        model_type: Type of model to evaluate: 'benchmark' or 'alternative' (default: 'benchmark')
        evaluation_grid_area: Grid cell area in hectares for evaluation (default: 100000 = 100km²)
        evaluation_xmax: Max x-axis value for evaluation plots (default: "default")
        evaluation_ymax: Max y-axis value for evaluation plots (default: "default")
        project_name: Project name to use in filenames (default: None)
        version: Version identifier to use in filenames (default: None)
        run_eval_cal: Whether to run evaluation for CAL phase (default: True)
        run_eval_cnf: Whether to run evaluation for CNF phase (default: True)
        cancel_flag: Optional callback function that returns True to cancel operation

    Returns:
        dict: Dictionary containing evaluation output paths:
            - evaluation_cal_plot: Path to CAL evaluation plot (if run_eval_cal=True)
            - evaluation_cnf_plot: Path to CNF evaluation plot (if run_eval_cnf=True)

    Raises:
        RuntimeError: If operation is cancelled by user
    """

    # Helper function to check cancellation
    def _check_cancel():
        if cancel_flag and cancel_flag():
            raise RuntimeError("Operation cancelled by user")

    _check_cancel()

    import tempfile
    from .utils import raster_calculator

    # Determine paths based on model type
    if model_type == 'benchmark':
        fitting_folder = folders.testing_benchmark_fitting
        prediction_folder = folders.testing_benchmark_prediction
        evaluation_folder = folders.testing_benchmark_evaluation
        model_name = "Benchmark Model"
        prefix = "BCM"
    elif model_type == 'alternative':
        fitting_folder = folders.testing_alternative_fitting
        prediction_folder = folders.testing_alternative_prediction
        evaluation_folder = folders.testing_alternative_evaluation
        model_name = "Alternative Model"
        prefix = "ALT"
    else:
        raise ValueError(f"Invalid model_type: {model_type}. Must be 'benchmark' or 'alternative'")

    # Validate at least one evaluation is selected
    if not run_eval_cal and not run_eval_cnf:
        raise ValueError("At least one evaluation (run_eval_cal or run_eval_cnf) must be True")

    # Build file paths based on standard naming convention with model prefix
    # Note: File numbering differs between BCM and ALT models
    from .utils import build_filename
    fitting_density_map_cal = os.path.join(fitting_folder, build_filename(f"0{'7' if model_type == 'benchmark' else '4'}_{prefix}_Fitting_Density_Map_CAL.tif", project_name, version))
    adjusted_prediction_density_map_cnf = os.path.join(prediction_folder, build_filename(f"04_{prefix}_Adjusted_Prediction_Density_Map_CNF.tif", project_name, version))

    # Generate deforestation maps on-demand from FCBM and run evaluations
    # All evaluation must happen inside the temp directory context
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mask FCBM to the area of interest
        fcbm_masked = os.path.join(temp_dir, "fcbm_masked.tif")
        expression_mask = "if(map1[1] == 1, map2[1], no_data)"
        raster_calculator(
            input_files=[jnr_with_exclusions_mask, fcbm_file],
            output_file=fcbm_masked,
            expression=expression_mask,
            out_dtype="uint8"
        )

        # Generate T1T2 deforestation
        t1t2_deforestation = os.path.join(temp_dir, "T1T2_deforestation.tif")
        expression_t1t2 = "if((map1[1]==6) | (map1[1]==7), 1, if(map1[1]==no_data, no_data, 0))"
        raster_calculator(
            input_files=fcbm_masked,
            output_file=t1t2_deforestation,
            expression=expression_t1t2,
            out_dtype="uint8"
        )

        # Generate T2T3 deforestation
        t2t3_deforestation = os.path.join(temp_dir, "T2T3_deforestation.tif")
        expression_t2t3 = "if(map1[1]==8, 1, if(map1[1]==no_data, no_data, 0))"
        raster_calculator(
            input_files=fcbm_masked,
            output_file=t2t3_deforestation,
            expression=expression_t2t3,
            out_dtype="uint8"
        )

        # Create Voronoi mask (JNR only, no exclusions) for improved polygon generation
        jnr_voronoi_mask = os.path.join(temp_dir, "voronoi_mask.tif")
        evaluator = ModelEvaluation()
        evaluator.create_voronoi_mask(jnr_lb_full_areas, jnr_value, jnr_voronoi_mask)
        _check_cancel()

        # Initialize result variables
        evaluation_cal_plot = None
        evaluation_cnf_plot = None

        ######### Fitting Phase (CAL) Evaluation #########
        if run_eval_cal:
            _check_cancel()
            print("\n" + "="*60)
            print(f"Running Model Evaluation for {model_name} - Fitting Phase (CAL)...")
            print("="*60)

            evaluation_cal_plot = os.path.join(evaluation_folder, build_filename(f"01_{prefix}_Fitting_Phase_Evaluation.png", project_name, version))

            evaluator.run_evaluation(
                grid_area=evaluation_grid_area,
                density_map=fitting_density_map_cal,
                deforestation_map=t1t2_deforestation,
                mask_voronoi=jnr_voronoi_mask,
                mask_exclusions=jnr_with_exclusions_mask,
                title=f"VT7 {model_name} - Fitting Phase (CAL)",
                out_fn=evaluation_cal_plot,
                xmax=evaluation_xmax,
                ymax=evaluation_ymax
            )

            print(f"CAL Evaluation plot saved: {evaluation_cal_plot}")
            print("="*60 + "\n")
            _check_cancel()


        ######### Prediction Phase (CNF) Evaluation #########
        if run_eval_cnf:
            _check_cancel()
            print("\n" + "="*60)
            print(f"Running Model Evaluation for {model_name} - Prediction Phase (CNF)...")
            print("="*60)

            evaluation_cnf_plot = os.path.join(evaluation_folder, build_filename(f"02_{prefix}_Prediction_Phase_Evaluation.png", project_name, version))

            evaluator.run_evaluation(
                grid_area=evaluation_grid_area,
                density_map=adjusted_prediction_density_map_cnf,
                deforestation_map=t2t3_deforestation,
                mask_voronoi=jnr_voronoi_mask,
                mask_exclusions=jnr_with_exclusions_mask,
                title=f"VT7 {model_name} - Prediction Phase (CNF)",
                out_fn=evaluation_cnf_plot,
                xmax=evaluation_xmax,
                ymax=evaluation_ymax
            )

            print(f"CNF Evaluation plot saved: {evaluation_cnf_plot}")
            print("="*60 + "\n")
            _check_cancel()

        # Build completion message
        evals_run = []
        if run_eval_cal:
            evals_run.append("CAL")
        if run_eval_cnf:
            evals_run.append("CNF")
        print("="*60)
        print(f"Model Evaluation - {model_name} ({', '.join(evals_run)}) COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")

    # Return evaluation outputs (after temp directory is cleaned up)
    return {
        'evaluation_cal_plot': evaluation_cal_plot,
        'evaluation_cnf_plot': evaluation_cnf_plot
    }

# ======================================
# Testing Stage - Benchmark Model/Alternative Model
# ======================================

