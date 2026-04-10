import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import re
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Columbus Picking Velocity")

# --- 2. DATA SOURCES ---
# Using the Columbus Google Sheet ID for Picking Data
SHEET_ID = "1VQcQxlNfLXaxNhpEpcsoLP-IClQ7pWyGHZ32_NLaIRI"

@st.cache_data(ttl=10)
def load_data():
    t = datetime.now().timestamp()
    
    # A. Load Picking Data from Google Sheets (RAW tab)
    RAW_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=RAW"
    df_raw = pd.read_csv(f"{RAW_URL}&t={t}")
    df_raw.columns = df_raw.columns.str.strip().str.replace(' ', '_').str.lower()
    
    # B. Load Layout (Direct Excel Scan)
    # This reads your Excel file as the "Source of Truth" for the map shape
    df_layout = pd.read_excel('Untitled spreadsheet (1).xlsx', header=None)
    
    return df_layout, df_raw

try:
    df_map, df_raw_data = load_data()

    def sanitize(text):
        if pd.isna(text): return ""
        return re.sub(r'[^A-Z0-9]', '', str(text).upper())

    # --- 3. FILTERS ---
    st.sidebar.title("🏃 Columbus Picking")
    client_list = ["All Clients"] + sorted(df_raw_data['client_name'].dropna().unique().tolist())
    selected_client = st.sidebar.selectbox("Filter by Client", client_list)

    # --- 4. DATA PREP ---
    if selected_client != "All Clients":
        df_work = df_raw_data[df_raw_data['client_name'] == selected_client].copy()
    else:
        df_work = df_raw_data.copy()

    # Standardize column names for the handshake
    if 'bay' in df_work.columns: 
        df_work = df_work.rename(columns={'bay': 'bay_name'})
        
    df_work['match_key'] = df_work['bay_name'].apply(sanitize)
    
    # Calculate Velocity (Count of picks per bay)
    bay_counts = df_work['match_key'].value_counts().to_dict()

    # --- 5. GRID SCAN (Turning Excel into a Picking Grid) ---
    color_grid = pd.DataFrame(index=df_map.index, columns=df_map.columns, dtype=float)
    label_positions = []
    processed_labels = set()
    
    search_query = st.sidebar.text_input("🔍 Search Bay (e.g. PS-B-11)")
    search_key = sanitize(search_query) if search_query else None
    found_coords = None

    for r in range(len(df_map)):
        for c in range(len(df_map.columns)):
            val = str(df_map.iloc[r, c]).strip()
            if val and val.lower() != "nan" and val != "":
                m_key = sanitize(val)
                
                # Assign Count (Velocity)
                count = bay_counts.get(m_key, 0)
                # If 0 picks, we use 0.001 to show our "Neutral Gray"
                color_grid.iloc[r, c] = count if count > 0 else 0.001
                
                if search_key and m_key == search_key:
                    found_coords = (r, c)

                # Label Logic (e.g., PS-A, PS-B)
                clean_name = re.sub(r'\d+', '', val).rstrip('-').strip()
                if f"{clean_name}_{c}" not in processed_labels:
                    label_positions.append((r, c, clean_name))
                    processed_labels.add(f"{clean_name}_{c}")
            else:
                color_grid.iloc[r, c] = np.nan

    # --- 6. VISUALIZATION ---
    st.title(f"Columbus Picking Velocity: {selected_client}")
    
    max_val = max(bay_counts.values()) if bay_counts else 1
    
    plt.rcParams['figure.facecolor'] = '#121212'
    fig, ax = plt.subplots(figsize=(25, 12)) 
    ax.set_facecolor('#121212')
    
    # Heatmap Colors: Neutral Gray -> Green -> Red
    colors = ["#f2f2f2", "#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]
    cmap = mcolors.LinearSegmentedColormap.from_list("velocity", colors, N=256)
    
    sns.heatmap(color_grid.astype(float), cmap=cmap, cbar=True, linewidths=0.2, 
                linecolor='#121212', mask=color_grid.isnull(), ax=ax, vmin=0, vmax=max_val)

    if found_coords:
        ax.add_patch(plt.Rectangle((found_coords[1], found_coords[0]), 1, 1, fill=False, edgecolor='#00ffff', lw=8))

    for r, c, name in label_positions:
        ax.text(c + 0.5, r - 0.7, name, ha='center', va='bottom', color='white', weight='bold', fontsize=9)

    plt.axis('off')
    st.pyplot(fig, use_container_width=True)

    # --- 7. SUMMARY DASHBOARD ---
    st.markdown("---")
    st.subheader(f"📑 Columbus Picking Summary ({selected_client})")
    
    sum_col1, sum_col2, sum_col3 = st.columns(3)
    
    with sum_col1:
        st.markdown("### 🏟️ Top 15 Bays")
        bay_rank = df_work['bay_name'].value_counts().reset_index()
        bay_rank.columns = ['Bay', 'Picks']
        st.dataframe(bay_rank.head(15), use_container_width=True, hide_index=True)
        
    with sum_col2:
        st.markdown("### 📍 Top 15 Locations")
        loc_rank = df_work['location'].value_counts().reset_index()
        loc_rank.columns = ['Location', 'Picks']
        st.dataframe(loc_rank.head(15), use_container_width=True, hide_index=True)
        
    with sum_col3:
        st.markdown("### 👤 Top Clients (Site Activity)")
        client_rank = df_raw_data['client_name'].value_counts().reset_index()
        client_rank.columns = ['Client', 'Total Picks']
        st.dataframe(client_rank.head(15), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
