from __future__ import annotations

import io
import logging
from pathlib import Path

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, layout, pymupdf
from ezdxf.addons.drawing.config import (
    BackgroundPolicy,
    ColorPolicy,
    Configuration,
    LineweightPolicy,
)
from PIL import Image

logger = logging.getLogger(__name__)


def _load_dxf_document(dxf_path: Path) -> ezdxf.EzDxfDoc:
    """
    Load the DXF document and audit it.

    We log auditor issues but do not abort rendering on errors; we want
    a best-effort render, since this is for previews/thumbnails.
    """
    if not dxf_path.is_file():
        raise FileNotFoundError(f"DXF file does not exist: {dxf_path}")

    logger.info("Loading DXF file for rendering: %s", dxf_path)

    doc = ezdxf.readfile(dxf_path)
    auditor = doc.audit()

    num_errors = len(getattr(auditor, "errors", []))
    if num_errors > 0:
        logger.warning(
            "DXF auditor reported %d issue(s) in %s. Proceeding with rendering.",
            num_errors,
            dxf_path,
        )

    return doc


def _create_page() -> layout.Page:
    """
    Create a page definition for PyMuPdfBackend.

    width=0 and height=0 tell ezdxf to auto-fit the content bounding box.
    Units are mm; max_width / max_height roughly correspond to A0.
    """
    return layout.Page(
        width=0,                # auto-detect from content
        height=0,               # auto-detect from content
        units=layout.Units.mm,  # treat drawing units as millimeters
        margins=layout.Margins.all(0),
        max_width=1189,         # ~A0 width in mm
        max_height=841,         # ~A0 height in mm
    )


def _create_settings(scale: float = 1.0) -> layout.Settings:
    """
    Layout settings for the render. For now we use a 1:1 scale; adjust later
    if you want to change plotted size.
    """
    return layout.Settings(scale=scale)


def _create_config() -> Configuration:
    """
    Rendering configuration: white background, colored entities, relative
    lineweights. This matches what you tested in the standalone script.
    """
    return Configuration(
        background_policy=BackgroundPolicy.WHITE,
        color_policy=ColorPolicy.COLOR,
        lineweight_policy=LineweightPolicy.RELATIVE,
        lineweight_scaling=1.0,
    )


def _render_to_backend(
    dxf_path: Path,
) -> tuple[ezdxf.EzDxfDoc, pymupdf.PyMuPdfBackend]:
    """
    Core rendering step:

    - Load DXF
    - Build RenderContext + PyMuPdfBackend
    - Draw modelspace into the backend

    We render **modelspace** because that's what gave you the exact DWG
    replica in your test.
    """
    doc = _load_dxf_document(dxf_path)
    msp = doc.modelspace()

    backend = pymupdf.PyMuPdfBackend()
    ctx = RenderContext(doc)
    config = _create_config()

    frontend = Frontend(ctx, backend, config=config)
    logger.info("Drawing DXF modelspace to PyMuPdf backend: %s", dxf_path)
    frontend.draw_layout(msp)

    return doc, backend


def render_dxf_to_pdf(dxf_path: Path, pdf_path: Path, dpi: int = 300) -> None:
    """
    Render DXF → vector PDF using ezdxf + PyMuPdfBackend.

    dpi is not strictly used for vector PDF resolution, but we keep it in
    the signature to stay parallel with the PNG function.
    """
    logger.info("Rendering DXF→PDF: %s -> %s", dxf_path, pdf_path)

    _, backend = _render_to_backend(dxf_path)
    page = _create_page()
    settings = _create_settings(scale=1.0)

    pdf_bytes = backend.get_pdf_bytes(page, settings=settings)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(pdf_bytes)

    if pdf_path.is_file():
        logger.info(
            "PDF rendered: %s (%.1f KB)",
            pdf_path,
            pdf_path.stat().st_size / 1024.0,
        )
    else:
        logger.warning(
            "PDF rendering reported success but file not found: %s",
            pdf_path,
        )


def render_dxf_to_png(
    dxf_path: Path,
    png_path: Path,
    dpi: int = 300,
) -> None:
    """
    Render DXF → full-size PNG using the same PyMuPdf render as PDF.

    We use PyMuPdfBackend.get_pixmap_bytes(...) with fmt='png' to get a
    bitmap from the same vector render used for PDF. DPI controls raster
    resolution (effective image size).
    """
    logger.info("Rendering DXF→PNG: %s -> %s (dpi=%d)", dxf_path, png_path, dpi)

    _, backend = _render_to_backend(dxf_path)
    page = _create_page()
    settings = _create_settings(scale=1.0)

    # Direct PNG bytes from backend; dpi affects pixel dimensions.
    png_bytes = backend.get_pixmap_bytes(
        page,
        fmt="png",
        settings=settings,
        dpi=dpi,
        alpha=False,
    )

    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.write_bytes(png_bytes)

    if png_path.is_file():
        logger.info(
            "PNG rendered: %s (%.1f KB)",
            png_path,
            png_path.stat().st_size / 1024.0,
        )
    else:
        logger.warning(
            "PNG rendering reported success but file not found: %s",
            png_path,
        )


def generate_thumbnail_from_png(
    png_path: Path,
    thumbnail_path: Path,
    max_size: int = 256,
) -> None:
    """
    Downscale a full-size PNG to a square-bounded thumbnail, preserving
    aspect ratio. This is used by the ingestion pipeline for quick previews.
    """
    if not png_path.is_file():
        raise FileNotFoundError(f"PNG file does not exist: {png_path}")

    logger.info(
        "Generating thumbnail from %s -> %s (max_size=%d)",
        png_path,
        thumbnail_path,
        max_size,
    )

    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(png_path) as img:
        img.thumbnail((max_size, max_size))
        img.save(thumbnail_path, format="PNG")

    logger.info(
        "Thumbnail rendered: %s (%.1f KB)",
        thumbnail_path,
        thumbnail_path.stat().st_size / 1024.0,
    )
