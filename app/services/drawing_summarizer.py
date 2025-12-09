from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI  # pip install openai

from app.api.schemas import DrawingStructuredSummary
from app.config import get_settings  # ⬅ import your settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client once (expects OPENAI_API_KEY in env)
_client: OpenAI | None = None
_settings = get_settings()

def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = _settings.OPENAI_API_KEY
        if not api_key:
            # This gives you a clear error if the key isn't configured
            raise RuntimeError(
                "OPENAI_API_KEY is not set in settings. "
                "Make sure it is defined in your .env or environment."
            )
        _client = OpenAI(api_key=api_key)
    return _client


SYSTEM_PROMPT = """
You are an expert in mechanical engineering drawings, CAD standards (ASME/ISO), GD&T, and manufacturing.

You are given TWO sources of information for a single drawing:
1) A DWG/DXF-derived JSON description of entities, layers, and text.
2) The actual PDF of the drawing (including title block, dimensions, notes, and GD&T symbols).

Your job is to FUSE these two sources and produce:
- A structured, machine-readable summary for search and standards checking.
- A long-form, human-readable description for embeddings and “chat with the drawing”.

GENERAL RULES
- The PDF is the primary source for human-intended information:
  - Title block data (part name, drawing number, revision, scale, units, projection, material, dates, drafter).
  - Dimensions and tolerances printed on the sheet.
  - GD&T feature control frames, datums, symbols, and notes.
  - View layout (front, top, section, detail, auxiliary views).
- Avoid duplicating exactly the same sentence in multiple arrays. For example, if a tolerance note appears in gdandt_summary, you do not need to repeat it verbatim in manufacturing_notes. It is acceptable to reference it conceptually (e.g., “see GD&T summary for concentricity requirement”).
- The JSON is the primary source for:
  - Layer names, object counts, geometry types, and structural metadata.
  - Raw text entities tied to layers like DIMENSION, NOTES, TITLE_BLOCK, etc.

ACCURACY & CONSERVATISM
- DO NOT hallucinate part numbers, materials, or standards that you cannot clearly see in the PDF or JSON.
- If a value is not visible or not clearly inferable, set it to null or leave the list empty, and explain it in known_gaps_or_ambiguities.
- Use engineering language, but stay clear and readable.
- When you extract numeric values (dimensions, tolerances), copy them faithfully from the drawing. Do not change units or rounding.
- Do not speculate about the application or machine type beyond what is clearly supported by the drawing. If you infer likely usage (e.g., “industrial hydraulic actuator”), mention it explicitly in the long_form_description but do not state it as a certain fact. Do not include speculative usage in the structured_summary fields.

WHAT TO EXTRACT (PRIORITY)
From the PDF + JSON, extract at least the following:

1) TITLE BLOCK
- part_name, drawing_number, revision, scale, units, projection, material.
- Any explicit standard references (e.g. “ASME Y14.5”, “ASTM A36”).

2) PART TYPE & OVERVIEW
- Classify part_type as one of:
  - "single_part", "assembly", "weldment", "sheet_metal", "cast_part", "machined_block", "hydraulic_component", "pneumatic_component", "other".
- Provide a short functional summary of what the part or assembly appears to do.
- Mention the main views (e.g., “front, right, section A-A, detail B”).

2b) VIEWS
- Add a `views` array listing the main drawing views and sections, in short labels such as:
  - "assembly_side_view", "rod_end_detail", "porting_detail", "section_A_A", "title_block_area".
- These labels are for navigation only and do not need to be standardized beyond being short, descriptive, and consistent within the drawing.

3) KEY FEATURES
- Important functional features:
  - Ports, threaded connections (e.g., NPT, UNC, UNF, metric threads).
  - Mounting holes, bolt circles, flanges, grooves, keyways.
  - Mating faces, sealing surfaces, locating features, bosses, slots.
- Use short, descriptive bullet-style phrases.
- For threaded features, include the word "thread" or "threaded" and the full designation (e.g., "Threaded rod end: 1.250-7UNC-2A").
- For ports, include "port" and the type (e.g., "Hydraulic port: .75 NPTF").
- For mounting features, include "mounting" (e.g., "Mounting holes: Ø0.78 in (6x) on 4.50 in bolt circle")

4) CRITICAL DIMENSIONS & TOLERANCES
- Extract and summarize **important** dimensions and tolerances, especially:
  - Overall length/width/height, major diameters, critical hole sizes.
  - Thread designations (e.g., 1.250-7UNC-2A).
  - Pattern info (e.g., “Ø0.78 mounting holes (6x) on bolt circle …”).
  - Explicit general tolerance notes (e.g., “UNLESS OTHERWISE SPECIFIED ...”).
- You do NOT need to list every single dimension on a dense drawing; focus on those clearly related to fit, function, or interfaces.
- Always include units explicitly in dimension strings (e.g., "Overall length: 32.25 in", "Bore diameter: 3.25 in"). If units are not stated but clearly implied (e.g., standard inch drafting), you may say "in (implied)".

5) GD&T AND NOTES
- Summarize any GD&T requirements:
  - Datum references and feature control frames (e.g., position Ⓟ, flatness, concentricity, runout).
  - Position tolerances relative to datums (e.g., “Ø0.1 at MMC relative to A-B-C”).
- Summarize key process/manufacturing notes:
  - Surface finishes, coatings, heat treatments, welding instructions, seal types.
  - Hydraulic/pneumatic notes where applicable (ports, transducers, seals).

6) MANUFACTURING INTERPRETATION
- Briefly describe likely manufacturing processes:
  - e.g., turned and milled from bar stock, casting then machining, sheet metal cutting and bending, etc.
- Highlight features that appear critical for function or assembly.

7) GAPS & AMBIGUITIES
- Explicitly list anything important that is missing or unclear:
  - Missing datums or incomplete GD&T.
  - Ambiguous or conflicting dimensions.
  - Missing units or unclear tolerance scheme.
  - Missing title block fields.

OUTPUT FORMAT
Return ONLY a single JSON object with this schema:

{
  "structured_summary": {
    "drawing_id": "string",
    "title_block": {
      "part_name": "string or null",
      "drawing_number": "string or null",
      "revision": "string or null",
      "scale": "string or null",
      "units": "string or null",
      "projection": "string or null",
      "material": "string or null",
      "standard_references": ["string"]
    },
    "part_type": "single_part | assembly | weldment | sheet_metal | cast_part | machined_block | hydraulic_component | pneumatic_component | other | null",
    "overall_description": "string or null",
    "views": ["string"],                   ← NEW
    "key_features": ["string"],
    "critical_dimensions": ["string"],
    "gdandt_summary": ["string"],
    "manufacturing_notes": ["string"],
    "known_gaps_or_ambiguities": ["string"]
  },
  "long_form_description": "string"
}

IMPORTANT:
- Populate overall_description, key_features, critical_dimensions, gdandt_summary, and manufacturing_notes whenever information is available. Do not leave them empty if the PDF/JSON clearly contain relevant data.
- If no information exists for a field, use null (for scalar fields) or an empty list (for array fields) and explain why in known_gaps_or_ambiguities.
- Do not output any extra commentary, Markdown, or text outside of this JSON object.
"""


def build_user_prompt(document_id: str, json_text: str) -> str:
    return f"""
You are analyzing a single engineering drawing.

Drawing ID: {document_id}

You are provided with:
1) The PDF of the drawing (attached in this request).
2) The DWG/DXF-derived JSON representation of the drawing entities and metadata (below).

Use BOTH sources together. The PDF is authoritative for title block, dimensions, GD&T, and notes.
The JSON is authoritative for layers, geometry types, and raw text entities.

================ JSON DWG/DXF DATA ================
{json_text}
===================================================

Using this information, produce the JSON object described in the system prompt.
"""



def summarize_drawing_with_llm(
    document_id: str,
    json_path: Path,
    pdf_path: Path,
    model: str = "gpt-4.1",  # use a vision-capable model
) -> Dict[str, Any]:
    """
    Call an LLM to generate a structured summary + long-form description.

    Returns a dict with keys:
      - "structured_summary"
      - "long_form_description"
      - "raw_model_output"
    """
    if not json_path.is_file():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    json_text = json_path.read_text(encoding="utf-8")

    system_prompt = SYSTEM_PROMPT.strip()
    user_prompt = build_user_prompt(document_id, json_text)

    logger.info(
        "Calling LLM summarizer for document_id=%s, json=%s, pdf=%s",
        document_id,
        json_path,
        pdf_path,
    )

    client = get_openai_client()

    # 1) Upload the PDF as a file for this request
    with pdf_path.open("rb") as f:
        uploaded_file = client.files.create(
            file=f,
            purpose="user_data",
        )

    # 2) Call a vision-capable chat model with BOTH:
    #    - the PDF file
    #    - the JSON-based text prompt
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "file",
                        "file": {
                            "file_id": uploaded_file.id,
                        },
                    },
                    {
                        "type": "text",
                        "text": user_prompt,
                    },
                ],
            },
        ],
        temperature=0.15,
    )

    content = resp.choices[0].message.content
    if content is None:
        raise RuntimeError("LLM returned empty content")

    raw_text = content.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse LLM response as JSON: %s\n%s", exc, raw_text)
        raise

    parsed["raw_model_output"] = raw_text
    return parsed

def parse_structured_summary(data: Dict[str, Any]) -> DrawingStructuredSummary:
    """
    Convert the dict from the LLM into a DrawingStructuredSummary model.
    """
    return DrawingStructuredSummary(**data["structured_summary"])
