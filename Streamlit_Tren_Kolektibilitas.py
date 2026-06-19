import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# 1. Konfigurasi Halaman
# ==========================================
st.set_page_config(page_title="Dashboard Tren Kolektibilitas", layout="wide")

# ==========================================
# 2. Fitur Upload Data & Membaca File
# ==========================================
st.sidebar.header("📁 Upload Data")
uploaded_file = st.sidebar.file_uploader("Masukkan file data (CSV / Excel)", type=["csv", "xlsx"])

if not uploaded_file:
    st.info("👋 Silakan upload file data CSV atau Excel di menu sebelah kiri untuk memulai analisa dashboard.")
    st.stop()

@st.cache_data
def load_uploaded_data(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    elif file.name.endswith('.xlsx'):
        df = pd.read_excel(file)

    df['TanggalValuta'] = pd.to_datetime(df['TanggalValuta'])
    df['Kolektibilitas'] = df['Kolektibilitas'].astype(int)
    df['CIF'] = df['CIF'].astype(str).str.replace(r'\.0$', '', regex=True)
    df['NoRekening'] = df['NoRekening'].astype(str).str.replace(r'\.0$', '', regex=True)
    df['Segmen'] = df['Segmen'].astype(str).str.strip()
    return df

try:
    df_raw = load_uploaded_data(uploaded_file)
    df_filtered = df_raw.copy()
except Exception as e:
    st.error(f"❌ Gagal memproses file. Pastikan nama kolom di dalam file sudah sesuai. Detail Error: {e}")
    st.stop()

# ==========================================
# 3. Sidebar Filters (Cascading)
# ==========================================
st.sidebar.header("Konfigurasi Filter")

# --- Periode ---
tahun_list = sorted(df_raw['DateYear'].dropna().unique().astype(int).tolist())
bulan_list = sorted(df_raw['DateMonth'].dropna().unique().astype(int).tolist())

st.sidebar.markdown("**Periode Awal**")
col1, col2 = st.sidebar.columns(2)
start_year  = col1.selectbox("Tahun", options=tahun_list, index=0, key='start_y')
start_month = col2.selectbox("Bulan", options=bulan_list, index=0, key='start_m')

st.sidebar.markdown("**Periode Akhir**")
col3, col4 = st.sidebar.columns(2)
end_year  = col3.selectbox("Tahun", options=tahun_list, index=len(tahun_list)-1, key='end_y')
end_month = col4.selectbox("Bulan", options=bulan_list, index=len(bulan_list)-1, key='end_m')

start_key = start_year * 100 + start_month
end_key   = end_year   * 100 + end_month

# Basis filter rentang waktu
df_raw['SortKey_Temp'] = df_raw['DateYear'] * 100 + df_raw['DateMonth']
df_temp = df_raw[
    (df_raw['SortKey_Temp'] >= start_key) &
    (df_raw['SortKey_Temp'] <= end_key)
].copy()

# ── Filter 1: Segmen (dari kolom Segmen) ──
segmen_list = sorted(df_temp['Segmen'].dropna().unique().tolist())
selected_segmen = st.sidebar.multiselect("Pilih Segmen", options=segmen_list)
if selected_segmen:
    df_temp = df_temp[df_temp['Segmen'].isin(selected_segmen)]

# ── Filter 2: Kolektibilitas ──
kolek_list = sorted(df_temp['Kolektibilitas'].dropna().unique().astype(int).tolist())
selected_kolek = st.sidebar.multiselect("Pilih Kolektibilitas", options=kolek_list)
if selected_kolek:
    norek_kolek = df_temp[df_temp['Kolektibilitas'].isin(selected_kolek)]['NoRekening'].unique()
    df_temp = df_temp[df_temp['NoRekening'].isin(norek_kolek)]

# ── Filter 3: Status Pelunasan ──
pelunasan_list = sorted(df_temp['StatusPelunasan'].dropna().unique().tolist())
selected_pelunasan = st.sidebar.multiselect("Pilih Status Pelunasan", options=pelunasan_list)
if selected_pelunasan:
    df_temp = df_temp[df_temp['StatusPelunasan'].isin(selected_pelunasan)]

# ── Filter 4: Status Restruk ──
restruk_info_temp = df_temp.groupby('NoRekening')['TanggalValuta'].nunique()
df_temp['Is_Restruk_Temp'] = df_temp['NoRekening'].map(
    lambda x: "Restruk" if restruk_info_temp.get(x, 0) > 1 else "Non-Restruk"
)
restruk_options = sorted(df_temp['Is_Restruk_Temp'].unique().tolist())
selected_restruk = st.sidebar.multiselect("Pilih Status Restruk", options=restruk_options)
if selected_restruk:
    df_temp = df_temp[df_temp['Is_Restruk_Temp'].isin(selected_restruk)]

# ── Filter 5: CIF ──
cif_list = sorted(df_temp['CIF'].dropna().unique().tolist())
selected_cif = st.sidebar.multiselect("Pilih CIF", options=cif_list)
if selected_cif:
    df_temp = df_temp[df_temp['CIF'].isin(selected_cif)]

# ── Filter 6: Nama Debitur ──
debitur_list = sorted(df_temp['NamaDebitur'].dropna().unique().tolist())
selected_debitur = st.sidebar.multiselect("Pilih Nama Debitur", options=debitur_list)
if selected_debitur:
    df_temp = df_temp[df_temp['NamaDebitur'].isin(selected_debitur)]

# ── Filter 7: No Rekening ──
norek_list = sorted(df_temp['NoRekening'].dropna().unique().tolist())
selected_norek = st.sidebar.multiselect("Pilih No Rekening", options=norek_list)
if selected_norek:
    df_temp = df_temp[df_temp['NoRekening'].isin(selected_norek)]

# ==========================================
# 4. df_filtered = hasil akhir cascading filter
# ==========================================
# df_temp sudah mengandung SEMUA filter sidebar (periode, segmen, kolek,
# pelunasan, restruk, cif, debitur, norek) — langsung pakai sebagai df_filtered.
df_filtered = df_temp.copy()

# ==========================================
# 5. Judul & Pengolahan Data Pivot
# ==========================================
st.title("📊 Dashboard Tren Kolektibilitas")

if df_filtered.empty:
    st.warning("Data tidak ditemukan dengan kombinasi filter tersebut.")
else:
    df_filtered = df_filtered.sort_values(['CIF', 'NoRekening', 'TanggalValuta', 'DateYear', 'DateMonth'])

    # Identifikasi Restruk
    restruk_info = df_filtered.groupby('NoRekening')['TanggalValuta'].nunique()
    df_filtered['Is_Restruk'] = df_filtered['NoRekening'].map(lambda x: 1 if restruk_info[x] > 1 else 0)

    # Periode & SortKey
    df_filtered['SortKey'] = df_filtered['DateYear'] * 100 + df_filtered['DateMonth']
    df_filtered['Periode']  = 'M' + df_filtered['DateMonth'].astype(str) + '-' + df_filtered['DateYear'].astype(str).str[-2:]
    ordered_periods = df_filtered.sort_values('SortKey')['Periode'].unique()

    # Ambil JenisFasilitas & Segmen terkini per NoRekening
    idx_terkini = df_filtered.groupby('NoRekening')['SortKey'].idxmax()
    df_info_terkini = df_filtered.loc[idx_terkini, ['NoRekening', 'JenisFasilitas', 'Segmen']]

    # Pivot Tren
    df_trend = df_filtered.pivot_table(
        index=['CIF', 'NamaDebitur', 'NoRekening', 'Is_Restruk'],
        columns='Periode',
        values='Kolektibilitas',
        aggfunc='max'
    )
    valid_periods = [p for p in ordered_periods if p in df_trend.columns]
    df_trend = df_trend[valid_periods].reset_index()

    # Gabungkan info terkini
    df_trend = pd.merge(df_trend, df_info_terkini, on='NoRekening', how='left')
    kolom_identitas = ['CIF', 'NamaDebitur', 'NoRekening', 'Is_Restruk', 'Segmen', 'JenisFasilitas']
    df_trend = df_trend[kolom_identitas + valid_periods]

    # Metrik Ringkas
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Debitur",    df_trend['NamaDebitur'].nunique())
    col2.metric("Total Rekening",   df_trend['NoRekening'].nunique())
    col3.metric("Rekening Restruk", df_trend[df_trend['Is_Restruk'] == 1]['NoRekening'].nunique())

    st.markdown("### Tabel Tren Kolektibilitas Berdasarkan Filter")
    st.dataframe(df_trend, use_container_width=True)

    # ==========================================
    # 6. Visualisasi
    # ==========================================
    st.markdown("---")
    st.markdown("### 📈 Visualisasi Data")

    # --- A. Line Chart ---
    st.markdown("#### Tren Kolektibilitas per Rekening")
    top_10_norek = df_trend['NoRekening'].unique()[:10].tolist()
    selected_chart_norek = st.multiselect(
        "Pilih No. Rekening (Maksimal 10 disarankan):",
        options=df_trend['NoRekening'].unique().tolist(),
        default=top_10_norek
    )

    if selected_chart_norek:
        df_line = df_filtered[df_filtered['NoRekening'].isin(selected_chart_norek)].copy()

        # Label legend: NoRekening | NamaDebitur terkini
        nama_map = (
            df_line.sort_values('SortKey')
            .groupby('NoRekening')['NamaDebitur']
            .last()
            .to_dict()
        )
        df_line['Label'] = df_line['NoRekening'].map(
            lambda x: f"{x} | {nama_map.get(x, '')}"
        )

        # Urutkan periode kronologis
        df_line['Periode'] = pd.Categorical(df_line['Periode'], categories=valid_periods, ordered=True)
        df_line = df_line.sort_values('Periode')

        fig_line = px.line(
            df_line,
            x='Periode',
            y='Kolektibilitas',
            color='Label',
            markers=True,
            title='Tren Kolektibilitas per Rekening',
            labels={
                'Kolektibilitas': 'Kolektibilitas',
                'Periode': 'Periode',
                'Label': 'No Rekening | Debitur'
            },
            category_orders={'Periode': list(valid_periods)},
        )

        fig_line.update_traces(
            mode='lines+markers',
            marker=dict(size=8),
            line=dict(width=2),
            hovertemplate='<b>%{fullData.name}</b><br>Periode: %{x}<br>Kolektibilitas: %{y}<extra></extra>',
        )

        fig_line.update_layout(
            yaxis=dict(
                tickmode='array',
                tickvals=[1, 2, 3, 4, 5],
                ticktext=['1 - Lancar', '2 - DPK', '3 - KL', '4 - Diragukan', '5 - Macet'],
                range=[0.5, 5.5],
                title='Kolektibilitas',
                gridcolor='rgba(200,200,200,0.3)',
            ),
            xaxis=dict(title='Periode', tickangle=-30),
            legend=dict(
                title='No Rekening | Debitur',
                orientation='v',
                x=1.01,
                y=1,
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='rgba(200,200,200,0.5)',
                borderwidth=1,
            ),
            hovermode='x unified',
            height=480,
            margin=dict(t=60, b=60, r=300),
        )

        st.plotly_chart(fig_line, use_container_width=True)
        st.caption("💡 Klik nama di legend untuk sembunyikan/tampilkan garis. Double-click untuk isolasi satu garis.")
    else:
        st.info("Pilih setidaknya satu NoRekening untuk menampilkan grafik tren.")

    # --- B. Distribusi Kolektibilitas ---
    if len(valid_periods) > 0:
        latest_period = valid_periods[-1]
        st.markdown(f"#### Distribusi Posisi Kolektibilitas Terakhir ({latest_period})")

        df_latest = df_filtered[df_filtered['Periode'] == latest_period]
        dist_data = df_latest.groupby('Kolektibilitas')['NoRekening'].nunique().reset_index()
        dist_data.columns = ['Kolektibilitas', 'Jumlah Rekening']

        kol_labels = {1: "1 - Lancar", 2: "2 - DPK", 3: "3 - KL", 4: "4 - Diragukan", 5: "5 - Macet"}
        dist_data['Status'] = dist_data['Kolektibilitas'].map(lambda x: kol_labels.get(x, f"Kol {x}"))

        dist_data['Jumlah Rekening'] = dist_data['Jumlah Rekening'].astype(int)
        total_rekening = dist_data['Jumlah Rekening'].sum()
        dist_data['Persentase'] = (dist_data['Jumlah Rekening'] / total_rekening * 100).round(1)

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            fig_pie = px.pie(
                dist_data,
                names='Status',
                values='Jumlah Rekening',
                title='Persentase Kolektibilitas',
                hole=0.35,
            )
            fig_pie.update_traces(
                textposition='outside',
                texttemplate='<b>%{label}</b><br>%{percent:.1%}',
                hovertemplate='<b>%{label}</b><br>Jumlah Rekening: %{value}<br>Persentase: %{percent:.1%}<extra></extra>',
                pull=[0.05] * len(dist_data),
                textfont_size=12,
            )
            fig_pie.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                margin=dict(t=60, b=80, l=20, r=20),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_chart2:
            fig_bar = px.bar(
                dist_data,
                x='Status',
                y='Jumlah Rekening',
                text='Jumlah Rekening',
                title='Jumlah Rekening per Kolektibilitas',
                color='Status',
                custom_data=['Persentase']
            )
            fig_bar.update_traces(
                texttemplate='%{text} (%{customdata[0]:.1f}%)',
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Jumlah: %{y}<br>Persentase: %{customdata[0]:.1f}%<extra></extra>'
            )
            fig_bar.update_layout(
                showlegend=False,
                yaxis=dict(title='Jumlah Rekening'),
                margin=dict(t=60, b=40)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
