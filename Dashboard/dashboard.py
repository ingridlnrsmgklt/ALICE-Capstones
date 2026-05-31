import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="A.L.I.C.E Financial Dashboard",
    page_icon="💸",
    layout="wide"
)

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "alice_transactions_final.csv")

    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["weekly_budget_limit"] = pd.to_numeric(df["weekly_budget_limit"], errors="coerce")
    df["monthly_income"] = pd.to_numeric(df["monthly_income"], errors="coerce")
    df["is_impulsive"] = pd.to_numeric(df["is_impulsive"], errors="coerce").fillna(0).astype(int)

    return df

df = load_data()

# =========================
# HELPER
# =========================
def rupiah(value):
    return f"Rp {value:,.0f}".replace(",", ".")

def classify_user(row):
    if row["expense_ratio"] > 1:
        return "Overspending"
    elif row["impulsive_rate"] > 0.5:
        return "Impulsive"
    else:
        return "Controlled"

# =========================
# SIDEBAR FILTER
# =========================
st.sidebar.title("🔎 Filter Dashboard")

user_options = ["All"] + sorted(df["user_id"].unique().tolist())
selected_user = st.sidebar.selectbox("Pilih User ID", user_options)

month_options = ["All"] + sorted(df["month"].unique().tolist())
selected_month = st.sidebar.selectbox("Pilih Bulan", month_options)

category_options = ["All"] + sorted(df["category"].unique().tolist())
selected_category = st.sidebar.selectbox("Pilih Kategori", category_options)

filtered_df = df.copy()

if selected_user != "All":
    filtered_df = filtered_df[filtered_df["user_id"] == selected_user]

if selected_month != "All":
    filtered_df = filtered_df[filtered_df["month"] == selected_month]

if selected_category != "All":
    filtered_df = filtered_df[filtered_df["category"] == selected_category]

# =========================
# WEEKLY AGGREGATION
# =========================
weekly_df = filtered_df.groupby(["user_id", "year", "week_number"]).agg(
    total_spent=("amount", "sum"),
    impulsive_spent=("amount", lambda x: x[filtered_df.loc[x.index, "is_impulsive"] == 1].sum()),
    weekly_budget_limit=("weekly_budget_limit", "first"),
    impulsive_rate=("is_impulsive", "mean")
).reset_index()

weekly_df["expense_ratio"] = weekly_df["total_spent"] / weekly_df["weekly_budget_limit"]
weekly_df["pct_spent_total"] = weekly_df["expense_ratio"] * 100
weekly_df["pct_spent_impulsive"] = weekly_df["impulsive_spent"] / weekly_df["weekly_budget_limit"] * 100
weekly_df["is_near_budget"] = weekly_df["expense_ratio"] >= 0.8
weekly_df["is_over_budget"] = weekly_df["expense_ratio"] > 1
weekly_df["user_behavior"] = weekly_df.apply(classify_user, axis=1)
weekly_df["potential_savings"] = weekly_df["total_spent"] * 0.15

def alarm_status(pct):
    if pct < 50:
        return "Aman (<50%)"
    elif pct < 80:
        return "Waspada (50-79%)"
    else:
        return "Alarm 80% (>=80%)"

weekly_df["alarm_status"] = weekly_df["pct_spent_impulsive"].apply(alarm_status)

# =========================
# TITLE
# =========================
st.title("💸 A.L.I.C.E Financial Dashboard")
st.caption("Artificial Intelligence for Literacy, Investment, and Cost Efficiency")

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📌 Overview",
    "🚨 Preventive Analytics",
    "📈 Productive Analytics",
    "👤 User Behavior",
    "🤖 AI Recommendation",
    "🎯 Business Conclusion"
])

# =========================
# TAB 1: OVERVIEW
# =========================
with tab1:
    st.subheader("Executive Summary")

    total_users = filtered_df["user_id"].nunique()
    total_transactions = len(filtered_df)
    total_spending = filtered_df["amount"].sum()
    avg_transaction = filtered_df["amount"].mean()
    avg_monthly_income = filtered_df["monthly_income"].mean()

    lifestyle_spending = filtered_df[filtered_df["is_impulsive"] == 1]["amount"].sum()
    potential_saving = lifestyle_spending * 0.15

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Users", total_users)
    col2.metric("Total Transactions", f"{total_transactions:,}")
    col3.metric("Total Spending", rupiah(total_spending))
    col4.metric("Avg Transaction", rupiah(avg_transaction))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Avg Monthly Income", rupiah(avg_monthly_income))
    col6.metric("Lifestyle Spending", rupiah(lifestyle_spending))
    col7.metric("Potential Saving 15%", rupiah(potential_saving))
    col8.metric("Potential Saving 5 Years", rupiah(potential_saving * 5))

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        category_spending = filtered_df.groupby("category")["amount"].sum().reset_index()
        fig = px.pie(
            category_spending,
            names="category",
            values="amount",
            title="Distribusi Pengeluaran Berdasarkan Kategori",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        monthly_spending = filtered_df.groupby("month")["amount"].sum().reset_index()
        fig = px.line(
            monthly_spending,
            x="month",
            y="amount",
            markers=True,
            title="Tren Total Pengeluaran Bulanan"
        )
        fig.update_layout(yaxis_title="Total Spending")
        st.plotly_chart(fig, use_container_width=True)

    st.info(
        "Insight: Dashboard menunjukkan gambaran umum pola pengeluaran user, "
        "termasuk total transaksi, kategori dominan, dan potensi dana yang dapat dialihkan menjadi saving/investasi."
    )

# =========================
# TAB 2: PREVENTIVE ANALYTICS
# =========================
with tab2:
    st.subheader("Preventive Analytics: Alarm Keuangan 80%")

    if weekly_df.empty:
        st.warning("Data tidak tersedia untuk filter yang dipilih.")
    else:
        avg_expense_ratio = weekly_df["expense_ratio"].mean()
        overbudget_rate = weekly_df["is_over_budget"].mean() * 100
        near_budget_rate = weekly_df["is_near_budget"].mean() * 100

        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Budget Usage", f"{avg_expense_ratio*100:.1f}%")
        col2.metric("Near Budget Weeks", f"{near_budget_rate:.1f}%")
        col3.metric("Overbudget Weeks", f"{overbudget_rate:.1f}%")

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=avg_expense_ratio * 100,
            title={"text": "Average Budget Usage (%)"},
            gauge={
                "axis": {"range": [0, 150]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 50], "color": "lightgreen"},
                    {"range": [50, 80], "color": "khaki"},
                    {"range": [80, 150], "color": "lightcoral"}
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 80
                }
            }
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)

        risk_summary = weekly_df.groupby("alarm_status").agg(
            total_weeks=("user_id", "count"),
            deficit_rate=("is_over_budget", "mean"),
            avg_total_spending=("pct_spent_total", "mean")
        ).reset_index()

        risk_summary["deficit_rate"] *= 100

        fig = px.bar(
            risk_summary,
            x="alarm_status",
            y="deficit_rate",
            text=risk_summary["deficit_rate"].round(1),
            title="Risiko Overbudget Berdasarkan Status Alarm Lifestyle",
            labels={
                "alarm_status": "Status Alarm",
                "deficit_rate": "Risiko Overbudget (%)"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

        weekly_trend = weekly_df.groupby("week_number").agg(
            total_spent=("total_spent", "mean"),
            weekly_budget_limit=("weekly_budget_limit", "mean")
        ).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=weekly_trend["week_number"],
            y=weekly_trend["total_spent"],
            mode="lines+markers",
            name="Average Weekly Spending"
        ))
        fig.add_trace(go.Scatter(
            x=weekly_trend["week_number"],
            y=weekly_trend["weekly_budget_limit"],
            mode="lines",
            name="Average Weekly Budget"
        ))
        fig.update_layout(
            title="Tren Pengeluaran Mingguan vs Budget",
            xaxis_title="Week Number",
            yaxis_title="Amount"
        )
        st.plotly_chart(fig, use_container_width=True)

        impulsive_category = filtered_df[filtered_df["is_impulsive"] == 1].groupby("category")["amount"].sum().reset_index()
        fig = px.bar(
            impulsive_category.sort_values("amount", ascending=True),
            x="amount",
            y="category",
            orientation="h",
            title="Kategori Impulsif Penyebab Kebocoran Pengeluaran"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.success(
            "Insight: Threshold 80% dapat digunakan sebagai indikator early warning karena minggu dengan status alarm "
            "menunjukkan risiko overbudget yang lebih tinggi."
        )

# =========================
# TAB 3: PRODUCTIVE ANALYTICS
# =========================
with tab3:
    st.subheader("Productive Analytics: Lifestyle Leakage to Investment")

    lifestyle_df = filtered_df[filtered_df["is_impulsive"] == 1]

    annual_lifestyle = lifestyle_df.groupby("user_id").agg(
        total_annual_lifestyle=("amount", "sum"),
        avg_lifestyle_transaction=("amount", "mean")
    ).reset_index()

    if annual_lifestyle.empty:
        st.warning("Tidak ada data lifestyle untuk filter yang dipilih.")
    else:
        saving_rate = st.slider(
            "Simulasi Pengurangan Lifestyle Spending (%)",
            min_value=0,
            max_value=50,
            value=15,
            step=1
        ) / 100

        annual_lifestyle["potential_annual_investment"] = annual_lifestyle["total_annual_lifestyle"] * saving_rate
        annual_lifestyle["potential_monthly_investment"] = annual_lifestyle["potential_annual_investment"] / 12
        annual_lifestyle["potential_5yr_investment"] = annual_lifestyle["potential_annual_investment"] * 5

        avg_lifestyle = annual_lifestyle["total_annual_lifestyle"].mean()
        avg_annual_investment = annual_lifestyle["potential_annual_investment"].mean()
        avg_monthly_investment = annual_lifestyle["potential_monthly_investment"].mean()
        avg_5yr_investment = annual_lifestyle["potential_5yr_investment"].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Avg Lifestyle / Year", rupiah(avg_lifestyle))
        col2.metric("Potential Saving / Month", rupiah(avg_monthly_investment))
        col3.metric("Potential Saving / Year", rupiah(avg_annual_investment))
        col4.metric("Potential Saving / 5 Years", rupiah(avg_5yr_investment))

        conversion_df = pd.DataFrame({
            "Metric": [
                "Lifestyle Spending / Year",
                f"Saving {saving_rate*100:.0f}% / Year",
                "Accumulated Saving / 5 Years"
            ],
            "Amount": [
                avg_lifestyle,
                avg_annual_investment,
                avg_5yr_investment
            ]
        })

        fig = px.bar(
            conversion_df,
            x="Metric",
            y="Amount",
            text=conversion_df["Amount"].apply(rupiah),
            title="Simulasi Konversi Pengeluaran Lifestyle Menjadi Dana Produktif"
        )
        st.plotly_chart(fig, use_container_width=True)

        def classify_spender(x):
            if x < 10_000_000:
                return "Low Spender"
            elif x < 25_000_000:
                return "Medium Spender"
            else:
                return "High Spender"

        annual_lifestyle["spender_segment"] = annual_lifestyle["total_annual_lifestyle"].apply(classify_spender)

        segment_summary = annual_lifestyle.groupby("spender_segment").agg(
            total_users=("user_id", "count"),
            avg_lifestyle=("total_annual_lifestyle", "mean"),
            avg_potential_investment=("potential_annual_investment", "mean")
        ).reset_index()

        fig = px.bar(
            segment_summary,
            x="spender_segment",
            y="avg_potential_investment",
            text=segment_summary["avg_potential_investment"].apply(rupiah),
            title="Potensi Dana Produktif Berdasarkan Segmentasi User"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.info(
            "Insight: Pengurangan kecil pada pengeluaran lifestyle dapat dikonversi menjadi dana produktif yang signifikan, "
            "terutama untuk user dengan kategori Medium dan High Spender."
        )

# =========================
# TAB 4: USER BEHAVIOR
# =========================
with tab4:
    st.subheader("User Behavior Analytics")

    if weekly_df.empty:
        st.warning("Data tidak tersedia untuk filter yang dipilih.")
    else:
        behavior_count = weekly_df["user_behavior"].value_counts().reset_index()
        behavior_count.columns = ["user_behavior", "count"]

        fig = px.pie(
            behavior_count,
            names="user_behavior",
            values="count",
            title="Distribusi Perilaku User",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

        fig = px.histogram(
            weekly_df,
            x="impulsive_rate",
            nbins=20,
            title="Distribusi Impulsive Rate Mingguan"
        )
        st.plotly_chart(fig, use_container_width=True)

        top_risk_users = weekly_df.groupby("user_id").agg(
            avg_expense_ratio=("expense_ratio", "mean"),
            overbudget_weeks=("is_over_budget", "sum"),
            avg_impulsive_rate=("impulsive_rate", "mean"),
            total_potential_savings=("potential_savings", "sum")
        ).reset_index()

        top_risk_users = top_risk_users.sort_values(
            ["overbudget_weeks", "avg_expense_ratio"],
            ascending=False
        ).head(10)

        top_risk_users["avg_expense_ratio"] = top_risk_users["avg_expense_ratio"] * 100
        top_risk_users["avg_impulsive_rate"] = top_risk_users["avg_impulsive_rate"] * 100

        st.write("Top 10 Risk Users")
        st.dataframe(top_risk_users, use_container_width=True)

        st.warning(
            "Insight: User dengan frekuensi overbudget tinggi dan impulsive rate besar perlu menjadi prioritas intervensi AI."
        )

# =========================
# TAB 5: AI RECOMMENDATION
# =========================
with tab5:
    st.subheader("AI Financial Recommendation")

    if weekly_df.empty:
        st.warning("Data tidak tersedia untuk filter yang dipilih.")
    else:
        avg_ratio = weekly_df["expense_ratio"].mean()
        avg_impulsive_rate = weekly_df["impulsive_rate"].mean()
        avg_potential_saving = weekly_df["potential_savings"].mean()

        st.write("### Financial Health Status")

        if avg_ratio > 1:
            st.error("🚨 Status: Overspending")
            st.write(
                "Pengeluaran rata-rata sudah melewati budget mingguan. "
                "Disarankan untuk membatasi transaksi kategori lifestyle selama minggu berjalan."
            )
        elif avg_ratio >= 0.8:
            st.warning("⚠️ Status: Near Budget Limit")
            st.write(
                "Pengeluaran sudah mendekati 80% dari budget. "
                "User sebaiknya mulai mengurangi transaksi non-primer."
            )
        else:
            st.success("✅ Status: Controlled")
            st.write(
                "Pengeluaran masih berada dalam batas aman. "
                "User dapat mempertahankan pola konsumsi saat ini."
            )

        st.write("### Personalized Recommendation")

        if avg_impulsive_rate > 0.5:
            st.warning(
                "Impulsive rate cukup tinggi. Fokus utama rekomendasi AI adalah mengurangi pengeluaran Entertainment, Shopping, dan Hobby."
            )
        else:
            st.info(
                "Impulsive rate masih terkendali. Rekomendasi AI dapat diarahkan pada konsistensi saving dan investasi rutin."
            )

        st.write("### Saving Opportunity")
        st.success(
            f"Dengan mengurangi sekitar 15% dari pengeluaran mingguan, user berpotensi menghemat rata-rata "
            f"{rupiah(avg_potential_saving)} per minggu."
        )

        st.write("### Suggested Action")
        st.markdown("""
        - Batasi transaksi lifestyle ketika budget usage mencapai 80%.
        - Prioritaskan kebutuhan dasar sebelum entertainment dan shopping.
        - Alihkan hasil penghematan ke dana darurat atau investasi rendah risiko.
        - Gunakan notifikasi mingguan sebagai reminder sebelum terjadi overbudget.
        """)

# =========================
# TAB 6: BUSINESS CONCLUSION
# =========================
with tab6:
    st.header("🎯 Kesimpulan Business Questions")
    st.caption("Jawaban konkrit atas pertanyaan bisnis berdasarkan data agregasi pada dashboard saat ini.")

    # --- Kalkulasi Dinamis untuk Kesimpulan ---
    # 1. Kalkulasi BQ 1 (Preventif)
    # Menghitung probabilitas defisit JIKA pengeluaran impulsif sudah menyentuh ambang batas alarm (80%)
    if weekly_df.empty:
        overbudget_prob = 0
    else:
        # Menggunakan pct_spent_impulsive agar match 100% dengan bar chart Tab 2
        high_risk_weeks = weekly_df[weekly_df["pct_spent_impulsive"] >= 80]
        if high_risk_weeks.empty:
            overbudget_prob = 0
        else:
            overbudget_prob = high_risk_weeks["is_over_budget"].mean() * 100

    # 2. Kalkulasi BQ 2 (Produktif)
    # Menghitung potensi tabungan tahunan dari penekanan 15% biaya impulsif
    lifestyle_df_c = filtered_df[filtered_df["is_impulsive"] == 1]
    annual_lifestyle_c = lifestyle_df_c.groupby("user_id")["amount"].sum().reset_index()
    
    if annual_lifestyle_c.empty:
        avg_annual_savings = 0
    else:
        avg_annual_savings = (annual_lifestyle_c["amount"] * 0.15).mean()

    # --- TAMPILAN BQ 1 ---
    st.subheader("A. Analisis Preventif & Forecasting")
    st.info(
        "**Pertanyaan Bisnis:**\n\n"
        "*Sejauh mana efektivitas model peramalan (Cashflow forecasting) dengan ambang batas (threshold) "
        "pada kategori pengeluaran impulsive (hiburan & hobi) dalam mendeteksi risiko dan mencegah defisit "
        "kas mingguan pada pengguna usia 18-25 tahun?*"
    )
    
    st.markdown(
        f"**Jawaban Berdasarkan Analitik:**\n\n"
        f"Berdasarkan visualisasi pada **Tab Preventive Analytics**, penetapan ambang batas terbukti sangat krusial. "
        f"Model data mendemonstrasikan bahwa ketika tren pengeluaran impulsif pengguna menembus batas alarm peringatan dini (80%), "
        f"probabilitas mereka untuk berujung pada defisit kas (*overbudgeting*) di akhir minggu mencapai angka yang sangat fatal, yaitu **{overbudget_prob:.1f}%**.\n\n"
        f"**Kesimpulan:** Sistem *Early Warning* A.L.I.C.E secara empiris tervalidasi sangat efektif dan mutlak diperlukan. Intervensi alarm "
        f"sebelum pengeluaran gaya hidup memakan habis kuota anggaran memberi ruang bagi pengguna untuk mengerem perilaku impulsifnya sebelum saldo kas benar-benar defisit."
    )

    st.divider()

    # --- TAMPILAN BQ 2 ---
    st.subheader("B. Analisis Produktif & Pemulihan Keuangan")
    st.success(
        "**Pertanyaan Bisnis:**\n\n"
        "*Berapa potensi optimalisasi anggaran berupa alokasi tabungan tahunan yang dapat dihasilkan "
        "jika model AI berhasil menekan pengeluaran kategori lifestyle sebesar 15% setiap bulan bagi pengguna "
        "dengan disposable income menengah ke bawah?*"
    )
    
    st.markdown(
        f"**Jawaban Berdasarkan Analitik:**\n\n"
        f"Melalui simulasi matematis pada **Tab Productive Analytics**, apabila model AI berhasil menekan perilaku "
        f"kebocoran halus (*lifestyle inflation*) sebesar 15%, maka rata-rata pengguna pada populasi ini dapat menyelamatkan "
        f"ekses dana yang bisa dikonversi menjadi alokasi tabungan (*savings*) dengan rata-rata **{rupiah(avg_annual_savings)} per tahun**.\n\n"
        f"**Kesimpulan:** Rekomendasi persentase menabung dan investasi dari A.L.I.C.E sangat rasional, terukur secara data, "
        f"dan berdampak masif bagi pemulihan ketahanan finansial (*disposable income*) pengguna jangka panjang."
    )

# =========================
# FOOTER
# =========================
st.divider()
st.caption("A.L.I.C.E Dashboard | Financial Literacy, Investment, and Cost Efficiency")
