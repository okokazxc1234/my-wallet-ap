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
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .big-display {
        background-color: #1e1e23; color: #00ff41; padding: 15px; border-radius: 15px;
        text-align: right; font-family: 'monospace'; font-size: 42px; font-weight: bold;
        margin-bottom: 20px; border: 2px solid #3d3d4d;
    }
    div.stButton > button { width: 100%; height: 60px; font-size: 20px; font-weight: bold; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Google Sheets 連線與快取 ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gs_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

# 關鍵優化：使用 ttl (生存時間) 讓資料在 10 分鐘內只讀取一次，除非手動清除快取
@st.cache_data(ttl=600)
def fetch_data():
    try:
        client = get_gs_client()
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        return wks.get_all_records(), wks
    except Exception as e:
        st.error(f"讀取資料失敗: {e}")
        return [], None

# 取得資料
records, wks = fetch_data()

fixed_val, pocket_val = 0.0, 0.0
if records:
    last_row = records[-1]
    fixed_val = float(last_row.get('定存總額', 0))
    pocket_val = float(last_row.get('零用總額', 0))

# --- 3. 畫面顯示 ---
st.markdown(f"### 🍎 目前資產狀態")
col1, col2 = st.columns(2)
col1.metric("🔒 定存", f"${fixed_val:,.0f}")
col2.metric("💳 零用", f"${pocket_val:,.0f}")

tabs = st.tabs(["📝 快速記帳", "📜 明細", "⚙️ 設定"])

with tabs[0]:
    input_date = st.date_input("日期", datetime.now())
    CATEGORIES = {
        "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "點心": "🍰", 
        "交通": "🚗", "購物": "🛍️", "娛樂": "🎮", "日用品": "🧻", "其他": "✨"
    }
    all_opts = [f"{v} {k}" for k, v in CATEGORIES.items()]
    sel_full = st.pills("類別", all_opts, selection_mode="single", default=all_opts[0])
    current_cat = (sel_full if sel_full else all_opts[0]).split(" ")[1]
    
    st.markdown(f'<div class="big-display">{st.session_state.calc_val}</div>', unsafe_allow_html=True)

    # 鍵盤邏輯
    def press(d):
        if d == "AC": st.session_state.calc_val = "0"
        elif d == "DEL": st.session_state.calc_val = st.session_state.calc_val[:-1] if len(st.session_state.calc_val) > 1 else "0"
        else:
            if st.session_state.calc_val == "0": st.session_state.calc_val = str(d)
            else: st.session_state.calc_val += str(d)

    k1, k2, k3, k4 = st.columns(4)
    if k1.button("7"): press("7"); st.rerun()
    if k2.button("8"): press("8"); st.rerun()
    if k3.button("9"): press("9"); st.rerun()
    if k4.button("⌫"): press("DEL"); st.rerun()
    if k1.button("4"): press("4"); st.rerun()
    if k2.button("5"): press("5"); st.rerun()
    if k3.button("6"): press("6"); st.rerun()
    if k4.button("×"): press("*"); st.rerun()
    if k1.button("1"): press("1"); st.rerun()
    if k2.button("2"): press("2"); st.rerun()
    if k3.button("3"): press("3"); st.rerun()
    if k4.button("-"): press("-"); st.rerun()
    if k1.button("0"): press("0"); st.rerun()
    if k2.button("."): press("."); st.rerun()
    if k3.button("AC"): press("AC"); st.rerun()
    if k4.button("+"): press("+"); st.rerun()

    note = st.text_input("備註 (選填)")
    
    if st.button("🚀 確認送出支出", type="primary"):
        try:
            amt = float(eval(st.session_state.calc_val))
            if amt > 0 and wks:
                wks.append_row([str(input_date), f"{CATEGORIES[current_cat]} {current_cat}", note if note else current_cat, amt, "支出", fixed_val, pocket_val - amt])
                st.session_state.calc_val = "0"
                st.cache_data.clear() # 關鍵：成功送出後才清除快取，強制下次讀取新資料
                st.rerun()
        except:
            st.error("請檢查輸入數字")

with tabs[1]:
    if records:
        df = pd.DataFrame(records).iloc[::-1] # 反轉顯示最新明細
        for i, row in df.head(10).iterrows(): # 只顯示最近 10 筆
            st.text(f"{row['日期']} | {row['類別']} | ${row['金額']}")

with tabs[2]:
    if st.button("🔄 手動重新整理資料"):
        st.cache_data.clear()
        st.rerun()
