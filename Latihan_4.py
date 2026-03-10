import streamlit as st
import pandas as pd
import numpy as np
from pyproj import Transformer
import matplotlib.pyplot as plt
import contextily as ctx
import json

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatics Plotter", layout="wide")

# --- LOGIK DATA (GEOMATIK) ---
# EPSG:4390 (Kertau) ke WGS 84
transformer_wgs84 = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)
# EPSG:4390 ke Web Mercator (Satelit)
transformer_web = Transformer.from_crs("EPSG:4390", "EPSG:3857", always_xy=True)

def kira_brg_dst(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    dist = np.sqrt(de**2 + dn**2)
    brg = np.degrees(np.arctan2(de, dn))
    if brg < 0: brg += 360
    d = int(brg); m = int((brg-d)*60); s = round((((brg-d)*60)-m)*60,0)
    
    angle = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
    if angle > 90: angle -= 180
    elif angle < -90: angle += 180
    return f"{d}°{m:02d}'{s:02.0f}\"", dist, angle

def kira_luas(df):
    x, y = df['E'].values, df['N'].values
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- SIDEBAR UI ---
st.sidebar.title("🌍 Sistem Geomatik PUO")
uploaded_file = st.sidebar.file_uploader("Muat Naik Fail CSV", type=["csv"])

st.sidebar.markdown("---")
st.sidebar.subheader("Kawalan Paparan")
show_sat = st.sidebar.checkbox("Google Satellite", value=True)
show_stn = st.sidebar.checkbox("Label Stesen", value=True)
show_brg = st.sidebar.checkbox("Bearing & Jarak", value=True)

# --- MAIN CONTENT ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper().strip() for c in df.columns]
    
    if 'E' in df.columns and 'N' in df.columns:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Penukaran Koordinat untuk Paparan
        if show_sat:
            wm_coords = [transformer_web.transform(e, n) for e, n in zip(df['E'], df['N'])]
            e_disp = [c[0] for c in wm_coords]
            n_disp = [c[1] for c in wm_coords]
            ax.set_axis_off()
        else:
            e_disp = df['E'].tolist()
            n_disp = df['N'].tolist()

        e_plot = e_disp + [e_disp[0]]
        n_plot = n_disp + [n_disp[0]]

        # Lukis Poligon
        ax.plot(e_plot, n_plot, color='cyan', marker='o', markersize=5, linewidth=2)
        ax.fill(e_plot, n_plot, color='cyan', alpha=0.3)

        # Tambah Basemap Google Satellite
        if show_sat:
            google_sat = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
            ctx.add_basemap(ax, source=google_sat)

        # Labeling
        perimeter = 0
        for i in range(len(df)):
            p1_orig = [df['E'].iloc[i], df['N'].iloc[i]]
            p2_orig = [df['E'].iloc[(i+1)%len(df)], df['N'].iloc[(i+1)%len(df)]]
            brg_txt, dst_val, angle = kira_brg_dst(p1_orig, p2_orig)
            perimeter += dst_val

            if show_stn:
                stn_val = df['STN'].iloc[i] if 'STN' in df.columns else i+1
                ax.text(e_disp[i], n_disp[i], f"STN {int(stn_val)}", color='yellow', fontsize=9, fontweight='bold')

            if show_brg:
                mid_e = (e_disp[i] + e_disp[(i+1)%len(df)])/2
                mid_n = (n_disp[i] + n_disp[(i+1)%len(df)])/2
                ax.text(mid_e, mid_n, f"{brg_txt}\n{dst_val:.2f}m", color='white', 
                        fontsize=7, ha='center', rotation=angle, fontweight='bold',
                        bbox=dict(boxstyle='round', fc='black', alpha=0.5, ec='none'))

        # Paparan Plot di Streamlit
        st.pyplot(fig)

        # Info Box
        luas_m2 = kira_luas(df)
        c1, c2, c3 = st.columns(3)
        c1.metric("Luas (m²)", f"{luas_m2:.2f}")
        c2.metric("Luas (Ekar)", f"{luas_m2/4046.856:.4f}")
        c3.metric("Perimeter (m)", f"{perimeter:.2f}")
        
    else:
        st.error("Fail CSV tidak mempunyai lajur E atau N!")
else:
    st.info("Sila muat naik fail CSV di sidebar untuk memulakan.")
