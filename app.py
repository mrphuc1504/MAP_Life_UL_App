from datetime import datetime
import io
import unicodedata
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# ---------------------------------------------------------
# 1. CẤU HÌNH GIAO DIỆN DI ĐỘNG (MOBILE-FIRST) & ẨN HỆ THỐNG
# ---------------------------------------------------------
st.set_page_config(
    page_title="MAP Life UL Mobile", page_icon="🛡️", layout="centered"
)

mobile_css = """
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

    body {
        font-size: 15px;
    }
    .stNumberInput, .stSelectbox, .stRadio, .stSlider {
        margin-bottom: 8px;
    }
    </style>
"""
st.markdown(mobile_css, unsafe_allow_html=True)


def fmt_vnd(amount):
    return f"{int(amount):,}".replace(",", ".") + " VNĐ"


def fmt_vnd_short(amount):
    return f"{int(amount):,}".replace(",", ".")


def remove_accents(text):
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


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


st.title("🛡️ MAP Life UL")
st.caption("Công cụ minh họa dòng tiền & tư vấn bảo hiểm tối ưu trên di động")

# ---------------------------------------------------------
# 2. KHU VỰC NHẬP LIỆU TRỰC TIẾP TRÊN MÀN HÌNH CHÍNH (MOBILE LAYOUT)
# ---------------------------------------------------------
st.markdown("### 📋 1. Chọn sản phẩm BH")
product_choice = st.selectbox(
    "Sản phẩm:",
    ["MAP Life Hạnh Phúc (UL2)", "MAP Life Bình An (UL3)"],
    label_visibility="collapsed",
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

st.markdown("---")
st.markdown("### 👤 2. Thông tin KH")
fullname = st.text_input("Họ và tên NĐBH", "Lộc Đại Phu")
gender = st.radio("Giới tính", ["Nam", "Nữ"], horizontal=True)

col_d, col_m, col_y = st.columns(3)
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

st.info(
    f"💡 Ngày sinh: **{birth_day:02d}/{birth_month:02d}/{birth_year}** | Tuổi:"
    f" **{entry_age} tuổi**"
)

st.markdown("---")
st.markdown("### 💰 3. Thông tin Hợp đồng")

if (
    "prev_prod_tp" not in st.session_state
    or st.session_state.prev_prod_tp != prod_code
):
    st.session_state.tp_input = default_tp_m
    st.session_state.prev_prod_tp = prod_code

tp_in_millions = st.number_input(
    "Phí cơ bản hàng năm (Triệu VNĐ):",
    min_value=float(abs_min_tp / 1_000_000),
    step=1.0,
    format="%g",
    key="tp_input",
)
target_premium = int(tp_in_millions * 1_000_000)

if target_premium < abs_min_tp:
    st.error(
        f"⚠️ **Cảnh báo:** Phí tối thiểu cho {prod_name} là"
        f" **{fmt_vnd(abs_min_tp)}**!"
    )
else:
    st.success(f"👉 **Phí đóng:** `{fmt_vnd(target_premium)}`")

prem_term = st.slider(
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

sa_in_millions = st.number_input(
    "Số Tiền Bảo Hiểm (STBH) chính (Triệu VNĐ):",
    min_value=0.0,
    step=10.0,
    format="%g",
    key="sa_input",
)
sum_assured = int(sa_in_millions * 1_000_000)
st.success(f"👉 **STBH chính:** `{fmt_vnd(sum_assured)}`")

st.caption(
    f"📌 *Hạn mức STBH động ({entry_age} tuổi, phí {fmt_vnd(target_premium)}):*\n"
    f"- Tối thiểu (Min): **{fmt_vnd(dynamic_min_sa)}**\n"
    f"- Tối đa (Max): **{fmt_vnd(dynamic_max_sa)}**"
)

if sum_assured < dynamic_min_sa or sum_assured > dynamic_max_sa:
    st.warning(
        f"⚠️ STBH ngoài khung cho phép ({fmt_vnd(dynamic_min_sa)} - {fmt_vnd(dynamic_max_sa)})"
    )

# ---------------------------------------------------------
# SẢN PHẨM BỔ TRỢ (RIDERS)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 🛡️ 4. SP bổ trợ (Riders)")

use_cir1 = st.checkbox("Bệnh hiểm nghèo (CIR1)", value=False)
sa_cir1 = 0
if use_cir1:
    sa_cir1_m = st.number_input(
        "STBH CIR1 (Tối đa 400tr):",
        min_value=0.0,
        max_value=400.0,
        value=100.0,
        step=100.0,
        format="%g",
    )
    sa_cir1 = int(sa_cir1_m * 1_000_000)

use_cir2 = st.checkbox("Bệnh hiểm nghèo nâng cao (CIR2)", value=False)
sa_cir2 = 0
if use_cir2:
    sa_cir2_m = st.number_input(
        "STBH CIR2 (Tối đa 500tr):",
        min_value=0.0,
        max_value=500.0,
        value=100.0,
        step=100.0,
        format="%g",
    )
    sa_cir2 = int(sa_cir2_m * 1_000_000)

use_pa = st.checkbox("Bảo hiểm Hỗ trợ TTVV do Tai nạn (PDD1)", value=False)
sa_pa = 0
if use_pa:
    sa_pa_m = st.number_input(
        "STBH Tai nạn (Tối đa 500tr):",
        min_value=0.0,
        max_value=500.0,
        value=100.0,
        step=100.0,
        format="%g",
    )
    sa_pa = int(sa_pa_m * 1_000_000)


# ---------------------------------------------------------
# 3. ENGINE TÍNH TOÁN DÒNG TIỀN (CÓ TÍNH PHÍ RỦI RO BỔ TRỢ)
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
    interest_rate=0.05,
):
    records = []
    accumulated_prem = 0
    account_value = 0
    init_fee_rate = {1: 0.50, 2: 0.30, 3: 0.20, 4: 0.20, 5: 0.20}

    sa_to_tp_ratio = sa / tp if tp > 0 else 0

    if prod_code == "UL2":
        special_bonus_rate = min(1.0, max(0.25, sa_to_tp_ratio / 60.0))
    else:
        special_bonus_rate = min(0.5, max(0.15, sa_to_tp_ratio / 80.0))

    max_years = max(1, 100 - entry_age)

    for pol_year in range(1, max_years + 1):
        current_age = entry_age + pol_year - 1

        yearly_prem = tp if pol_year <= prem_term else 0
        accumulated_prem += yearly_prem

        fee_rate = init_fee_rate.get(pol_year, 0.02)
        invest_prem = yearly_prem * (1 - fee_rate)

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

        else:  # UL3
            if pol_year % 3 == 0:
                bonus += tp * 0.04

            if pol_year == 10:
                bonus += tp * special_bonus_rate

        coi_rate_main = 0.0015 + (current_age * 0.0001)
        coi_fee_main = sa * coi_rate_main

        coi_fee_cir1 = (
            sa_cir1 * (0.0008 + current_age * 0.00005) if sa_cir1 > 0 else 0
        )
        coi_fee_cir2 = (
            sa_cir2 * (0.0012 + current_age * 0.00006) if sa_cir2 > 0 else 0
        )
        coi_fee_pa = sa_pa * 0.0012 if sa_pa > 0 else 0

        total_rider_fee = coi_fee_cir1 + coi_fee_cir2 + coi_fee_pa
        total_coi_fee = coi_fee_main + total_rider_fee

        account_value = (
            account_value + invest_prem - total_coi_fee + bonus
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
            "Phí Đóng Dự Kiến": yearly_prem,
            "Tổng Phí Lũy Kế": accumulated_prem,
            "Phí Bổ Trợ": total_rider_fee,
            "Thưởng Gắn Bó": bonus,
            "Quyền Lợi Tử Vong": death_benefit,
            "Giá Trị Tài Khoản": account_value,
            "Giá Trị Hoàn Lại": surrender_val,
        })

    return pd.DataFrame(records)


def get_rider_fee_year1(age, sa_cir1, sa_cir2, sa_pa):
    fee_cir1 = sa_cir1 * (0.0008 + age * 0.00005) if sa_cir1 > 0 else 0
    fee_cir2 = sa_cir2 * (0.0012 + age * 0.00006) if sa_cir2 > 0 else 0
    fee_pa = sa_pa * 0.0012 if sa_pa > 0 else 0
    return fee_cir1, fee_cir2, fee_pa


# ---------------------------------------------------------
# 4. HÀM TẠO FILE PDF (CÓ CỘT PHÍ BỔ TRỢ & KHÔNG DẤU)
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
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=30,
        bottomMargin=30,
    )
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#003366"),
        alignment=1,
    )

    sub_style = ParagraphStyle(
        "SubStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#222222"),
    )

    elements.append(Paragraph("BANG MINH HOA QUYEN LOI BAO HIEM", title_style))
    elements.append(Spacer(1, 8))

    safe_name = remove_accents(fullname)
    safe_prod = remove_accents(prod_name)

    info_html = f"""
    <b>San pham:</b> {safe_prod}<br/>
    <b>Khach hang:</b> {safe_name} | <b>Tuoi:</b> {entry_age}<br/>
    <b>STBH chinh:</b> {fmt_vnd(sum_assured)} | <b>Phi co ban:</b> {fmt_vnd(target_premium)}/nam ({prem_term} nam)
    """

    f1, f2, f3 = get_rider_fee_year1(entry_age, sa_cir1, sa_cir2, sa_pa)
    rider_parts = []
    if sa_cir1 > 0:
        rider_parts.append(
            f"CIR1 ({fmt_vnd(sa_cir1)} - Phi nam 1: {fmt_vnd_short(f1)} VND)"
        )
    if sa_cir2 > 0:
        rider_parts.append(
            f"CIR2 ({fmt_vnd(sa_cir2)} - Phi nam 1: {fmt_vnd_short(f2)} VND)"
        )
    if sa_pa > 0:
        rider_parts.append(
            f"Tai nan ({fmt_vnd(sa_pa)} - Phi nam 1: {fmt_vnd_short(f3)} VND)"
        )

    rider_str = (
        ", ".join(rider_parts) if rider_parts else "Khong co san pham bo tro"
    )
    info_html += f"<br/><b>Bo tro:</b> {rider_str}"

    elements.append(Paragraph(remove_accents(info_html), sub_style))
    elements.append(Spacer(1, 10))

    table_data = [[
        "Nam/Tuoi",
        "Phi Dong",
        "Phi Bo Tro",
        "Thuong",
        "Tu Vong",
        "Gia Tri TK",
        "Hoan Lai",
    ]]

    for _, row in df_p.iterrows():
        table_data.append([
            str(row["Năm/Tuổi"]),
            fmt_vnd_short(row["Phí Đóng Dự Kiến"]),
            fmt_vnd_short(row["Phí Bổ Trợ"]),
            fmt_vnd_short(row["Thưởng Gắn Bó"]),
            fmt_vnd_short(row["Quyền Lợi Tử Vong"]),
            fmt_vnd_short(row["Giá Trị Tài Khoản"]),
            fmt_vnd_short(row["Giá Trị Hoàn Lại"]),
        ])

    # Tổng chiều rộng trang A4 là ~595pt, trừ lề 40pt còn lại 555pt vừa khít 7 cột
    t = Table(
        table_data, colWidths=[55, 75, 75, 60, 95, 100, 95], repeatRows=1
    )
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
            ("TOPPADDING", (0, 1), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#f8f9fa")],
            ),
        ])
    )

    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------
# 5. HIỂN THỊ KẾT QUẢ GỌN GÀNG & KÈM PHÍ RỦI RO SẢN PHẨM BỔ TRỢ
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 📊 Tóm tắt Quyền lợi")

df_proj = generate_ul_projection(
    prod_code,
    entry_age,
    target_premium,
    prem_term,
    sum_assured,
    sa_cir1,
    sa_cir2,
    sa_pa,
)

col_res1, col_res2 = st.columns(2)
with col_res1:
    st.markdown(f"**Sản phẩm:** `{prod_name}`")
    st.markdown(f"**STBH chính:** `{fmt_vnd_short(sum_assured)} VNĐ`")
with col_res2:
    st.markdown(f"**Phí hàng năm:** `{fmt_vnd_short(target_premium)} VNĐ`")
    st.markdown(
        f"**Tổng phí ({prem_term} năm):**"
        f" `{fmt_vnd_short(target_premium * prem_term)} VNĐ`"
    )

f1, f2, f3 = get_rider_fee_year1(entry_age, sa_cir1, sa_cir2, sa_pa)
riders_summary = []
if sa_cir1 > 0:
    riders_summary.append(
        f"CIR1: {fmt_vnd_short(sa_cir1)}đ (Phí năm 1:"
        f" {fmt_vnd_short(f1)} VNĐ)"
    )
if sa_cir2 > 0:
    riders_summary.append(
        f"CIR2: {fmt_vnd_short(sa_cir2)}đ (Phí năm 1:"
        f" {fmt_vnd_short(f2)} VNĐ)"
    )
if sa_pa > 0:
    riders_summary.append(
        f"Tai nạn: {fmt_vnd_short(sa_pa)}đ (Phí năm 1:"
        f" {fmt_vnd_short(f3)} VNĐ)"
    )

if riders_summary:
    st.markdown("🛡️ **Sản phẩm bổ trợ & Phí rủi ro năm 1:**")
    for r in riders_summary:
        st.markdown(f"- {r}")
else:
    st.markdown("🛡️ **Sản phẩm bổ trợ:** Không có")

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
        f"💡 Ở lãi suất 5%/năm, Giá trị tài khoản vượt Tổng phí đóng từ **Năm"
        f" thứ {be_year}** (lúc **{be_age} tuổi**) đạt **{be_acc_val}**."
    )
else:
    st.warning("💡 Giá trị tài khoản chưa vượt Tổng phí đóng trong minh họa.")

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
)
st.download_button(
    label="📥 Tải Minh Họa Nháp (PDF)",
    data=pdf_buffer,
    file_name=f"Minh_Hoa_Dich_Vu_{prod_code}_{fullname.replace(' ', '_')}.pdf",
    mime="application/pdf",
    type="primary",
    use_container_width=True,
)

st.markdown("---")
st.subheader("📋 Chi Tiết Dòng Tiền")

if not df_proj.empty:
    df_display = df_proj.copy().fillna(0)
    money_cols = [
        "Phí Đóng Dự Kiến",
        "Tổng Phí Lũy Kế",
        "Phí Bổ Trợ",
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
            "Phí Bổ Trợ",
            "Thưởng Gắn Bó",
            "Quyền Lợi Tử Vong",
            "Giá Trị Tài Khoản",
            "Giá Trị Hoàn Lại",
        ]],
        use_container_width=True,
        height=450,
    )
else:
    st.warning("⚠️ Vui lòng kiểm tra lại thông tin đầu vào.")
