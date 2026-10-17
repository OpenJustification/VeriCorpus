from pathlib import Path
from vericorpus.config import Settings
from vericorpus.pipeline import prepare

manifest = prepare(
    Path("paper.pdf"),
    Path("vericorpus_output"),
    Settings(
        use_tesseract=True,
        use_paddleocr=False,
        use_docling=False,
        use_glmocr=False,
        use_olmocr=False,
        offline=True,
    ),
)
print(manifest["reproducibility_grade"])
