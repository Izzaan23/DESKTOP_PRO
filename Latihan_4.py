import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
import numpy as np
from pyproj import Transformer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import contextily as ctx  # Tambahan untuk imej satelit

# --- KONFIGURASI TEMA ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SistemPoligonDesktop(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SISTEM PENGURUSAN MAKLUMAT TANAH (DESKTOP)")
        self.geometry("1200x800")

        # Logik Data
        # EPSG:4390 (Kertau) ke WGS 84 (Geodetik)
        self.transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)
        # EPSG:4390 ke EPSG:3857 (Web Mercator) - Diperlukan untuk peta satelit
        self.to_web_mercator = Transformer.from_crs("EPSG:4390", "EPSG:3857", always_xy=True)
        
        self.df = None
        self.user_names = {"11": "Izzaan", "12": "Adam Muqhris", "13": "Alif"}
        
        # Variable untuk On/Off
        self.show_sat = ctk.BooleanVar(value=False)
        self.show_brg = ctk.BooleanVar(value=True)
        self.show_stn = ctk.BooleanVar(value=True)
        
        # UI Log Masuk
        self.tunjukkan_halaman_login()

    # --- FUNGSI GEOMATIK ASAL ---
    def kira_brg_dst(self, p1, p2):
        de, dn = p2[0] - p1[0], p2[1] - p1[1]
        dist = np.sqrt(de**2 + dn**2)
        brg = np.degrees(np.arctan2(de, dn))
        if brg < 0: brg += 360
        d = int(brg); m = int((brg-d)*60); s = round((((brg-d)*60)-m)*60,0)
        
        angle = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
        if angle > 90: angle -= 180
        elif angle < -90: angle += 180
        
        return f"{d}°{m:02d}'{s:02.0f}\"", dist, angle

    def kira_luas(self, df):
        x, y = df['E'].values, df['N'].values
        return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

    # --- UI LOGIC ---
    def tunjukkan_halaman_login(self):
        self.login_frame = ctk.CTkFrame(self, width=400, height=500)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self.login_frame, text="🔓 LOG MASUK SISTEM", font=("Arial", 20, "bold")).pack(pady=30)
        self.u_id = ctk.CTkEntry(self.login_frame, placeholder_text="ID Pengguna", width=250)
        self.u_id.pack(pady=10)
        self.u_pass = ctk.CTkEntry(self.login_frame, placeholder_text="Kata Laluan", show="*", width=250)
        self.u_pass.pack(pady=10)
        ctk.CTkButton(self.login_frame, text="Log Masuk", command=self.proses_login, width=250).pack(pady=20)
        ctk.CTkLabel(self.login_frame, text="Pembangun: Izzaan | Geomatics PUO", font=("Arial", 10)).pack(pady=10)

    def proses_login(self):
        userid = self.u_id.get()
        password = self.u_pass.get()
        if userid in self.user_names and password == "admin123":
            self.user_logged_in = self.user_names[userid]
            self.login_frame.destroy()
            self.bina_antaramuka_utama()
        else:
            messagebox.showerror("Ralat", "ID atau Kata Laluan Salah!")

    def bina_antaramuka_utama(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        ctk.CTkLabel(self.sidebar, text=f"Hi, {self.user_logged_in}! 👋", font=("Arial", 16, "bold")).pack(pady=20)
        ctk.CTkButton(self.sidebar, text="📂 Muat Naik CSV", command=self.muat_naik_fail).pack(pady=10, padx=20)
        
        ctk.CTkLabel(self.sidebar, text="KAWALAN PAPARAN", font=("Arial", 12, "bold")).pack(pady=(20,5))
        ctk.CTkSwitch(self.sidebar, text="Google Satelit", variable=self.show_sat, command=self.update_plot).pack(pady=5, padx=20, anchor="w")
        ctk.CTkSwitch(self.sidebar, text="Label Stesen", variable=self.show_stn, command=self.update_plot).pack(pady=5, padx=20, anchor="w")
        ctk.CTkSwitch(self.sidebar, text="Bearing & Jarak", variable=self.show_brg, command=self.update_plot).pack(pady=5, padx=20, anchor="w")

        self.lbl_info = ctk.CTkLabel(self.sidebar, text="Maklumat Lot:\n-", justify="left", font=("Arial", 12))
        self.lbl_info.pack(pady=20, padx=20)

        ctk.CTkButton(self.sidebar, text="💾 Eksport GeoJSON", fg_color="green", command=self.eksport_geojson).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar, text="🚪 Log Keluar", fg_color="#942626", command=self.quit).pack(side="bottom", pady=20)

        self.main_view = ctk.CTkFrame(self)
        self.main_view.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        self.fig, self.ax = plt.subplots(figsize=(8, 6), facecolor='#1e1e1e')
        self.ax.set_facecolor('#1e1e1e')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_view)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def muat_naik_fail(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file_path:
            self.df = pd.read_csv(file_path)
            self.df.columns = [c.upper().strip() for c in self.df.columns]
            if 'E' in self.df.columns and 'N' in self.df.columns:
                self.plot_poligon()
            else:
                messagebox.showerror("Ralat", "Fail CSV mesti ada lajur E dan N!")

    def update_plot(self):
        if self.df is not None:
            self.plot_poligon()

    def plot_poligon(self):
        if self.df is not None:
            self.ax.clear()
            
            # --- AUTO CONVERT KOORDINAT ---
            if self.show_sat.get():
                # Tukar EPSG:4390 ke EPSG:3857 supaya selari dengan peta satelit
                wm_coords = [self.to_web_mercator.transform(e, n) for e, n in zip(self.df['E'], self.df['N'])]
                e_disp = [c[0] for c in wm_coords]
                n_disp = [c[1] for c in wm_coords]
                self.ax.set_axis_off() 
            else:
                # Guna koordinat asal (RSO) jika satelit ditutup
                e_disp = self.df['E'].tolist()
                n_disp = self.df['N'].tolist()
                self.ax.set_axis_on()

            stn = self.df['STN'].tolist()
            e_plot = e_disp + [e_disp[0]]
            n_plot = n_disp + [n_disp[0]]
            
            # Plot Poligon
            self.ax.plot(e_plot, n_plot, color='cyan', marker='o', markersize=4, linewidth=1.5, alpha=0.9)
            self.ax.fill(e_plot, n_plot, color='cyan', alpha=0.2)
            
            # --- TAMBAH GOOGLE SATELLITE ---
            if self.show_sat.get():
                try:
                    # Menggunakan source Google Satellite XYZ
                    google_sat = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
                    ctx.add_basemap(self.ax, source=google_sat)
                except Exception as e:
                    print(f"Ralat peta: {e}")

            perimeter = 0
            bil_titik = len(self.df)

            for i in range(bil_titik):
                # Pengiraan bearing/jarak mestilah guna koordinat ASAL (E, N) untuk ketepatan ukur
                p1_orig = [self.df['E'].iloc[i], self.df['N'].iloc[i]]
                p2_orig = [self.df['E'].iloc[(i+1)%bil_titik], self.df['N'].iloc[(i+1)%bil_titik]]
                brg_txt, dst_val, angle = self.kira_brg_dst(p1_orig, p2_orig)
                perimeter += dst_val

                # 1. Label Stesen
                if self.show_stn.get():
                    self.ax.annotate(f"{int(stn[i])}", (e_disp[i], n_disp[i]), color='yellow', 
                                     fontweight='bold', fontsize=9, xytext=(5, 5), textcoords='offset points')
                
                # 2. Label Bearing & Jarak
                if self.show_brg.get():
                    mid_e, mid_n = (e_disp[i] + e_disp[(i+1)%bil_titik])/2, (n_disp[i] + n_disp[(i+1)%bil_titik])/2
                    label_txt = f"{brg_txt}\n{dst_val:.2f}m"
                    self.ax.text(mid_e, mid_n, label_txt, color='white', fontsize=8, 
                                 ha='center', va='center', rotation=angle, fontweight='bold',
                                 bbox=dict(boxstyle='round,pad=0.2', fc='black', alpha=0.6, ec='none'))

            # Update Maklumat Lot
            luas_m2 = self.kira_luas(self.df)
            self.lbl_info.configure(text=f"Maklumat Lot:\nLuas: {luas_m2:.2f} m²\nPerimeter: {perimeter:.2f} m\nStesen: {bil_titik}")
            
            self.ax.set_aspect('equal')
            self.ax.set_title("PELAN TRAVERSE @ GOOGLE SATELLITE", color='white', fontsize=12, pad=20)
            self.canvas.draw()

    def eksport_geojson(self):
        if self.df is None: return messagebox.showwarning("Amaran", "Sila muat naik fail dahulu!")
        save_path = filedialog.asksaveasfilename(defaultextension=".geojson", filetypes=[("GeoJSON Files", "*.geojson")])
        if save_path:
            try:
                coords_wgs = [self.transformer.transform(e, n) for e, n in zip(self.df['E'], self.df['N'])]
                lon_lat = [[c[0], c[1]] for c in coords_wgs]
                features = []
                poly_coords = lon_lat + [lon_lat[0]]
                features.append({
                    "type": "Feature",
                    "properties": {"Nama": "Lot Tanah", "Luas_m2": round(self.kira_luas(self.df), 2)},
                    "geometry": {"type": "Polygon", "coordinates": [poly_coords]}
                })
                geojson_data = {"type": "FeatureCollection", "features": features}
                with open(save_path, 'w') as f:
                    json.dump(geojson_data, f, indent=4)
                messagebox.showinfo("Berjaya", "Fail GeoJSON berjaya disimpan!")
            except Exception as e:
                messagebox.showerror("Ralat", f"Gagal: {e}")

if __name__ == "__main__":
    app = SistemPoligonDesktop()
    app.mainloop()