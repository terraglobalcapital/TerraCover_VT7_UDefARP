# VT0007 UDef-ARP Standalone

Standalone version of the VT0007 (UDef-ARP) workflow processor with GUI.

## Overview

This tool implements the VT0007 methodology for:
- Activity Data processing
- Benchmark Model evaluation
- Alternative Model evaluation
- Deforestation map generation with uncertainty assessment

## Corrections & Documentation

This standalone tool is a **corrected and enhanced** implementation of the Verra UDef-ARP reference code. It fixes several bugs present in the original Verra implementation (and, where noted, in the newer **UDef-ARP v2.11** release) and improves the methodology in line with the VT0007 specification.

Detailed technical documentation for every bug fix and enhancement — including code comparisons, mathematical proofs, and a per-bug evaluation of whether Verra's v2.11 resolves each issue — is in the [`docs/`](docs) folder (Markdown sources, with Word copies under [`docs/word version/`](docs/word%20version)):

| Document | Topic |
|----------|-------|
| `VT7_UDef-ARP_Version_Comparison_2.11_vs_Original.md` | Full comparison: Original vs v2.11 vs TerraCover |
| `VT7_Geometric_Distribution_Analysis.md` | Geometric classification off-by-one + alternative-model formula |
| `VT7_AR_Adjustment_Bug_Fixes.md` | Bidirectional AR adjustment + ETP metadata rescaling |
| `VT7_Adjustment_Ratio_Implementation_Analysis.md` | Accumulative AR iteration (VT0007 compliance) |
| `VT7_Deforestation_Map_Variable_Reference_Bug.md` | `fmask` variable-reference bug |
| `VT7_Missing_Vulnerability_Zones_Bug_Fix.md` | NaN propagation from missing vulnerability zones |
| `VT7_Frequency_table_changes.md` | NoData handling + Int16 overflow in frequency tables |
| `VT7_Evaluation_Improvements.md` | Dual-mask Thiessen evaluation + scatter-plot enhancements |
| `VT7_Spatial_Deforestation_Allocation.md` | Spatial deforestation allocation |

Code paths cited in these documents are relative to this repository root (e.g. `terracover/modules/vt7/adjustment.py`). References to `verra_code/UDef-ARP-main` and `UDef-ARP-main 2.11` denote Verra's public UDef-ARP reference code used for comparison and are not shipped with this tool.

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
├── docs/                   # Bug-fix & methodology documentation
│   ├── *.md                            # Markdown sources
│   └── word version/                   # Word (.docx) copies
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
