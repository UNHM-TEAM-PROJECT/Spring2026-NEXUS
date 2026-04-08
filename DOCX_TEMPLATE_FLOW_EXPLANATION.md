# DOCX Template Updater and App Flow (Simple Explanation)

## What this document covers
- Simple explanation of each function in docx_template_updater.py
- Control flow from index.html -> api_routes.py -> docx_template_updater.py -> download

## Function-by-function explanation (in control-flow order)

### fill_docx_template_from_detector_result(template_path, detector_result, output_path)
This is the main entry point used by the backend route.
It takes detector data, converts it into template values, replaces placeholders in the DOCX, fills unresolved placeholders with Missing, and saves the file.

### _to_template_values(record)
This prepares a clean, flat dictionary that matches template placeholders.
It reads direct keys first, then fallback nested detector keys, removes repeated headers, formats long text, and normalizes empty values.

### _clean(value)
This makes sure every value is safe to write into the template.
If a value is empty, None, or a complex type, it returns Missing; otherwise it returns trimmed text.

### _get(data, *keys)
This safely reads nested keys without throwing errors.
If any intermediate key is missing or not a dictionary, it returns None.

### _strip_redundant_header(value, aliases)
This removes repeated section titles from extracted text.
It prevents duplication when the template already has a header and detector text also starts with that same header.

### _format_structured_text(value)
This cleans messy detector text into readable content.
It splits by separators (like bullets, semicolons, numbered items), removes duplicates, and returns compact text or bullet-style lines.

### _replace_all(doc, values)
This applies placeholder replacement across the full document.
It processes normal paragraphs, table cells, headers, and footers so replacements happen everywhere.

### _replace_placeholders_in_paragraph(paragraph, values)
This finds tokens such as {{field_name}} in one paragraph.
For each token, it looks up a value and replaces the exact text span.

### _replace_span_in_runs(runs, start, end, replacement)
DOCX paragraphs are split into multiple runs, so direct string replacement is not always enough.
This helper replaces text by character range across runs while preserving surrounding content.

### _replace_unresolved(doc)
After known fields are replaced, this catches any placeholders that are still unresolved.
It replaces all remaining {{...}} tokens with Missing so no raw placeholders remain in output.

### fill_docx_template(template_path, data_path, output_path, index)
This is a compatibility helper for file-based workflows.
It reads JSON from disk, selects a record by index if needed, and then calls the main fill function.

## End-to-end control flow in simple English

1. User uploads a file in index.html.
The browser sends the file to the backend /upload route.

2. api_routes.py receives the upload and runs detectors.
The backend returns detected fields and missing fields to the frontend.

3. Frontend shows results and asks user to fill missing values.
When user submits, frontend sends those values to /submit_missing_fields.

4. api_routes.py combines detector output and user input using _build_template_payload.
This creates one final payload with all template keys.

5. api_routes.py calls fill_docx_template_from_detector_result in docx_template_updater.py.
That function prepares values, replaces placeholders in DOCX, handles unresolved fields, and saves a generated file.

6. api_routes.py returns the generated DOCX as a download response.
index.html receives the file as a blob and triggers browser download for the user.

## Data communication summary
- index.html to api_routes.py:
  - Upload request to /upload (file)
  - Submit request to /submit_missing_fields (user_inputs and filename)

- api_routes.py to docx_template_updater.py:
  - Calls fill_docx_template_from_detector_result with template path, merged payload, and temp output path

- docx_template_updater.py back to api_routes.py:
  - Saves completed DOCX to output path

- api_routes.py back to index.html:
  - Sends DOCX bytes as attachment response for download
