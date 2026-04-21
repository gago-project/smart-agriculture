import os
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GAGO_CLOUD_ROOT = PROJECT_ROOT.parent.parent

source = Path(os.getenv("SOIL_EXCEL_SOURCE") or GAGO_CLOUD_ROOT / "doc/0414/土壤墒情仪数据(2).xlsx")
output = Path(os.getenv("SOIL_EXCEL_PREVIEW_OUTPUT") or PROJECT_ROOT / "docs/architecture/soil-excel-preview.csv")

df = pd.read_excel(source).head(50)
output.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output, index=False)
print(f'exported {output}')
