from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sn
import streamlit as st
import pandas as pd
import numpy as np
from operator import attrgetter

# Pengaturan pandas agar semua kolom tampil
pd.set_option("display.max_columns", None)

import streamlit as st
import pandas as pd
import plotly.express as px  # Tambahan library untuk Pie & Bar Chart

# ==========================================
# 1. Konfigurasi Halaman
# ==========================================
st.set_page_config(page_title="Dashboard Tren Kolektibilitas", layout="wide")

# ==========================================
# 2. Fitur Upload Data & Membaca File
# ==========================================
st.sidebar.header("📁 Upload Data")
uploaded_file = st.sidebar.file_uploader("Masukkan file data (CSV / Excel)", type=["csv", "xlsx"])

# Menghentikan web memuat bagian bawah jika belum ada file yang di-upload
if not uploaded_file:
    st.info("👋 Silakan upload file data CSV atau Excel di menu sebelah kiri untuk memulai analisa dashboard.")
    st.stop()

# Fungsi untuk membaca file dengan Cache agar web tidak lambat
@st.cache_data
def load_uploaded_data(file):
     
    # Membaca data berdasarkan format file
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    elif file.name.endswith('.xlsx'):
        df = pd.read_excel(file)
        
    # Memastikan format tipe data sesuai kebutuhan pivot
    df['TanggalValuta'] = pd.to_datetime(df['TanggalValuta'])
    df['Kolektibilitas'] = df['Kolektibilitas'].astype(int)
    # Memaksa jadi string dan menghapus akhiran .0 jika Streamlit sempat membacanya sebagai desimal
    df['CIF'] = df['CIF'].astype(str).str.replace(r'\.0$', '', regex=True)
    df['NoRekening'] = df['NoRekening'].astype(str).str.replace(r'\.0$', '', regex=True)
 
    return df

# Mencoba memuat data dari file yang di-upload
try:
    df_raw = load_uploaded_data(uploaded_file)
    df_filtered = df_raw.copy()
except Exception as e:
    st.error(f"❌ Gagal memproses file. Pastikan nama kolom di dalam file sudah sesuai. Detail Error: {e}")
    st.stop()

# ==========================================
# 3. Sidebar Filters
# ==========================================
st.sidebar.header("Konfigurasi Filter")

# Buat list unik untuk Tahun dan Bulan (Pastikan berurutan)
tahun_list = sorted(df_raw['DateYear'].dropna().unique().astype(int).tolist())
bulan_list = sorted(df_raw['DateMonth'].dropna().unique().astype(int).tolist())

# Input Periode Awal
st.sidebar.markdown("**Periode Awal**")
col1, col2 = st.sidebar.columns(2)
start_year = col1.selectbox("Tahun", options=tahun_list, index=0, key='start_y')
start_month = col2.selectbox("Bulan", options=bulan_list, index=0, key='start_m')

# Input Periode Akhir
st.sidebar.markdown("**Periode Akhir**")
col3, col4 = st.sidebar.columns(2)
end_year = col3.selectbox("Tahun", options=tahun_list, index=len(tahun_list)-1, key='end_y')
end_month = col4.selectbox("Bulan", options=bulan_list, index=len(bulan_list)-1, key='end_m')

# Membuat SortKey untuk membatasi rentang waktu secara matematis
start_key = (start_year * 100) + start_month
end_key = (end_year * 100) + end_month

# Buat SortKey di df_raw untuk memudahkan filter awal
df_raw['SortKey_Temp'] = df_raw['DateYear'] * 100 + df_raw['DateMonth']

# Filter Dinamis berdasarkan Rentang Waktu yang dipilih
df_temp = df_raw[(df_raw['SortKey_Temp'] >= start_key) & (df_raw['SortKey_Temp'] <= end_key)]

cif_list = df_temp['CIF'].dropna().unique().tolist()
selected_cif = st.sidebar.multiselect("Pilih CIF", options=cif_list)

debitur_list = df_temp['NamaDebitur'].dropna().unique().tolist()
selected_debitur = st.sidebar.multiselect("Pilih Nama Debitur", options=debitur_list)

norek_list = df_temp['NoRekening'].dropna().unique().tolist()
selected_norek = st.sidebar.multiselect("Pilih No Rekening", options=norek_list)

fasilitas_list = df_temp['JenisFasilitas'].dropna().unique().tolist()
selected_fasilitas = st.sidebar.multiselect("Pilih Jenis Fasilitas", options=fasilitas_list)

# ==========================================
# 4. Menerapkan Filter ke DataFrame
# ==========================================
# 1. Filter Rentang Waktu
df_filtered = df_filtered[(df_filtered['DateYear'] * 100 + df_filtered['DateMonth'] >= start_key) & 
                          (df_filtered['DateYear'] * 100 + df_filtered['DateMonth'] <= end_key)]

# 2. Filter Multiselect Lainnya
if selected_cif:
    df_filtered = df_filtered[df_filtered['CIF'].isin(selected_cif)]
if selected_debitur:
    df_filtered = df_filtered[df_filtered['NamaDebitur'].isin(selected_debitur)]
if selected_norek:
    df_filtered = df_filtered[df_filtered['NoRekening'].isin(selected_norek)]
if selected_fasilitas:
    df_filtered = df_filtered[df_filtered['JenisFasilitas'].isin(selected_fasilitas)]

# ==========================================
# 5. Judul & Pengolahan Data Pivot
# ==========================================
st.title("📊 Dashboard Tren Kolektibilitas")

if df_filtered.empty:
    st.warning("Data tidak ditemukan dengan kombinasi filter tersebut.")
else:
    # A. Pastikan pengurutan data sesuai hierarki
    df_filtered = df_filtered.sort_values(['CIF', 'NoRekening', 'TanggalValuta', 'DateYear', 'DateMonth'])

    # B. Identifikasi Restrukturisasi (Restruk)
    restruk_info = df_filtered.groupby('NoRekening')['TanggalValuta'].nunique()
    df_filtered['Is_Restruk'] = df_filtered['NoRekening'].map(lambda x: 1 if restruk_info[x] > 1 else 0)

    # C. Membuat kolom Periode dan SortKey (Bantuan Pengurutan)
    df_filtered['SortKey'] = df_filtered['DateYear'] * 100 + df_filtered['DateMonth']
    df_filtered['Periode'] = 'M' + df_filtered['DateMonth'].astype(str) + '-' + df_filtered['DateYear'].astype(str).str[-2:]

    # D. Ambil daftar Periode unik berdasarkan urutan SortKey terkecil
    ordered_periods = df_filtered.sort_values('SortKey')['Periode'].unique()

    # E. Pivot data untuk melihat tren per NoRekening
    df_trend = df_filtered.pivot_table(
        index=['CIF', 'NamaDebitur', 'NoRekening', 'JenisFasilitas', 'Is_Restruk'], 
        columns='Periode', 
        values='Kolektibilitas', 
        aggfunc='max'
    )

    # F. Reindex kolom menggunakan urutan kronologis yang sudah dibuat
    valid_periods = [p for p in ordered_periods if p in df_trend.columns]
    df_trend = df_trend[valid_periods]
    
    # Reset index agar tampilan di Streamlit lebih rapi
    df_trend = df_trend.reset_index()

    # Tampilkan Metrik Singkat
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Debitur", df_trend['NamaDebitur'].nunique())
    col2.metric("Total Rekening", df_trend['NoRekening'].nunique())
    col3.metric("Rekening Restruk", df_trend[df_trend['Is_Restruk'] == 1]['NoRekening'].nunique())

    # Tampilkan Tabel Tren
    st.markdown("### Tabel Tren Kolektibilitas Berdasarkan Filter")
    st.dataframe(df_trend, use_container_width=True)

    # ==========================================
    # 6. Fitur Visualisasi (Line Chart, Pie Chart, Bar Chart)
    # ==========================================
    st.markdown("---")
    st.markdown("### 📈 Visualisasi Data")

    # --- A. LINE CHART (Maksimal 10 Debitur) ---
    st.markdown("#### Tren Kolektibilitas per Debitur")
    
    # Ambil 10 debitur unik teratas sebagai default pilihan
    top_10_debitur = df_trend['NamaDebitur'].unique()[:10].tolist()
    
    selected_chart_debitur = st.multiselect(
        "Pilih Debitur (Maksimal 10 disarankan):",
        options=df_trend['NamaDebitur'].unique().tolist(),
        default=top_10_debitur
    )

    if selected_chart_debitur:
        # Filter khusus untuk chart
        df_line = df_filtered[df_filtered['NamaDebitur'].isin(selected_chart_debitur)]
        
        # Buat pivot data untuk line chart: Index = Periode, Columns = NamaDebitur
        df_line_pivot = df_line.pivot_table(
            index='Periode', 
            columns='NamaDebitur', 
            values='Kolektibilitas', 
            aggfunc='max'
        )
        
        # Urutkan index berdasarkan valid_periods secara kronologis
        df_line_pivot = df_line_pivot.reindex(valid_periods)
        
        st.line_chart(df_line_pivot)
    else:
        st.info("Pilih setidaknya satu debitur untuk menampilkan grafik tren.")

    # --- B. DISTRIBUSI KOLEKTIBILITAS (Pie & Bar Chart) ---
    # Mengambil bulan terakhir dari filter sebagai acuan distribusi posisi terkini
    if len(valid_periods) > 0:
        latest_period = valid_periods[-1]
        st.markdown(f"#### Distribusi Posisi Kolektibilitas Terakhir ({latest_period})")

        # Tarik data khusus di bulan terakhir
        df_latest = df_filtered[df_filtered['Periode'] == latest_period]
        
        # Hitung jumlah rekening per angka kolektibilitas
        dist_data = df_latest.groupby('Kolektibilitas')['NoRekening'].nunique().reset_index()
        dist_data.columns = ['Kolektibilitas', 'Jumlah Rekening']
        
        # Mapping label nama kolektibilitas
        kol_labels = {1: "1 - Lancar", 2: "2 - DPK", 3: "3 - KL", 4: "4 - Diragukan", 5: "5 - Macet"}
        dist_data['Status'] = dist_data['Kolektibilitas'].map(lambda x: kol_labels.get(x, f"Kol {x}"))

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            # Pie Chart
            fig_pie = px.pie(
                dist_data, 
                names='Status', 
                values='Jumlah Rekening',
                title='Persentase Kolektibilitas',
                hole=0.4 # Membuatnya menjadi Donut Chart (opsional)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_chart2:
            # Bar Chart
            fig_bar = px.bar(
                dist_data, 
                x='Status', 
                y='Jumlah Rekening',
                text='Jumlah Rekening',
                title='Jumlah Rekening per Kolektibilitas',
                color='Status'
            )
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(showlegend=False) # Sembunyikan legend karena x-axis sudah jelas
            st.plotly_chart(fig_bar, use_container_width=True)
