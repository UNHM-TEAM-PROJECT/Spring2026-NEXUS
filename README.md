# Syllabus Field Detector

## Project Overview

The **Syllabus Field Detector** is a web application that automatically analyzes academic syllabi to extract and validate 19 different course information fields. Built for university administrators, department chairs, and academic compliance teams, the system helps ensure syllabi meet institutional standards and accreditation requirements. When required information is missing, the system prompts the user to provide it, and generates a completed syllabus template with the provided information as a downloadable document.

**Who It Serves:**
- **Academic Departments** — Verify syllabus compliance with accreditation standards (e.g., presence of Student Learning Outcomes)
- **Instructors** — Quickly check if their syllabi contain all required information
- **Institutional Research** — Extract standardized course data for databases and reporting
- **Quality Assurance Teams** — Batch-process syllabi to identify missing or incomplete fields

**Key Features:**
- Detects 19 fields including SLOs, instructor info, grading policies, and course modality
- Uses lightweight pattern matching for fast, explainable results with confidence scores
- Provides instant, explainable results with confidence scores
- Supports batch processing via ZIP uploads or folder selection
- Achieves **92.4% F1 Score** overall across all detectors (tested on 310 files)
- Guides users through filling all missing fields via an interactive UI form and generates a downloadable updated DOCX template

---

## File and Folder Organization

```
Fall2025-Team-Alpha/
│
├── main.py                     # Application entry point - starts Flask server
├── config.py                   # Server configuration (host, port, logging)
├── api_routes.py               # HTTP request handlers, orchestrates all detectors
├── document_processing.py      # PDF/DOCX text extraction engine
├── docx_template_updater.py    # Fills DOCX template placeholders from detector/user inputs
├── template_generator.py       # Legacy text template helper
│
├── detectors/                  # 19 specialized field detection modules
│   ├── __init__.py
│   ├── slo_detector.py                  # Student Learning Outcomes
│   ├── online_detection.py              # Course modality (Online/Hybrid/In-Person)
│   ├── instructor_detector.py           # Instructor name, title, department
│   ├── email_detector.py                # Instructor email address
│   ├── office_information_detection.py  # Office location, hours, phone
│   ├── credit_hours_detection.py        # Credit hours
│   ├── workload_detection.py            # Expected study hours
│   ├── grading_scale_detection.py       # Letter grade scale (A-F)
│   ├── grading_process_detection.py     # Grading procedures/policies
│   ├── assignment_types_detection.py    # Assignment categories
│   ├── assignment_delivery_detection.py # Submission platforms (Canvas, etc.)
│   ├── late_missing_work_detector.py    # Late work policies
│   ├── response_time_detector.py        # Email response time commitments
│   ├── class_location_detector.py       # Physical class locations
│   └── preferred_contact_detector.py    # Preferred contact method
│
├── templates/
│   └── index.html              # Web UI with drag-and-drop file upload
├── updated_syllabus_detector_common_template.docx  # Active DOCX template
│
├── static/
│   ├── architecture.png        # System architecture diagram
│   ├── logo3.png              # Application logo
│   └── favicon.ico            # Browser favicon
│
├── Team_Alpha_Fall_2025_syllabus/  # Evaluation syllabi set A
├── Team_Nexus_Spring_2026_syllabus/ # Evaluation syllabi set B
├── Team_Alpha_Fall_2025.json        # Ground truth for set A
├── Team_Nexus_Spring_2026.json      # Ground truth for set B
├── test_runner.py              # Automated testing framework
├── test_results.json           # Test metrics output
├── new_test_results.json       # Additional test metrics output
│
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── DockerREADME.md             # Docker deployment guide
├── DEVELOPER_GUIDE.md          # How to add new detectors
└── README.md                   # This file
```

---

## System Architecture

![System Architecture](static/architecture.png)

### High-Level Design

The application follows a modular pipeline architecture:

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌────────────┐
│   Web UI    │────▶│  Flask Server    │────▶│   Document      │────▶│  Detector  │
│ (index.html)│     │  (api_routes.py) │     │   Processing    │     │   Engine   │
└─────────────┘     └──────────────────┘     └─────────────────┘     └────────────┘
                                                     │                      │
                                                     ▼                      ▼
                                              ┌─────────────┐      ┌──────────────┐
                                              │ PDF/DOCX    │      │ 19 Detectors │
                                              │ Extraction  │      │ (parallel)   │
                                              └─────────────┘      └──────────────┘
```

### Key Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **Entry Point** | `main.py` | Starts Flask server on port 8001 |
| **Configuration** | `config.py` | Logging level, host, port, debug settings |
| **API Layer** | `api_routes.py` | Handles uploads, orchestrates detectors, returns JSON |
| **Text Extraction** | `document_processing.py` | Extracts text from PDF (pdfplumber) and DOCX (python-docx) |
| **Detectors** | `detectors/*.py` | 19 independent modules, each detecting one field |
| **Frontend** | `templates/index.html` | Drag-and-drop interface, displays results |
| **Template Generator** | `docx_template_updater.py` | Fills `updated_syllabus_detector_common_template.docx` using detector output + user inputs |

### Data Flow

1. **Upload** — User uploads PDF/DOCX/ZIP via web interface
2. **Extract** — `document_processing.py` extracts text and tables from document
3. **Detect** — Text is passed to all 19 detectors in parallel
4. **Respond** — Each detector returns `{field_name, found, content, confidence}`
5. **Display** — Results rendered in UI with FOUND/MISSING status and evidence
6. **Prompt** — If fields are missing, frontend displays an input form for all missing fields; user submits values, backend generates and returns a completed template as a downloadable DOCX file

### Detector Pattern

Each detector is an independent module following this interface:

```python
class XxxDetector:
    def detect(self, text: str) -> dict:
        return {
            'field_name': 'xxx',
            'found': True/False,
            'content': 'extracted value' or 'Missing',
            'confidence': 0.0-1.0  # optional
        }
```

---

## Data Model

This application does not use a database. All data is processed in-memory and results are returned directly to the user.

### Ground Truth Schema (for testing)

The `ground_truth.json` file stores expected values for test syllabi:

```json
{
  "file_name": "Example_Syllabus.pdf",
  "modality": "Online",
  "SLOs": true,
  "email": "professor@unh.edu",
  "credit_hour": "3",
  "workload": "9 hours per week",
  "instructor_name": "Dr. Jane Smith",
  "instructor_title": "Associate Professor",
  "instructor_department": "Computer Science",
  "office_address": "Kingsbury Hall N229",
  "office_hours": "MWF 2-4pm",
  "office_phone": "(603) 862-1234",
  "preferred_contact_method": "Email",
  "assignment_types_title": true,
  "deadline_expectations_title": true,
  "assignment_delivery": "Canvas",
  "final_grade_scale": true,
  "response_time": "24 hours",
  "class_location": "Room 204",
  "grading_process": true
}
```

---

## Installation and Deployment Instructions

### Local Development Setup

**Prerequisites:**
- Python 3.8 or higher
- pip (Python package manager)

**Step-by-step:**

```bash
# 1. Clone the repository
git clone https://github.com/UNHM-TEAM-PROJECT/Fall2025-Team-Alpha.git
cd Fall2025-Team-Alpha

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python main.py

# 5. Open browser to http://localhost:8001
```

**Dependencies:**
- `flask==3.0.3` — Web framework
- `pdfplumber==0.11.4` — PDF text extraction
- `python-docx==1.1.0` — Word document processing
- `python-dotenv==1.0.1` — Environment configuration
- `lxml>=4.9.0` — XML parsing for DOCX

### Production Deployment (Docker on VM)

**Prerequisites:**
- SSH access to the VM (whitemount.sr.unh.edu)
- Docker installed on VM

**Step-by-step:**

```bash
# 1. SSH into the VM
ssh username@whitemount.sr.unh.edu

# 2. Clone the repository
git clone git@github.com:UNHM-TEAM-PROJECT/Spring2026-NEXUS.git
cd Spring2026-NEXUS

# 3. Build Docker image
docker build -t syllabus-checker .

# 4. Run container
docker run -p 8001:8001 syllabus-checker

# OR run in background (persists after logout):
nohup docker run -p 8001:8001 syllabus-checker > runtime.log 2>&1 &

# 5. Access at https://whitemount-t1.sr.unh.edu
```

**Useful Docker Commands:**
```bash
docker ps                    # List running containers
docker stop <container_id>   # Stop a container
docker logs <container_id>   # View container logs
docker images                # List built images
```

See `DockerREADME.md` for detailed deployment instructions including SSH key setup for 2FA.

### Configuration

| Setting | Location | Default | Description |
|---------|----------|---------|-------------|
| Host | `config.py` | `0.0.0.0` | Server bind address |
| Port | `config.py` | `8001` | Server port |
| Debug | `config.py` | `True` | Flask debug mode |
| Log Level | `config.py` | `INFO` | Logging verbosity |

**No API keys or external services are required for the current workflow.** The application runs offline using rule-based detectors.

---

## Usage Guide

### Web Interface

1. **Open the application** at `http://localhost:8001` (local) or `https://whitemount-t1.sr.unh.edu` (production)

2. **Upload a syllabus:**
   - Drag and drop a file onto the upload area, OR
   - Click to browse and select a file
   - Supported formats: PDF, DOCX, ZIP (for batch)

3. **View results:**
   - **SLO Status** — PASS (green) or FAIL (red) with preview of detected SLOs
   - **Modality Badge** — Online, In-Person, or Hybrid with confidence score
   - **Field Cards** — Each detected field shows FOUND/MISSING status with extracted content

4. **Generate updated template:**
   - Fill all missing fields shown in the UI form
   - Click **Generate & Download DOCX** to populate placeholders and download the updated syllabus template

5. **Batch processing:**
   - Upload a ZIP file containing multiple syllabi
   - Results are displayed for each file in the archive

### Running Tests

```bash
# Run automated tests against ground truth
python test_runner.py

# Results saved to test_results.json
```

### Current Test Results (310 total files)
| Field | Accuracy | Precision | Recall | F1 Score |
|-------|----------|-----------|--------|----------|
| modality | 83.2% | 89.1% | 92.3% | 90.7% |
| SLOs | 98.1% | 98.7% | 94.9% | 96.7% |
| email | 94.8% | 100.0% | 94.2% | 97.0% |
| credit_hour | 94.2% | 97.4% | 91.9% | 94.6% |
| workload | 94.5% | 91.9% | 92.9% | 92.4% |
| instructor_name | 90.3% | 100.0% | 90.0% | 94.7% |
| instructor_title | 93.9% | 89.2% | 90.1% | 89.7% |
| instructor_department | 94.5% | 87.5% | 90.0% | 88.7% |
| office_address | 90.6% | 92.3% | 86.7% | 89.4% |
| office_hours | 87.4% | 96.1% | 85.9% | 90.6% |
| office_phone | 90.6% | 90.9% | 84.3% | 87.4% |
| preferred_contact_method | 94.5% | 86.8% | 69.2% | 75.1% |
| assignment_types_title | 92.3% | 90.4% | 95.8% | 93.0% |
| deadline_expectations_title | 91.6% | 94.4% | 92.1% | 93.2% |
| assignment_delivery | 90.6% | 96.4% | 90.3% | 93.3% |
| final_grade_scale | 91.9% | 94.1% | 89.0% | 91.4% |
| response_time | 98.4% | 92.7% | 96.8% | 94.4% |
| class_location | 87.4% | 91.5% | 89.6% | 90.5% |
| grading_process | 95.2% | 98.2% | 94.8% | 96.5% |
| **OVERALL** | **92.3%** | **94.3%** | **90.6%** | **92.4%** |
 
## Next Steps and Future Work

### Technical Debt

1. **Scanned PDF Support** — Current system cannot extract text from image-based/scanned PDFs. Consider integrating OCR (e.g., Tesseract) for these cases.

2. **Edge Case Handling** — Some syllabi use non-standard formatting that causes detection failures. The detectors could be improved to handle more variations.

3. **Test Coverage** — Unit tests exist for some detectors but not all. Expanding test coverage would improve reliability.

### Recommended Improvements for Future Teams

1. **Solve Edge Cases** — Analyze false negatives in `test_results.json` to identify common failure patterns and add handling for them.

2. **Add New Detectors** — Potential fields to add:
   - Textbook/required materials
   - Course schedule/calendar
   - Attendance policy
   - Academic integrity policy

3. **UI Enhancements:**
   - Export results to CSV/JSON
   - Side-by-side comparison of multiple syllabi
   - Highlight detected sections in original document

4. **Performance Optimization** — For large batch uploads, consider parallel processing of files.

### Known Issues

1. **Ground Truth Alignment** — Ensure filenames in test JSON exactly match dataset filenames before running `test_runner.py`.

2. **Image-Based PDFs** — Pages 14-17 in some test PDFs are image-based and cannot be processed (warning logged but no text extracted)

3. **Low Character Count Warning** — Some PDFs trigger "possible scanned/image-based PDF" warnings due to low text density

---

## Tech Stack

- **Backend:** Python 3.8+, Flask 3.0.3
- **PDF Processing:** pdfplumber 0.11.4
- **DOCX Processing:** python-docx 1.1.0
- **Deployment:** Docker

---

## Documentation Links

- **Developer Guide:** See `DEVELOPER_GUIDE.md` for adding new detectors
- **Docker Guide:** See `DockerREADME.md` for VM deployment details
- **Test Results Guide:** See `test_results_guide.md` for understanding metrics

---

## Contributors

**Fall 2025 Team Alpha** — University of New Hampshire
**Spring 2026 Team Nexus** - Univeristy of New Hampshire
