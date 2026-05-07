import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered")

# 初始化 Session State
if 'calc_val' not in st.session_state:
    st.session_state.calc_val = "0"

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    
    /* 強制按鈕橫向 4 欄排列 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    div[data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
    }
    
    /* 按鈕樣式優化 */
    div.stButton > button {
        width: 100% !important;
        height: 55px !important;
        padding: 0 !important;
        font-size: 18px !important;
        border-radius: 10px !important;
    }
    
    .big-display {
        background-color: #1e1e23; color: #00ff41; padding: 15px; border-radius: 15px;
        text-align: right; font-family: 'monospace'; font-size: 42px; font-weight: bold;
        margin-bottom: 10px; border: 2px solid #3d3d4d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Google Sheets 快取連線 ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gs_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def fetch_data():
    try:
        client = get_gs_client()
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        data = wks.get_all_records()
        return data, wks
    except:
        return [], None

records, wks = fetch_data()
fixed_val, pocket_val = 0.0, 0.0
if records:
    last = records[-1]
    fixed_val, pocket_val = float(last.get('定存總額', 0)), float(last.get('零用總額', 0))

# --- 3. 介面 ---
st.markdown(f"### 🍎 目前資產狀態")
c1, c2 = st.columns(2)
c1.metric("🔒 定存", f"${fixed_val:,.0f}")
c2.metric("💳 零用", f"${pocket_val:,.0f}")

tabs = st.tabs(["📝 快速記帳", "📜 明細", "⚙️ 設定"])

with tabs[0]:
    input_date = st.date_input("日期", datetime.now())
    CATEGORIES = {"早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "點心": "🍰", "交通": "🚗", "購物": "🛍️", "娛樂": "🎮", "其他": "✨"}
    sel = st.pills("類別", [f"{v} {k}" for k, v in CATEGORIES.items()], selection_mode="single", default="🥪 早餐")
    current_cat = (sel if sel else "🥪 早餐").split(" ")[1]
    
    st.markdown(f'<div class="big-display">{st.session_state.calc_val}</div>', unsafe_allow_html=True)

    def press(d):
        if d == "AC": st.session_state.calc_val = "0"
        elif d == "DEL": st.session_state.calc_val = st.session_state.calc_val[:-1] if len(st.session_state.calc_val) > 1 else "0"
        else:
            if st.session_state.calc_val == "0" and d != ".": st.session_state.calc_val = str(d)
            else: st.session_state.calc_val += str(d)

    # 鍵盤區 - 強制 Row 不換行
    r1 = st.columns(4)
    if r1[0].button("7", key="k7"): press("7"); st.rerun()
    if r1[1].button("8", key="k8"): press("8"); st.rerun()
    if r1[2].button("9", key="k9"): press("9"); st.rerun()
    if r1[3].button("⌫", key="kd"): press("DEL"); st.rerun()

    r2 = st.columns(4)
    if r2[0].button("4", key="k4"): press("4"); st.rerun()
    if r2[1].button("5", key="k5"): press("5"); st.rerun()
    if r2[2].button("6", key="k6"): press("6"); st.rerun()
    if r2[3].button("×", key="km"): press("*"); st.rerun()

    r3 = st.columns(4)
    if r3[0].button("1", key="k1"): press("1"); st.rerun()
    if r3[1].button("2", key="k2"): press("2"); st.rerun()
    if r3[2].button("3", key="k3"): press("3"); st.rerun()
    if r3[3].button("-", key="ks"): press("-"); st.rerun()

    r4 = st.columns(4)
    if r4[0].button("0", key="k0"): press("0"); st.rerun()
    if r4[1].button(".", key="kp"): press("."); st.rerun()
    if r4[2].button("AC", key="ka"): press("AC"); st.rerun()
    if r4[3].button("+", key="ka1"): press("+"); st.rerun()

    note = st.text_input("備註 (選填)")
    if st.button("🚀 確認送出支出", type="primary", use_container_width=True):
        try:
            amt = float(eval(st.session_state.calc_val))
            if amt > 0 and wks:
                wks.append_row([str(input_date), f"{CATEGORIES[current_cat]} {current_cat}", note if note else current_cat, amt, "支出", fixed_val, pocket_val - amt])
                st.session_state.calc_val = "0"
                st.cache_data.clear()
                st.rerun()
        except: st.error("數字無效")

with tabs[1]:
    if records:
        df = pd.DataFrame(records).iloc[::-1]
        st.dataframe(df.head(20), use_container_width=True)

with tabs[2]:
    if st.button("🔄 刷新資料"):
        st.cache_data.clear()
        st.rerun()
