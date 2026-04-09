import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import re
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Columbus Site: Picking Velocity")

# --- 2. DATA SOURCES ---
# Columbus Spreadsheet ID
SHEET_ID = "1VQcQxlNfLXaxNhpEpcsoLP-IClQ7pWyGHZ32_NLaIRI"
RAW_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=RAW"

st.sidebar.title("🏃 Columbus Navigation")

@st.cache_data(ttl=10)
def load_picking_data():
    t = datetime.now().timestamp()
    df_raw = pd.read_csv(f"{RAW_URL}&t={t}")
    # Still assumes master_blueprint.csv is in your repository
    df_bp = pd.read_csv('master_blueprint.csv')
    df_raw.columns = df_raw.columns.str.strip().str.replace(' ', '_').str.lower()
    return df_bp, df_raw

try:
    df_blueprint, df_raw_data = load_picking_data()

    def sanitize(text):
        return re.sub(r'[^A-Z0-9]', '', str(text)).upper()

    # --- 3. FILTERS (Removed Level Selection) ---
    client_list = ["All Clients"] + sorted(df_raw_data['client_name'].dropna().unique().tolist())
    selected_client = st.sidebar.selectbox("Filter by Client", client_list)

    # --- 4. DATA PREP (No level filtering needed) ---
    df_map_bp = df_blueprint.copy()
    df_map_bp['match_key'] = df_map_bp['bay_name'].apply(sanitize)
    valid_map_bays = set(df_map_bp['match_key'].unique())

    if selected_client != "All Clients":
        df_work = df_raw_data[df_raw_data['client_name'] == selected_client].copy()
    else:
        df_work = df_raw_data.copy()

    df_work['bay_key'] = df_work['bay'].apply(sanitize)
    # Only keep picks that exist within our Columbus layout
    df_mapped_only = df_work[df_work['bay_key'].isin(valid_map_bays)].copy()

    # --- 5. CALCULATIONS FOR SUMMARY ---
    bay_rank = df_mapped_only['bay'].value_counts().reset_index()
    bay_rank.columns = ['Bay', 'Picks']
    
    loc_rank = df_mapped_only['location'].value_counts().reset_index()
    loc_rank.columns = ['Location', 'Picks']
    
    client_rank = df_mapped_only['client_name'].value_counts().reset_index()
    client_rank.columns = ['Client', 'Picks']

    # --- 6. GRID MAPPING ---
    if df_map_bp.empty:
        st.error("No layout data found in master_blueprint.csv")
    else:
        max_r, max_c = int(df_map_bp['grid_row'].max() + 1), int(df_map_bp['grid_col'].max() + 1)
        color_grid = np.full((max_r, max_c), np.nan)
        
        bay_counts_dict = df_mapped_only['bay_key'].value_counts().to_dict()
        
        for _, row in df_map_bp.iterrows():
            r, c, m_key = int(row['grid_row']), int(row['grid_col']), row['match_key']
            count = bay_counts_dict.get(m_key, 0)
            # Use 0.001 to show the neutral gray for empty bays
            color_grid[r, c] = count if count > 0 else 0.001

        # --- 7. VISUALIZATION ---
        st.title(f"Columbus Picking Velocity: {selected_client}")
        
        max_val = max(bay_counts_dict.values()) if bay_counts_dict else 1
        fig, ax = plt.subplots(figsize=(25, 12), facecolor='none')
        ax.set_facecolor('none')
        
        colors = ["#f2f2f2", "#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]
        cmap = mcolors.LinearSegmentedColormap.from_list("velocity", colors, N=256)
        
        sns.heatmap(color_grid, cmap=cmap, cbar=True, linewidths=0.2, linecolor='#dddddd', vmin=0, vmax=max_val, mask=np.isnan(color_grid), ax=ax)

        processed_labels = set()
        for _, row in df_map_bp.iterrows():
            r, c = int(row['grid_row']), int(row['grid_col'])
            clean_label = re.sub(r'\d+$', '', str(row['bay_name'])).rstrip('-').strip()
            if f"{clean_label}_{c}" not in processed_labels:
                ax.text(c + 0.5, r - 0.7, clean_label, ha='center', va='bottom', color='#aaaaaa', weight='bold', fontsize=9)
                processed_labels.add(f"{clean_label}_{c}")

        plt.axis('off')
        st.pyplot(fig, use_container_width=True)

        # --- 8. THE SUMMARY DASHBOARD ---
        st.markdown("---")
        st.subheader("📑 Columbus Activity Summary")
        
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        
        with sum_col1:
            st.markdown("### 🏟️ Top 15 Bays")
            st.dataframe(bay_rank.head(15), use_container_width=True, hide_index=True)
            
        with sum_col2:
            st.markdown("### 📍 Top 15 Locations")
            st.dataframe(loc_rank.head(15), use_container_width=True, hide_index=True)
            
        with sum_col3:
            st.markdown("### 👤 Top Clients")
            if selected_client != "All Clients":
                st.info(f"Viewing: **{selected_client}**")
            st.dataframe(client_rank.head(15), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
