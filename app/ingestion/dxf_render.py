# app/ingestion/dxf_render.py
from __future__ import annotations

import logging
from pathlib import Path

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from PIL import Image

logger = logging.getLogger(__name__)


def _load_dxf_document(dxf_path: Path) -> ezdxf.EzDxfDoc:
    """
    Load the DXF document and audit it. We log auditor issues but do not
    abort rendering on errors; we want a best-effort render.
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


def _select_best_layout(doc: ezdxf.EzDxfDoc):
    """
    Heuristic to pick the layout to render.

    Strategy:
    - Log all layouts for debugging (name, is_modelspace, entity counts).
    - Prefer a paperspace layout that has at least one non-viewport entity
      (e.g., title blocks, dimensions, text), picking the one with the most.
    - If no such paperspace layouts exist, fall back to modelspace.
    """
    modelspace = doc.modelspace()

    layout_summaries = []
    for layout in doc.layouts:
        # Count all entities and "non-viewport" entities.
        total = len(layout)
        non_viewport_count = 0
        for e in layout:
            dxftype = e.dxftype()
            if dxftype not in {"VIEWPORT", "ACAD_PROXY_ENTITY"}:
                non_viewport_count += 1

        layout_summaries.append(
            (layout.name, layout.is_modelspace, total, non_viewport_count)
        )

    for name, is_model, total, non_view in layout_summaries:
        logger.info(
            "DXF layout '%s' (modelspace=%s): total_entities=%d, "
            "non_viewport_entities=%d",
            name,
            is_model,
            total,
            non_view,
        )

    # Candidate paperspace layouts with at least one non-viewport entity
    candidate_layouts = []
    for layout in doc.layouts:
        if layout.is_modelspace:
            continue

        non_viewport_count = 0
        for e in layout:
            dxftype = e.dxftype()
            if dxftype not in {"VIEWPORT", "ACAD_PROXY_ENTITY"}:
                non_viewport_count += 1

        if non_viewport_count > 0:
            candidate_layouts.append((layout, non_viewport_count))

    if candidate_layouts:
        # Pick the paperspace layout with the most non-viewport entities
        best_layout, best_count = max(candidate_layouts, key=lambda tup: tup[1])
        logger.info(
            "Selected paperspace layout '%s' for rendering "
            "(non_viewport_entities=%d).",
            best_layout.name,
            best_count,
        )
        return best_layout

    # Fallback: no good paperspace layout, use modelspace
    logger.info(
        "No suitable paperspace layout with non-viewport entities found; "
        "rendering modelspace only (layout='%s').",
        modelspace.name,
    )
    return modelspace



def _render_dxf_to_matplotlib_figure(dxf_path: Path, dpi: int = 300):
    """
    Load a DXF and render the chosen layout to a Matplotlib figure.
    We explicitly force all layers to be visible, including the DIMENSIONS layer,
    so that annotations and title blocks show up in the rendered output.
    """
    logger.info("Loading DXF file for rendering: %s", dxf_path)
    doc, layout = _load_dxf_document(dxf_path)

    # Create Matplotlib figure/axes
    fig = plt.figure(figsize=(11, 8.5), dpi=dpi)
    ax = fig.add_subplot(1, 1, 1)

    # Build a render context
    ctx = RenderContext(doc)
    ctx.set_current_layout(layout)

    # 🔧 NEW: force all layers (including DIMENSIONS) to be visible
    for name, props in ctx.layers.items():
        # props is a LayerProperties object
        props.is_off = False
        props.is_frozen = False

    # Optionally, log that DIMENSIONS is on:
    dim_props = ctx.layers.get("DIMENSIONS") or ctx.layers.get("Dimensions")
    if dim_props:
        logger.debug(
            "DIMENSIONS layer visible: is_off=%s, is_frozen=%s",
            dim_props.is_off,
            dim_props.is_frozen,
        )
    else:
        logger.debug("No 'DIMENSIONS' layer found in ctx.layers; available: %s", list(ctx.layers.keys()))

    # Render
    backend = MatplotlibBackend(ax)  # note: just (ax), not (ctx, ax)
    frontend = Frontend(ctx, backend)
    logger.info(
        "Drawing DXF layout '%s' (paperspace=%s) to Matplotlib canvas: %s",
        layout.name,
        getattr(layout, "paperspace", False),
        dxf_path,
    )
    frontend.draw_layout(layout, finalize=True)

    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout(pad=0)

    return fig, ax


def render_dxf_to_pdf(dxf_path: Path, pdf_path: Path, dpi: int = 300) -> None:
    logger.info("Rendering DXF→PDF: %s -> %s (dpi=%d)", dxf_path, pdf_path, dpi)

    fig, _ = _render_dxf_to_matplotlib_figure(dxf_path, dpi=dpi)

    import matplotlib.pyplot as plt

    fig.savefig(pdf_path, dpi=dpi)
    plt.close(fig)

    if pdf_path.is_file():
        logger.info(
            "PDF rendered: %s (%.1f KB)",
            pdf_path,
            pdf_path.stat().st_size / 1024.0,
        )
    else:
        logger.warning("PDF rendering reported success but file not found: %s", pdf_path)


def render_dxf_to_png(dxf_path: Path, png_path: Path, dpi: int = 300) -> None:
    logger.info("Rendering DXF→PNG: %s -> %s (dpi=%d)", dxf_path, png_path, dpi)

    fig, _ = _render_dxf_to_matplotlib_figure(dxf_path, dpi=dpi)

    import matplotlib.pyplot as plt

    fig.savefig(png_path, dpi=dpi)
    plt.close(fig)

    if png_path.is_file():
        logger.info(
            "PNG rendered: %s (%.1f KB)",
            png_path,
            png_path.stat().st_size / 1024.0,
        )
    else:
        logger.warning("PNG rendering reported success but file not found: %s", png_path)


def generate_thumbnail_from_png(
    png_path: Path,
    thumbnail_path: Path,
    max_size: int = 512,
) -> None:
    if not png_path.is_file():
        raise FileNotFoundError(f"PNG file does not exist: {png_path}")

    logger.info(
        "Generating thumbnail from %s -> %s (max_size=%d)",
        png_path,
        thumbnail_path,
        max_size,
    )

    with Image.open(png_path) as img:
        img.thumbnail((max_size, max_size))
        img.save(thumbnail_path, format="PNG")

    logger.info(
        "Thumbnail rendered: %s (%.1f KB)",
        thumbnail_path,
        thumbnail_path.stat().st_size / 1024.0,
    )

