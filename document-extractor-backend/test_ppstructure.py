from pathlib import Path
from paddleocr import PPStructureV3

PDF_PATH = Path(r"DELTA CHEMICAL-A182.PDF")
OUTPUT_DIR = Path("ppstructure_output")
OUTPUT_DIR.mkdir(exist_ok=True)

pipeline = PPStructureV3(
    device="cpu",
    enable_mkldnn=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    use_seal_recognition=False,
    use_formula_recognition=False,
    use_chart_recognition=False,
    use_region_detection=False,

    layout_detection_model_dir=r"C:\Users\Mithun.Purushothaman\.paddlex\official_models\PP-DocLayout_plus-L",
    table_classification_model_dir=r"C:\Users\Mithun.Purushothaman\.paddlex\official_models\PP-LCNet_x1_0_table_cls",
    text_detection_model_dir=r"C:\Users\Mithun.Purushothaman\.paddlex\official_models\PP-OCRv5_server_det",
    text_recognition_model_dir=r"C:\Users\Mithun.Purushothaman\.paddlex\official_models\PP-OCRv5_server_rec",
    wired_table_structure_recognition_model_dir=r"C:\Users\Mithun.Purushothaman\.paddlex\official_models\SLANeXt_wired",
    wired_table_cells_detection_model_dir=r"C:\Users\Mithun.Purushothaman\.paddlex\official_models\RT-DETR-L_wired_table_cell_det",
    wireless_table_cells_detection_model_dir=r"C:\Users\Mithun.Purushothaman\.paddlex\official_models\RT-DETR-L_wireless_table_cell_det",
)

print("Running PP-StructureV3...")

for result in pipeline.predict(str(PDF_PATH)):
    result.print()
    result.save_to_json(save_path=str(OUTPUT_DIR))
    result.save_to_markdown(save_path=str(OUTPUT_DIR))

print("DONE")