import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. 連線與頁面設定 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered", initial_sidebar_state="collapsed")

# --- 超強手機版按鈕 CSS 補丁：強制精緻緊湊佈局 ---
st.markdown("""
    <style>
    /* 1. 強制所有 Col 不換行，且寬度 25% */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important; /* 按鈕之間的間距 */
        margin-bottom: 2px !important;
    }
    div[data-testid="column"] {
        width: 25% !important;
        flex: 1 1 calc(25% - 2px) !important;
        min-width: calc(25% - 2px) !important;
    }

    /* 2. 針對鍵盤內的按鈕進行高度控制 (關鍵！) */
    [data-testid="stBaseButton-secondary"] {
        height: 45px !important;     /* 強制高度，讓按鈕變扁 */
        line-height: 45px !important;
        padding: 0px !important;      /* 移除內部間距 */
        margin: 0px !important;
        font-size: 18px !important;   /* 調整按鈕字體大小 */
        border-radius: 5px !important;
    }

    /* 3. 優化數字顯示螢幕 */
    .calc-screen {
        background-color: #1e1e23;
        color: #ffffff;
        padding: 10px 15px;
        border-radius: 8px;
        text-align: right;
        margin-bottom: 8px;
        font-family: 'Courier New', monospace;
        font-size: 32px;
        font-weight: bold;
        border: 1px solid #3d3d4d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Google Sheets 連線設定 ---
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

        tabs = st.tabs(["📝 快速記帳", "📊 分析", "📜 明細管理", "⚙️ 設定"])

        # --- Tab 1: 快速記帳 (虛擬鍵盤已優化) ---
        with tabs[0]:
            if 'calc_val' not in st.session_state: st.session_state.calc_val = "0"
            
            st.markdown("#### 📅 1. 日期與類別")
            input_date = st.date_input("日期", datetime.now(), label_visibility="collapsed")
            all_options = [f"{v} {k}" for k, v in CATEGORIES.items()]
            sel_full = st.pills("類別選擇", all_options, selection_mode="single", default=all_options[0], label_visibility="collapsed")
            current_cat_name = (sel_full if sel_full else all_options[0]).split(" ")[1]

            st.markdown("---")
            
            # 使用自定義 CSS 類別的顯示螢幕
            st.markdown(f'<div class="calc-screen">{st.session_state.calc_val}</div>', unsafe_allow_html=True)

            def press(key):
                if key == "AC": st.session_state.calc_val = "0"
                elif key == "DEL": st.session_state.calc_val = st.session_state.calc_val[:-1] if len(st.session_state.calc_val) > 1 else "0"
                else:
                    if st.session_state.calc_val == "0": st.session_state.calc_val = str(key)
                    else: st.session_state.calc_val += str(key)

            # 鍵盤排列 (緊湊)
            keys = [
                ['7', '8', '9', 'DEL'],
                ['4', '5', '6', '*'],
                ['1', '2', '3', '-'],
                ['0', '.', 'AC', '+']
            ]

            # 渲染鍵盤 (這部分會套用 CSS 補丁)
            for row in keys:
                cols = st.columns(4)
                for i, key in enumerate(row):
                    if cols[i].button(key, key=f"kb_{key}_{row}", use_container_width=True):
                        press(key)

            item_note = st.text_input("備註 (選填)")

            if st.button("🚀 確認送出帳單", type="primary", use_container_width=True):
                try:
                    # 計算結果
                    expr = st.session_state.calc_val.replace('x', '*').replace('÷', '/')
                    final_amt = float(eval(expr))
                    
                    if final_amt > 0:
                        wks.append_row([str(input_date), f"{CATEGORIES[current_cat_name]} {current_cat_name}", item_note if item_note else current_cat_name, final_amt, "支出", fixed_val, pocket_val - final_amt])
                        st.session_state.calc_val = "0"
                        st.success(f"已紀錄支出 ${final_amt}")
                        st.rerun()
                except:
                    st.error("金額計算錯誤")

        # --- 其他分頁保持原功能 ---
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

    except Exception as e:
        st.error(f"❌ 錯誤: {e}")
