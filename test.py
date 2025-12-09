from pathlib import Path

from app.config import get_settings
from app.ingestion.dwg_to_dxf import convert_dwg_to_dxf, DwgToDxfError
from app.ingestion.dxf_render import (
    render_dxf_to_pdf,
    render_dxf_to_png,
    generate_thumbnail_from_png,
)
from app.ingestion.dwg_json import run_dwg_to_json

settings = get_settings()

document_id = "8325cc5b2c99a96cdec94ff9871a468ecdc053696e0a9d7586eca60001a2c055"

ingested_dwg = Path(settings.ingested_dir) / f"{document_id}.dwg"
derived_dir = Path(settings.derived_dir)

print("Using DWG:", ingested_dwg)

try:
    dxf_path = convert_dwg_to_dxf(ingested_dwg, derived_dir, settings.dwg2dxf_path)
    print("DXF path:", dxf_path)
except DwgToDxfError as exc:
    print("DXF conversion FAILED:", exc)
    raise  # for now, bubble it up so we can see it
	
render_dxf_to_pdf(dxf_path, pdf_path, dpi=300)
render_dxf_to_png(dxf_path, png_path, dpi=300)
generate_thumbnail_from_png(png_path, thumb_path)


