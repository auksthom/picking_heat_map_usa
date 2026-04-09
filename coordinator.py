import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# 1. LOAD THE VISUAL LAYOUT
# This reads your Excel exactly as it looks. 
# Make sure to install openpyxl first: pip install openpyxl
layout_file = 'Untitled spreadsheet (1).xlsx'
df_layout = pd.read_excel(layout_file, header=None)

# 2. LOAD YOUR DATA
df_stock = pd.read_csv('stock_report.csv') 
df_caps = pd.read_csv('warehouse_capacity.csv') 

# Merge stock and capacity
df_data = pd.merge(df_caps, df_stock, on='Bay_Name', how='left').fillna(0)
df_data['Util_%'] = (df_data['Used_m3'] / df_data['Capacity_m3']) * 100

# Create a quick dictionary for fast lookup: { 'WS-E-1': 85.0, ... }
util_map = pd.Series(df_data['Util_%'].values, index=df_data['Bay_Name']).to_dict()

# 3. BUILD THE MAP MATRICES
# We create two grids with the exact same shape as your Excel file
color_grid = df_layout.copy()
label_grid = df_layout.copy()

for r in range(len(df_layout)):
    for c in range(len(df_layout.columns)):
        bay_name = str(df_layout.iloc[r, c]).strip()
        
        if pd.notna(df_layout.iloc[r, c]) and bay_name != "nan":
            # If the bay name in Excel matches our data, put the % in the color grid
            color_grid.iloc[r, c] = util_map.get(bay_name, 0)
            label_grid.iloc[r, c] = bay_name # Keep the name for the label
        else:
            color_grid.iloc[r, c] = None # Empty space
            label_grid.iloc[r, c] = ""

# Convert color_grid to numbers so the heatmap can read it
color_grid = color_grid.apply(pd.to_numeric, errors='coerce')

# 4. DRAW THE BIRD'S EYE VIEW
plt.figure(figsize=(25, 15))

sns.heatmap(
    color_grid, 
    annot=label_grid.values, 
    fmt="", 
    cmap="RdYlGn_r", 
    linewidths=0.5, 
    linecolor='#dddddd',
    cbar_kws={'label': '% Capacity Used'},
    vmin=0, vmax=100
)

# Clean up the look
plt.title("WAREHOUSE LIVE MAP (EXACT EXCEL LAYOUT)", fontsize=30, pad=30)
plt.axis('off') # Hides the Excel row/column numbers
plt.gca().set_facecolor('#fdfdfd') # Light background for empty areas

plt.tight_layout()
plt.show()