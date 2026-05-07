import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered", initial_sidebar_state="collapsed")

# 初始化計算機狀態
if 'calc_val' not in st.session_state:
    st.session_state.calc_val = "0"

# --- 自定義 CSS：美化 UI 並強迫手機版橫向排列 ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    
    /* 螢幕顯示區域 */
    .big-display {
        background-color: #1e1e23; color: #00ff41; padding: 20px; border-radius: 15px;
        text-align: right; font-family: 'monospace'; font-size: 48px; font-weight: bold;
        margin-bottom: 10px; border: 2px solid #3d3d4d; box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
    }
    
    /* 強制按鈕在手機上不換行 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 6px !important;
    }
    div[data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
    }
    
    /* 按鈕美化 */
    div.stButton > button {
        width: 100% !important; height: 60px !important;
        font-size: 22px !important; font-weight: bold !important;
        border-radius: 12px !important; background-color: #f8f9fa;
        border: 1px solid #ddd; color: #333;
    }
    /* 運算符按鈕顏色 */
    div.stButton > button[key^="op_"] { background-color: #f1f3f5; color: #007bff; }
    /* 功能按鈕顏色 */
    div.stButton > button[key^="fn_"] { background-color: #e9ecef; color: #dc3545; }
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

# 鍵盤點擊邏輯
def press(key):
    cur = st.session_state.calc_val
    if key == "AC": st.session_state.calc_val = "0"
    elif key == "DEL": st.session_state.calc_val = cur[:-1] if len(cur) > 1 else "0"
    elif key == "=":
        try: st.session_state.calc_val = str(eval(cur.replace('×', '*').replace('÷', '/')))
        except: st.session_state.calc_val = "Error"
    else:
        if cur in ["0", "Error"]: st.session_state.calc_val = str(key)
        else: st.session_state.calc_val += str(key)

# --- 主程式執行 ---
client = get_gs_client()
if client:
    sh = client.open("my_wallet_db")
    wks = sh.get_worksheet(0)
    recs = wks.get_all_records()
    df = pd.DataFrame(recs)
    
    fixed_val = float(df.iloc[-1]['定存總額']) if not df.empty else 0
    pocket_val = float(df.iloc[-1]['零用總額']) if not df.empty else 0

    st.markdown(f"### 🍎 帳戶總覽")
    c1, c2 = st.columns(2)
    c1.metric("🔒 定存", f"${fixed_val:,.0f}")
    c2.metric("💳 零用", f"${pocket_val:,.0f}")

    tabs = st.tabs(["📝 快速記帳", "📊 分析", "📜 管理", "⚙️ 設定"])

    with tabs[0]:
        input_date = st.date_input("日期", datetime.now())
        
        CATEGORIES = {"早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "點心": "🍰", "交通": "🚗", "購物": "🛍️", "娛樂": "🎮", "其他": "✨"}
        sel = st.pills("類別", [f"{v} {k}" for k, v in CATEGORIES.items()], selection_mode="single", default="🥪 早餐")
        curr_cat = (sel if sel else "🥪 早餐").split(" ")[1]

        # 顯示金額螢幕
        st.markdown(f'<div class="big-display">{st.session_state.calc_val}</div>', unsafe_allow_html=True)

        # --- 數字鍵盤區 ---
        col1 = st.columns(4)
        if col1[0].button("7"): press("7"); st.rerun()
        if col1[1].button("8"): press("8"); st.rerun()
        if col1[2].button("9"): press("9"); st.rerun()
        if col1[3].button("÷", key="op_div"): press("/"); st.rerun()

        col2 = st.columns(4)
        if col2[0].button("4"): press("4"); st.rerun()
        if col2[1].button("5"): press("5"); st.rerun()
        if col2[2].button("6"): press("6"); st.rerun()
        if col2[3].button("×", key="op_mul"): press("*"); st.rerun()

        col3 = st.columns(4)
        if col3[0].button("1"): press("1"); st.rerun()
        if col3[1].button("2"): press("2"); st.rerun()
        if col3[2].button("3"): press("3"); st.rerun()
        if col3[3].button("-", key="op_sub"): press("-"); st.rerun()

        col4 = st.columns(4)
        if col4[0].button("0"): press("0"); st.rerun()
        if col4[1].button("."): press("."); st.rerun()
        if col4[2].button("AC", key="fn_ac"): press("AC"); st.rerun()
        if col4[3].button("+", key="op_add"): press("+"); st.rerun()

        col5 = st.columns([1, 3])
        if col5[0].button("⌫", key="fn_del"): press("DEL"); st.rerun()
        if col5[1].button("＝ 計算結果", key="op_eq"): press("="); st.rerun()

        note = st.text_input("備註 (選填)")
        
        if st.button("🚀 確認送出支出", type="primary", use_container_width=True):
            try:
                final_amt = float(eval(st.session_state.calc_val))
                if final_amt > 0:
                    wks.append_row([str(input_date), f"{CATEGORIES[curr_cat]} {curr_cat}", note if note else curr_cat, final_amt, "支出", fixed_val, pocket_val - final_amt])
                    st.session_state.calc_val = "0"
                    st.success(f"已記錄 ${final_amt}")
                    st.rerun()
            except: st.error("金額計算錯誤")

    # --- 分析/明細 (簡略版，保持原本功能) ---
    with tabs[1]:
        if not df.empty:
            df_exp = df[df['類型'] == '支出'].copy()
            st.plotly_chart(px.pie(df_exp, values='金額', names='類別', hole=0.4), use_container_width=True)
    
    with tabs[2]:
        st.dataframe(df.iloc[::-1].head(15), use_container_width=True)
