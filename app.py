import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. 頁面與 CSS 補丁 (精緻緊湊化) ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 強制手機版 4 欄位佈局 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        margin-bottom: 2px !important;
    }
    div[data-testid="column"] {
        width: 25% !important;
        flex: 1 1 calc(25% - 4px) !important;
        min-width: calc(25% - 4px) !important;
    }
    /* 鍵盤按鈕高度優化 */
    [data-testid="stBaseButton-secondary"] {
        height: 48px !important;
        line-height: 48px !important;
        padding: 0px !important;
        font-size: 20px !important;
        border-radius: 8px !important;
    }
    /* 模擬螢幕外觀 */
    .calc-screen {
        background-color: #1e1e23;
        color: #00ff41; /* 懷舊電腦綠 */
        padding: 10px 15px;
        border-radius: 10px;
        text-align: right;
        margin-bottom: 10px;
        font-family: 'Courier New', monospace;
        font-size: 36px;
        font-weight: bold;
        border: 2px solid #3d3d4d;
        box-shadow: inset 0 0 10px #000;
    }
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
    except Exception as e:
        st.error(f"❌ 連線失敗: {e}")
        return None

CATEGORIES = {
    "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", 
    "點心": "🍰", "酒類": "🍺", "交通": "🚗", "購物": "🛍️", 
    "娛樂": "🎮", "日用品": "🧻", "房租": "🏠", "醫療": "🏥", 
    "社交": "👥", "禮物": "🎁", "數位": "💻", "其他": "✨"
}

client = get_gs_client()

if client:
    try:
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        all_records = wks.get_all_records()
        df = pd.DataFrame(all_records)

        # 讀取當前餘額
        if not df.empty:
            fixed_val = float(df.iloc[-1]['定存總額'])
            pocket_val = float(df.iloc[-1]['零用總額'])
        else:
            fixed_val, pocket_val = 0.0, 0.0

        st.markdown(f"### 🍎 目前餘額")
        c1, c2 = st.columns(2)
        c1.metric("🔒 定存金庫", f"${fixed_val:,.0f}")
        c2.metric("💳 零用預算", f"${pocket_val:,.0f}")

        tabs = st.tabs(["📝 快速記帳", "📊 分析", "📜 明細管理", "⚙️ 設定"])

        # --- Tab 1: 快速記帳 ---
        with tabs[0]:
            if 'calc_val' not in st.session_state: st.session_state.calc_val = "0"
            
            st.markdown("#### 📅 1. 日期與分類")
            input_date = st.date_input("選擇日期", datetime.now(), label_visibility="collapsed")
            
            all_opts = [f"{v} {k}" for k, v in CATEGORIES.items()]
            sel_full = st.pills("類別", all_opts, selection_mode="single", default=all_opts[0], label_visibility="collapsed")
            current_cat_name = (sel_full if sel_full else all_opts[0]).split(" ")[1]

            st.markdown("---")
            st.markdown(f'<div class="calc-screen">{st.session_state.calc_val}</div>', unsafe_allow_html=True)

            def press(key):
                if key == "AC": st.session_state.calc_val = "0"
                elif key == "DEL": 
                    st.session_state.calc_val = st.session_state.calc_val[:-1] if len(st.session_state.calc_val) > 1 else "0"
                else:
                    if st.session_state.calc_val == "0": st.session_state.calc_val = str(key)
                    else: st.session_state.calc_val += str(key)

            keys = [['7', '8', '9', 'DEL'], ['4', '5', '6', '*'], ['1', '2', '3', '-'], ['0', '.', 'AC', '+']]
            for row in keys:
                cols = st.columns(4)
                for i, k in enumerate(row):
                    if cols[i].button(k, key=f"kb_{k}_{row}"): press(k)

            item_note = st.text_input("備註 (選填)")
            if st.button("✅ 存入金庫", type="primary", use_container_width=True):
                try:
                    final_amt = float(eval(st.session_state.calc_val))
                    if final_amt > 0:
                        wks.append_row([str(input_date), f"{CATEGORIES[current_cat_name]} {current_cat_name}", item_note if item_note else current_cat_name, final_amt, "支出", fixed_val, pocket_val - final_amt])
                        st.session_state.calc_val = "0"
                        st.balloons()
                        st.rerun()
                except: st.error("計算失敗，請檢查輸入內容")

        # --- Tab 2: 分析 ---
        with tabs[1]:
            if not df.empty:
                df_exp = df[df['類型'] == '支出'].copy()
                if not df_exp.empty:
                    df_exp['金額'] = pd.to_numeric(df_exp['金額'])
                    fig = px.pie(df_exp, values='金額', names='類別', hole=0.4, title="支出佔比")
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("尚無支出資料可分析")
            else: st.info("尚無資料")

        # --- Tab 3: 明細管理 (原地編輯版) ---
        with tabs[2]:
            st.markdown("#### 📜 歷史明細紀錄")
            if not df.empty:
                for i in range(len(df)-1, -1, -1):
                    row = df.iloc[i]
                    edit_key = f"edit_{i}"
                    with st.expander(f"{row['日期']} | {row['類別']} | ${row['金額']}"):
                        if not st.session_state.get(edit_key, False):
                            st.write(f"項目: {row['項目']}")
                            st.write(f"類型: {row['類型']}")
                            c1, c2 = st.columns(2)
                            if c1.button("✏️ 編輯", key=f"btn_ed_{i}"):
                                st.session_state[edit_key] = True
                                st.rerun()
                            if c2.button("🗑️ 刪除", key=f"btn_de_{i}"):
                                adj = float(row['金額']) if row['類型'] == "支出" else -float(row['金額'])
                                wks.delete_rows(i + 2)
                                wks.append_row([str(
