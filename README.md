# VT0007 UDef-ARP Standalone

Standalone version of the VT0007 (UDef-ARP) workflow processor with GUI.

## Overview

This tool implements the VT0007 methodology for:
- Activity Data processing
- Benchmark Model evaluation
- Alternative Model evaluation
- Deforestation map generation with uncertainty assessment

## Requirements

- Windows 10/11 (64-bit)
- Anaconda or Miniconda installed
- Python 3.11+
- GDAL 3.6+
- ~2 GB free disk space

## Installation

### Quick Installation (Recommended)

Use the automated installer in the `installation/` folder:

1. Navigate to the `installation/` folder
2. Double-click `install_udef_arp.bat`
3. Select option **1** to install Visual C++ Redistributables (if not already installed)
4. Select option **2** to install the `udef_arp` environment
5. Select option **3** to validate the installation

For detailed instructions, see [`installation/UDEF_ARP_INSTALLATION_GUIDE.md`](installation/UDEF_ARP_INSTALLATION_GUIDE.md).

### Manual Installation

1. Create a conda environment:
```bash
conda create -n udef_arp python=3.11
conda activate udef_arp
```

2. Install GDAL (recommended via conda-forge):
```bash
conda install -c conda-forge gdal=3.10
```

3. Install remaining dependencies:
```bash
pip install -r installation/requirements.txt
```

## Usage

1. Activate the environment:
```bash
conda activate udef_arp
```

2. Run the GUI application:
```bash
python run_vt7.py
```

## Structure

```
vt7_udef_arp/
├── run_vt7.py              # Entry point
├── README.md               # This file
├── installation/           # Installation files
│   ├── install_udef_arp.bat           # Automated installer
│   ├── requirements.txt               # Python dependencies
│   └── UDEF_ARP_INSTALLATION_GUIDE.md # Detailed installation guide
└── terracover/
    ├── core/              # Core utilities
    ├── modules/           # VT7 processing modules
    │   ├── udef_arp.py    # Main workflow
    │   └── vt7/           # VT7 sub-modules
    ├── gui_src/           # GUI components
    └── images/            # Documentation images
```

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
| SciPy | latest | Statistical analysis |
| PyQt6 | 6.7.1 | GUI framework |
| lxml | 4.9.4 | XML processing |

## Troubleshooting

See the [Installation Guide](installation/UDEF_ARP_INSTALLATION_GUIDE.md#troubleshooting) for common issues and solutions.

## License

Copyright (c) Terra Global Capital. All rights reserved.
This code is proprietary and confidential.
