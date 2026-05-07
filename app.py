import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered", initial_sidebar_state="collapsed")

# 設置 Session State 初始值
if 'calc_val' not in st.session_state:
    st.session_state.calc_val = "0"

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    /* 大螢幕螢幕樣式 */
    .big-display {
        background-color: #1e1e23; color: #00ff41; padding: 15px; border-radius: 15px;
        text-align: right; font-family: 'monospace'; font-size: 42px; font-weight: bold;
        margin-bottom: 20px; border: 2px solid #3d3d4d; box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
    }
    /* 讓按鈕整齊 */
    div.stButton > button { width: 100%; height: 60px; font-size: 20px; font-weight: bold; border-radius: 12px; }
    .stPills div[role="listbox"] { justify-content: center; }
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
        col1, col2 = st.columns(2)
        col1.metric("🔒 定存", f"${fixed_val:,.0f}")
        col2.metric("💳 零用", f"${pocket_val:,.0f}")

        tabs = st.tabs(["📝 快速記帳", "📜 明細", "⚙️ 設定"])

        with tabs[0]:
            input_date = st.date_input("日期", datetime.now())
            CATEGORIES = {
                "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "點心": "🍰", 
                "酒類": "🍺", "交通": "🚗", "購物": "🛍️", "娛樂": "🎮", "日用品": "🧻", 
                "房租": "🏠", "醫療": "🏥", "社交": "👥", "禮物": "🎁", "數位": "💻", "其他": "✨"
            }
            all_opts = [f"{v} {k}" for k, v in CATEGORIES.items()]
            sel_full = st.pills("類別", all_opts, selection_mode="single", default=all_opts[0])
            current_cat = (sel_full if sel_full else all_opts[0]).split(" ")[1]
            
            # --- 大數字螢幕 ---
            st.markdown(f'<div class="big-display">{st.session_state.calc_val}</div>', unsafe_allow_html=True)

            # --- 原生按鈕鍵盤 (保證同步) ---
            def add_digit(d):
                if st.session_state.calc_val == "0": st.session_state.calc_val = str(d)
                else: st.session_state.calc_val += str(d)

            def clear_val(): st.session_state.calc_val = "0"
            def backspace(): 
                st.session_state.calc_val = st.session_state.calc_val[:-1] if len(st.session_state.calc_val) > 1 else "0"

            # 繪製鍵盤排版
            k_col1, k_col2, k_col3, k_col4 = st.columns(4)
            if k_col1.button("7"): add_digit(7); st.rerun()
            if k_col2.button("8"): add_digit(8); st.rerun()
            if k_col3.button("9"): add_digit(9); st.rerun()
            if k_col4.button("⌫", type="secondary"): backspace(); st.rerun()

            if k_col1.button("4"): add_digit(4); st.rerun()
            if k_col2.button("5"): add_digit(5); st.rerun()
            if k_col3.button("6"): add_digit(6); st.rerun()
            if k_col4.button("×"): add_digit("*"); st.rerun()

            if k_col1.button("1"): add_digit(1); st.rerun()
            if k_col2.button("2"): add_digit(2); st.rerun()
            if k_col3.button("3"): add_digit(3); st.rerun()
            if k_col4.button("-"): add_digit("-"); st.rerun()

            if k_col1.button("0"): add_digit(0); st.rerun()
            if k_col2.button("."): add_digit("."); st.rerun()
            if k_col3.button("AC"): clear_val(); st.rerun()
            if k_col4.button("+"): add_digit("+"); st.rerun()

            note = st.text_input("備註 (選填)")
            
            if st.button("🚀 確認送出支出", type="primary"):
                try:
                    # 直接從 Session State 計算結果
                    amt = float(eval(st.session_state.calc_val))
                    if amt > 0:
                        wks.append_row([str(input_date), f"{CATEGORIES[current_cat]} {current_cat}", note if note else current_cat, amt, "支出", fixed_val, pocket_val - amt])
                        st.session_state.calc_val = "0" # 送出後重置
                        st.balloons()
                        st.rerun()
                    else:
                        st.warning("金額需大於 0")
                except:
                    st.error("計算錯誤，請按 AC 重來")

        # --- 明細分頁 ---
        with tabs[1]:
            if records:
                df = pd.DataFrame(records)
                for i in range(len(df)-1, -1, -1):
                    row = df.iloc[i]
                    with st.expander(f"{row['日期']} | {row['類別']} | ${row['金額']}"):
                        if st.button("🗑️ 刪除", key=f"del_{i}"):
                            adj = float(row['金額']) if row['類型'] == "支出" else -float(row['金額'])
                            wks.delete_rows(i + 2)
                            wks.append_row([str(datetime.now().date()), "🔄 系統", "刪除校正", 0, "校正", fixed_val, pocket_val + adj])
                            st.rerun()

        with tabs[2]:
            st.markdown("#### 💰 資金入帳管理")
            col_a, col_b = st.columns(2)
            i_f = col_a.number_input("📥 存入定存", min_value=0.0)
            i_p = col_b.number_input("📥 存入零用", min_value=0.0)
            if st.button("🚀 執行撥款入帳"):
                if (i_f + i_p) > 0:
                    wks.append_row([str(datetime.now().date()), "💰 收入", "入帳", i_f + i_p, "收入", fixed_val + i_f, pocket_val + i_p])
                    st.rerun()

    except Exception as e: st.error(f"連線異常: {e}")
