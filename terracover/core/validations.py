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


from pathlib import Path
from typing import List, Dict, Union, Tuple, Optional
from pathlib import Path
import warnings


# ------------------------------------------------------------------------


class _FileOverwriteValidator:
    """
    A validator to check if files exist and warn about potential overwrites.
    Works with any file extension and returns error messages for existing files.
    """
    
    @classmethod
    def validate_file_overwrite(cls, file_path: str, check_writable: bool = True) -> List[str]:
        """
        Validates if a file exists and would be overwritten.
        
        Args:
            file_path (str): Path to the file to check
            check_writable (bool): If True, also checks if existing file can be overwritten
            
        Returns:
            List[str]: List of error messages. Empty list if file doesn't exist (safe to create).
        """
        errors = []
        
        # Check if file path is provided
        if not file_path:
            errors.append("File path cannot be empty or None")
            return errors
        
        # Convert to Path object for easier handling
        path = Path(file_path)
        
        # Check if file exists
        if path.exists():
            if path.is_file():
                errors.append(f"File exists: {file_path}")
                
                # Check if the existing file can be overwritten (writable)
                if check_writable:
                    try:
                        # Test write permission by attempting to open in append mode
                        with open(path, 'a'):
                            pass
                    except PermissionError:
                        errors.append(f"File exists but cannot be overwritten: Permission denied for {file_path}")
                    except OSError as e:
                        errors.append(f"File exists but cannot be overwritten: {str(e)}")
                    except Exception as e:
                        errors.append(f"Unexpected error checking file write permissions: {str(e)}")
                        
            elif path.is_dir():
                errors.append(f"Path exists but is a directory, not a file: {file_path}")
            else:
                errors.append(f"Path exists but is not a regular file: {file_path}")
        
        return errors
    
    @classmethod
    def validate_multiple_files_overwrite(cls, file_paths: List[str], 
                                         check_writable: bool = True) -> List[str]:
        """
        Validates multiple files for potential overwrites.
        
        Args:
            file_paths (List[str]): List of file paths to check
            check_writable (bool): If True, also checks if existing files can be overwritten
            
        Returns:
            List[str]: List of error messages. Empty list if no files exist.
        """
        errors = []
        
        if not file_paths:
            errors.append("File paths list cannot be empty or None")
            return errors
        
        for file_path in file_paths:
            file_errors = cls.validate_file_overwrite(file_path, check_writable)
            errors.extend(file_errors)
        
        return errors
    
    @classmethod
    def validate_output_directory(cls, output_dir: str, output_files: List[str], 
                                 check_writable: bool = True) -> List[str]:
        """
        Validates an output directory and checks for potential file overwrites.
        
        Args:
            output_dir (str): Path to the output directory
            output_files (List[str]): List of output file names (without directory path)
            check_writable (bool): If True, checks write permissions
            
        Returns:
            List[str]: List of error messages. Empty list if no issues found.
        """
        errors = []
        
        if not output_dir:
            errors.append("Output directory path cannot be empty or None")
            return errors
        
        if not output_files:
            errors.append("Output files list cannot be empty or None")
            return errors
        
        # Validate the output directory first
        output_dir_path = Path(output_dir)
        
        if not output_dir_path.exists():
            errors.append(f"Output directory does not exist: {output_dir}")
            return errors
        
        if not output_dir_path.is_dir():
            errors.append(f"Output path is not a directory: {output_dir}")
            return errors
        
        # Check if directory is writable
        if check_writable:
            try:
                import tempfile
                with tempfile.TemporaryFile(dir=output_dir):
                    pass
            except PermissionError:
                errors.append(f"Output directory is not writable: Permission denied for {output_dir}")
            except OSError as e:
                errors.append(f"Output directory is not writable: {str(e)}")
            except Exception as e:
                errors.append(f"Unexpected error testing directory write permissions: {str(e)}")
        
        # Check each output file for potential overwrites
        for file_name in output_files:
            if not file_name:
                errors.append("Output file name cannot be empty")
                continue
                
            full_file_path = output_dir_path / file_name
            file_errors = cls.validate_file_overwrite(str(full_file_path), check_writable)
            errors.extend(file_errors)
        
        return errors
    
    @classmethod
    def validate_batch_processing(cls, input_files: List[str], output_dir: str, 
                                 output_suffix: str = "_processed", 
                                 output_extension: str = None,
                                 check_writable: bool = True) -> List[str]:
        """
        Validates batch processing scenario where input files generate output files.
        
        Args:
            input_files (List[str]): List of input file paths
            output_dir (str): Directory where output files will be created
            output_suffix (str): Suffix to add to output file names
            output_extension (str): Extension for output files. If None, keeps original extension
            check_writable (bool): If True, checks write permissions
            
        Returns:
            List[str]: List of error messages. Empty list if no overwrites detected.
        """
        errors = []
        
        if not input_files:
            errors.append("Input files list cannot be empty or None")
            return errors
        
        if not output_dir:
            errors.append("Output directory cannot be empty or None")
            return errors
        
        # Validate output directory
        output_dir_path = Path(output_dir)
        
        if not output_dir_path.exists():
            errors.append(f"Output directory does not exist: {output_dir}")
            return errors
        
        if not output_dir_path.is_dir():
            errors.append(f"Output path is not a directory: {output_dir}")
            return errors
        
        # Check if directory is writable
        if check_writable:
            try:
                import tempfile
                with tempfile.TemporaryFile(dir=output_dir):
                    pass
            except PermissionError:
                errors.append(f"Output directory is not writable: Permission denied for {output_dir}")
            except OSError as e:
                errors.append(f"Output directory is not writable: {str(e)}")
            except Exception as e:
                errors.append(f"Unexpected error testing directory write permissions: {str(e)}")
        
        # Generate output file paths and check for overwrites
        for input_file in input_files:
            if not input_file:
                errors.append("Input file path cannot be empty")
                continue
            
            input_path = Path(input_file)
            
            # Generate output filename
            if output_extension:
                # Use specified extension
                output_name = f"{input_path.stem}{output_suffix}.{output_extension.lstrip('.')}"
            else:
                # Keep original extension
                output_name = f"{input_path.stem}{output_suffix}{input_path.suffix}"
            
            output_file_path = output_dir_path / output_name
            
            # Check for potential overwrite
            file_errors = cls.validate_file_overwrite(str(output_file_path), check_writable)
            errors.extend(file_errors)
        
        return errors
    
    @classmethod
    def get_existing_files(cls, file_paths: List[str]) -> List[str]:
        """
        Returns a list of files that exist from the provided file paths.
        
        Args:
            file_paths (List[str]): List of file paths to check
            
        Returns:
            List[str]: List of existing file paths
        """
        existing_files = []
        
        if not file_paths:
            return existing_files
        
        for file_path in file_paths:
            if file_path and Path(file_path).is_file():
                existing_files.append(file_path)
        
        return existing_files
    
    @classmethod
    def count_overwrites(cls, file_paths: List[str]) -> Dict[str, int]:
        """
        Counts how many files would be overwritten vs created new.
        
        Args:
            file_paths (List[str]): List of file paths to analyze
            
        Returns:
            Dict[str, int]: Dictionary with counts of existing vs new files
        """
        result = {
            'existing_files': 0,
            'new_files': 0,
            'invalid_paths': 0
        }
        
        if not file_paths:
            return result
        
        for file_path in file_paths:
            if not file_path:
                result['invalid_paths'] += 1
                continue
                
            path = Path(file_path)
            if path.exists() and path.is_file():
                result['existing_files'] += 1
            elif not path.exists():
                result['new_files'] += 1
            else:
                result['invalid_paths'] += 1
        
        return result


# ------------------------------------------------------------------------


class _FolderValidator:
    """
    A simple validator for folder/directory validation.
    Provides basic folder validation with error list return format.
    """
    
    @classmethod
    def validate_folder(cls, folder_path: str, check_readable: bool = True, 
                       check_writable: bool = False, check_empty: bool = False) -> List[str]:
        """
        Validates if a folder exists and optionally checks permissions and content.
        
        Args:
            folder_path (str): Path to the folder to validate
            check_readable (bool): If True, checks if folder can be read
            check_writable (bool): If True, checks if folder can be written to
            check_empty (bool): If True, validates that folder is not empty
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        errors = []
        
        # Check if folder path is provided
        if not folder_path:
            errors.append("Folder path cannot be empty or None")
            return errors
        
        # Convert to Path object for easier handling
        path = Path(folder_path)
        
        # Check if folder exists
        if not path.exists():
            errors.append(f"Folder does not exist: {folder_path}")
            return errors  # No point checking other things if folder doesn't exist
        
        # Check if path is actually a directory
        if not path.is_dir():
            errors.append(f"Path is not a directory: {folder_path}")
            return errors
        
        # Check if folder can be read
        if check_readable:
            try:
                # Try to list directory contents
                list(path.iterdir())
            except PermissionError:
                errors.append(f"Folder cannot be read: Permission denied for {folder_path}")
            except OSError as e:
                errors.append(f"Folder cannot be read: {str(e)}")
            except Exception as e:
                errors.append(f"Unexpected error reading folder: {str(e)}")
        
        # Check if folder can be written to
        if check_writable:
            try:
                # Try to create a temporary file to test write permissions
                import tempfile
                with tempfile.TemporaryFile(dir=folder_path):
                    pass  # Just test creation and deletion
            except PermissionError:
                errors.append(f"Folder is not writable: Permission denied for {folder_path}")
            except OSError as e:
                errors.append(f"Folder is not writable: {str(e)}")
            except Exception as e:
                errors.append(f"Unexpected error testing folder write permissions: {str(e)}")
        
        # Check if folder is empty (if requested to validate non-empty)
        if check_empty:
            try:
                # Check if folder has any contents
                if not any(path.iterdir()):
                    errors.append(f"Folder is empty: {folder_path}")
            except PermissionError:
                errors.append(f"Cannot check if folder is empty: Permission denied for {folder_path}")
            except Exception as e:
                errors.append(f"Error checking folder contents: {str(e)}")
        
        return errors
    
    @classmethod
    def validate_folder_structure(cls, base_folder: str, required_subfolders: List[str], 
                                 create_missing: bool = False) -> List[str]:
        """
        Validates that a folder contains required subfolders.
        
        Args:
            base_folder (str): Path to the base folder
            required_subfolders (List[str]): List of required subfolder names
            create_missing (bool): If True, attempts to create missing subfolders
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        errors = []
        
        # First validate the base folder
        base_errors = cls.validate_folder(base_folder)
        if base_errors:
            errors.extend(base_errors)
            return errors  # Can't check subfolders if base folder is invalid
        
        if not required_subfolders:
            return errors  # No subfolders to check
        
        base_path = Path(base_folder)
        
        for subfolder_name in required_subfolders:
            if not subfolder_name:
                errors.append("Subfolder name cannot be empty")
                continue
                
            subfolder_path = base_path / subfolder_name
            
            if not subfolder_path.exists():
                if create_missing:
                    try:
                        subfolder_path.mkdir(parents=True, exist_ok=True)
                    except PermissionError:
                        errors.append(f"Cannot create required subfolder: Permission denied for {subfolder_path}")
                    except OSError as e:
                        errors.append(f"Cannot create required subfolder {subfolder_path}: {str(e)}")
                    except Exception as e:
                        errors.append(f"Unexpected error creating subfolder {subfolder_path}: {str(e)}")
                else:
                    errors.append(f"Required subfolder does not exist: {subfolder_path}")
            elif not subfolder_path.is_dir():
                errors.append(f"Required subfolder path exists but is not a directory: {subfolder_path}")
        
        return errors
    
    @classmethod
    def validate_multiple_folders(cls, folder_paths: List[str], check_readable: bool = True,
                                 check_writable: bool = False, check_empty: bool = False) -> List[str]:
        """
        Validates multiple folders with the same criteria.
        
        Args:
            folder_paths (List[str]): List of folder paths to validate
            check_readable (bool): If True, checks if folders can be read
            check_writable (bool): If True, checks if folders can be written to
            check_empty (bool): If True, validates that folders are not empty
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        errors = []
        
        if not folder_paths:
            errors.append("Folder paths list cannot be empty or None")
            return errors
        
        for folder_path in folder_paths:
            folder_errors = cls.validate_folder(folder_path, check_readable, check_writable, check_empty)
            # Prefix errors with folder path for clarity
            for error in folder_errors:
                if not error.startswith(folder_path):
                    errors.append(f"{folder_path}: {error}")
                else:
                    errors.append(error)
        
        return errors


# ------------------------------------------------------------------------


class _SpatialFileValidator:
    """
    A comprehensive validator for spatial files (vector and raster formats).
    Provides validation for file existence, extensions, readability, coordinate systems,
    raster alignment, and CRS consistency across multiple files.
    """
    
    # Supported file extensions
    VECTOR_EXTENSIONS = {'.shp', '.gpkg'}
    RASTER_EXTENSIONS = {'.tif', '.tiff'}
    ALL_EXTENSIONS = VECTOR_EXTENSIONS | RASTER_EXTENSIONS
    
    @classmethod
    def validate_vector_file(cls, file_path: str, require_projected: bool = False) -> List[str]:
        """
        Validates if a vector file exists and has a valid spatial file extension (.shp or .gpkg).
        Optionally validates that the coordinate system is projected (not geographical).
        
        Args:
            file_path (str): Path to the file to validate
            require_projected (bool): If True, validates that CRS is projected, not geographical
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        errors = []
        
        # Check if file path is provided
        if not file_path:
            errors.append("File path cannot be empty or None")
            return errors
        
        # Convert to Path object for easier handling
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            errors.append(f"File does not exist: {file_path}")
        elif not path.is_file():
            errors.append(f"Path is not a file: {file_path}")
        
        # Check file extension
        file_extension = path.suffix.lower()
        
        if file_extension not in cls.VECTOR_EXTENSIONS:
            errors.append(f"Invalid file extension '{file_extension}'. Must be .shp or .gpkg")
        
        # Check if file can be read (only if file exists)
        if path.exists() and path.is_file():
            try:
                # Test basic read permission
                with open(path, 'rb') as f:
                    f.read(1)  # Try to read just one byte
            except PermissionError:
                errors.append(f"File cannot be read: Permission denied for {file_path}")
            except IOError as e:
                errors.append(f"File cannot be read: {str(e)}")
            except Exception as e:
                errors.append(f"Unexpected error reading file: {str(e)}")
        
        # Check coordinate reference system if required
        if require_projected and path.exists() and path.is_file() and file_extension in cls.VECTOR_EXTENSIONS:
            try:
                import geopandas as gpd
                import warnings
                
                # Suppress warnings for cleaner error messages
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    # Read spatial file
                    gdf = gpd.read_file(file_path)
                    
                    # Check if CRS is defined
                    if gdf.crs is None:
                        errors.append("File has no coordinate reference system (CRS) defined")
                    else:
                        # Check if CRS is geographical (lat/lon) vs projected
                        try:
                            # GeoPandas 1.1.1 compatible CRS check
                            is_geographic = gdf.crs.is_geographic if hasattr(gdf.crs, 'is_geographic') else gdf.crs.to_string().startswith('GEOGCS')
                            if is_geographic:
                                crs_name = gdf.crs.name if hasattr(gdf.crs, 'name') else str(gdf.crs)
                                errors.append(f"File uses geographical coordinate system ({crs_name}). Projected coordinate system required")
                        except AttributeError:
                            # Fallback for older GeoPandas versions
                            crs_str = str(gdf.crs)
                            if 'GEOGCS' in crs_str or 'EPSG:4326' in crs_str:
                                errors.append(f"File uses geographical coordinate system ({crs_str}). Projected coordinate system required")
                            
            except ImportError:
                errors.append("Cannot validate coordinate system: geopandas library not available")
            except Exception as e:
                errors.append(f"Error checking coordinate system: {str(e)}")
        
        return errors

    @classmethod
    def validate_raster_file(cls, file_path: str, require_projected: bool = False) -> List[str]:
        """
        Validates if a raster file exists and has a valid extension (.tif or .tiff).
        Optionally validates that the coordinate system is projected (not geographical).
        
        Args:
            file_path (str): Path to the raster file to validate
            require_projected (bool): If True, validates that CRS is projected, not geographical
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        errors = []
        
        # Check if file path is provided
        if not file_path:
            errors.append("File path cannot be empty or None")
            return errors
        
        # Convert to Path object for easier handling
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            errors.append(f"File does not exist: {file_path}")
        elif not path.is_file():
            errors.append(f"Path is not a file: {file_path}")
        
        # Check file extension
        file_extension = path.suffix.lower()
        
        if file_extension not in cls.RASTER_EXTENSIONS:
            errors.append(f"Invalid file extension '{file_extension}'. Must be .tif or .tiff")
        
        # Check if file can be read (only if file exists)
        if path.exists() and path.is_file():
            try:
                # Test basic read permission
                with open(path, 'rb') as f:
                    f.read(1)  # Try to read just one byte
            except PermissionError:
                errors.append(f"File cannot be read: Permission denied for {file_path}")
            except IOError as e:
                errors.append(f"File cannot be read: {str(e)}")
            except Exception as e:
                errors.append(f"Unexpected error reading file: {str(e)}")
        
        # Check coordinate reference system if required
        if require_projected and path.exists() and path.is_file() and file_extension in cls.RASTER_EXTENSIONS:
            try:
                import rasterio
                import warnings
                
                # Suppress warnings for cleaner error messages
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    # Read raster file
                    with rasterio.open(file_path) as src:
                        # Check if CRS is defined
                        if src.crs is None:
                            errors.append("Raster file has no coordinate reference system (CRS) defined")
                        else:
                            # Check if CRS is geographical (lat/lon) vs projected
                            try:
                                # Rasterio compatible CRS check
                                is_geographic = src.crs.is_geographic if hasattr(src.crs, 'is_geographic') else 'GEOGCS' in str(src.crs)
                                if is_geographic:
                                    errors.append(f"Raster uses geographical coordinate system ({src.crs}). Projected coordinate system required")
                            except AttributeError:
                                # Fallback for compatibility
                                crs_str = str(src.crs)
                                if 'GEOGCS' in crs_str or 'EPSG:4326' in crs_str:
                                    errors.append(f"Raster uses geographical coordinate system ({crs_str}). Projected coordinate system required")
                            
            except ImportError:
                errors.append("Cannot validate coordinate system: rasterio library not available")
            except Exception as e:
                errors.append(f"Error checking raster coordinate system: {str(e)}")
        
        return errors

    @classmethod
    def validate_raster_alignment(cls, file_paths: List[str]) -> List[str]:
        """
        Validates that multiple raster files (.tif or .tiff) have the same extent 
        and number of rows and columns.
        
        Args:
            file_paths (List[str]): List of paths to raster files to validate
            
        Returns:
            List[str]: List of error messages. Empty list if all files are aligned.
        """
        errors = []
        
        # Check if file paths list is provided and not empty
        if not file_paths:
            errors.append("File paths list cannot be empty or None")
            return errors
        
        if len(file_paths) < 2:
            errors.append("At least 2 files are required for alignment validation")
            return errors
        
        # First validate each file individually
        valid_files = []
        for file_path in file_paths:
            file_errors = cls.validate_raster_file(file_path)
            if file_errors:
                # Add file-specific errors
                for error in file_errors:
                    errors.append(f"{file_path}: {error}")
            else:
                valid_files.append(file_path)
        
        # If we don't have at least 2 valid files, can't check alignment
        if len(valid_files) < 2:
            errors.append("Need at least 2 valid raster files to check alignment")
            return errors
        
        # Check alignment of valid files
        try:
            import rasterio
            import warnings
            
            # Suppress warnings for cleaner error messages
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Get properties from the first file as reference
                reference_file = valid_files[0]
                reference_props = {}
                
                with rasterio.open(reference_file) as ref_src:
                    reference_props = {
                        'bounds': ref_src.bounds,
                        'width': ref_src.width,
                        'height': ref_src.height,
                        'transform': ref_src.transform,
                        'crs': ref_src.crs
                    }
                
                # Compare all other files to the reference
                for i, file_path in enumerate(valid_files[1:], 1):
                    with rasterio.open(file_path) as src:
                        # Check dimensions (rows and columns)
                        if src.height != reference_props['height']:
                            errors.append(f"Height mismatch: {reference_file} has {reference_props['height']} rows, "
                                        f"{file_path} has {src.height} rows")
                        
                        if src.width != reference_props['width']:
                            errors.append(f"Width mismatch: {reference_file} has {reference_props['width']} columns, "
                                        f"{file_path} has {src.width} columns")
                        
                        # Check extent (bounds)
                        if src.bounds != reference_props['bounds']:
                            errors.append(f"Extent mismatch: {reference_file} bounds {reference_props['bounds']}, "
                                        f"{file_path} bounds {src.bounds}")
                        
                        # Check transform (pixel size and origin)
                        if src.transform != reference_props['transform']:
                            errors.append(f"Transform mismatch: {reference_file} and {file_path} have different "
                                        f"pixel sizes or origins")
                        
                        # Optional: Check CRS compatibility
                        if src.crs != reference_props['crs']:
                            errors.append(f"CRS mismatch: {reference_file} uses {reference_props['crs']}, "
                                        f"{file_path} uses {src.crs}")
                            
        except ImportError:
            errors.append("Cannot validate raster alignment: rasterio library not available")
        except Exception as e:
            errors.append(f"Error checking raster alignment: {str(e)}")
        
        return errors

    @classmethod
    def validate_crs_consistency(cls, file_paths: List[str]) -> List[str]:
        """
        Validates that multiple spatial files (tif, tiff, shp, gpkg) all have 
        the same coordinate reference system (CRS).
        
        Args:
            file_paths (List[str]): List of paths to spatial files to validate
            
        Returns:
            List[str]: List of error messages. Empty list if all files have the same CRS.
        """
        errors = []
        
        # Check if file paths list is provided and not empty
        if not file_paths:
            errors.append("File paths list cannot be empty or None")
            return errors
        
        if len(file_paths) < 2:
            errors.append("At least 2 files are required for CRS consistency validation")
            return errors
        
        # Group files by type and validate each
        vector_files = []
        raster_files = []
        invalid_files = []
        
        for file_path in file_paths:
            path = Path(file_path)
            extension = path.suffix.lower()
            
            if extension in cls.VECTOR_EXTENSIONS:
                file_errors = cls.validate_vector_file(file_path)
                if file_errors:
                    invalid_files.append((file_path, file_errors))
                else:
                    vector_files.append(file_path)
                    
            elif extension in cls.RASTER_EXTENSIONS:
                file_errors = cls.validate_raster_file(file_path)
                if file_errors:
                    invalid_files.append((file_path, file_errors))
                else:
                    raster_files.append(file_path)
            else:
                errors.append(f"Unsupported file type: {file_path}. Must be .shp, .gpkg, .tif, or .tiff")
        
        # Report invalid files
        for file_path, file_errors in invalid_files:
            for error in file_errors:
                errors.append(f"{file_path}: {error}")
        
        # Get all valid files
        all_valid_files = vector_files + raster_files
        
        # If we don't have at least 2 valid files, can't check CRS consistency
        if len(all_valid_files) < 2:
            errors.append("Need at least 2 valid spatial files to check CRS consistency")
            return errors
        
        # Check CRS consistency
        try:
            # Get CRS from each file
            file_crs_info = []
            
            # Process vector files
            if vector_files:
                try:
                    import geopandas as gpd
                    import warnings
                    
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        
                        for file_path in vector_files:
                            gdf = gpd.read_file(file_path)
                            if gdf.crs is None:
                                errors.append(f"Vector file has no CRS defined: {file_path}")
                            else:
                                # GeoPandas 1.1.1 compatible EPSG extraction
                                try:
                                    epsg_code = gdf.crs.to_epsg()
                                except (AttributeError, ValueError):
                                    # Fallback for older versions or invalid CRS
                                    epsg_code = None
                                
                                file_crs_info.append({
                                    'file': file_path,
                                    'crs': gdf.crs,
                                    'crs_string': str(gdf.crs),
                                    'epsg': epsg_code,
                                    'type': 'vector'
                                })
                                
                except ImportError:
                    errors.append("Cannot validate vector file CRS: geopandas library not available")
                except Exception as e:
                    errors.append(f"Error reading vector files: {str(e)}")
            
            # Process raster files
            if raster_files:
                try:
                    import rasterio
                    import warnings
                    
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        
                        for file_path in raster_files:
                            with rasterio.open(file_path) as src:
                                if src.crs is None:
                                    errors.append(f"Raster file has no CRS defined: {file_path}")
                                else:
                                    # Rasterio compatible EPSG extraction
                                    try:
                                        epsg_code = src.crs.to_epsg() if hasattr(src.crs, 'to_epsg') else None
                                    except (AttributeError, ValueError):
                                        epsg_code = None
                                    
                                    file_crs_info.append({
                                        'file': file_path,
                                        'crs': src.crs,
                                        'crs_string': str(src.crs),
                                        'epsg': epsg_code,
                                        'type': 'raster'
                                    })
                                    
                except ImportError:
                    errors.append("Cannot validate raster file CRS: rasterio library not available")
                except Exception as e:
                    errors.append(f"Error reading raster files: {str(e)}")
            
            # Compare CRS across all files
            if len(file_crs_info) >= 2:
                reference_info = file_crs_info[0]
                reference_crs = reference_info['crs']
                reference_file = reference_info['file']
                
                for i, current_info in enumerate(file_crs_info[1:], 1):
                    current_crs = current_info['crs']
                    current_file = current_info['file']
                    
                    # Check if CRS are the same
                    crs_match = False
                    
                    # Try EPSG code comparison first (most reliable)
                    ref_epsg = reference_info['epsg']
                    curr_epsg = current_info['epsg']
                    
                    if ref_epsg and curr_epsg:
                        if ref_epsg == curr_epsg:
                            crs_match = True
                        else:
                            errors.append(f"EPSG code mismatch: {reference_file} uses EPSG:{ref_epsg}, "
                                        f"{current_file} uses EPSG:{curr_epsg}")
                            continue
                    
                    # If no EPSG codes available, compare CRS objects directly
                    if not crs_match and not (ref_epsg and curr_epsg):
                        try:
                            # For rasterio and geopandas CRS objects, try direct comparison
                            if reference_crs == current_crs:
                                crs_match = True
                            else:
                                # Compare string representations as fallback
                                if reference_info['crs_string'] == current_info['crs_string']:
                                    crs_match = True
                                else:
                                    errors.append(f"CRS mismatch: {reference_file} uses '{reference_info['crs_string']}', "
                                                f"{current_file} uses '{current_info['crs_string']}'")
                        except Exception:
                            errors.append(f"Cannot compare CRS between {reference_file} and {current_file}")
            
        except Exception as e:
            errors.append(f"Error checking CRS consistency: {str(e)}")
        
        return errors

    @classmethod
    def validate_file_by_extension(cls, file_path: str, require_projected: bool = False) -> List[str]:
        """
        Automatically validates a file based on its extension using the appropriate method.
        
        Args:
            file_path (str): Path to the file to validate
            require_projected (bool): If True, validates that CRS is projected, not geographical
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        if not file_path:
            return ["File path cannot be empty or None"]
        
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension in cls.VECTOR_EXTENSIONS:
            return cls.validate_vector_file(file_path, require_projected)
        elif extension in cls.RASTER_EXTENSIONS:
            return cls.validate_raster_file(file_path, require_projected)
        else:
            return [f"Unsupported file extension '{extension}'. Must be one of: {', '.join(cls.ALL_EXTENSIONS)}"]

    @classmethod
    def validate_multiple_files(cls, file_paths: List[str], require_projected: bool = False, 
                            check_alignment: bool = False, check_crs_consistency: bool = False) -> List[str]:
        """
        Comprehensive validation of multiple files with optional additional checks.
        
        Args:
            file_paths (List[str]): List of file paths to validate
            require_projected (bool): If True, validates that CRS is projected for all files
            check_alignment (bool): If True, checks raster alignment (only for raster files)
            check_crs_consistency (bool): If True, checks CRS consistency across all files
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        all_errors = []
        
        if not file_paths:
            return ["File paths list cannot be empty or None"]
        
        # Validate each file individually
        valid_files = []
        raster_files = []
        
        for file_path in file_paths:
            file_errors = cls.validate_file_by_extension(file_path, require_projected)
            if file_errors:
                # Add file-specific errors
                for error in file_errors:
                    all_errors.append(f"{file_path}: {error}")
            else:
                # File is valid, add to valid files list
                valid_files.append(file_path)
                
                # Collect raster files for alignment check
                path = Path(file_path)
                if path.suffix.lower() in cls.RASTER_EXTENSIONS:
                    raster_files.append(file_path)
        
        # Only proceed with additional checks if we have valid files and no errors so far
        if not all_errors:
            # Check raster alignment if requested and we have enough valid raster files
            if check_alignment and len(raster_files) >= 2:
                alignment_errors = cls.validate_raster_alignment(raster_files)
                all_errors.extend(alignment_errors)
            elif check_alignment and len(raster_files) < 2:
                all_errors.append("Alignment check requested but fewer than 2 raster files provided")
            
            # Check CRS consistency if requested and we have enough valid files
            if check_crs_consistency and len(valid_files) >= 2:
                crs_errors = cls.validate_crs_consistency(valid_files)
                all_errors.extend(crs_errors)
            elif check_crs_consistency and len(valid_files) < 2:
                all_errors.append("CRS consistency check requested but fewer than 2 valid files provided")
        
        return all_errors


# ------------------------------------------------------------------------


class _VectorColumnValidator:
    """
    Validator for vector file (shapefile/geopackage) column validation.

    Provides validation for:
    - Column existence
    - Column data types (integer, float, string)
    - Multiple column validation
    """

    @classmethod
    def validate_columns(cls, file_path: str,
                        required_columns: Optional[List[str]] = None,
                        column_types: Optional[Dict[str, str]] = None) -> List[str]:
        """
        Validate vector file columns and their data types.

        Args:
            file_path (str): Path to vector file (.shp or .gpkg)
            required_columns (List[str], optional): List of column names that must exist
            column_types (Dict[str, str], optional): Dict mapping column names to expected types.
                Valid types: 'integer', 'float', 'string'

        Returns:
            List[str]: List of error messages. Empty list if no errors found.

        Example:
            >>> errors = _VectorColumnValidator.validate_columns(
            ...     file_path="regions.shp",
            ...     required_columns=["region_id", "name"],
            ...     column_types={"region_id": "integer", "name": "string"}
            ... )
        """
        errors = []

        # Validate file path
        if not file_path:
            errors.append("File path cannot be empty or None")
            return errors

        # Read vector file
        try:
            import geopandas as gpd
            import numpy as np

            gdf = gpd.read_file(file_path)
        except Exception as e:
            errors.append(f"Cannot read vector file: {str(e)}")
            return errors

        # Validate required columns exist
        if required_columns:
            for column in required_columns:
                if column and column not in gdf.columns:
                    available_columns = ", ".join(gdf.columns.tolist())
                    errors.append(
                        f"Column '{column}' does not exist. "
                        f"Available columns: {available_columns}"
                    )

        # Validate column data types
        if column_types and not errors:  # Only if column existence passed
            for column, expected_type in column_types.items():
                if column and column in gdf.columns:
                    actual_dtype = gdf[column].dtype

                    if expected_type == 'integer':
                        if not np.issubdtype(actual_dtype, np.integer):
                            errors.append(
                                f"Column '{column}' has type '{actual_dtype}' "
                                f"but integer type required"
                            )
                    elif expected_type == 'float':
                        if not np.issubdtype(actual_dtype, np.floating):
                            errors.append(
                                f"Column '{column}' has type '{actual_dtype}' "
                                f"but float type required"
                            )
                    elif expected_type == 'string':
                        if actual_dtype != 'object':
                            errors.append(
                                f"Column '{column}' has type '{actual_dtype}' "
                                f"but string type required"
                            )

        return errors

    @classmethod
    def validate_column_exists(cls, file_path: str, column_name: str) -> List[str]:
        """
        Validate that a single column exists in a vector file.

        Args:
            file_path (str): Path to vector file
            column_name (str): Column name to check

        Returns:
            List[str]: List of error messages. Empty if column exists.
        """
        return cls.validate_columns(file_path, required_columns=[column_name])

    @classmethod
    def validate_column_type(cls, file_path: str, column_name: str,
                            expected_type: str) -> List[str]:
        """
        Validate that a column has the expected data type.

        Args:
            file_path (str): Path to vector file
            column_name (str): Column name to check
            expected_type (str): Expected type ('integer', 'float', or 'string')

        Returns:
            List[str]: List of error messages. Empty if type matches.
        """
        return cls.validate_columns(
            file_path,
            required_columns=[column_name],
            column_types={column_name: expected_type}
        )


# ------------------------------------------------------------------------


class _ClassDefValidator:
    """
    A validator for class definition files used by _ClassDef.
    Provides optional column validation for Excel files containing class definitions.
    """
    
    @classmethod
    def validate_class_definition_file(cls, class_def_file: str, column_id: str = None, 
                                     column_label: str = None, column_label_reclass: str = None,
                                     column_category: str = None, columns_RGB: Union[List[str], Tuple[str, str, str]] = None,
                                     column_confusion: str = None, column_temporal_filter: str = None,
                                     column_from_class: str = None, column_to_class: str = None,
                                     column_transitions: str = None) -> List[str]:
        """
        Validates a class definition Excel file and its column structure.
        All column validations are optional - only specified columns are validated.
        
        Args:
            class_def_file (str): Path to the Excel class definition file
            column_id (str, optional): Name of the column containing numeric IDs
            column_label (str, optional): Name of the column containing labels
            column_label_reclass (str, optional): Name of the column containing reclassification labels
            column_category (str, optional): Name of the column defining category groups
            columns_RGB (list/tuple, optional): List/tuple of 3 RGB column names
            column_confusion (str, optional): Name of the column for confusion matrix inclusion
            column_temporal_filter (str, optional): Name of the column for temporal filter inclusion
            column_from_class (str, optional): Name of the column for transition 'from' class
            column_to_class (str, optional): Name of the column for transition 'to' class
            column_transitions (str, optional): Name of the column for transition type
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        errors = []
        
        # Basic file validation
        if not class_def_file:
            errors.append("Class definition file path cannot be empty or None")
            return errors
            
        file_path = Path(class_def_file)
        if not file_path.exists():
            errors.append(f"Class definition file not found: {class_def_file}")
            return errors
            
        file_ext = file_path.suffix.lower()
        if file_ext not in ('.xlsx', '.xls'):
            errors.append(f"Unsupported file format '{file_ext}'. Only .xlsx and .xls are supported.")
            return errors
        
        # Try to read the Excel file
        try:
            import pandas as pd
            import numpy as np
            
            tp = pd.read_excel(class_def_file, sheet_name=0, keep_default_na=False)
            tp_tr = None
            
            # Check if transitions sheet is needed and exists
            if all(col is not None for col in [column_from_class, column_to_class, column_transitions]):
                try:
                    tp_tr = pd.read_excel(class_def_file, sheet_name=1, keep_default_na=False)
                except Exception:
                    errors.append("Transitions data requested but second sheet not found or readable")
                    return errors
                    
        except Exception as e:
            errors.append(f"Failed to read Excel file: {e}")
            return errors
        
        # Clean and validate main DataFrame
        tp = tp.mask(tp == '', np.nan)
        tp = tp.dropna(axis=0, how="any")
        tp = tp.dropna(axis=1, how="all")
        
        if tp.empty:
            errors.append("Class definition file contains no valid data after cleaning")
            return errors
        
        # Validate optional columns exist in main sheet
        if column_id is not None:
            validation_errors = cls._validate_column_exists(tp, column_id, 'column_id')
            errors.extend(validation_errors)
            
        if column_label is not None:
            validation_errors = cls._validate_column_exists(tp, column_label, 'column_label')
            errors.extend(validation_errors)
            
        if column_label_reclass is not None:
            validation_errors = cls._validate_column_exists(tp, column_label_reclass, 'column_label_reclass')
            errors.extend(validation_errors)
            
        if column_category is not None:
            validation_errors = cls._validate_column_exists(tp, column_category, 'column_category')
            errors.extend(validation_errors)
            
        if column_confusion is not None:
            validation_errors = cls._validate_column_exists(tp, column_confusion, 'column_confusion')
            errors.extend(validation_errors)
            
        if column_temporal_filter is not None:
            validation_errors = cls._validate_column_exists(tp, column_temporal_filter, 'column_temporal_filter')
            errors.extend(validation_errors)
        
        # Validate RGB columns
        if columns_RGB is not None:
            if not isinstance(columns_RGB, (tuple, list)) or len(columns_RGB) != 3:
                errors.append("columns_RGB must be a tuple or list of exactly 3 column names: (red, green, blue)")
            else:
                for i, rgb_col in enumerate(columns_RGB):
                    color_names = ['red', 'green', 'blue']
                    validation_errors = cls._validate_column_exists(tp, rgb_col, f'RGB {color_names[i]} column')
                    errors.extend(validation_errors)
                    
                    # Validate RGB values are in correct range (0-255) with row reporting
                    if rgb_col in tp.columns:
                        try:
                            rgb_values = pd.to_numeric(tp[rgb_col], errors='coerce')
                            
                            # Check for non-numeric values
                            if rgb_values.isna().any():
                                non_numeric_rows = tp[rgb_values.isna()].index + 2
                                errors.append(f"RGB column '{rgb_col}' contains non-numeric values (rows: {list(non_numeric_rows)})")
                            
                            # Check for out-of-range values
                            out_of_range_mask = (rgb_values < 0) | (rgb_values > 255)
                            if out_of_range_mask.any():
                                out_of_range_rows = tp[out_of_range_mask].index + 2
                                out_of_range_values = rgb_values[out_of_range_mask].unique()
                                errors.append(f"RGB column '{rgb_col}' contains values outside range 0-255: {out_of_range_values.tolist()} (rows: {list(out_of_range_rows)})")
                        except Exception as e:
                            errors.append(f"Error validating RGB column '{rgb_col}': {e}")
        
        # Validate transition columns if transitions DataFrame exists
        if tp_tr is not None:
            if column_from_class is not None:
                validation_errors = cls._validate_column_exists(tp_tr, column_from_class, 'column_from_class')
                errors.extend(validation_errors)
                
            if column_to_class is not None:
                validation_errors = cls._validate_column_exists(tp_tr, column_to_class, 'column_to_class')
                errors.extend(validation_errors)
                
            if column_transitions is not None:
                validation_errors = cls._validate_column_exists(tp_tr, column_transitions, 'column_transitions')
                errors.extend(validation_errors)
        
        # Validate data consistency if key columns are provided
        if column_id is not None and column_id in tp.columns:
            # Check for valid integer IDs with row-level reporting
            try:
                id_values = pd.to_numeric(tp[column_id], errors='coerce')
                
                # Check for non-numeric values
                if id_values.isna().any():
                    non_numeric_rows = tp[id_values.isna()].index + 2  # +2 for Excel row numbers
                    errors.append(f"ID column '{column_id}' contains non-numeric values (rows: {list(non_numeric_rows)})")
                else:
                    # Check if values are integers
                    non_integer_mask = ~id_values.apply(lambda x: x == int(x) if pd.notna(x) else True)
                    if non_integer_mask.any():
                        non_integer_rows = tp[non_integer_mask].index + 2
                        errors.append(f"ID column '{column_id}' must contain only integer values (rows: {list(non_integer_rows)})")
                    
                    # Check for negative values with row numbers
                    negative_mask = (id_values < 0)
                    if negative_mask.any():
                        negative_rows = tp[negative_mask].index + 2
                        negative_values = id_values[negative_mask].unique()
                        errors.append(f"ID column '{column_id}' contains negative values: {negative_values.tolist()} (rows: {list(negative_rows)}). Values must be non-negative integers")
                    
                    # Check for duplicate IDs with row numbers
                    duplicate_mask = id_values.duplicated(keep=False)
                    if duplicate_mask.any():
                        duplicate_rows = tp[duplicate_mask].index + 2
                        duplicates = id_values[duplicate_mask].unique()
                        errors.append(f"ID column '{column_id}' contains duplicate values: {duplicates.tolist()} (rows: {list(duplicate_rows)})")
            except Exception as e:
                errors.append(f"Error validating ID column '{column_id}': {e}")
        
        # Validate confusion column values with row reporting
        if column_confusion is not None and column_confusion in tp.columns:
            valid_confusion_values = {'yes', 'no'}
            tp_confusion_lower = tp[column_confusion].astype(str).str.lower()
            invalid_mask = ~tp_confusion_lower.isin(valid_confusion_values)
            
            if invalid_mask.any():
                invalid_rows = tp[invalid_mask].index + 2
                invalid_values = set(tp[invalid_mask][column_confusion].astype(str).unique())
                errors.append(f"Confusion column '{column_confusion}' contains invalid values: {invalid_values} (rows: {list(invalid_rows)}). Must be 'yes' or 'no'")
        
        # Validate temporal filter column values with row reporting
        if column_temporal_filter is not None and column_temporal_filter in tp.columns:
            valid_temporal_values = {'yes', 'no'}
            tp_temporal_lower = tp[column_temporal_filter].astype(str).str.lower()
            invalid_mask = ~tp_temporal_lower.isin(valid_temporal_values)
            
            if invalid_mask.any():
                invalid_rows = tp[invalid_mask].index + 2
                invalid_values = set(tp[invalid_mask][column_temporal_filter].astype(str).unique())
                errors.append(f"Temporal filter column '{column_temporal_filter}' contains invalid values: {invalid_values} (rows: {list(invalid_rows)}). Must be 'yes' or 'no'")
        
        # Advanced data consistency validations
        consistency_errors = cls._validate_data_consistency(tp, tp_tr, column_id, column_label, 
                                                          column_label_reclass, column_from_class, 
                                                          column_to_class, column_transitions)
        errors.extend(consistency_errors)
        
        return errors
    
    @classmethod
    def _validate_column_exists(cls, df, column: str, column_desc: str) -> List[str]:
        """
        Validate that a column exists in the DataFrame.
        
        Args:
            df: pandas DataFrame to check
            column (str): Column name to validate
            column_desc (str): Description of the column for error messages
            
        Returns:
            List[str]: List of error messages. Empty list if column exists.
        """
        errors = []
        
        if column is not None and column not in df.columns:
            available_columns = list(df.columns)
            errors.append(f"Column '{column}' ({column_desc}) not found in class definition file. Available columns: {available_columns}")
        
        return errors
    
    @classmethod
    def _validate_data_consistency(cls, tp, tp_tr, column_id: str, column_label: str,
                                 column_label_reclass: str, column_from_class: str,
                                 column_to_class: str, column_transitions: str) -> List[str]:
        """
        Validate data consistency across columns with row-level error reporting.
        
        Args:
            tp: Main DataFrame
            tp_tr: Transitions DataFrame (can be None)
            column_*: Column names (can be None if not specified)
            
        Returns:
            List[str]: List of error messages with row numbers when applicable
        """
        errors = []
        
        try:
            import pandas as pd
            import numpy as np
            
            # 1. Label-ID consistency validation
            if column_id is not None and column_label is not None and \
               column_id in tp.columns and column_label in tp.columns:
                
                # Check for labels that map to multiple different IDs
                label_id_mapping = tp.groupby(column_label)[column_id].apply(lambda x: set(x)).to_dict()
                inconsistent_labels = []
                
                for label, id_set in label_id_mapping.items():
                    if len(id_set) > 1:
                        # Find row numbers for this inconsistent label
                        problem_rows = tp[tp[column_label] == label].index + 2  # +2 for Excel row numbers (header + 0-based)
                        inconsistent_labels.append(f"'{label}' maps to multiple IDs {sorted(id_set)} (rows: {list(problem_rows)})")
                
                if inconsistent_labels:
                    errors.append(f"Label-ID consistency errors - each label must map to only one ID:")
                    for error in inconsistent_labels:
                        errors.append(f"  - {error}")
            
            # 2. Reclassification logic validation  
            if column_label is not None and column_label_reclass is not None and \
               column_label in tp.columns and column_label_reclass in tp.columns:
                
                original_labels = set(tp[column_label].astype(str))
                reclass_labels = set(tp[column_label_reclass].astype(str))
                
                # Check if all reclassification labels exist in original labels
                missing_labels = reclass_labels - original_labels
                if missing_labels:
                    # Find rows with problematic reclassification labels
                    problem_details = []
                    for missing_label in missing_labels:
                        problem_rows = tp[tp[column_label_reclass].astype(str) == missing_label].index + 2
                        problem_details.append(f"'{missing_label}' (rows: {list(problem_rows)})")
                    
                    errors.append(f"Reclassification validation errors - these reclassification labels don't exist in original labels:")
                    for detail in problem_details:
                        errors.append(f"  - {detail}")
            
            # 3. Transition consistency validation
            if tp_tr is not None and column_label is not None and column_label in tp.columns and \
               all(col is not None and col in tp_tr.columns for col in [column_from_class, column_to_class]):
                
                main_labels = set(tp[column_label].astype(str))
                from_labels = set(tp_tr[column_from_class].astype(str))
                to_labels = set(tp_tr[column_to_class].astype(str))
                
                # Check from_class labels
                missing_from_labels = from_labels - main_labels
                if missing_from_labels:
                    problem_details = []
                    for missing_label in missing_from_labels:
                        problem_rows = tp_tr[tp_tr[column_from_class].astype(str) == missing_label].index + 2
                        problem_details.append(f"'{missing_label}' (transition sheet rows: {list(problem_rows)})")
                    
                    errors.append(f"Transition 'from_class' validation errors - these labels don't exist in main sheet:")
                    for detail in problem_details:
                        errors.append(f"  - {detail}")
                
                # Check to_class labels  
                missing_to_labels = to_labels - main_labels
                if missing_to_labels:
                    problem_details = []
                    for missing_label in missing_to_labels:
                        problem_rows = tp_tr[tp_tr[column_to_class].astype(str) == missing_label].index + 2
                        problem_details.append(f"'{missing_label}' (transition sheet rows: {list(problem_rows)})")
                    
                    errors.append(f"Transition 'to_class' validation errors - these labels don't exist in main sheet:")
                    for detail in problem_details:
                        errors.append(f"  - {detail}")
        
        except Exception as e:
            errors.append(f"Error during data consistency validation: {str(e)}")
        
        return errors
    
    @classmethod
    def validate_columns_only(cls, class_def_file: str, columns_to_check: Dict[str, str]) -> List[str]:
        """
        Validate only specific columns exist in a class definition file.
        
        Args:
            class_def_file (str): Path to the Excel class definition file
            columns_to_check (Dict[str, str]): Dictionary mapping column names to descriptions
            
        Returns:
            List[str]: List of error messages. Empty list if all specified columns exist.
        """
        errors = []
        
        # Basic file validation
        if not class_def_file:
            errors.append("Class definition file path cannot be empty or None")
            return errors
            
        file_path = Path(class_def_file)
        if not file_path.exists():
            errors.append(f"Class definition file not found: {class_def_file}")
            return errors
        
        # Try to read the Excel file
        try:
            import pandas as pd
            tp = pd.read_excel(class_def_file, sheet_name=0, keep_default_na=False)
        except Exception as e:
            errors.append(f"Failed to read Excel file: {e}")
            return errors
        
        # Validate each specified column
        for column_name, column_desc in columns_to_check.items():
            if column_name is not None:
                validation_errors = cls._validate_column_exists(tp, column_name, column_desc)
                errors.extend(validation_errors)
        
        return errors


# ------------------------------------------------------------------------


class _GeometryValidator:
    """
    A comprehensive validator for spatial file geometries.
    Provides validation for geometry validity, empty geometries, spatial overlaps,
    and spatial extent checking for both single and multiple files.
    """
    
    # Supported file extensions
    VECTOR_EXTENSIONS = {'.shp', '.gpkg'}
    RASTER_EXTENSIONS = {'.tif', '.tiff'}
    ALL_EXTENSIONS = VECTOR_EXTENSIONS | RASTER_EXTENSIONS
    
    @classmethod
    def validate_geometries(cls, file_paths: Union[str, List[str]], 
                           check_empty: bool = True, 
                           check_validity: bool = True, 
                           check_overlap: bool = False) -> List[str]:
        """
        Validates geometries in spatial files for common issues.
        
        Args:
            file_paths (str or List[str]): Single file path or list of file paths to validate
            check_empty (bool): If True, checks for empty geometries
            check_validity (bool): If True, checks for invalid geometries (self-intersections, etc.)
            check_overlap (bool): If True, checks for spatial overlap between input files
            
        Returns:
            List[str]: List of error messages. Empty list if no geometry issues found.
        """
        errors = []
        
        # Handle single file input
        if isinstance(file_paths, str):
            file_paths = [file_paths]
        
        if not file_paths:
            errors.append("No file paths provided for geometry validation")
            return errors
        
        # First validate each file individually
        valid_files = []
        for file_path in file_paths:
            # Check if it's a vector file
            path = Path(file_path)
            if path.suffix.lower() not in cls.VECTOR_EXTENSIONS:
                errors.append(f"Geometry validation only applies to vector files (.shp, .gpkg): {file_path}")
                continue
                
            # Basic file validation
            file_errors = cls._validate_vector_file_basic(file_path)
            if file_errors:
                for error in file_errors:
                    errors.append(f"{file_path}: {error}")
                continue
            
            valid_files.append(file_path)
        
        # If we don't have valid files, can't check geometries
        if not valid_files:
            errors.append("No valid vector files found for geometry validation")
            return errors
        
        # Check geometries in each valid file
        try:
            import geopandas as gpd
            from shapely.validation import explain_validity
            
            file_gdfs = {}  # Store geodataframes for overlap checking
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                for file_path in valid_files:
                    try:
                        gdf = gpd.read_file(file_path)
                        
                        # Check if file has any features
                        if len(gdf) == 0:
                            errors.append(f"File contains no features: {file_path}")
                            continue
                        
                        # Store for overlap checking
                        file_gdfs[file_path] = gdf
                        
                        # Check for empty geometries
                        if check_empty:
                            empty_count = gdf.geometry.isna().sum() + gdf.geometry.is_empty.sum()
                            if empty_count > 0:
                                errors.append(f"File contains {empty_count} empty or null geometries: {file_path}")
                        
                        # Check for invalid geometries
                        if check_validity:
                            invalid_geometries = []
                            for idx, geom in enumerate(gdf.geometry):
                                if geom is not None and not geom.is_empty:
                                    if not geom.is_valid:
                                        try:
                                            reason = explain_validity(geom)
                                            invalid_geometries.append(f"Feature {idx}: {reason}")
                                        except:
                                            invalid_geometries.append(f"Feature {idx}: Invalid geometry")
                            
                            if invalid_geometries:
                                errors.append(f"File contains {len(invalid_geometries)} invalid geometries in {file_path}:")
                                # Limit to first 5 errors to avoid overwhelming output
                                for error in invalid_geometries[:5]:
                                    errors.append(f"  - {error}")
                                if len(invalid_geometries) > 5:
                                    errors.append(f"  - ... and {len(invalid_geometries) - 5} more invalid geometries")
                        
                        # Check geometry types consistency
                        geom_types = gdf.geometry.geom_type.unique()
                        geom_types = [gt for gt in geom_types if gt is not None]  # Remove None values
                        
                        if len(geom_types) > 1:
                            errors.append(f"File contains mixed geometry types: {geom_types} in {file_path}")
                        
                        # Check for required geometry types (assuming polygons for this use case)
                        if geom_types and not any(gt in ['Polygon', 'MultiPolygon'] for gt in geom_types):
                            errors.append(f"File should contain Polygon or MultiPolygon geometries, found: {geom_types} in {file_path}")
                        
                    except Exception as e:
                        errors.append(f"Error reading geometries from {file_path}: {str(e)}")
            
            # Check for spatial overlap between files
            if check_overlap and len(file_gdfs) >= 2:
                overlap_errors = cls._check_geometry_overlaps(file_gdfs)
                errors.extend(overlap_errors)
                        
        except ImportError:
            errors.append("Cannot validate geometries: geopandas library not available")
        except Exception as e:
            errors.append(f"Error during geometry validation: {str(e)}")
        
        return errors

    @classmethod  
    def validate_spatial_extent(cls, file_paths: Union[str, List[str]]) -> List[str]:
        """
        Validates that spatial files have overlapping geographic extents.
        
        Args:
            file_paths (str or List[str]): Single file path or list of file paths
            
        Returns:
            List[str]: List of error messages. Empty list if extents overlap appropriately.
        """
        errors = []
        
        # Handle single file input  
        if isinstance(file_paths, str):
            file_paths = [file_paths]
            
        if len(file_paths) < 2:
            return errors  # Need at least 2 files to check overlap
        
        try:
            import geopandas as gpd
            
            bounds_info = []
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                for file_path in file_paths:
                    try:
                        # Check if it's a vector or raster file
                        path = Path(file_path)
                        extension = path.suffix.lower()
                        
                        if extension in cls.VECTOR_EXTENSIONS:
                            gdf = gpd.read_file(file_path)
                            if len(gdf) > 0:
                                bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
                                crs = gdf.crs
                            else:
                                errors.append(f"Vector file contains no features: {file_path}")
                                continue
                                
                        elif extension in cls.RASTER_EXTENSIONS:
                            import rasterio
                            with rasterio.open(file_path) as src:
                                bounds = src.bounds
                                crs = src.crs
                        else:
                            continue  # Skip unsupported file types
                        
                        bounds_info.append({
                            'file': file_path,
                            'bounds': bounds,
                            'crs': crs
                        })
                        
                    except Exception as e:
                        errors.append(f"Error reading spatial extent from {file_path}: {str(e)}")
            
            # Check for extent overlap
            if len(bounds_info) >= 2:
                extent_errors = cls._check_extent_overlaps(bounds_info)
                errors.extend(extent_errors)
                        
        except ImportError:
            errors.append("Cannot validate spatial extents: required libraries not available")
        except Exception as e:
            errors.append(f"Error during spatial extent validation: {str(e)}")
        
        return errors
    
    @classmethod
    def validate_comprehensive(cls, file_paths: Union[str, List[str]], 
                            check_empty: bool = True,
                            check_validity: bool = True, 
                            check_geometry_overlap: bool = False,
                            check_extent_overlap: bool = True) -> List[str]:
        """
        Comprehensive validation combining geometry and spatial extent checks.
        Note: Geometry validation only applies to vector files (.shp, .gpkg).
        Spatial extent validation applies to both vector and raster files.
        
        Args:
            file_paths (str or List[str]): Single file path or list of file paths
            check_empty (bool): If True, checks for empty geometries (vector files only)
            check_validity (bool): If True, checks for invalid geometries (vector files only)
            check_geometry_overlap (bool): If True, checks for spatial overlap between geometries (vector files only)
            check_extent_overlap (bool): If True, checks for spatial extent overlap (all files)
            
        Returns:
            List[str]: List of error messages. Empty list if no issues found.
        """
        all_errors = []
        
        # Handle single file input
        if isinstance(file_paths, str):
            file_paths = [file_paths]
        
        # Separate vector and raster files
        vector_files = []
        all_files = []
        
        for file_path in file_paths:
            path = Path(file_path)
            extension = path.suffix.lower()
            all_files.append(file_path)
            
            if extension in cls.VECTOR_EXTENSIONS:
                vector_files.append(file_path)
        
        # Run geometry validation only on vector files
        if vector_files:
            geometry_errors = cls.validate_geometries(
                vector_files, 
                check_empty=check_empty,
                check_validity=check_validity, 
                check_overlap=check_geometry_overlap
            )
            all_errors.extend(geometry_errors)
        
        # Run spatial extent validation on all files (if requested)
        if check_extent_overlap and len(all_files) >= 2:
            extent_errors = cls.validate_spatial_extent(all_files)
            all_errors.extend(extent_errors)
        
        return all_errors
    
    @classmethod
    def _calculate_area_hectares(cls, geometry, crs) -> float:
        """
        Calculate area in hectares, handling different CRS units.
        
        Args:
            geometry: Shapely geometry object
            crs: Coordinate Reference System from geopandas/rasterio
            
        Returns:
            float: Area in hectares
        """
        try:
            if crs is None:
                # No CRS information, assume meters and warn
                return geometry.area / 10000
                
            # Check if CRS is geographic (lat/lon)
            if crs.is_geographic:
                try:
                    # For geographic CRS, use geodesic area calculation
                    import pyproj
                    geod = pyproj.Geod(ellps='WGS84')
                    area_m2 = abs(geod.geometry_area_perimeter(geometry)[0])
                    return area_m2 / 10000
                except ImportError:
                    # Fallback: approximate using simple area (not accurate for large areas)
                    # Convert degrees to approximate meters (very rough)
                    # This is not accurate but better than nothing
                    return (geometry.area * 111320 * 111320) / 10000  # Rough conversion
                except Exception:
                    # If geodesic calculation fails, use fallback
                    return geometry.area / 10000
            else:
                # For projected CRS, check units
                try:
                    # Get unit information from CRS
                    unit_name = crs.axis_info[0].unit_name.lower() if crs.axis_info else 'unknown'
                    
                    if unit_name in ['metre', 'meter', 'm']:
                        area_m2 = geometry.area
                    elif unit_name in ['foot', 'ft', 'feet']:
                        # Convert square feet to square meters
                        area_m2 = geometry.area * 0.092903
                    elif unit_name in ['kilometre', 'kilometer', 'km']:
                        # Convert square kilometers to square meters
                        area_m2 = geometry.area * 1000000
                    else:
                        # Unknown units, assume meters (most common for projected CRS)
                        area_m2 = geometry.area
                        
                    return area_m2 / 10000  # Convert to hectares
                    
                except (AttributeError, IndexError):
                    # If we can't get unit info, assume meters
                    return geometry.area / 10000
                    
        except Exception:
            # Ultimate fallback - assume meters
            return geometry.area / 10000 if hasattr(geometry, 'area') else 0.0
    
    @classmethod
    def _validate_vector_file_basic(cls, file_path: str) -> List[str]:
        """Basic file validation for vector files."""
        errors = []
        
        if not file_path:
            errors.append("File path cannot be empty or None")
            return errors
        
        path = Path(file_path)
        
        if not path.exists():
            errors.append(f"File does not exist: {file_path}")
        elif not path.is_file():
            errors.append(f"Path is not a file: {file_path}")
        
        # Check file extension
        file_extension = path.suffix.lower()
        if file_extension not in cls.VECTOR_EXTENSIONS:
            errors.append(f"Invalid file extension '{file_extension}'. Must be .shp or .gpkg")
        
        # Check if file can be read
        if path.exists() and path.is_file():
            try:
                with open(path, 'rb') as f:
                    f.read(1)
            except PermissionError:
                errors.append(f"File cannot be read: Permission denied for {file_path}")
            except IOError as e:
                errors.append(f"File cannot be read: {str(e)}")
            except Exception as e:
                errors.append(f"Unexpected error reading file: {str(e)}")
        
        return errors
    
    @classmethod
    def _check_geometry_overlaps(cls, file_gdfs: Dict) -> List[str]:
        """Check for spatial overlap between geometries in different files."""
        errors = []
        
        try:
            file_list = list(file_gdfs.keys())
            for i in range(len(file_list)):
                for j in range(i + 1, len(file_list)):
                    file1, file2 = file_list[i], file_list[j]
                    gdf1, gdf2 = file_gdfs[file1], file_gdfs[file2]
                    
                    # Ensure same CRS for overlap check
                    if gdf1.crs != gdf2.crs:
                        try:
                            gdf2_reprojected = gdf2.to_crs(gdf1.crs)
                        except (ValueError, RuntimeError, Exception) as e:
                            errors.append(f"Cannot reproject for overlap check between {file1} and {file2}: {str(e)}")
                            continue
                    else:
                        gdf2_reprojected = gdf2
                    
                    # Check for overlap
                    try:
                        # Create union of all geometries in each file
                        union1 = gdf1.geometry.unary_union
                        union2 = gdf2_reprojected.geometry.unary_union
                        
                        if union1.intersects(union2):
                            # Calculate overlap area using CRS-aware method
                            overlap = union1.intersection(union2)
                            if hasattr(overlap, 'area') and overlap.area > 0:
                                # Use CRS-aware area calculation
                                overlap_area_ha = cls._calculate_area_hectares(overlap, gdf1.crs)
                                errors.append(f"Spatial overlap detected between {file1} and {file2}: "
                                            f"{overlap_area_ha:.2f} hectares")
                    except Exception as e:
                        errors.append(f"Error checking overlap between {file1} and {file2}: {str(e)}")
                        
        except Exception as e:
            errors.append(f"Error during overlap analysis: {str(e)}")
        
        return errors
    
    @classmethod
    def _check_extent_overlaps(cls, bounds_info: List[Dict]) -> List[str]:
        """Check for spatial extent overlap between files."""
        errors = []
        
        reference = bounds_info[0]
        ref_bounds = reference['bounds']
        ref_crs = reference['crs']
        
        for other in bounds_info[1:]:
            other_bounds = other['bounds']
            other_crs = other['crs']
            
            # Check if CRS match
            if ref_crs != other_crs:
                errors.append(f"Cannot compare extents: CRS mismatch between {reference['file']} "
                            f"({ref_crs}) and {other['file']} ({other_crs})")
                continue
            
            # Check for overlap: files overlap if not completely separate
            # bounds = [minx, miny, maxx, maxy]
            ref_minx, ref_miny, ref_maxx, ref_maxy = ref_bounds
            other_minx, other_miny, other_maxx, other_maxy = other_bounds
            
            # No overlap if one file is completely to the left, right, above, or below the other
            no_overlap = (ref_maxx < other_minx or  # ref is left of other
                         other_maxx < ref_minx or  # other is left of ref
                         ref_maxy < other_miny or  # ref is below other
                         other_maxy < ref_miny)    # other is below ref
            
            if no_overlap:
                errors.append(f"No spatial overlap between {reference['file']} and {other['file']}")
        
        return errors


# ------------------------------------------------------------------------


class _ColorTableValidator:
    """
    A validator for color table validation from dictionaries and TIF files.
    """
    
    @classmethod
    def validate_color_table_dict(cls, data_dict):
        """
        Validates color table dictionary structure and RGB values.
        Input form:
        {'1': ('1000', '200', '0'), '2': ('10', '20', '10')}
        
        Args:
            data_dict (dict): Dictionary with integer keys and RGB tuple values
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        errors = []
        color_names = ['Red', 'Green', 'Blue']
        
        for key, rgb_tuple in data_dict.items():
            # Validate key
            try:
                if int(key) < 0:
                    errors.append(f"Key '{key}': Must be non-negative")
            except (ValueError, TypeError):
                errors.append(f"Key '{key}': Must be a valid integer")
            
            # Validate tuple/list structure - accept both tuples and lists
            if not isinstance(rgb_tuple, (tuple, list)) or len(rgb_tuple) != 3:
                errors.append(f"Key '{key}': Value must be a 3-element tuple or list")
                continue
            
            # Validate RGB values
            for color_name, color_value in zip(color_names, rgb_tuple):
                try:
                    color_int = int(color_value)
                    if not (0 <= color_int <= 255):
                        errors.append(f"Key '{key}': {color_name} must be 0-255, got: {color_int}")
                except (ValueError, TypeError):
                    errors.append(f"Key '{key}': {color_name} '{color_value}' must be a valid integer")
        
        return errors
    
    @classmethod
    def validate_color_table_list_dict(cls, data):
        """
        Validate list of dictionaries in the form:
        [{'Value': '1', 'Red': '1000', 'Green': '200', 'Blue': '0'}, 
         {'Value': '2', 'Red': '10', 'Green': '20', 'Blue': '10'}]
        
        Args:
            data (list): List of dictionaries with 'Value', 'Red', 'Green', 'Blue' keys
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        errors = []
        
        if not isinstance(data, list):
            errors.append("Input must be a list of dictionaries")
            return errors
        
        if len(data) == 0:
            errors.append("Input list cannot be empty")
            return errors
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"Item {i}: Must be a dictionary")
                continue
            
            # Check for required keys
            required_keys = {'Value', 'Red', 'Green', 'Blue'}
            missing_keys = required_keys - set(item.keys())
            if missing_keys:
                errors.append(f"Item {i}: Missing required keys: {missing_keys}")
                continue
            
            # Validate Value (class ID)
            try:
                key = int(item['Value'])
                if key < 0:
                    errors.append(f"Item {i}: Value must be non-negative, got: {key}")
            except (ValueError, TypeError):
                errors.append(f"Item {i}: Value '{item['Value']}' must be a valid integer")
            
            # Validate RGB values
            for color in ['Red', 'Green', 'Blue']:
                try:
                    color_value = int(item[color])
                    if not (0 <= color_value <= 255):
                        errors.append(f"Item {i}: {color} must be 0-255, got: {color_value}")
                except (ValueError, TypeError):
                    errors.append(f"Item {i}: {color} '{item[color]}' must be a valid integer")
        
        return errors
    
    @classmethod
    def validate_color_table(cls, data):
        """
        Unified validation for color table data that accepts both formats:
        1) Dictionary format: {1: (255, 0, 0), 2: (0, 255, 0)}
        2) List of dictionaries format: [{'Value': '1', 'Red': '255', 'Green': '0', 'Blue': '0'}, ...]
        
        Automatically detects the input format and applies appropriate validation.
        
        Args:
            data (dict or list): Color table data in either format
            
        Returns:
            List[str]: List of error messages. Empty list if no errors found.
        """
        errors = []
        
        if data is None:
            errors.append("Color table data cannot be None")
            return errors
        
        # Detect input format and validate accordingly
        if isinstance(data, dict):
            # Dictionary format: {1: (255, 0, 0), 2: (0, 255, 0)}
            if len(data) == 0:
                errors.append("Color table dictionary cannot be empty")
            else:
                dict_errors = cls.validate_color_table_dict(data)
                errors.extend(dict_errors)
                
        elif isinstance(data, list):
            # List of dictionaries format: [{'Value': '1', 'Red': '255', 'Green': '0', 'Blue': '0'}, ...]
            if len(data) == 0:
                errors.append("Color table list cannot be empty")
            else:
                list_errors = cls.validate_color_table_list_dict(data)
                errors.extend(list_errors)
                
        else:
            errors.append(f"Color table data must be either a dictionary or a list of dictionaries, got: {type(data).__name__}")
        
        return errors
    
    @classmethod
    def validate_and_normalize_color_table(cls, data):
        """
        Validates color table data in either format and normalizes it to dictionary format.
        Combines validation and transformation into a single operation.
        
        Args:
            data (dict or list): Color table data in either format
            
        Returns:
            tuple: (errors: List[str], normalized_data: dict or None)
                - errors: List of validation error messages
                - normalized_data: Dictionary format {class_id: (r, g, b)} with integer keys/values, 
                  or None if validation failed
        """
        errors = []
        normalized_data = None
        
        # First validate the input
        validation_errors = cls.validate_color_table(data)
        if validation_errors:
            errors.extend(validation_errors)
            return errors, None
        
        try:
            # Transform to normalized dictionary format
            if isinstance(data, dict):
                # Already in dictionary format, just ensure integer conversion
                normalized_data = {int(k): tuple(map(int, v)) for k, v in data.items()}
                
            elif isinstance(data, list):
                # Transform from list format to dictionary format
                temp_dict = {item['Value']: (item['Red'], item['Green'], item['Blue']) for item in data}
                normalized_data = {int(k): tuple(map(int, v)) for k, v in temp_dict.items()}
            
        except (ValueError, TypeError, KeyError) as e:
            errors.append(f"Error normalizing color table data: {str(e)}")
            normalized_data = None
        except Exception as e:
            errors.append(f"Unexpected error during normalization: {str(e)}")
            normalized_data = None
        
        return errors, normalized_data
    
    @classmethod
    def validate_tif_color_table(cls, tif_file_path):
        """
        Validates if a TIF file has a color table.
        
        Args:
            tif_file_path (str): Path to the TIF file
            
        Returns:
            List[str]: List of error messages. Empty list if TIF has a valid color table.
        """
        errors = []
        
        if not tif_file_path:
            errors.append("TIF file path cannot be empty or None")
            return errors
        
        path = Path(tif_file_path)
        
        # Check file extension
        file_extension = path.suffix.lower()
        if file_extension not in {'.tif', '.tiff'}:
            errors.append(f"Invalid file extension '{file_extension}'. Must be .tif or .tiff")
            return errors
        
        try:
            import rasterio
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                with rasterio.open(tif_file_path) as src:
                    # Check if the TIF has a color table
                    colormap = src.colormap(1)  # Get colormap for band 1
                    
                    if not colormap:
                        errors.append(f"TIF file has no color table: {tif_file_path}")
                    else:
                        # Validate that the color table has entries
                        if len(colormap) == 0:
                            errors.append(f"TIF file has an empty color table: {tif_file_path}")
                        
                        # Optional: validate color table entries format
                        invalid_entries = []
                        for value, color in colormap.items():
                            if not isinstance(color, (tuple, list)) or len(color) < 3:
                                invalid_entries.append(value)
                            else:
                                # Check RGB values are in valid range
                                for i, component in enumerate(color[:3]):
                                    if not isinstance(component, int) or not (0 <= component <= 255):
                                        invalid_entries.append(value)
                                        break
                        
                        if invalid_entries:
                            errors.append(f"TIF file has invalid color table entries for values: {invalid_entries[:5]} "
                                        f"{'...' if len(invalid_entries) > 5 else ''} in {tif_file_path}")
                            
        except ImportError:
            errors.append("Cannot validate TIF color table: rasterio library not available")
        except Exception as e:
            errors.append(f"Error checking TIF color table: {str(e)}")

        return errors


# ------------------------------------------------------------------------


class _ClassParameterValidator:
    """
    Validator for class/pixel value parameters commonly used in raster analysis.

    Validates parameters that can be:
    - A single integer (e.g., target class value)
    - A list of integers (e.g., multiple class values)
    - None (optional parameter)

    Rejects floats, strings, booleans, and other non-integer types.
    """

    @classmethod
    def validate_class_parameter(cls, value, parameter_name: str,
                                 allow_none: bool = False,
                                 allow_empty_list: bool = False) -> List[str]:
        """
        Validates a class/pixel value parameter.

        Args:
            value: The value to validate (can be int, list of ints, or None)
            parameter_name (str): Name of the parameter (for error messages)
            allow_none (bool): If True, None values are accepted. Default False.
            allow_empty_list (bool): If True, empty lists are accepted. Default False.

        Returns:
            List[str]: List of validation error messages. Empty list if valid.

        Examples:
            >>> validator = _ClassParameterValidator()
            >>> validator.validate_class_parameter(1, "target_class")
            []  # Valid

            >>> validator.validate_class_parameter([1, 2, 3], "target_class")
            []  # Valid

            >>> validator.validate_class_parameter(1.5, "target_class")
            ['target_class must be an integer, found float: 1.5']

            >>> validator.validate_class_parameter("abc", "target_class")
            ['target_class must be an integer or list of integers, found invalid value: 'abc'']

            >>> validator.validate_class_parameter(None, "base_class", allow_none=True)
            []  # Valid when allow_none=True

            >>> validator.validate_class_parameter([1, 2.5, 3], "target_class")
            ['target_class must only contain integer values, found float: 2.5']
        """
        errors = []

        # Check for None
        if value is None:
            if allow_none:
                return errors  # Valid
            else:
                errors.append(f"{parameter_name} is required")
                return errors

        # Check for string (invalid)
        if isinstance(value, str):
            errors.append(f"{parameter_name} must be an integer or list of integers, found invalid value: '{value}'")
            return errors

        # Check for float (invalid)
        if isinstance(value, float):
            errors.append(f"{parameter_name} must be an integer, found float: {value}")
            return errors

        # Check for boolean (invalid - check before int since bool is subclass of int)
        if isinstance(value, bool):
            errors.append(f"{parameter_name} must be an integer or list of integers, got boolean")
            return errors

        # Check for list
        if isinstance(value, list):
            # Check for empty list
            if len(value) == 0:
                if allow_empty_list:
                    return errors  # Valid
                else:
                    errors.append(f"{parameter_name} must contain at least one class value")
                    return errors

            # Validate all items in the list are integers
            for i, item in enumerate(value):
                if isinstance(item, bool):
                    errors.append(f"{parameter_name} must only contain integer values, found boolean at position {i}")
                    break
                elif isinstance(item, float):
                    errors.append(f"{parameter_name} must only contain integer values, found float: {item}")
                    break
                elif isinstance(item, str):
                    errors.append(f"{parameter_name} must only contain integer values, found string: '{item}'")
                    break
                elif not isinstance(item, int):
                    errors.append(f"{parameter_name} must only contain integer values, found {type(item).__name__}: {item}")
                    break

            return errors

        # Check for single integer value
        if isinstance(value, int):
            return errors  # Valid

        # Any other type is invalid
        errors.append(f"{parameter_name} must be an integer or list of integers, got {type(value).__name__}")
        return errors

    @classmethod
    def validate_multiple_class_parameters(cls, parameters: Dict[str, Tuple],
                                          allow_none_for_all: bool = False) -> List[str]:
        """
        Validates multiple class parameters at once.

        Args:
            parameters (Dict[str, Tuple]): Dictionary mapping parameter names to (value, allow_none, allow_empty_list)
                Example: {
                    "target_class": (value1, False, False),
                    "base_class": (value2, True, False)
                }
            allow_none_for_all (bool): If True, overrides individual allow_none settings

        Returns:
            List[str]: List of all validation error messages. Empty list if all valid.

        Example:
            >>> validator = _ClassParameterValidator()
            >>> params = {
            ...     "target_class": (1, False, False),
            ...     "base_class": (None, True, False)
            ... }
            >>> validator.validate_multiple_class_parameters(params)
            []  # Both valid
        """
        all_errors = []

        for param_name, param_config in parameters.items():
            if len(param_config) == 3:
                value, allow_none, allow_empty_list = param_config
            elif len(param_config) == 2:
                value, allow_none = param_config
                allow_empty_list = False
            else:
                value = param_config[0] if param_config else None
                allow_none = allow_none_for_all
                allow_empty_list = False

            # Override allow_none if global flag is set
            if allow_none_for_all:
                allow_none = True

            errors = cls.validate_class_parameter(value, param_name, allow_none, allow_empty_list)
            all_errors.extend(errors)

        return all_errors


# ------------------------------------------------------------------------


class _WindowParameterValidator:
    """
    Validator for window size parameters commonly used in moving window analysis.

    Validates parameters that must be:
    - A positive odd integer (e.g., 3, 5, 7, 11)
    - Used for focal/neighborhood operations in raster analysis

    Rejects even numbers, negative values, zero, floats, strings, and other invalid types.
    """

    @classmethod
    def validate_window_parameter(cls, value, parameter_name: str = "window",
                                  min_value: int = 1,
                                  max_value: Optional[int] = None) -> List[str]:
        """
        Validates a window size parameter for moving window operations.

        Args:
            value: The value to validate (must be a positive odd integer)
            parameter_name (str): Name of the parameter (for error messages). Default "window".
            min_value (int): Minimum allowed window size (must be odd). Default 1.
            max_value (int, optional): Maximum allowed window size (must be odd). Default None (no max).

        Returns:
            List[str]: List of validation error messages. Empty list if valid.

        Examples:
            >>> validator = _WindowParameterValidator()
            >>> validator.validate_window_parameter(3, "window")
            []  # Valid

            >>> validator.validate_window_parameter(5, "window")
            []  # Valid

            >>> validator.validate_window_parameter(4, "window")
            ['window must be an odd number (e.g., 3, 5, 7), got 4']

            >>> validator.validate_window_parameter(0, "window")
            ['window must be a positive integer, got 0']

            >>> validator.validate_window_parameter(-3, "window")
            ['window must be a positive integer, got -3']

            >>> validator.validate_window_parameter(3.5, "window")
            ['window must be an integer, got float']

            >>> validator.validate_window_parameter("5", "window")
            ['window must be an integer, got str']

            >>> validator.validate_window_parameter(101, "window", max_value=99)
            ['window must be between 1 and 99, got 101']
        """
        errors = []

        # Check for None
        if value is None:
            errors.append(f"{parameter_name} is required")
            return errors

        # Check for string (invalid)
        if isinstance(value, str):
            errors.append(f"{parameter_name} must be an integer, got str")
            return errors

        # Check for float (invalid)
        if isinstance(value, float):
            errors.append(f"{parameter_name} must be an integer, got float")
            return errors

        # Check for boolean (invalid - check before int since bool is subclass of int)
        if isinstance(value, bool):
            errors.append(f"{parameter_name} must be an integer, got boolean")
            return errors

        # Check for integer type
        if not isinstance(value, int):
            errors.append(f"{parameter_name} must be an integer, got {type(value).__name__}")
            return errors

        # Check for positive value
        if value < 1:
            errors.append(f"{parameter_name} must be a positive integer, got {value}")
            return errors

        # Check if value is odd
        if value % 2 == 0:
            errors.append(f"{parameter_name} must be an odd number (e.g., 3, 5, 7), got {value}")
            return errors

        # Check minimum value (if specified and different from default)
        if min_value > 1 and value < min_value:
            if min_value % 2 == 0:
                errors.append(f"{parameter_name} min_value must be odd, got {min_value}")
            else:
                errors.append(f"{parameter_name} must be at least {min_value}, got {value}")
            return errors

        # Check maximum value (if specified)
        if max_value is not None:
            if max_value % 2 == 0:
                errors.append(f"{parameter_name} max_value must be odd, got {max_value}")
            elif value > max_value:
                if min_value > 1:
                    errors.append(f"{parameter_name} must be between {min_value} and {max_value}, got {value}")
                else:
                    errors.append(f"{parameter_name} must be at most {max_value}, got {value}")
            return errors

        return errors

    @classmethod
    def validate_multiple_window_parameters(cls, parameters: Dict[str, Tuple]) -> List[str]:
        """
        Validates multiple window parameters at once.

        Args:
            parameters (Dict[str, Tuple]): Dictionary mapping parameter names to (value, min_value, max_value)
                Example: {
                    "window": (5, 1, None),
                    "kernel_size": (3, 3, 11)
                }
                Note: min_value and max_value are optional in tuple (can use just (value,))

        Returns:
            List[str]: List of all validation error messages. Empty list if all valid.

        Example:
            >>> validator = _WindowParameterValidator()
            >>> params = {
            ...     "window": (5, 1, None),
            ...     "kernel_size": (3, 3, 11)
            ... }
            >>> validator.validate_multiple_window_parameters(params)
            []  # Both valid
        """
        all_errors = []

        for param_name, param_config in parameters.items():
            if len(param_config) == 3:
                value, min_value, max_value = param_config
            elif len(param_config) == 2:
                value, min_value = param_config
                max_value = None
            else:
                value = param_config[0] if param_config else None
                min_value = 1
                max_value = None

            errors = cls.validate_window_parameter(value, param_name, min_value, max_value)
            all_errors.extend(errors)

        return all_errors


# ------------------------------------------------------------------------


class _DateParameterValidator:
    """
    Validator and converter for date parameters used in temporal analysis.

    Validates and converts dates to decimal year format for precise temporal calculations.
    Supports multiple date formats commonly used in remote sensing and GIS applications.

    Accepted formats:
    - YYYY (e.g., 2015) - Year only
    - YYYYMMDD (e.g., 20150615) - Compact format
    - YYYY/MM/DD (e.g., 2015/06/15) - Slash-separated
    - YYYY-MM-DD (e.g., 2015-06-15) - Dash-separated (ISO 8601)
    """

    @classmethod
    def parse_date_to_decimal_year(cls, date_value: Union[str, int, float]) -> float:
        """
        Convert date value to decimal year format.

        Converts various date formats to a decimal year representation where
        the fractional part represents the position within the year (0.0 to 0.999).
        Handles leap years correctly.

        Args:
            date_value: Date in various formats (str, int, or float)

        Returns:
            float: Date as decimal year (e.g., 2015.4493 for June 15, 2015)

        Raises:
            ValueError: If date format is not recognized or invalid

        Examples:
            >>> _DateParameterValidator.parse_date_to_decimal_year(2015)
            2015.0

            >>> _DateParameterValidator.parse_date_to_decimal_year("20150615")
            2015.4493150684931

            >>> _DateParameterValidator.parse_date_to_decimal_year("2015-06-15")
            2015.4493150684931

            >>> _DateParameterValidator.parse_date_to_decimal_year("2015/06/15")
            2015.4493150684931
        """
        from datetime import datetime

        # If already a number, return as float
        if isinstance(date_value, (int, float)):
            return float(date_value)

        # Convert string to stripped version
        date_str = str(date_value).strip()

        # Try different date formats
        date_formats = [
            ('%Y%m%d', 'YYYYMMDD'),      # 20150615
            ('%Y/%m/%d', 'YYYY/MM/DD'),  # 2015/06/15
            ('%Y-%m-%d', 'YYYY-MM-DD'),  # 2015-06-15
        ]

        # Try parsing as date with different formats
        for date_format, format_name in date_formats:
            try:
                date_obj = datetime.strptime(date_str, date_format)
                # Convert to decimal year
                year = date_obj.year
                # Calculate day of year (1-365/366)
                day_of_year = date_obj.timetuple().tm_yday
                # Days in year (handle leap years)
                days_in_year = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
                # Return as decimal year
                decimal_year = year + (day_of_year - 1) / days_in_year
                return decimal_year
            except ValueError:
                continue

        # Try parsing as just a year (YYYY)
        try:
            year_value = float(date_str)
            # Validate it's a reasonable year
            if 1900 <= year_value <= 2200:
                return year_value
        except ValueError:
            pass

        # If nothing worked, raise error with helpful message
        raise ValueError(
            f"Invalid date format: '{date_value}'. "
            f"Accepted formats: YYYY (e.g., 2015), YYYYMMDD (e.g., 20150615), "
            f"YYYY/MM/DD (e.g., 2015/06/15), YYYY-MM-DD (e.g., 2015-06-15)"
        )

    @classmethod
    def validate_date_parameter(cls, value, parameter_name: str,
                                min_year: float = 1900.0,
                                max_year: float = 2200.0) -> Tuple[List[str], Optional[float]]:
        """
        Validates a date parameter and converts it to decimal year.

        Args:
            value: The value to validate (can be str, int, float, or None)
            parameter_name (str): Name of the parameter (for error messages)
            min_year (float): Minimum allowed year (default: 1900.0)
            max_year (float): Maximum allowed year (default: 2200.0)

        Returns:
            Tuple[List[str], Optional[float]]: Tuple containing:
                - List of validation error messages (empty if valid)
                - Converted decimal year value (None if validation failed)

        Examples:
            >>> errors, value = _DateParameterValidator.validate_date_parameter(2015, "from_date")
            >>> errors
            []
            >>> value
            2015.0

            >>> errors, value = _DateParameterValidator.validate_date_parameter("2015-06-15", "from_date")
            >>> errors
            []
            >>> value
            2015.4493150684931

            >>> errors, value = _DateParameterValidator.validate_date_parameter("invalid", "from_date")
            >>> len(errors)
            1
        """
        errors = []

        # Check for None
        if value is None:
            errors.append(f"{parameter_name} is required")
            return errors, None

        # Try to parse the date
        try:
            decimal_year = cls.parse_date_to_decimal_year(value)
        except ValueError as e:
            errors.append(str(e))
            return errors, None

        # Validate year range
        if decimal_year < min_year or decimal_year > max_year:
            errors.append(
                f"{parameter_name} year {decimal_year:.2f} is outside valid range "
                f"({min_year:.0f}-{max_year:.0f})"
            )
            return errors, None

        return errors, decimal_year

    @classmethod
    def validate_date_range(cls, from_date, to_date,
                           from_param_name: str = "from_date",
                           to_param_name: str = "to_date",
                           min_year: float = 1900.0,
                           max_year: float = 2200.0,
                           allow_equal: bool = False) -> Tuple[List[str], Optional[float]]:
        """
        Validates a date range (from_date to to_date) and calculates the period.

        Args:
            from_date: Start date value
            to_date: End date value
            from_param_name (str): Name of from_date parameter (for error messages)
            to_param_name (str): Name of to_date parameter (for error messages)
            min_year (float): Minimum allowed year (default: 1900.0)
            max_year (float): Maximum allowed year (default: 2200.0)
            allow_equal (bool): If True, allows from_date == to_date (default: False)

        Returns:
            Tuple[List[str], Optional[float]]: Tuple containing:
                - List of validation error messages (empty if valid)
                - Calculated period in years (abs(to_date - from_date), None if validation failed)

        Examples:
            >>> errors, period = _DateParameterValidator.validate_date_range(2015, 2020, "from_date", "to_date")
            >>> errors
            []
            >>> period
            5.0

            >>> errors, period = _DateParameterValidator.validate_date_range("2015-06-15", "2020-12-31", "from_date", "to_date")
            >>> errors
            []
            >>> period  # approximately 5.544 years
            5.544109589041096
        """
        all_errors = []

        # Validate from_date
        from_errors, from_decimal = cls.validate_date_parameter(
            from_date, from_param_name, min_year, max_year
        )
        all_errors.extend(from_errors)

        # Validate to_date
        to_errors, to_decimal = cls.validate_date_parameter(
            to_date, to_param_name, min_year, max_year
        )
        all_errors.extend(to_errors)

        # If either date is invalid, return early
        if from_decimal is None or to_decimal is None:
            return all_errors, None

        # Calculate period
        period = abs(to_decimal - from_decimal)

        # Check if dates are equal (only if not allowed)
        if not allow_equal and from_decimal == to_decimal:
            all_errors.append(
                f"{from_param_name} and {to_param_name} must be different "
                f"(both are {from_decimal})"
            )
            return all_errors, None

        # Check if period is positive
        if period <= 0 and not allow_equal:
            all_errors.append(
                f"Analysis period must be greater than 0 years, got {period:.4f} "
                f"({from_param_name}={from_decimal}, {to_param_name}={to_decimal})"
            )
            return all_errors, None

        return all_errors, period


# ------------------------------------------------------------------------

