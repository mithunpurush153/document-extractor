from paddleocr import TableRecognitionPipelineV2

pipeline = TableRecognitionPipelineV2(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    device="cpu",
)

output = pipeline.predict("ASTM A 276.PDF")
pipeline = TableRecognitionPipelineV2(
    use doc orientation_classify=False,
    use doc unwarping=False,
    device="cpu",
for result in output:
  result.print()
  result.save_to_json("./paddle_table_output")
  result.save_to_html("./paddle_table_output")

print("DONE")

from paddleocr import TableRecognitionPipelineV2)

for result in output:
    result.print()
    result.save_to_json("./paddle_table_output")
    result.save_to_html("./paddle_table_output")

print("DONE")
for result in output:
    result.print()
    result.save_to_json("./paddle_table_output")
    result.save_to_html("./paddle_table_output")
from paddleocr import TableRecognitionPipelineV2

