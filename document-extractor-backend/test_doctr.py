import truststore
truststore.inject_into_ssl()

from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

print("Loading model...")
model = ocr_predictor(pretrained=True)

print("Loading PDF...")
doc = DocumentFile.from_pdf("uploads/ABB_Report.pdf")  # Change path if needed

print("Running OCR...")
result = model(doc)

print(result.export())