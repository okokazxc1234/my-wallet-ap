import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. 頁面與終極 CSS 強制佈局 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 強制手機版鍵盤 4 欄網格 */
    div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 6px !important;
        padding: 5px 0 !important;
    }
    div[data-testid="column"] {
        width: 100% !important;
        min-width: 0 !important;
        flex: none !important;
    }
    /* 鍵盤按鈕樣式 */
    [data-testid="stBaseButton-secondary"] {
        height: 55px !important;
        width: 100% !important;
        font-size: 22px !important;
        font-weight: bold !important;
        border-radius: 12px !important;
    }
    /* 計算機螢幕 */
    .calc-screen {
        background-color: #1e1e23;
        color: #00ff41;
        padding: 12px 18px;
        border-radius: 15px;
        text-align: right;
        margin-bottom: 12px;
        font-family: 'monospace';
        font-size: 38px;
        font-weight: bold;
        border: 2px solid #3d3d4d;
    }
    /* 自定義餘額卡片 (解決 st.metric 變成 ... 的問題) */
    .balance-container {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 20px;
    }
    .balance-card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 10px;
        border-radius: 12px;
        width: 48%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .balance-label {
        font-size: 14px;
        color: #666;
        margin-bottom: 4px;
    }
    .balance-value {
        font-size: 20px;
        font-weight: bold;
        color: #333;
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
    except: return None

CATEGORIES = {
    "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", 
    "點心": "🍰", "酒類": "🍺", "交通": "🚗", "購物": "🛍️", 
    "娛樂": "🎮", "日用品": "🧻", "房租": "🏠", "醫療": "🏥", 
    "社交": "👥", "禮物": "🎁", "數位": "💻", "其他": "✨"
}

client = get_gs_client()
fixed_val, pocket_val = 0.0, 0.0
df = pd.DataFrame()

if client:
    try:
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        records = wks.get_all_records()
        
        if records:
            df = pd.DataFrame(records)
            last_row = df.iloc[-1]
            fixed_val = float(last_row.get('定存總額', 0))
            pocket_val = float(last_row.get('零用總額', 0))

        st.markdown("### 🍎 目前資產狀態")
        
        # 使用自定義 HTML 代替 st.metric，防止數字變成 ...
        st.markdown(f"""
            <div class="balance-container">
                <div class="balance-card">
                    <div class="balance-label">🔒 定存</div>
                    <div class="balance-value">${fixed_val:,.0f}</div>
                </div>
                <div class="balance-card">
                    <div class="balance-label">💳 零用</div>
                    <div class="balance-value">${pocket_val:,.0f}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        tabs = st.tabs(["📝 記帳", "📊 分析", "📜 明細", "⚙️ 設定"])

        with tabs[0]:
            if 'calc_val' not in st.session_state: st.session_state.calc_val = "0"
            input_date = st.date_input("日期", datetime.now())
            all_opts = [f"{v} {k}" for k, v in CATEGORIES.items()]
            sel_full = st.pills("類別", all_opts, selection_mode="single", default=all_opts[0])
            current_cat = (sel_full if sel_full else all_opts[0]).split(" ")[1]

            st.markdown(f'<div class="calc-screen">{st.session_state.calc_val}</div>', unsafe_allow_html=True)

            def press(key):
                if key == "AC": st.session_state.calc_val = "0"
                elif key == "DEL": 
                    st.session_state.calc_val = st.session_state.calc_val[:-1] if len(st.session_state.calc_val) > 1 else "0"
                else:
                    if st.session_state.calc_val == "0": st.session_state.calc_val = str(key)
                    else: st.session_state.calc_val += str(key)

            keys = ['7','8','9','DEL','4','5','6','*','1','2','3','-','0','.','AC','+']
            cols = st.columns(len(keys))
            for i, k in enumerate(keys):
                if cols[i].button(k, key=f"kb_{k}_{i}"): press(k)

            note = st.text_input("備註 (選填)")
            if st.button("🚀 確認送出", type="primary", use_container_width=True):
                try:
                    final_amt = float(eval(st.session_state.calc_val))
                    if final_amt > 0:
                        wks.append_row([str(input_date), f"{CATEGORIES[current_cat]} {current_cat}", note if note else current_cat, final_amt, "支出", fixed_val, pocket_val - final_amt])
                        st.session_state.calc_val = "0"
                        st.success(f"已記錄 ${final_amt}")
                        st.rerun()
                except: st.error("金額有誤")

        with tabs[1]:
            if not df.empty:
                df_exp = df[df['類型'] == '支出'].copy()
                if not df_exp.empty:
                    df_exp['金額'] = pd.to_numeric(df_exp['金額'])
                    fig = px.pie(df_exp, values='金額', names='類別', hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            if not df.empty:
                for i in range(len(df)-1, -1, -1):
                    row = df.iloc[i]
                    with st.expander(f"{row['日期']} | {row['類別']} | ${row['金額']}"):
                        st.write(f"項目: {row['項目']}")
                        if st.button("🗑️ 刪除", key=f"del_{i}"):
                            adj = float(row['金額']) if row['類型'] == "支出" else -float(row['金額'])
                            wks.delete_rows(i + 2)
                            wks.append_row([str(datetime.now().date()), "🔄 系統", "刪除校正", 0, "校正", fixed_val, pocket_val + adj])
                            st.rerun()

        with tabs[3]:
            st.markdown("#### 💰 薪資入帳")
            s_amt = st.number_input("薪資總額", value=0.0)
            s_ratio = st.slider("存入定存 %", 0, 100, 30)
            if st.button("🚀 確認入帳", use_container_width=True):
                to_f = s_amt * (s_ratio / 100)
                to_p = s_amt - to_f
                wks.append_row([str(datetime.now().date()), "💰 收入", "薪水", s_amt, "收入", fixed_val + to_f, pocket_val + to_p])
                st.rerun()
            
            st.markdown("---")
            st.markdown("#### ⚙️ 金額校正")
            new_f = st.number_input("校正定存", value=fixed_val)
            new_p = st.number_input("校正零用", value=pocket_val)
            if st.button("💾 覆蓋餘額"):
                wks.append_row([str(datetime.now().date()), "⚙️ 系統", "手動校正", 0, "校正", new_f, new_p])
                st.rerun()

    except Exception as e: st.error(f"❌ 錯誤: {e}")
