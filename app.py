import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. 頁面與終極 CSS ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 隱藏不想看到的 Streamlit 元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 鍵盤網格佈局 */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-top: 5px;
    }
    .grid-item {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 12px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: bold;
        color: #333;
        cursor: pointer;
        user-select: none;
        -webkit-tap-highlight-color: transparent;
    }
    .grid-item:active { background-color: #e2e6ea; transform: scale(0.95); }
    .grid-item.special { background-color: #e9ecef; color: #007bff; }
    
    /* 螢幕樣式 */
    #display {
        background-color: #1e1e23;
        color: #00ff41;
        padding: 15px;
        border-radius: 15px;
        text-align: right;
        font-family: 'monospace';
        font-size: 42px;
        font-weight: bold;
        margin-bottom: 10px;
        min-height: 70px;
        border: 2px solid #3d3d4d;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
    }

    /* 餘額卡片 */
    .balance-container { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 15px; }
    .balance-card { background: #fff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 12px; width: 48%; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .balance-label { font-size: 14px; color: #666; margin-bottom: 4px;}
    .balance-value { font-size: 22px; font-weight: bold; color: #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Google Sheets 連線 ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gs_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except: return None

client = get_gs_client()
fixed_val, pocket_val = 0.0, 0.0
records = []

if client:
    try:
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        records = wks.get_all_records()
        if records:
            last_row = records[-1]
            fixed_val = float(last_row.get('定存總額', 0))
            pocket_val = float(last_row.get('零用總額', 0))

        st.markdown(f"### 🍎 目前資產狀態")
        st.markdown(f"""
            <div class="balance-container">
                <div class="balance-card"><div class="balance-label">🔒 定存</div><div class="balance-value">${fixed_val:,.0f}</div></div>
                <div class="balance-card"><div class="balance-label">💳 零用</div><div class="balance-value">${pocket_val:,.0f}</div></div>
            </div>
        """, unsafe_allow_html=True)

        tabs = st.tabs(["📝 快速記帳", "📜 明細管理", "⚙️ 設定"])

        # --- Tab 1: 記帳 ---
        with tabs[0]:
            input_date = st.date_input("日期", datetime.now())
            CATEGORIES = {
                "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "點心": "🍰", 
                "酒類": "🍺", "交通": "🚗", "購物": "🛍️", "娛樂": "🎮", "日用品": "🧻", 
                "房租": "🏠", "醫療": "🏥", "社交": "👥", "禮物": "🎁", "數位": "💻", "其他": "✨"
            }
            all_opts = [f"{v} {k}" for k, v in CATEGORIES.items()]
