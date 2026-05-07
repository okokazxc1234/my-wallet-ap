import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered", initial_sidebar_state="collapsed")

# 這裡的 CSS 確保隱藏欄位完全不佔空間且看不見
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
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
        margin-bottom: 5px;
        min-height: 70px;
        border: 2px solid #3d3d4d;
    }
    
    /* 這是隱藏輸入框的絕招：讓它高度0、寬度0、透明度0 */
    .hidden-box {
        height: 0px;
        overflow: hidden;
        margin: 0;
        padding: 0;
        opacity: 0;
    }
    
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

        tabs = st.tabs(["📝 快速記帳", "📜 明細", "⚙️ 設定"])

        with tabs[0]:
            input_date = st.date_input("日期", datetime.now())
            CATEGORIES = {
                "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "點心": "🍰", 
                "酒類": "🍺", "交通": "🚗", "購物": "🛍️", "娛樂": "🎮", "日用品": "🧻", 
                "房租": "🏠", "醫療": "🏥", "社交": "👥", "禮物": "🎁", "數位": "💻", "其他": "✨"
            }
            all_opts = [f"{v} {k}" for k, v in CATEGORIES.items()]
            sel_full = st.pills("類別", all_opts, selection_mode="single", default=all_opts[0], label_visibility="collapsed")
            current_cat = (sel_full if sel_full else all_opts[0]).split(" ")[1]

            st.markdown('<div id="display">0</div>', unsafe_allow_html=True)
            
            # --- 核心：用 CSS 徹底隱藏普通輸入框 ---
            st.markdown('<div class="hidden-box">', unsafe_allow_html=True)
            # 給它一個超獨特的 Label 讓 JS 好找
            st.text_input("FOR_JS_SYNC", value="0", key="amt_sync_key", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)

            calc_html = """
            <html>
            <head>
                <style>
                .grid-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 5px; }
                .grid-item {
                    background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 12px; height: 60px;
                    display: flex; align-items: center; justify-content: center; font-size: 24px;
                    font-weight: bold; color: #333; cursor: pointer; user-select: none; font-family: sans-serif;
                    -webkit-tap-highlight-color: transparent;
                }
                .grid-item:active { background-color: #e2e6ea; transform: scale(0.95); }
                .grid-item.special { background-color: #f1f3f5; color: #007bff; }
                </style>
            </head>
            <body>
                <div class="grid-container">
                    <div class="grid-item" onclick="press('7')">7</div><div class="grid-item" onclick="press('8')">8</div><div class="grid-item" onclick="press('9')">9</div><div class="grid-item special" onclick="press('DEL')">⌫</div>
                    <div class="grid-item" onclick="press('4')">4</div><div class="grid-item" onclick="press('5')">5</div><div class="grid-item" onclick="press('6')">6</div><div class="grid-item special" onclick="press('*')">×</div>
                    <div class="grid-item" onclick="press('1')">1</div><div class="grid-item" onclick="press('2')">2</div><div class="grid-item" onclick="press('3')">3</div><div class="grid-item special" onclick="press('-')">-</div>
                    <div class="grid-item" onclick="press('0')">0</div><div class="grid-item" onclick="press('.')">.</div><div class="grid-item special" onclick="press('AC')">AC</div><div class="grid-item special" onclick="press('+')">+</div>
                </div>
                <script>
                function press(key) {
                    const display = window.parent.document.getElementById('display');
                    const inputs = window.parent.document.querySelectorAll('input');
                    let target = null;
                    // 根據我們設定的內容尋找同步框
                    for (let i of inputs) {
                        if (i.ariaLabel === 'FOR_JS_SYNC') { target = i; break; }
                    }
                    
                    let current = display.innerText;
                    if (key === 'AC') { current = '0'; }
                    else if (key === 'DEL') { current = current.length > 1 ? current.slice(0, -1) : '0'; }
                    else {
                        if (current === '0' && key !== '.') { current = key; }
                        else { current += key; }
                    }
                    display.innerText = current;
                    
                    if (target) {
                        target.value = current;
                        target.dispatchEvent(new Event('input', { bubbles: true }));
                        target.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
                </script>
            </body>
            </html>
            """
            components.html(calc_html, height=310)

            note = st.text_input("備註 (選填)")
            
            if st.button("🚀 確認送出支出", type="primary", use_container_width=True):
                # 讀取 session_state
                raw_val = st.session_state.amt_sync_key
                try:
                    amt = float(eval(raw_val))
                    if amt > 0:
                        wks.append_row([str(input_date), f
