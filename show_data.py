import pandas as pd
import pickle

with open(r'C:\Users\derri\.openclaw\workspace\excel_data.pkl', 'rb') as f:
    data = pickle.load(f)

# Save each sheet to CSV
for sheet, df in data['sheets'].items():
    csv_name = sheet.replace(" ", "_")
    csv_path = rf'C:\Users\derri\.openclaw\workspace\{csv_name}.csv'
    df.to_csv(csv_path, index=False)
    print(f'Saved: {csv_path}')

print()
print('=== PROJECT METADATA ===')
for k, v in data['metadata'].items():
    print(f'{k}: {v}')

print()
print('=== SAMPLE DATA FROM Financial_Status ===')
df = data['sheets']['Financial Status']
print(df[['Item_Code', 'Item_Name', 'Tender', 'Budget_1st', 'Committed_Value', 'Cost']].head(20).to_string(index=False))
