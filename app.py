from datetime import datetime
import io
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import streamlit as st

# ---------------------------------------------------------
# 1. CẤU HÌNH TRANG WEB & ẨN GIAO DIỆN HỆ THỐNG
# ---------------------------------------------------------
st.set_page_config(
    page_title="Tính nhanh UL",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="auto",
)

hide_ui_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stToolbar"] {display: none !important; height: 0px !important; visibility: hidden !important;}
    [data-testid="stDecoration"] {visibility: hidden !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important;}
    .viewerBadge_container__1QSob {display: none !important;}
    iframe[src*="streamlit.app"] {display: none !important;}
    button[kind="header"] {display: none !important;}
    </style>
"""
st.markdown(hide_ui_style, unsafe_allow_html=True)


def fmt_vnd(amount):
    return f"{int(amount):,}".replace(",", ".") + " VNĐ"


def fmt_vnd_short(amount):
    return f"{int(amount):,}".replace(",", ".")


def get_sam_multipliers(prod_code, age):
    if prod_code == "UL2":
        if age <= 30:
            return 25, 90
        elif age <= 40:
            return 20, 75
        elif age <= 50:
            return 15, 55
        elif age <= 60:
            return 10, 35
        else:
            return 5, 20
    else:  # UL3
        if age <= 30:
            return 20, 100
        elif age <= 40:
            return 18, 80
        elif age <= 50:
            return 15, 60
        elif age <= 60:
            return 10, 40
        else:
            return 5, 25


st.title("🛡️ MINH HỌA UL")
st.caption(
    "Công cụ hỗ trợ tư vấn & tính toán quyền lợi sản phẩm MAP Life Hạnh Phúc (UL2) & Bình An (UL3) kèm Sản phẩm bổ trợ"
)

# ---------------------------------------------------------
# 2. THANH THÔNG TIN BÊN (SIDEBAR)
# ---------------------------------------------------------
st.sidebar.header("📋 THÔNG TIN")

product_choice = st.sidebar.selectbox(
    "Lựa chọn sản phẩm bảo hiểm:",
    ["MAP Life Hạnh Phúc (UL2)", "MAP Life Bình An (UL3)"],
    key="prod_choice",
)

if "UL2" in product_choice:
    prod_code = "UL2"
    prod_name = "MAP Life Hạnh Phúc"
    min_term, max_term = 4, 20
    default_tp_m = 10.0
    abs_min_tp = 10_000_000
    abs_min_sa = 250_000_000
else:
    prod_code = "UL3"
    prod_name = "MAP Life Bình An"
    min_term, max_term = 3, 20
    default_tp_m = 8.0
    abs_min_tp = 8_000_000
    abs_min_sa = 200_000_000

st.sidebar.markdown("---")
st.sidebar.subheader("👤 Thông tin Khách hàng")

fullname = st.sidebar.text_input("Họ và tên NĐBH", "Nguyễn Văn A")
gender = st.sidebar.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)

col_d, col_m, col_y = st.sidebar.columns(3)
with col_y:
    birth_year = col_y.selectbox(
        "Năm sinh", range(1950, 2027), index=40, key="b_year"
    )
with col_m:
    birth_month = col_m.selectbox(
        "Tháng", range(1, 13), index=0, key="b_month"
    )
with col_d:
    birth_day = col_d.selectbox("Ngày", range(1, 32), index=0, key="b_day")

today = datetime.now()
try:
    dob = datetime(birth_year, birth_month, birth_day)
    entry_age = (
        today.year
        - dob.year
        - ((today.month, today.day) < (dob.month, dob.day))
    )
except ValueError:
    entry_age = today.year - birth_year

st.sidebar.info(
    f"💡 Ngày sinh: **{birth_day:02d}/{birth_month:02d}/{birth_year}** | Tuổi tham gia: **{entry_age} tuổi**"
)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Thông tin Hợp đồng chính")

if (
    "prev_prod_tp" not in st.session_state
    or st.session_state.prev_prod_tp != prod_code
):
    st.session_state.tp_input = default_tp_m
    st.session_state.prev_prod_tp = prod_code

tp_in_millions = st.sidebar.number_input(
    "Phí bảo hiểm cơ bản hàng năm (Triệu VNĐ):",
    min_value=float(abs_min_tp / 1_000_000),
    step=1.0,
    format="%g",
    key="tp_input",
)
target_premium = int(tp_in_millions * 1_000_000)

if target_premium < abs_min_tp:
    st.sidebar.error(
        f"⚠️ **Cảnh báo:** Phí bảo hiểm tối thiểu cho {prod_name} là"
        f" **{fmt_vnd(abs_min_tp)}**!"
    )
else:
    st.sidebar.success(f"👉 **Phí cơ bản:** `{fmt_vnd(target_premium)}`")

prem_term = st.sidebar.slider(
    "Thời hạn đóng phí dự kiến (năm):",
    min_value=min_term,
    max_value=max_term,
    value=10,
    key="term_slider",
)

sam_min_mult, sam_max_mult = get_sam_multipliers(prod_code, entry_age)
dynamic_min_sa = max(abs_min_sa, target_premium * sam_min_mult)
dynamic_max_sa = target_premium * sam_max_mult
min_sa_m = float(dynamic_min_sa / 1_000_000)

config_changed = (
    st.session_state.get("prev_prod") != prod_code
    or st.session_state.get("prev_tp") != target_premium
    or st.session_state.get("prev_age") != entry_age
)

if config_changed or "sa_input" not in st.session_state:
    st.session_state.sa_input = min_sa_m
    st.session_state.prev_prod = prod_code
    st.session_state.prev_tp = target_premium
    st.session_state.prev_age = entry_age

sa_in_millions = st.sidebar.number_input(
    "Số Tiền Bảo Hiểm (STBH) chính (Triệu VNĐ):",
    min_value=0.0,
    step=10.0,
    format="%g",
    key="sa_input",
)
sum_assured = int(sa_in_millions * 1_000_000)
st.sidebar.success(f"👉 **STBH chính:** `{fmt_vnd(sum_assured)}`")

st.sidebar.caption(
    f"📌 *Hạn mức STBH động ({entry_age} tuổi, phí {fmt_vnd(target_premium)}):*\n"
    f"- Tối thiểu (Min): **{fmt_vnd(dynamic_min_sa)}**\n"
    f"- Tối đa (Max): **{fmt_vnd(dynamic_max_sa)}**"
)

if sum_assured < dynamic_min_sa or sum_assured > dynamic_max_sa:
    st.sidebar.warning(
        f"⚠️ STBH vượt ngoài phạm vi cho phép ({fmt_vnd(dynamic_min_sa)} - {fmt_vnd(dynamic_max_sa)})"
    )

# ---------------------------------------------------------
# CẤU HÌNH SẢN PHẨM BỔ TRỢ (RIDERS)
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Sản phẩm bổ trợ (Riders)")

use_cir1 = st.sidebar.checkbox("Bảo hiểm Bệnh hiểm nghèo (CIR1)", value=False)
sa_cir1 = 0
if use_cir1:
    sa_cir1_m = st.sidebar.number_input(
        "STBH CIR1 (Triệu VNĐ - Tối đa 400tr):",
        min_value=100.0,
        max_value=400.0,
        value=100.0,
        step=100.0,
        format="%g",
    )
    sa_cir1 = int(sa_cir1_m * 1_000_000)

use_cir2 = st.sidebar.checkbox(
    "Bảo hiểm Bệnh hiểm nghèo nâng cao (CIR2)", value=False
)
sa_cir2 = 0
if use_cir2:
    sa_cir2_m = st.sidebar.number_input(
        "STBH CIR2 (Triệu VNĐ - Tối đa 500tr):",
        min_value=100.0,
        max_value=500.0,
        value=100.0,
        step=100.0,
        format="%g",
    )
    sa_cir2 = int(sa_cir2_m * 1_000_000)

use_pa = st.sidebar.checkbox("Bảo hiểm hỗ trợ TTVV do Tai Nạn (PDD1)", value=False)
sa_pa = 0
if use_pa:
    sa_pa_m = st.sidebar.number_input(
        "STBH Tai nạn (Triệu VNĐ - Tối đa 500tr):",
        min_value=100.0,
        max_value=500.0,
        value=100.0,
        step=100.0,
        format="%g",
    )
    sa_pa = int(sa_pa_m * 1_000_000)


# ---------------------------------------------------------
# 3. ENGINE TÍNH TOÁN DÒNG TIỀN (CÓ TÍCH HỢP HỆ SỐ GIỚI TÍNH)
# ---------------------------------------------------------
def generate_ul_projection(
    prod_code,
    entry_age,
    tp,
    prem_term,
    sa,
    sa_cir1,
    sa_cir2,
    sa_pa,
    gender,
    interest_rate=0.05,
):
    records = []
    accumulated_prem = 0
    account_value = 0
    init_fee_rate = {1: 0.50, 2: 0.30, 3: 0.20, 4: 0.20, 5: 0.20}

    # Hệ số điều chỉnh phí rủi ro theo giới tính (Nam = 1.0, Nữ = 0.85 do tỷ lệ rủi ro thấp hơn)
    gender_factor = 1.0 if gender == "Nam" else 0.85

    sa_to_tp_ratio = sa / tp if tp > 0 else 0
    special_bonus_rate = (
        min(1.0, max(0.25, sa_to_tp_ratio / 60.0))
        if prod_code == "UL2"
        else 0.0
    )

    max_years = max(1, 100 - entry_age)

    for pol_year in range(1, max_years + 1):
        current_age = entry_age + pol_year - 1

        rider_prem_cir1 = (
            sa_cir1 * (0.0008 + current_age * 0.00005) * gender_factor
            if sa_cir1 > 0
            else 0
        )
        rider_prem_cir2 = (
            sa_cir2 * (0.0012 + current_age * 0.00006) * gender_factor
            if sa_cir2 > 0
            else 0
        )
        rider_prem_pa = sa_pa * 0.0012 * gender_factor if sa_pa > 0 else 0

        annual_rider_prem = (
            rider_prem_cir1 + rider_prem_cir2 + rider_prem_pa
            if pol_year <= prem_term
            else 0
        )

        yearly_prem_main = tp if pol_year <= prem_term else 0
        yearly_prem_total = yearly_prem_main + annual_rider_prem
        accumulated_prem += yearly_prem_total

        fee_rate = init_fee_rate.get(pol_year, 0.02)
        invest_prem = yearly_prem_main * (1 - fee_rate)

        bonus = 0
        if prod_code == "UL2":
            if pol_year == 4:
                bonus += tp * 0.06
            elif pol_year == 8:
                bonus += tp * 0.12
            elif pol_year >= 12 and pol_year % 4 == 0:
                bonus += tp * 0.18

            if pol_year == 10:
                bonus += tp * special_bonus_rate

        else:  # UL3 - Chỉ có thưởng định kỳ mỗi 3 năm
            if pol_year % 3 == 0:
                bonus += tp * 0.04

        coi_fee_main = (
            sa * (0.0015 + (current_age * 0.0001)) * gender_factor
        )

        account_value = (
            account_value + invest_prem - coi_fee_main + bonus
        ) * (1 + interest_rate)
        if account_value < 0:
            account_value = 0

        surrender_penalty = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.2}.get(
            pol_year, 0.0
        )
        surrender_val = max(0, account_value * (1 - surrender_penalty))
        death_benefit = max(sa, account_value)

        records.append({
            "Năm HĐ": pol_year,
            "Tuổi NĐBH": current_age,
            "Năm/Tuổi": f"{pol_year}/{current_age}",
            "Phí Đóng Dự Kiến": yearly_prem_total,
            "Tổng Phí Lũy Kế": accumulated_prem,
            "Thưởng Gắn Bó": bonus,
            "Quyền Lợi Tử Vong": death_benefit,
            "Giá Trị Tài Khoản": account_value,
            "Giá Trị Hoàn Lại": surrender_val,
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------
# 4. HÀM TẠO FILE PDF
# ---------------------------------------------------------
def create_pdf_report(
    fullname,
    prod_name,
    entry_age,
    sum_assured,
    target_premium,
    prem_term,
    df_p,
    sa_cir1,
    sa_cir2,
    sa_pa,
    gender,
):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 40, "BANG MINH HOA QUYEN LOI BAO HIEM")
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0, 0.3, 0.6)
    c.drawString(
        50,
        height - 60,
        f"San pham: {prod_name.replace('Hạnh Phúc', 'Hanh Phuc').replace('Bình An', 'Binh An')} ({gender})",
    )

    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(
        50,
        height - 85,
        f"Khach hang: {fullname} | Gioi tinh: {gender} | Tuoi: {entry_age}",
    )
    c.drawString(
        50,
        height - 100,
        f"STBH chinh: {fmt_vnd(sum_assured)} | Phi co ban: {fmt_vnd(target_premium)}/nam ({prem_term} nam)",
    )

    rider_str = "Bo tro: "
    if sa_cir1 > 0:
        rider_str += f"CIR1 ({fmt_vnd(sa_cir1)}) "
    if sa_cir2 > 0:
        rider_str += f"CIR2 ({fmt_vnd(sa_cir2)}) "
    if sa_pa > 0:
        rider_str += f"Tai nan ({fmt_vnd(sa_pa)})"
    if sa_cir1 == 0 and sa_cir2 == 0 and sa_pa == 0:
        rider_str += "Khong co"

    c.drawString(50, height - 115, rider_str)

    c.setFont("Helvetica-Bold", 8)
    y_start = height - 140
    c.drawString(
        50,
        y_start,
        "Nam/Tuoi    Phi Dong     Tong Phi     Thuong     Tu Vong     Gia Tri TK     Hoan Lai",
    )
    c.line(50, y_start - 5, width - 50, y_start - 5)

    c.setFont("Helvetica", 8)
    y = y_start - 20

    for index, row in df_p.iterrows():
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 8)
            y = height - 50

        line_str = (
            f"{row['Năm/Tuổi']:<11} "
            f"{fmt_vnd_short(row['Phí Đóng Dự Kiến']):<12} "
            f"{fmt_vnd_short(row['Tổng Phí Lũy Kế']):<13} "
            f"{fmt_vnd_short(row['Thưởng Gắn Bó']):<10} "
            f"{fmt_vnd_short(row['Quyền Lợi Tử Vong']):<11} "
            f"{fmt_vnd_short(row['Giá Trị Tài Khoản']):<14} "
            f"{fmt_vnd_short(row['Giá Trị Hoàn Lại'])}"
        )
        c.drawString(50, y, line_str)
        y -= 15

    c.save()
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------
# 5. HIỂN THỊ GIAO DIỆN WEB
# ---------------------------------------------------------
df_proj = generate_ul_projection(
    prod_code,
    entry_age,
    target_premium,
    prem_term,
    sum_assured,
    sa_cir1,
    sa_cir2,
    sa_pa,
    gender,
)

first_year_rider_prem = (
    (sa_cir1 * (0.0008 + entry_age * 0.00005) if sa_cir1 > 0 else 0)
    + (sa_cir2 * (0.0012 + entry_age * 0.00006) if sa_cir2 > 0 else 0)
    + (sa_pa * 0.0012 if sa_pa > 0 else 0)
)
total_first_year_prem = target_premium + first_year_rider_prem

col1, col2, col3, col4 = st.columns(4)
col1.metric("Sản phẩm", prod_name)
col2.metric("Số Tiền Bảo Hiểm", fmt_vnd(sum_assured))
col3.metric("Tổng Phí Năm Đầu", fmt_vnd(total_first_year_prem))
col4.metric(
    "Tổng Phí Dự Kiến",
    fmt_vnd(
        (target_premium * prem_term)
        + (first_year_rider_prem * prem_term if prem_term > 0 else 0)
    ),
)

st.markdown("---")

breakeven_df = df_proj[
    df_proj["Giá Trị Tài Khoản"] >= df_proj["Tổng Phí Lũy Kế"]
]

if not breakeven_df.empty:
    first_be = breakeven_df.iloc[0]
    be_year = int(first_be["Năm HĐ"])
    be_age = int(first_be["Tuổi NĐBH"])
    be_acc_val = fmt_vnd(first_be["Giá Trị Tài Khoản"])

    st.success(
        f"💡 **({prod_name} - {gender}):** Ở mức lãi suất giả định 5%/năm, Giá trị tài khoản hợp đồng sẽ **vượt Tổng phí đóng** từ **Năm hợp đồng thứ {be_year}** (lúc khách hàng **{be_age} tuổi**) với số tiền đạt **{be_acc_val}**."
    )
else:
    st.warning(
        f"💡 **Lưu ý ({prod_name}):** Với mức phí và thời gian đóng phí hiện tại, Giá trị tài khoản chưa vượt Tổng phí đóng trong khoảng thời gian minh họa."
    )

col_title, col_btn = st.columns([3, 1])
with col_title:
    st.subheader("📋 Dòng Tiền Chi Tiết (Kèm Sản Phẩm Bổ Trợ)")
with col_btn:
    pdf_buffer = create_pdf_report(
        fullname,
        prod_name,
        entry_age,
        sum_assured,
        target_premium,
        prem_term,
        df_proj,
        sa_cir1,
        sa_cir2,
        sa_pa,
        gender,
    )
    st.download_button(
        label="📥 Tải Minh Họa Nháp (PDF)",
        data=pdf_buffer,
        file_name=f"Minh_Hoa_Dich_Vu_{prod_code}_{fullname.replace(' ', '_')}_{gender}.pdf",
        mime="application/pdf",
        type="primary",
    )

if not df_proj.empty:
    df_display = df_proj.copy().fillna(0)
    money_cols = [
        "Phí Đóng Dự Kiến",
        "Tổng Phí Lũy Kế",
        "Thưởng Gắn Bó",
        "Quyền Lợi Tử Vong",
        "Giá Trị Tài Khoản",
        "Giá Trị Hoàn Lại",
    ]

    for col in money_cols:
        df_display[col] = df_display[col].apply(fmt_vnd)

    st.dataframe(
        df_display[[
            "Năm/Tuổi",
            "Phí Đóng Dự Kiến",
            "Tổng Phí Lũy Kế",
            "Thưởng Gắn Bó",
            "Quyền Lợi Tử Vong",
            "Giá Trị Tài Khoản",
            "Giá Trị Hoàn Lại",
        ]],
        use_container_width=True,
        height=550,
    )
else:
    st.warning("⚠️ Không có dữ liệu minh họa. Vui lòng kiểm tra lại Ngày sinh.")
