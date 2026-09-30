# coding=utf-8
# ------------------------------------------------------------------------
#   Copyright:  © Terra Global Capital. All rights reserved.
# ------------------------------------------------------------------------
"""Output provenance — embed *how a file was produced* into the file's own metadata.

Every spatial output carries a small record: which module made it, with what arguments, and
when. Self-describing outputs make MRV / audit traceability possible without external run logs
(answer "what parameters produced this credit raster?" straight from the file, forever).

Metadata schema (keys written):
    TC_module     — module display name (e.g. "FCBM Generator")
    TC_arguments  — JSON of the module's input arguments (callables dropped, non-JSON stringified)
    TC_date       — ISO-8601 timestamp when the file was written
    TC_version    — TerraCover version, when known

Every writer is BEST-EFFORT: a metadata failure must never break a run. Callers may still wrap
in try/except, but these functions already swallow their own errors and return a bool.
"""

import json
import os
from datetime import datetime
from typing import Optional


# Output extensions that carry embedded provenance and belong in the workspace.
_OUTPUT_EXTS = (".tif", ".tiff", ".shp", ".gpkg", ".xlsx")


def scan_output_files(folder, min_mtime=0.0, exts=_OUTPUT_EXTS, recursive=True):
    """Enumerate the output files under ``folder`` (for get_workspace_outputs / provenance).

    A module whose engine writes many files into an output *directory* must return THIS from
    get_workspace_outputs() rather than the bare directory: a directory cannot be stamped
    (write_provenance dispatches by extension) and _collect_workspace_outputs never scans
    inside it, so declaring a folder ships every file inside it UNSTAMPED.

    Filters by mtime (``>= min_mtime`` with a -1s epsilon for FAT/NTFS quantization) so a
    persistent output folder does not re-enumerate files from previous runs — pass the
    processor's ``_run_start_time`` (set by BaseProcessor.run()).
    """
    if not folder or not os.path.isdir(folder):
        return []
    exts = tuple(e.lower() for e in exts)
    cutoff = (min_mtime or 0.0) - 1.0
    found = []
    walker = os.walk(folder) if recursive else [(folder, [], os.listdir(folder))]
    for root, _dirs, files in walker:
        for fname in files:
            if fname.lower().endswith(exts) and not fname.startswith("~$"):
                fpath = os.path.join(root, fname)
                try:
                    if os.path.getmtime(fpath) >= cutoff:
                        found.append(fpath)
                except OSError:
                    pass
    return found


_ENGINE_VERSION = None


def _git_short_sha() -> Optional[str]:
    """The short git SHA of the working tree this package lives in, or None (packaged build / no
    git / detached). Best-effort — never raises."""
    try:
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=here, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=5, text=True,
        )
        sha = (out.stdout or "").strip()
        return sha if out.returncode == 0 and sha else None
    except Exception:
        return None


def engine_version() -> str:
    """The version string embedded as TC_version: the package ``__version__`` plus the short git
    SHA when running from a source checkout (e.g. ``1.0.0+g1a2b3c4``); just ``__version__`` in a
    packaged build with no git. Computed once and cached — the hook calls it per output file."""
    global _ENGINE_VERSION
    if _ENGINE_VERSION is not None:
        return _ENGINE_VERSION
    base = "unknown"
    try:
        from terracover import __version__ as _v
        base = str(_v)
    except Exception:
        pass
    sha = _git_short_sha()
    _ENGINE_VERSION = f"{base}+g{sha}" if sha else base
    return _ENGINE_VERSION


def _serialize_args(args: Optional[dict]) -> str:
    """JSON-serialize an arguments dict. Callables (progress / cancel callbacks) are dropped;
    anything not natively JSON-serializable is stringified (file paths are already strings)."""
    safe = {}
    for key, value in (args or {}).items():
        if callable(value):
            continue
        try:
            json.dumps(value)
            safe[key] = value
        except (TypeError, ValueError):
            safe[key] = str(value)
    return json.dumps(safe, ensure_ascii=False, default=str)


def _provenance_metadata(module_name: str, args: Optional[dict],
                         version: Optional[str], created_iso: str) -> dict:
    md = {
        "TC_module": str(module_name or ""),
        "TC_arguments": _serialize_args(args),
        "TC_date": created_iso,
    }
    if version:
        md["TC_version"] = str(version)
    return md


def write_raster_provenance(path: str, module_name: str, args: Optional[dict] = None,
                            version: Optional[str] = None) -> bool:
    """Embed provenance into a GeoTIFF header via GDAL SetMetadata (a header-only rewrite —
    pixel data is untouched). Returns True on success, False on any failure."""
    try:
        from osgeo import gdal
    except Exception:
        return False
    ds = None
    try:
        ds = gdal.Open(path, gdal.GA_Update)
        if ds is None:
            return False
        md = ds.GetMetadata()
        md.update(_provenance_metadata(module_name, args, version, datetime.now().isoformat()))
        ds.SetMetadata(md)
        ds.FlushCache()
        return True
    except Exception:
        return False
    finally:
        ds = None


def write_vector_provenance(path: str, module_name: str, args: Optional[dict] = None,
                            version: Optional[str] = None) -> bool:
    """Embed provenance into a vector output. GeoPackage -> dataset metadata (the gpkg_metadata
    table, via GDAL SetMetadata). Shapefile -> a companion ``<name>.shp.xml`` sidecar (Shapefile
    has no native metadata slot). Returns True on success, False on any failure."""
    ext = os.path.splitext(path)[1].lower()
    created = datetime.now().isoformat()
    md = _provenance_metadata(module_name, args, version, created)

    if ext == ".gpkg":
        try:
            from osgeo import gdal
        except Exception:
            return False
        ds = None
        try:
            ds = gdal.OpenEx(path, gdal.OF_UPDATE | gdal.OF_VECTOR)
            if ds is None:
                return False
            # Provenance goes into the GeoPackage's dataset metadata (the gpkg_metadata table).
            # Readable by gdalinfo/ogrinfo and TerraCover SAT's metadata tab. (QGIS does not
            # surface gpkg metadata in its layer panels — a known QGIS limitation, not chased.)
            existing = ds.GetMetadata()
            existing.update(md)
            ds.SetMetadata(existing)
            ds.FlushCache()
            return True
        except Exception:
            return False
        finally:
            ds = None

    if ext == ".shp":
        try:
            from xml.sax.saxutils import escape
            lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<metadata>"]
            for key, value in md.items():
                lines.append(f"  <{key}>{escape(str(value))}</{key}>")
            lines.append("</metadata>")
            with open(path + ".xml", "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True
        except Exception:
            return False

    return False


def write_model_provenance(path: str, model_meta: dict) -> bool:
    """Add pipeline-level ``TC_MODEL_*`` keys to a raster/vector output.

    Additive: reads existing metadata and merges, so the tool's own
    ``TC_module`` / ``TC_arguments`` (written when the node ran) are preserved.
    *model_meta* keys are written verbatim (already prefixed, e.g. ``TC_MODEL``,
    ``TC_MODEL_NODE``, ``TC_MODEL_RUN``, ``TC_MODEL_GRAPH``). Best-effort."""
    md = {str(k): ("" if v is None else str(v)) for k, v in (model_meta or {}).items()}
    if not md:
        return False
    ext = os.path.splitext(path)[1].lower()

    if ext in (".tif", ".tiff", ".img", ".vrt"):
        try:
            from osgeo import gdal
        except Exception:
            return False
        ds = None
        try:
            ds = gdal.Open(path, gdal.GA_Update)
            if ds is None:
                return False
            existing = ds.GetMetadata()
            existing.update(md)
            ds.SetMetadata(existing)
            ds.FlushCache()
            return True
        except Exception:
            return False
        finally:
            ds = None

    if ext == ".gpkg":
        try:
            from osgeo import gdal
        except Exception:
            return False
        ds = None
        try:
            ds = gdal.OpenEx(path, gdal.OF_UPDATE | gdal.OF_VECTOR)
            if ds is None:
                return False
            # Provenance goes into the GeoPackage's dataset metadata (the gpkg_metadata table).
            # Readable by gdalinfo/ogrinfo and TerraCover SAT's metadata tab. (QGIS does not
            # surface gpkg metadata in its layer panels — a known QGIS limitation, not chased.)
            existing = ds.GetMetadata()
            existing.update(md)
            ds.SetMetadata(existing)
            ds.FlushCache()
            return True
        except Exception:
            return False
        finally:
            ds = None

    if ext == ".shp":
        # Merge into the companion <name>.shp.xml sidecar.
        try:
            from xml.sax.saxutils import escape
            side = path + ".xml"
            existing = ""
            if os.path.exists(side):
                with open(side, encoding="utf-8") as f:
                    existing = f.read()
            rows = "".join(f"  <{k}>{escape(v)}</{k}>\n" for k, v in md.items())
            if "</metadata>" in existing:
                merged = existing.replace("</metadata>", rows + "</metadata>")
            else:
                merged = ('<?xml version="1.0" encoding="UTF-8"?>\n<metadata>\n'
                          + rows + "</metadata>")
            with open(side, "w", encoding="utf-8") as f:
                f.write(merged)
            return True
        except Exception:
            return False

    return False


def _move_sheet_to_end(wb, title) -> None:
    """Move a worksheet to the last position (openpyxl keeps sheet order in wb._sheets).
    The arguments footer must always be the LAST sheet, even when a caller adds data
    sheets after it or a re-run's data-sheet rewrite pushes a stale footer to the front."""
    try:
        if title not in wb.sheetnames:
            return
        ws = wb[title]
        wb._sheets.remove(ws)
        wb._sheets.append(ws)
    except Exception:
        pass


def write_parameters_sheet(wb, params) -> None:
    """Append a 'Parameters' sheet to an openpyxl workbook, listing (name, value) argument pairs.

    A "generated" row with the report's creation date/time (local) is written first, so every
    workbook records when it was produced. Values are formatted for readability (bool -> True/False,
    dict/list -> one entry per line). This is the canonical statistics-workbook footer; the fcbm /
    exclusions / activity_shifting_leakage modules build it directly, and write_excel_provenance
    below adds it automatically to any other .xlsx output.
    """
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter  # noqa: F401  (kept for parity/callers)

    bold = Font(bold=True)

    def _fmt(value):
        if value is None:
            return ""
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, dict):
            return "\n".join(f"{k} = {v}" for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return "\n".join(str(v) for v in value)
        return str(value)

    ws = wb.create_sheet("Parameters")
    ws.cell(row=1, column=1, value="Parameter").font = bold
    ws.cell(row=1, column=2, value="Value").font = bold
    top = Alignment(vertical="top", wrap_text=True)

    rows = [("generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("TC_version", engine_version())] + list(params)
    for i, (name, value) in enumerate(rows):
        row_idx = 2 + i
        ws.cell(row=row_idx, column=1, value=name)
        cell = ws.cell(row=row_idx, column=2, value=_fmt(value))
        cell.alignment = top
    ws.column_dimensions['A'].width = 22
    ws.column_dimensions['B'].width = 80

    # The arguments footer belongs at the END of the workbook, after all data sheets.
    _move_sheet_to_end(wb, "Parameters")


def write_excel_provenance(path: str, module_name: str, args: Optional[dict] = None,
                           version: Optional[str] = None) -> bool:
    """Embed provenance into an .xlsx by appending a 'Parameters' sheet (the file has no header
    metadata slot). Re-opens the finished workbook, and is a NO-OP when a 'Parameters' sheet
    already exists — so modules that curate their own (fcbm / exclusions / activity_shifting_leakage)
    are respected and never duplicated. Returns True on success, False on any failure."""
    try:
        from openpyxl import load_workbook
    except Exception:
        return False
    try:
        wb = load_workbook(path)
        # If an arguments footer already exists — a module curated its own
        # (fcbm/exclusions/asl → "Parameters"; point_extractor → "Arguments"), or a
        # previous run left one — don't duplicate it, but ensure it stays the LAST
        # sheet. On re-runs, _SaveTable-style writers re-add their data sheet at the
        # end and push a stale footer to the front; move it back.
        existing = [s for s in ("Arguments", "Parameters") if s in wb.sheetnames]
        if existing:
            moved = False
            for s in existing:
                if wb.sheetnames[-1] != s:
                    _move_sheet_to_end(wb, s)
                    moved = True
            if moved:
                wb.save(path)
            return True
        # TC_version and the timestamp are added by write_parameters_sheet itself, so every caller
        # (this hook and the vt7 / terra_change / fcbm / exclusions write sites) gets them uniformly.
        params = [("module", str(module_name or ""))]
        for key, value in (args or {}).items():
            if callable(value):
                continue
            params.append((key, value))
        write_parameters_sheet(wb, params)
        wb.save(path)
        return True
    except Exception:
        return False


def write_provenance(path: str, module_name: str, args: Optional[dict] = None,
                     version: Optional[str] = None) -> bool:
    """Dispatch by file extension. Rasters (.tif/.tiff) -> GeoTIFF metadata; vectors
    (.shp/.gpkg) -> vector metadata / sidecar; Excel (.xlsx) -> a 'Parameters' sheet.
    Non-spatial files (.txt/.kml) are silently skipped (KML has no metadata slot)."""
    if not path or not isinstance(path, str):
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in (".tif", ".tiff"):
        return write_raster_provenance(path, module_name, args, version)
    if ext in (".shp", ".gpkg"):
        return write_vector_provenance(path, module_name, args, version)
    if ext == ".xlsx":
        return write_excel_provenance(path, module_name, args, version)
    return False
