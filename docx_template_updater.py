"""Fill detector placeholders in a DOCX template while preserving images.

Usage:
    python docx_template_updater.py \
        --template path/to/template.docx \
        --data detector_output.json \
        --output path/to/filled.docx \
        --index 0

Placeholders in the document should follow: {{field_name}}

This script supports both:
1) Flattened records (e.g., Team_Alpha_Fall_2025.json)
2) Raw /upload API responses with nested detector fields
   (single object or {'results': [...]} wrapper)
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any

from docx import Document


MISSING = "Missing"

# Placeholders expected by the syllabus template.
TEMPLATE_FIELDS = [
    "filename",
    "instructor_name",
    "instructor_title",
    "instructor_department",
    "email",
    "preferred_contact_method",
    "response_time",
    "office_address",
    "office_phone",
    "office_hours",
    "modality",
    "class_location",
    "assignment_types_title",
    "assignment_delivery",
    "deadline_expectations_title",
    "SLOs",
    "credit_hour",
    "workload",
    "grading_process",
    "final_grade_scale",
]


def _normalize_value(value: Any) -> str:
    if value is None:
        return MISSING

    # Avoid writing complex structures directly into template placeholders.
    if isinstance(value, (dict, list, tuple, set)):
        return MISSING

    text = str(value).strip()
    if not text:
        return MISSING
    if text.lower() in {"missing", "none", "null", "n/a", "na"}:
        return MISSING
    return text


def _get_nested(data: Dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _resolve_modality(record: Dict[str, Any]) -> str:
    val = _get_nested(record, "modality", "modality")
    if _normalize_value(val) != MISSING:
        return _normalize_value(val)

    val = record.get("course_delivery")
    if _normalize_value(val) != MISSING:
        return _normalize_value(val)

    return MISSING


def _resolve_slos(record: Dict[str, Any]) -> str:
    val = record.get("SLOs")
    if _normalize_value(val) != MISSING:
        return _normalize_value(val)

    val = record.get("slo_content")
    if _normalize_value(val) != MISSING:
        return _normalize_value(val)

    if bool(record.get("has_slos")):
        return "SLOs detected"

    return MISSING


def _to_template_values(record: Dict[str, Any]) -> Dict[str, str]:
    """Convert detector output (nested or flat) into template placeholders."""
    values: Dict[str, str] = {field: MISSING for field in TEMPLATE_FIELDS}

    # Preserve direct values first for compatibility with already-flattened JSON.
    for field in TEMPLATE_FIELDS:
        if field in record:
            values[field] = _normalize_value(record.get(field))

    # Map nested /upload detector response fields onto template placeholders.
    nested_map = {
        "filename": _normalize_value(record.get("filename")),
        "instructor_name": _normalize_value(_get_nested(record, "instructor", "name")),
        "instructor_title": _normalize_value(_get_nested(record, "instructor", "title")),
        "instructor_department": _normalize_value(_get_nested(record, "instructor", "department")),
        "email": _normalize_value(_get_nested(record, "email_information", "email")),
        "preferred_contact_method": _normalize_value(_get_nested(record, "preferred_information", "preferred")),
        "response_time": _normalize_value(_get_nested(record, "response_time", "content")),
        "office_address": _normalize_value(_get_nested(record, "office_information", "location")),
        "office_phone": _normalize_value(_get_nested(record, "office_information", "phone")),
        "office_hours": _normalize_value(_get_nested(record, "office_information", "hours")),
        "modality": _resolve_modality(record),
        "class_location": _normalize_value(_get_nested(record, "class_location", "content")),
        "assignment_types_title": _normalize_value(_get_nested(record, "assignment_types", "content")),
        "assignment_delivery": _normalize_value(_get_nested(record, "assignment_delivery", "content")),
        "deadline_expectations_title": _normalize_value(_get_nested(record, "late_information", "late")),
        "SLOs": _resolve_slos(record),
        "credit_hour": _normalize_value(_get_nested(record, "credit_hours", "hours")),
        "workload": _normalize_value(_get_nested(record, "workload_information", "description")),
        "grading_process": _normalize_value(_get_nested(record, "grading_process", "content")),
        "final_grade_scale": _normalize_value(_get_nested(record, "grading_scale", "content")),
    }

    # Nested values override direct values when they contain real detector output.
    for key, value in nested_map.items():
        if value != MISSING:
            values[key] = value

    return values


def _replace_in_runs(runs, values: Dict[str, str]) -> None:
    # Run-level replacement keeps images and other embedded content intact.
    for run in runs:
        if not run.text:
            continue
        updated = run.text
        for key, value in values.items():
            updated = updated.replace(f"{{{{{key}}}}}", value)
        run.text = updated


def _replace_leftover_placeholders(doc: Document) -> None:
    """Replace any unresolved {{placeholder}} text with 'Missing'."""
    pattern = re.compile(r"\{\{[^{}]+\}\}")

    def _replace_text(text: str) -> str:
        return pattern.sub(MISSING, text)

    for paragraph in doc.paragraphs:
        if pattern.search(paragraph.text or ""):
            paragraph.text = _replace_text(paragraph.text)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if pattern.search(paragraph.text or ""):
                        paragraph.text = _replace_text(paragraph.text)

    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            if pattern.search(paragraph.text or ""):
                paragraph.text = _replace_text(paragraph.text)
        for paragraph in section.footer.paragraphs:
            if pattern.search(paragraph.text or ""):
                paragraph.text = _replace_text(paragraph.text)


def _replace_in_doc(doc: Document, values: Dict[str, str]) -> None:
    for paragraph in doc.paragraphs:
        _replace_in_runs(paragraph.runs, values)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _replace_in_runs(paragraph.runs, values)

    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            _replace_in_runs(paragraph.runs, values)
        for paragraph in section.footer.paragraphs:
            _replace_in_runs(paragraph.runs, values)


def _load_record(data_file: Path, index: int) -> Dict[str, str]:
    raw = json.loads(data_file.read_text(encoding="utf-8"))

    if isinstance(raw, dict) and isinstance(raw.get("results"), list):
        raw = raw["results"]

    if isinstance(raw, list):
        if not raw:
            raise ValueError("JSON data file is an empty list.")
        if index < 0 or index >= len(raw):
            raise IndexError(
                f"index {index} is out of range for list of size {len(raw)}"
            )
        record = raw[index]
    elif isinstance(raw, dict):
        record = raw
    else:
        raise ValueError("JSON data must be an object or a list of objects.")

    if not isinstance(record, dict):
        raise ValueError("Selected JSON record must be an object.")

    return _to_template_values(record)


def fill_docx_template(template_path: Path, data_path: Path, output_path: Path, index: int) -> None:
    values = _load_record(data_path, index)
    doc = Document(str(template_path))
    _replace_in_doc(doc, values)
    _replace_leftover_placeholders(doc)
    doc.save(str(output_path))


def fill_docx_template_from_detector_result(
    template_path: Path,
    detector_result: Dict[str, Any],
    output_path: Path,
) -> None:
    """Populate a DOCX template from detector output dict (UI upload response shape)."""
    if not isinstance(detector_result, dict):
        raise ValueError("detector_result must be a JSON object/dict.")

    record: Dict[str, Any] = detector_result
    if isinstance(detector_result.get("results"), list):
        if not detector_result["results"]:
            raise ValueError("detector_result['results'] is empty.")
        first = detector_result["results"][0]
        if not isinstance(first, dict):
            raise ValueError("detector_result['results'][0] must be an object.")
        record = first

    values = _to_template_values(record)
    doc = Document(str(template_path))
    _replace_in_doc(doc, values)
    _replace_leftover_placeholders(doc)
    doc.save(str(output_path))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fill DOCX template placeholders with detector JSON fields"
    )
    parser.add_argument("--template", required=True, help="Input .docx template path")
    parser.add_argument("--data", required=True, help="JSON file path with detector data")
    parser.add_argument("--output", required=True, help="Output .docx path")
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="Record index when JSON file contains a list (default: 0)",
    )

    args = parser.parse_args()

    template_path = Path(args.template)
    data_path = Path(args.data)
    output_path = Path(args.output)

    if template_path.suffix.lower() != ".docx":
        raise ValueError("Template must be a .docx file.")

    fill_docx_template(template_path, data_path, output_path, args.index)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
