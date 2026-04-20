from pathlib import Path
import pandas as pd

source = Path('/Users/mac/Desktop/gago-cloud/doc/0414/土壤墒情仪数据(2).xlsx')
output = Path('/Users/mac/Desktop/gago-cloud/code/smart-agriculture/docs/architecture/soil-excel-preview.csv')

df = pd.read_excel(source).head(50)
output.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output, index=False)
print(f'exported {output}')
