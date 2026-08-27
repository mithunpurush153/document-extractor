# Document Extractor

A full-stack PDF document processing application for OCR, structured table extraction, stamp and signature detection, JSON generation, and ASTM chemical composition validation.

## Overview

Document Extractor is a full-stack document-processing application consisting of a Python/FastAPI backend and a React/Vite frontend.

The application processes scanned and digital PDF documents and converts their contents into structured, machine-readable data. The current production OCR pipeline uses docTR, while table reconstruction, stamp detection, signature detection, JSON output, and deterministic chemical validation are implemented as separate processing components.

The project also includes evaluation work on alternative OCR and document-processing technologies, including EasyOCR, Sarvam OCR, and PaddleOCR PP-StructureV3. These experiments were performed separately from the active production OCR pipeline.

## Main Features

- PDF upload and processing
- PDF page rendering using PyMuPDF
- OCR using docTR
- OCR bounding-box processing
- Structured table reconstruction
- Table extraction into JSON
- Stamp detection
- Signature detection
- Signature and stamp crop generation
- Frontend display of extracted tables
- Frontend display of AI detections
- JSON result download
- ASTM chemical composition validation
- Element-level PASS / FAIL / NOT_REPORTED results
- Runtime validation using uploaded supplier documents
- Separate reference-data support for ASTM standards

## System Architecture

```text
                         User
                           |
                           v
                 React / Vite Frontend
                           |
                           | HTTP
                           v
                    FastAPI Backend
                           |
                           v
                    PDF Upload
                           |
                           v
                  PyMuPDF PDF Rendering
                           |
                           v
                    Page Images
                           |
              +------------+------------+
              |                         |
              v                         v
          docTR OCR              Stamp / Signature
              |                    Detection
              v                         |
       OCR Bounding Boxes                |
              |                         v
              v                   Detection Crops
       Table Reconstruction
              |
              v
       tables_by_page JSON
              |
              v
      Chemical Validation
              |
              v
       Structured API Response
              |
              v
        React Results UI
```

## Repository Structure

```text
document-extractor/
│
├── document-extractor-backend/
│   ├── main.py
│   ├── routes.py
│   ├── schemas.py
│   ├── config.py
│   ├── utils.py
│   ├── chemical_compare_routes.py
│   ├── requirements.txt
│   │
│   ├── services/
│   │   ├── ocr_service.py
│   │   ├── pdf_service.py
│   │   ├── table_extractor.py
│   │   ├── stamp_detector.py
│   │   ├── signature_detector.py
│   │   ├── chemical_validator.py
│   │   ├── dynamic_chemical_validator.py
│   │   └── reference_data/
│   │       └── a194.json
│   │
│   ├── models/
│   │   ├── stamp_model/
│   │   └── signature_model/
│   │
│   ├── test_doctr.py
│   ├── test_chemical_integration.py
│   ├── test_ppstructure.py
│   └── test_table_paddle.py
│
├── document-extractor-frontend/
│   ├── src/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── .env.example
│
├── Documentation/
│   ├── Document_Extractor_Documentation.docx
│   └── Output_screenshots/
│
├── README.md
└── .gitignore
```

## Backend

### Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| API Framework | FastAPI |
| Server | Uvicorn |
| OCR | docTR |
| PDF Processing | PyMuPDF |
| Image Processing | OpenCV / NumPy |
| Table Processing | Pandas / Python |
| Stamp Detection | Hugging Face Transformers |
| Signature Detection | Ultralytics YOLO |
| Chemical Validation | Deterministic Python logic |
| Reference Data | JSON |

### Backend Processing Flow

```text
PDF
 ↓
PyMuPDF
 ↓
RGB Page Images
 ↓
docTR OCR
 ↓
OCR Detections
 ↓
Row / Column Detection
 ↓
Table Reconstruction
 ↓
tables_by_page
 ↓
Additional Detection Services
 ↓
Chemical Validation
 ↓
FastAPI JSON Response
```

### PDF Processing

The backend renders uploaded PDF pages into RGB image arrays using PyMuPDF.

The current document-processing configuration uses approximately 300 DPI for page rendering. Controlled rotation handling is used where required for OCR processing.

### OCR

The production OCR implementation uses docTR.

The OCR service initializes the pretrained docTR predictor and reuses the predictor instead of loading the OCR model for every request.

docTR detections are converted into the bounding-box representation required by the existing table-reconstruction logic.

The active OCR models used by the project are:

- `fast_base`
- `crnn_vgg16_bn`

EasyOCR and Sarvam OCR were evaluated during development but are not the active production OCR engine.

## Table Extraction

The application reconstructs structured tables from OCR detections.

The table-processing flow includes:

```text
OCR detections
    ↓
Row grouping
    ↓
Table block detection
    ↓
Column detection
    ↓
Column assignment
    ↓
DataFrame/table construction
    ↓
tables_by_page
```

The existing `tables_by_page` JSON structure is preserved so that downstream processing and frontend rendering can consume the same table representation.

Example structure:

```json
{
  "page_1": [
    {
      "rows": 4,
      "cols": 8,
      "columns": [],
      "data": []
    }
  ]
}
```

## Stamp Detection

The application includes a stamp-detection component.

The model is stored locally under:

```text
document-extractor-backend/models/stamp_model/
```

The model is loaded locally through the Hugging Face Transformers stack.

The detector returns:

- Detection confidence
- Bounding box

The backend can generate and expose detected stamp crops.

## Signature Detection

The application includes a signature-detection component using a locally stored YOLO checkpoint.

The model is stored under:

```text
document-extractor-backend/models/signature_model/best.pt
```

The detector returns confidence and bounding-box information.

The backend creates signature image crops and exposes the generated crop paths through the API for frontend display.

The project integrates the existing trained model and does not claim ownership of the original model training.

## Chemical Validation

Chemical validation is implemented as an additive document-level feature.

It does not replace the existing OCR or table-extraction pipeline.

The workflow is:

```text
Supplier PDF
      ↓
Extracted Tables
      ↓
Identify ASTM Standard
      ↓
Identify Material Grade
      ↓
Extract Observed Chemical Composition
      ↓
Load Reference Specification
      ↓
Deterministic Comparison
      ↓
PASS / FAIL / NOT_REPORTED
```

### Validation Rules

The validator supports deterministic rule types such as:

| Rule | Logic |
|---|---|
| MAX | observed value <= maximum specification |
| MIN | observed value >= minimum specification |
| RANGE | minimum <= observed value <= maximum specification |
| NOT_REPORTED | element is not present or is handled according to reference-data rules |

### Current Reference Data

Reference data is stored under:

```text
document-extractor-backend/services/reference_data/
```

Current implemented reference data includes:

```text
ASTM A194/A194M
Grade 8M
```

represented by:

```text
a194.json
```

### Validation Components

The main validator provides functions for:

```text
identify_standard_and_grade()
extract_chemical_composition()
validate_composition()
validate_supplier_document()
```

The validation logic is deterministic Python logic rather than an ML classifier.

### Tested Validation Results

The implementation was tested against ASTM A194/A194M Grade 8M material certificates.

```text
M16 Hex Nut Certificate
8 PASS
0 FAIL
1 NOT_REPORTED

M36 Hex Nut Certificate
8 PASS
0 FAIL
1 NOT_REPORTED
```

The validator consumes the existing extracted table structure and returns an additional `chemical_validation` field without changing the original table-extraction contract.

## API

### Main Extraction Endpoint

```http
POST /extract
```

This endpoint accepts a PDF and processes:

- PDF rendering
- OCR
- Table extraction
- Stamp detection
- Signature detection
- Chemical validation when applicable

### Health Endpoint

```http
GET /health
```

### JSON Download

```http
GET /download/{job_id}
```

This endpoint downloads the extracted table JSON.

### Detection Crop

```http
GET /crops/{job_id}/{filename}
```

This endpoint serves generated stamp/signature crops.

### Swagger Documentation

During local development:

```text
http://127.0.0.1:8000/docs
```

## API Response Structure

The API returns the existing document-extraction information together with optional detection and chemical-validation information.

```json
{
  "job_id": "...",
  "filename": "...",
  "total_pages": 1,
  "tables_by_page": {},
  "detections_by_page": {
    "page_1": {
      "stamps": [],
      "signatures": []
    }
  },
  "chemical_validation": null
}
```

When chemical validation applies:

```json
{
  "chemical_validation": {
    "identified_standard": "ASTM A194/A194M",
    "identified_grade": "8M",
    "reference": "A194",
    "observed_composition": {},
    "validation_result": {
      "elements": [],
      "summary": {
        "total": 9,
        "pass": 8,
        "fail": 0,
        "not_reported": 1
      }
    },
    "error": null
  }
}
```

## Frontend

The frontend is implemented using React and Vite.

### Frontend Responsibilities

- PDF upload interface
- Upload status and loading state
- Error handling
- Display extracted table results
- Page-by-page organization
- Display AI detections
- Display stamp detections
- Display signature detections
- Display actual detection crops
- Display ASTM chemical validation
- Display validation summaries
- JSON download

### Main Frontend Components

```text
src/
├── App.jsx
├── App.css
│
├── api/
│   ├── extractorApi.js
│   └── chemicalValidationApi.js
│
├── components/
│   ├── UploadPanel.jsx
│   ├── ResultsView.jsx
│   ├── PageSection.jsx
│   ├── TableBlock.jsx
│   ├── DetectionSection.jsx
│   ├── DetectionCard.jsx
│   ├── ChemicalValidationSection.jsx
│   ├── LiveChemicalValidationPanel.jsx
│   ├── JsonViewer.jsx
│   ├── LoadingState.jsx
│   ├── ErrorState.jsx
│   ├── EmptyState.jsx
│   └── Header.jsx
│
└── main.jsx
```

### Results Interface

The frontend result screen includes:

```text
Document Summary
      ↓
Detected Tables
      ↓
AI Detections
      ↓
Stamp / Signature Crops
      ↓
Chemical Requirements
      ↓
Download JSON
```

The chemical validation section is conditional and only appears when validation data is returned by the backend.

## Local Development

### Backend

Open a terminal and navigate to:

```powershell
cd C:\document-extractor\document-extractor-backend
```

Activate the Python virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the backend:

```powershell
python -m uvicorn main:app --reload
```

The backend runs at:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### Frontend

Open a second terminal:

```powershell
cd C:\document-extractor\document-extractor-frontend
```

Install dependencies:

```powershell
npm install
```

Start the frontend:

```powershell
npm run dev
```

The frontend normally runs at:

```text
http://localhost:5173
```

The backend and frontend are intentionally run as two separate processes.

They communicate through the FastAPI HTTP API.

## Managed Windows Environment

During development on the managed office machine, PowerShell and group-policy restrictions affected some executable wrappers.

The application itself was not changed to bypass corporate security controls.

In environments where the Vite wrapper is blocked, the frontend can be started using:

```powershell
node .\node_modules\vite\bin\vite.js
```

Similarly, the backend can be started through the Python module form:

```powershell
python -m uvicorn main:app --reload
```

## Testing

The project contains test scripts for:

- docTR OCR
- chemical-validation integration
- PaddleOCR / PP-StructureV3 experimentation
- table extraction

Examples:

```text
test_doctr.py
test_chemical_integration.py
test_ppstructure.py
test_table_paddle.py
```

## PP-StructureV3 Evaluation

PP-StructureV3 was evaluated separately as an alternative document/table-processing pipeline.

The experiment was performed because difficult engineering tables were being investigated for improved document-aware extraction.

### Local Test

The PP-StructureV3 pipeline was successfully initialized locally and the required model assets were downloaded and configured.

However, the available development machine does not have an NVIDIA GPU, so CPU inference was impractically slow for the tested documents.

### Colab GPU Test

The same pipeline was tested using a Google Colab T4 GPU.

The evaluation processed:

- ASTM A276 reference PDF
- Supplier test certificate

The reference document contained the UNS S32760 chemical requirements and the supplier report contained the observed composition.

The extracted values were compared element-by-element.

Result:

```text
11 PASS
0 FAIL
```

This experiment demonstrated that PP-StructureV3 can produce structured table information suitable for downstream chemical validation for the tested documents.

It is important to note that PP-StructureV3 was evaluated as a proof of concept and was not integrated into the current production OCR backend.

## OCR / Model Evaluation History

During development, multiple OCR/document-processing approaches were evaluated.

### EasyOCR

EasyOCR was used during the original table-reconstruction implementation and served as an early OCR baseline.

### Sarvam OCR

Sarvam OCR was evaluated on difficult engineering documents and its output was compared against the existing extraction approach.

### docTR

The backend OCR pipeline was migrated from EasyOCR to docTR while preserving the existing table-extraction interface and frontend behavior.

docTR is currently the production OCR implementation.

### PaddleOCR PP-StructureV3

PP-StructureV3 was evaluated separately for document-aware layout and table extraction.

The results showed successful extraction on selected A276/S32760 documents using a T4 GPU, but local CPU inference was not practical on the available machine.

## Documentation

Detailed technical documentation is included under:

```text
Documentation/Document_Extractor_Documentation.docx
```

Supporting screenshots are stored under:

```text
Documentation/Output_screenshots/
```

The documentation describes:

- System architecture
- Backend components
- Frontend components
- OCR pipeline
- Table reconstruction
- Stamp and signature detection
- Chemical validation
- Model usage
- Testing
- PP-StructureV3 evaluation
- Current limitations
- Recommended improvements

## Repository Guidelines

The repository should contain source code, configuration, documentation, and required model assets only.

The following should not be committed:

```text
venv/
paddle_env/
node_modules/
dist/
__pycache__/
*.pyc
uploads/
outputs/
crops/
ppstructure_output/
.env
```

Generated files and temporary runtime data should remain outside version control.

## Security

Do not commit API keys, passwords, credentials, tokens, or private configuration values.

Use:

```text
.env.example
```

to document required environment variables without exposing actual secrets.

## Current Project Status

```text
PDF Processing                     ✅ Working
docTR OCR                          ✅ Working
Table Extraction                   ✅ Working
Stamp Detection                    ✅ Working
Signature Detection                ✅ Working
Signature Crop Generation          ✅ Working
JSON Output / Download             ✅ Working
React Frontend                     ✅ Working
Chemical Validation                ✅ Working
ASTM A194 Grade 8M Validation     ✅ Tested
PP-StructureV3 Evaluation          ✅ Completed as POC
```

## Current Limitations

- OCR accuracy can vary for rotated engineering documents, dense tables, and low-quality scans.
- Chemical validation depends on correct OCR and table reconstruction.
- Additional ASTM standards require corresponding reference data.
- PP-StructureV3 local CPU inference is not currently practical on the available development machine.
- Model downloading can be affected by managed corporate-network restrictions.
- Generated uploads, crops, and outputs should remain runtime artifacts rather than source-controlled files.

## Recommended Future Improvements

- Build a repeatable benchmark set using difficult engineering PDFs.
- Compare OCR/document-processing models using measurable metrics.
- Measure table detection recall and cell-level value accuracy.
- Measure end-to-end latency and memory consumption.
- Extend ASTM reference data as business requirements are confirmed.
- Add automated integration tests for extraction and validation scenarios.
- Pin dependency and model versions for reproducibility.
- Use an approved artifact/model provisioning strategy for managed environments.

## Development Principle

The production system is intentionally separated into document extraction and business validation layers.

```text
Document Extraction
        ↓
Structured Data
        ↓
Business Validation
        ↓
Results
```

This separation allows the OCR/table pipeline to evolve independently from domain-specific validation rules.

## License / Internal Use

This project is intended for internal development and project evaluation. Refer to the organization's applicable policies for redistribution, model usage, and document handling.