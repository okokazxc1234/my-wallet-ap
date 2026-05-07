import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered")

# 初始化計算機狀態
if 'calc_val' not in st.session_state:
    st.session_state.calc_val = "0"

# --- 2. CSS 優化：強制手機版排版與美化 ---
st.markdown("""
    <style>
    /* 隱藏預設元件 */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    
    /* 螢幕顯示區 */
    .calc-screen {
        background-color: #1e1e23; color: #00ff41; padding: 15px; border-radius: 12px;
        text-align: right; font-family: 'monospace'; font-size: 36px; font-weight: bold;
        margin-bottom: 10px; border: 2px solid #3d3d4d;
    }
    
    /* 強制按鈕在手機橫向排列 (不換行) */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 4px !important;
    }
    div[data-testid="column"] { flex: 1 1 0% !important; min-width: 0 !important; }
    
    /* 按鈕樣式縮放 */
    div.stButton > button {
        width: 100% !important; height: 50px !important; padding: 0 !important;
        font-size: 18px !important; border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Google Sheets 連線與快取 ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gs_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=600) # 快取 10 分鐘，節省流量
def fetch_data():
    try:
        client = get_gs_client()
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        return wks.get_all_records(), wks
    except: return [], None

# --- 4. 邏輯處理 ---
records, wks = fetch_data()
df = pd.DataFrame(records)

# 取得目前餘額
if not df.empty:
    fixed_val = float(df.iloc[-1]['定存總額'])
    pocket_val = float(df.iloc[-1]['零用總額'])
else:
    fixed_val, pocket_val = 0.0, 0.0

def press(key):
    if key == "AC": st.session_state.calc_val = "0"
    elif key == "DEL": st.session_state.calc_val = st.session_state.calc_val[:-1] if len(st.session_state.calc_val) > 1 else "0"
    elif key == "=":
        try: st.session_state.calc_val = str(eval(st.session_state.calc_val.replace('×','*').replace('÷','/')))
        except: st.session_state.calc_val = "Error"
    else:
        if st.session_state.calc_val in ["0", "Error"]: st.session_state.calc_val = str(key)
        else: st.session_state.calc_val += str(key)

# --- 5. UI 介面 ---
st.markdown("### 🍎 帳戶餘額概覽")
m1, m2 = st.columns(2)
m1.metric("🔒 定存金庫", f"${fixed_val:,.0f}")
m2.metric("💳 零用預算", f"${pocket_val:,.0f}")

tabs = st.tabs(["📝 快速記帳", "📊 趨勢分析", "📜 明細管理", "⚙️ 帳戶設定"])

with tabs[0]:
    # 類別選擇 (Pills)
    CATEGORIES = {"早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "點心": "🍰", "交通": "🚗", "購物": "🛍️", "娛樂": "🎮", "其他": "✨"}
    sel = st.pills("選擇分類", [f"{v} {k}" for k, v in CATEGORIES.items()], selection_mode="single", default="🥪 早餐")
    curr_cat = (sel if sel else "🥪 早餐").split(" ")[1]
    
    # 計算機彈窗
    with st.popover(f"💰 點擊輸入金額： ${st.session_state.calc_val}", use_container_width=True):
        st.markdown(f'<div class="calc-screen">{st.session_state.calc_val}</div>', unsafe_allow_html=True)
        
        # 鍵盤 Grid
        for r in [["7","8","9","÷"], ["4","5","6","×"], ["1","2","3","-"], ["0",".","AC","+"]]:
            cols = st.columns(4)
            for i, b in enumerate(r):
                if cols[i].button(b, key=f"btn_{b}_{r}"): press(b); st.rerun()
        
        c_del, c_eq = st.columns([1, 2])
        if c_del.button("⌫", key="btn_del"): press("DEL"); st.rerun()
        if c_eq.button("＝ 計算結果", key="btn_eq", type="primary"): press("="); st.rerun()

    item_note = st.text_input("📝 備註 (選填)")
    input_date = st.date_input("📅 交易日期", datetime.now())

    if st.button("🚀 確認紀錄並送出", type="primary", use_container_width=True):
        try:
            amt = float(eval(st.session_state.calc_val))
            if amt > 0:
                wks.append_row([str(input_date), f"{CATEGORIES[curr_cat]} {curr_cat}", item_note if item_note else curr_cat, amt, "支出", fixed_val, pocket_val - amt])
                st.session_state.calc_val = "0"
                st.cache_data.clear() # 成功後清除快取，下次會抓到新餘額
                st.success(f"成功記錄：${amt}")
                st.rerun()
        except: st.error("金額無效")

with tabs[1]:
    if not df.empty:
        df_exp = df[df['類型'] == '支出'].copy()
        df_exp['金額'] = pd.to_numeric(df_exp['金額'])
        st.plotly_chart(px.pie(df_exp, values='金額', names='類別', hole=0.5, title="支出佔比"), use_container_width=True)

with tabs[2]:
    if not df.empty:
        st.dataframe(df.iloc[::-1].head(20), use_container_width=True)

with tabs[3]:
    if st.button("🔄 手動同步最新資料"):
        st.cache_data.clear()
        st.rerun()
    st.info("更多帳戶設定持續開發中...")
