#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   Year:               2025
#
#   VT0007 UDef-ARP Standalone
#   Run this script to launch the VT7 GUI application.
#
# ------------------------------------------------------------------------

import sys
import os

# Add the standalone directory to path
standalone_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, standalone_dir)

from terracover.modules.udef_arp import FuncInputs, udef_arp

if __name__ == "__main__":
    from terracover.gui_src.utils.run_gui import run_gui
    run_gui(FuncInputs(), udef_arp)
