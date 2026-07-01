# UDEF_ARP Installation Guide

## Overview

This guide describes how to install the standalone VT7 UDEF_ARP module environment. This is a lightweight environment specifically designed to run the UDEF_ARP workflow without the full TerraCover suite.

## Requirements

- Windows 10/11 (64-bit)
- Anaconda or Miniconda installed
- Internet connection for package downloads
- ~2 GB free disk space

## Quick Installation

1. Navigate to the installation folder:
   ```
   TerraCover\installation\
   ```

2. Double-click `install_udef_arp.bat`

3. Select option **1** to install Visual C++ Redistributables (if not already installed)

4. Select option **2** to install the udef_arp environment

5. Select option **3** to validate the installation

## Included Packages

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.11 | Runtime environment |
| GDAL | 3.10.3 | Raster processing |
| GeoPandas | 1.1.1 | Vector data processing |
| Pandas | latest | Data analysis |
| NumPy | latest | Numerical computing |
| Shapely | latest | Geometric operations |
| Matplotlib | latest | Plotting and visualization |
| Seaborn | latest | Statistical visualization |
| SciPy | latest | Statistical analysis (stats, Voronoi) |
| PyQt6 | 6.7.1 | GUI framework |
| lxml | 4.9.4 | XML processing (openpyxl compatibility) |

## Menu Options

### Option 1: Install Visual C++ Redistributables
Downloads and installs Microsoft Visual C++ Redistributables 2015-2022. Required for PyQt6 to work properly.

### Option 2: Install udef_arp Environment
Creates a new conda environment named `udef_arp` with all required packages. If the environment already exists, you will be prompted to overwrite it.

### Option 3: Validate Existing Environment
Tests all installed packages to verify they are working correctly. Run this after installation to confirm everything is set up properly.

### Option 4: Remove udef_arp Environment
Completely removes the udef_arp environment and cleans up conda cache.

### Option 5: Exit
Closes the installer.

## Using the Environment

### Activate the Environment

```bash
conda activate udef_arp
```

### Run the UDEF_ARP Module

Navigate to the standalone module directory and run:

```bash
cd TerraCover\terracover\modules\vt7\standalone\vt7_udef_arp
python run_vt7.py
```

### Deactivate the Environment

```bash
conda deactivate
```

## Troubleshooting

### PyQt6 Import Error
**Symptom:** `ImportError: DLL load failed` when importing PyQt6

**Solution:**
1. Run the installer and select option 1 to install Visual C++ Redistributables
2. Restart your computer
3. Try again

### GDAL Import Error
**Symptom:** `ImportError: cannot import name 'gdal' from 'osgeo'`

**Solution:**
1. Remove the environment (option 4)
2. Reinstall (option 2)
3. Make sure you have a stable internet connection during installation

### Environment Not Found
**Symptom:** `conda activate udef_arp` returns "Could not find conda environment"

**Solution:**
1. Run the installer
2. Select option 2 to install the environment
3. Follow the prompts

### Validation Fails for Some Packages
**Symptom:** Some packages show `[FAILED]` during validation

**Solution:**
1. Remove the environment (option 4)
2. Clean conda cache: `conda clean --all -y`
3. Reinstall (option 2)

## Differences from TerraRS-311c

The `udef_arp` environment is a minimal installation compared to the full `TerraRS-311c` environment:

| Feature | udef_arp | TerraRS-311c |
|---------|----------|--------------|
| Installation time | ~3-5 minutes | ~10-15 minutes |
| Disk space | ~1.5 GB | ~4 GB |
| Google Earth Engine | No | Yes |
| XGBoost | No | Yes |
| Rasterio | No (uses GDAL) | Yes |
| scikit-learn | No | Yes |

Use `udef_arp` when you only need to run the VT7 UDEF_ARP workflow. Use `TerraRS-311c` for full TerraCover functionality.

## Support

For issues or questions, contact:
- Email: david.montoya@terraglobalcapital.com
