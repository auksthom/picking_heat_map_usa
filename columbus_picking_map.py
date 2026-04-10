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
SHEET_ID = "1VQcQxlNfLXaxNhpEpcsoLP-IClQ7pWyGHZ32_NLaIRI"

@st.cache_data(ttl=10)
def load_data():
    t = datetime.now().timestamp()
    RAW_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=RAW"
    df_raw = pd.read_csv(f"{RAW_URL}&t={t}")
    df_raw.columns = df_raw.columns.str.strip().str.replace(' ', '_').str.lower()
    df_layout = pd.read_excel('Untitled spreadsheet (1).xlsx', header=None)
    return df_layout, df_raw

try:
    df_map, df_raw_data = load_data()

    def sanitize(text):
        if pd.isna(text): return ""
        return re.sub(r'[^A-Z0-9]', '', str(text)).upper()

    # --- 3. FILTERS ---
    st.sidebar.title("🏃 Columbus Picking")
    client_list = ["All Clients"] + sorted(df_raw_data['client_name'].dropna().unique().tolist())
    selected_client = st.sidebar.selectbox("Filter by Client", client_list)

    # --- 4. DATA PREP & GHOST FILTERING ---
    # Get valid bays from Excel
    valid_layout_bays = {sanitize(val) for val in df_map.values.flatten() if pd.notna(val) and str(val).strip().lower() != "nan"}

    # Prep the data
    df_raw_data['match_key'] = df_raw_data['bay'].apply(sanitize)

    # Global Ghosts (Every ghost on the site, regardless of client)
    df_global_ghosts = df_raw_data[~df_raw_data['match_key'].isin(valid_layout_bays)].copy()

    # Filtered Data for the Map
    if selected_client != "All Clients":
        df_work = df_raw_data[df_raw_data['client_name'] == selected_client].copy()
    else:
        df_work = df_raw_data.copy()

    df_mapped = df_work[df_work['match_key'].isin(valid_layout_bays)].copy()
    bay_counts = df_mapped['match_key'].value_counts().to_dict()

    # --- 5. GRID SCAN ---
    color_grid = pd.DataFrame(index=df_map.index, columns=df_map.columns, dtype=float)
    label_positions = []
    processed_labels = set()
    
    search_query = st.sidebar.text_input("🔍 Search Bay")
    search_key = sanitize(search_query) if search_query else None
    found_coords = None

    for r in range(len(df_map)):
        for c in range(len(df_map.columns)):
            val = str(df_map.iloc[r, c]).strip()
            if val and val.lower() != "nan" and val != "":
                m_key = sanitize(val)
                count = bay_counts.get(m_key, 0)
                color_grid.iloc[r, c] = count if count > 0 else 0.001
                if search_key and m_key == search_key: found_coords = (r, c)
                
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
    cmap = mcolors.LinearSegmentedColormap.from_list("velocity", ["#f2f2f2", "#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"], N=256)
    
    sns.heatmap(color_grid.astype(float), cmap=cmap, cbar=True, linewidths=0.2, 
                linecolor='#121212', mask=color_grid.isnull(), ax=ax, vmin=0, vmax=max_val)

    if found_coords:
        ax.add_patch(plt.Rectangle((found_coords[1], found_coords[0]), 1, 1, fill=False, edgecolor='#00ffff', lw=8))

    for r, c, name in label_positions:
        ax.text(c + 0.5, r - 0.7, name, ha='center', va='bottom', color='white', weight='bold', fontsize=9)

    plt.axis('off')
    st.pyplot(fig, use_container_width=True)

    # --- 7. SUMMARY DASHBOARDS ---
    st.markdown("---")
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader(f"🏟️ Top Mapped Bays ({selected_client})")
        st.dataframe(df_mapped['bay'].value_counts().reset_index(), use_container_width=True, hide_index=True)
        
    with col_right:
        st.error("👻 Ghost Location Auditor")
        ghost_view = st.radio("Show Ghosts for:", ["Current Client Only", "Entire Site (All Clients)"])
        
        if ghost_view == "Current Client Only":
            # Filter ghosts to just the selected client
            display_ghosts = df_global_ghosts[df_global_ghosts['client_name'] == selected_client] if selected_client != "All Clients" else df_global_ghosts
        else:
            display_ghosts = df_global_ghosts

        ghost_summary = display_ghosts['bay'].value_counts().reset_index()
        ghost_summary.columns = ['Bay Name', 'Pick Count']
        
        st.write(f"Showing {len(ghost_summary)} unmapped locations:")
        # Removed .head(15) so you see EVERYTHING
        st.dataframe(ghost_summary, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
