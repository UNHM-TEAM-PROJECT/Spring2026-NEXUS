"""Minimal DOCX template updater used by api_routes.

Replaces placeholders like {{field_name}} in paragraphs/tables/headers/footers.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict

from docx import Document


MISSING = "Missing"


def _clean(value: Any) -> str:
    if value is None:
        return MISSING
    if isinstance(value, (dict, list, tuple, set)):
        return MISSING
    text = str(value).strip()
    return text if text else MISSING


def _get(data: Dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _to_template_values(record: Dict[str, Any]) -> Dict[str, str]:
    """Accept either already-flat template keys or nested detector payload."""
    values = {
        "filename": _clean(record.get("filename")),
        "instructor_name": _clean(record.get("instructor_name")),
        "instructor_title": _clean(record.get("instructor_title")),
        "instructor_department": _clean(record.get("instructor_department")),
        "email": _clean(record.get("email")),
        "preferred_contact_method": _clean(record.get("preferred_contact_method")),
        "response_time": _clean(record.get("response_time")),
        "office_address": _clean(record.get("office_address")),
        "office_phone": _clean(record.get("office_phone")),
        "office_hours": _clean(record.get("office_hours")),
        "modality": _clean(record.get("modality")),
        "class_location": _clean(record.get("class_location")),
        "assignment_types_title": _clean(record.get("assignment_types_title")),
        "assignment_delivery": _clean(record.get("assignment_delivery")),
        "deadline_expectations_title": _clean(record.get("deadline_expectations_title")),
        "SLOs": _clean(record.get("SLOs")),
        "credit_hour": _clean(record.get("credit_hour")),
        "workload": _clean(record.get("workload")),
        "grading_process": _clean(record.get("grading_process")),
        "final_grade_scale": _clean(record.get("final_grade_scale")),
    }

    # If flat values are missing, attempt nested detector keys.
    fallback = {
        "instructor_name": _clean(_get(record, "instructor", "name")),
        "instructor_title": _clean(_get(record, "instructor", "title")),
        "instructor_department": _clean(_get(record, "instructor", "department")),
        "email": _clean(_get(record, "email_information", "email")),
        "preferred_contact_method": _clean(_get(record, "preferred_information", "preferred")),
        "response_time": _clean(_get(record, "response_time", "content")),
        "office_address": _clean(_get(record, "office_information", "location")),
        "office_phone": _clean(_get(record, "office_information", "phone")),
        "office_hours": _clean(_get(record, "office_information", "hours")),
        "modality": _clean(record.get("course_delivery")),
        "class_location": _clean(_get(record, "class_location", "content")),
        "assignment_types_title": _clean(_get(record, "assignment_types", "content")),
        "assignment_delivery": _clean(_get(record, "assignment_delivery", "content")),
        "deadline_expectations_title": _clean(_get(record, "late_information", "late")),
        "SLOs": _clean(record.get("slo_content") if record.get("has_slos") else None),
        "credit_hour": _clean(_get(record, "credit_hours", "hours")),
        "workload": _clean(_get(record, "workload_information", "description")),
        "grading_process": _clean(_get(record, "grading_process", "content")),
        "final_grade_scale": _clean(_get(record, "grading_scale", "content")),
    }

    for k, v in fallback.items():
        if values.get(k) == MISSING and v != MISSING:
            values[k] = v

    return values


def _replace_runs(runs, values: Dict[str, str]) -> None:
    for run in runs:
        if not run.text:
            continue
        t = run.text
        for key, value in values.items():
            t = t.replace("{{" + key + "}}", value)
        run.text = t


def _replace_all(doc: Document, values: Dict[str, str]) -> None:
    for p in doc.paragraphs:
        _replace_runs(p.runs, values)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_runs(p.runs, values)

    for section in doc.sections:
        for p in section.header.paragraphs:
            _replace_runs(p.runs, values)
        for p in section.footer.paragraphs:
            _replace_runs(p.runs, values)


def _replace_unresolved(doc: Document) -> None:
    pattern = re.compile(r"\{\{[^{}]+\}\}")

    def fix(text: str) -> str:
        return pattern.sub(MISSING, text or "")

    for p in doc.paragraphs:
        if pattern.search(p.text or ""):
            p.text = fix(p.text)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if pattern.search(p.text or ""):
                        p.text = fix(p.text)

    for section in doc.sections:
        for p in section.header.paragraphs:
            if pattern.search(p.text or ""):
                p.text = fix(p.text)
        for p in section.footer.paragraphs:
            if pattern.search(p.text or ""):
                p.text = fix(p.text)


def fill_docx_template_from_detector_result(
    template_path: Path,
    detector_result: Dict[str, Any],
    output_path: Path,
) -> None:
    if not isinstance(detector_result, dict):
        raise ValueError("detector_result must be a dict")

    record = detector_result
    if isinstance(record.get("results"), list) and record["results"]:
        record = record["results"][0]

    values = _to_template_values(record)
    doc = Document(str(template_path))
    _replace_all(doc, values)
    _replace_unresolved(doc)
    doc.save(str(output_path))


def fill_docx_template(template_path: Path, data_path: Path, output_path: Path, index: int) -> None:
    """Small file-based helper kept for compatibility."""
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("results"), list):
        raw = raw["results"]
    if isinstance(raw, list):
        if index < 0 or index >= len(raw):
            raise IndexError("index out of range")
        record = raw[index]
    elif isinstance(raw, dict):
        record = raw
    else:
        raise ValueError("JSON must be object or list")

    fill_docx_template_from_detector_result(template_path, record, output_path)
