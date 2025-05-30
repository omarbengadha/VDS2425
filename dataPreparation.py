import pandas as pd
import os

DATA_DIR = "VDS2425_Madrid"

pollutants = ['NO_2', 'PM10', 'O_3', 'CO', 'SO_2']

annual_data = []

for file in sorted(os.listdir(DATA_DIR)):
    if not file.endswith('.csv') or file == 'stations.csv':
        continue

    year = int(file.split('_')[1].split('.')[0])
    file_path = os.path.join(DATA_DIR, file)
    df = pd.read_csv(file_path, low_memory=False)

    if 'date' not in df.columns:
        continue

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['year'] = df['date'].dt.year
    df = df[df['year'] == year]

    valid_cols = [col for col in pollutants if col in df.columns]
    if not valid_cols or df[valid_cols].empty:
        continue

    avg_row = df[valid_cols].mean(numeric_only=True)
    avg_row['year'] = year
    annual_data.append(avg_row)

df_yearly = pd.DataFrame(annual_data).sort_values(
    'year').reset_index(drop=True)
df_yearly.to_csv("annual_pollution_2001_2018.csv", index=False)
