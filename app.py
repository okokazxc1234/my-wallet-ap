import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. 連線設定 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered")

# --- CSS 修正：強制手機版 columns 不換行 ---
st.markdown("""
    <style>
    [data-testid="column"] {
        width: calc(25% - 1rem) !important;
        flex: 1 1 calc(25% - 1rem) !important;
        min-width: calc(25% - 1rem) !important;
    }
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
    }
    </style>
    """, unsafe_allow_html=True)

scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

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

        fixed_val = float(df.iloc[-1]['定存總額']) if not df.empty else 50000.0
        pocket_val = float(df.iloc[-1]['零用總額']) if not df.empty else 5000.0

        st.markdown(f"### 🍎 帳戶總覽")
        c1, c2 = st.columns(2)
        c1.metric("🔒 定存", f"${fixed_val:,.0f}")
        c2.metric("💳 零用", f"${pocket_val:,.0f}")

        tabs = st.tabs(["📝 快速記帳", "📊 分析", "📜 明細", "⚙️ 設定"])

        with tabs[0]:
            if 'calc_val' not in st.session_state: st.session_state.calc_val = "0"
            
            input_date = st.date_input("日期", datetime.now())
            all_options = [f"{v} {k}" for k, v in CATEGORIES.items()]
            sel_full = st.pills("類別", all_options, selection_mode="single", default=all_options[0])
            current_cat_name = (sel_full if sel_full else all_options[0]).split(" ")[1]

            # 螢幕顯示
            st.markdown(f"""
            <div style="background-color:#262730; padding:15px; border-radius:10px; text-align:right; margin-bottom:10px; border: 1px solid #464b5d;">
                <span style="color:#ffffff; font-size:35px; font-family:monospace;">{st.session_state.calc_val}</span>
            </div>
            """, unsafe_allow_html=True)

            def press(key):
                if key == "AC": st.session_state.calc_val = "0"
                elif key == "DEL": st.session_state.calc_val = st.session_state.calc_val[:-1] if len(st.session_state.calc_val) > 1 else "0"
                else:
                    if st.session_state.calc_val == "0": st.session_state.calc_val = str(key)
                    else: st.session_state.calc_val += str(key)

            # 鍵盤佈局
            keys = [
                ['7', '8', '9', '/'],
                ['4', '5', '6', '*'],
                ['1', '2', '3', '-'],
                ['0', '.', 'AC', '+']
            ]

            for row in keys:
                cols = st.columns(4)
                for i, key in enumerate(row):
                    if cols[i].button(key, key=f"k_{key}_{row}", use_container_width=True):
                        press(key)

            item_note = st.text_input("備註")
            if st.button("🚀 確認送出", type="primary", use_container_width=True):
                try:
                    final_amt = float(eval(st.session_state.calc_val))
                    if final_amt > 0:
                        wks.append_row([str(input_date), f"{CATEGORIES[current_cat_name]} {current_cat_name}", item_note if item_note else current_cat_name, final_amt, "支出", fixed_val, pocket_val - final_amt])
                        st.session_state.calc_val = "0"
                        st.success(f"已紀錄 ${final_amt}")
                        st.rerun()
                except:
                    st.error("計算錯誤")

        # --- 之後的分頁保持不變 ---
        with tabs[2]:
            if not df.empty:
                for i in range(len(df)-1, -1, -1):
                    row = df.iloc[i]
                    with st.expander(f"{row['日期']} | {row['類別']} | ${row['金額']}"):
                        if st.button("🗑️ 刪除", key=f"dl_{i}"):
                            adj = float(row['金額']) if row['類型'] == "支出" else -float(row['金額'])
                            wks.delete_rows(i + 2)
                            wks.append_row([str(datetime.now().date()), "🔄 系統", "刪除校正", 0, "校正", fixed_val, pocket_val + adj])
                            st.rerun()

        with tabs[3]:
            s_amt = st.number_input("入帳金額", value=30000.0)
            if st.button("🚀 確認撥款", use_container_width=True):
                wks.append_row([str(datetime.now().date()), "💰 收入", "入帳", s_amt, "收入", fixed_val, pocket_val + s_amt])
                st.rerun()

    except Exception as e:
        st.error(f"❌ 錯誤: {e}")
