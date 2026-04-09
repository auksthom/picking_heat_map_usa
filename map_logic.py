import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import re
from datetime import datetime
import numpy as np

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="FC Map")

# --- 2. DATA SOURCE ---
SHEET_ID = "189xHc5ijA8Dd40agyp98Qo-p4P6xRzBNLilCOhyERQc"
STOCK_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=stock_report"
CAPS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=warehouse_capacity"

# --- 3. REFRESH LOGIC (8 AM & 8 PM) ---
def get_time_slot():
    now = datetime.now()
    if 8 <= now.hour < 20:
        return f"Morning_{now.strftime('%Y-%m-%d')}"
    else:
        return f"Night_{now.strftime('%Y-%m-%d')}"

@st.cache_data(ttl=None) 
def load_data(slot):
    t = datetime.now().timestamp() 
    df_s = pd.read_csv(f"{STOCK_URL}&t={t}")
    df_c = pd.read_csv(f"{CAPS_URL}&t={t}")
    # Still loading layout from your GitHub
    df_l = pd.read_excel('Untitled spreadsheet (1).xlsx', header=None)
    return df_l, df_s, df_c

try:
    current_slot = get_time_slot()
    df_layout, df_stock, df_caps = load_data(current_slot)

    # --- 4. CLEANING ---
    def clean_cols(df):
        df.columns = df.columns.str.strip().str.replace(' ', '_').str.lower()
        return df

    df_stock = clean_cols(df_stock)
    df_caps = clean_cols(df_caps)

    def create_match_key(text):
        return re.sub(r'[^a-zA-Z0-9]', '', str(text)).upper()

    df_stock['match_key'] = df_stock['bay_name'].apply(create_match_key)
    df_caps['match_key'] = df_caps['bay_name'].apply(create_match_key)

    df_master = pd.merge(df_caps, df_stock, on='match_key', how='left')
    df_master['val_used'] = pd.to_numeric(df_master['used_m3'], errors='coerce').fillna(0)
    df_master['val_cap'] = pd.to_numeric(df_master['capacity_m3'], errors='coerce').fillna(10)
    df_master['util_pct'] = (df_master['val_used'] / df_master['val_cap'].replace(0, 0.001)) * 100
    util_lookup = df_master.set_index('match_key')['util_pct'].to_dict()

    # --- 5. SEARCH ---
    st.title("FC Heat Map")
    search_query = st.sidebar.text_input("🔍 Search Bay (e.g. WS-E-1)")
    search_key = create_match_key(search_query) if search_query else None

    # --- 6. GRID & LABEL LOGIC (RESTORED) ---
    color_grid = pd.DataFrame(index=df_layout.index, columns=df_layout.columns, dtype=float)
    label_positions = []
    processed_labels = set() # This ensures we only show a name ONCE per column
    found_coords = None

    for r in range(len(df_layout)):
        for c in range(len(df_layout.columns)):
            val = str(df_layout.iloc[r, c]).strip()
            if val and val.lower() != "nan" and val != "":
                m_key = create_match_key(val)
                color_grid.iloc[r, c] = util_lookup.get(m_key, 0)
                
                # Search Highlight
                if search_key and m_key == search_key: 
                    found_coords = (r, c)
                
                # ORIGINAL LABEL LOGIC: 
                # Strips numbers to get the Bay Header (e.g., "WS-E")
                clean_name = re.sub(r'\d+', '', val).rstrip('-').strip()
                label_id = f"{clean_name}_{c}" 
                
                # Only add label if it's the first time seeing this Bay Type in this column
                if label_id not in processed_labels:
                    label_positions.append((r, c, clean_name))
                    processed_labels.add(label_id)
            else:
                color_grid.iloc[r, c] = np.nan

    # --- 7. VISUALIZATION ---
    plt.rcParams['figure.facecolor'] = '#121212'
    fig, ax = plt.subplots(figsize=(25, 12)) # Slightly larger for better spacing
    ax.set_facecolor('#121212')
    
    cmap = mcolors.LinearSegmentedColormap.from_list("", ["#2ecc71", "#f1c40f", "#e74c3c"])
    
    sns.heatmap(color_grid.clip(upper=100), cmap=cmap, cbar=False, 
                linewidths=1.5, linecolor='#121212', mask=color_grid.isnull(), ax=ax)

    if found_coords:
        ax.add_patch(plt.Rectangle((found_coords[1], found_coords[0]), 1, 1, fill=False, edgecolor='#00ffff', lw=8))

    # Place labels ABOVE the bays, just like before
    for r, c, name in label_positions:
        ax.text(c + 0.5, r - 0.7, name, ha='center', va='bottom', 
                color='white', fontsize=10, weight='bold')

    plt.axis('off')
    st.pyplot(fig, use_container_width=True)
    
    st.caption(f"Viewing data for: {current_slot} | Sheet Sync Active")

except Exception as e:
    st.error(f"Error: {e}")
