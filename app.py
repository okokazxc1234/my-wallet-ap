import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. 連線設定 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered")
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

        if df.empty:
            fixed_val, pocket_val = 50000.0, 5000.0
            fav_list = list(CATEGORIES.keys())[:4]
        else:
            fixed_val = float(df.iloc[-1]['定存總額'])
            pocket_val = float(df.iloc[-1]['零用總額'])
            df_exp = df[df['類型'] == '支出'].copy()
            if not df_exp.empty:
                df_exp['pure_cat'] = df_exp['類別'].apply(lambda x: x.split(" ")[-1] if " " in str(x) else x)
                top_cats = df_exp['pure_cat'].value_counts().index.tolist()
                fav_list = top_cats + [c for c in CATEGORIES.keys() if c not in top_cats]
            else:
                fav_list = list(CATEGORIES.keys())[:4]

        st.markdown(f"### 🍎 帳戶總覽")
        c1, c2 = st.columns(2)
        c1.metric("🔒 定存金庫", f"${fixed_val:,.0f}")
        c2.metric("💳 零用預算", f"${pocket_val:,.0f}")

        tabs = st.tabs(["📝 快速記帳", "📊 分析", "📜 明細管理", "⚙️ 設定"])

        # --- Tab 1: 快速記帳 (使用 Pills 標籤，完全不跳鍵盤) ---
        with tabs[0]:
            st.markdown("#### 📅 1. 選擇日期")
            input_date = st.date_input("日期", datetime.now(), label_visibility="collapsed")
            
            st.markdown("#### 🏷️ 2. 選擇分類")
            # 這裡使用 st.pills，它在手機上是純按鈕選擇，不會觸發鍵盤
            all_options = [f"{v} {k}" for k, v in CATEGORIES.items()]
            
            # 處理初始選中項
            default_selection = all_options[0]
            if 'temp_cat' in st.session_state:
                try: 
                    default_selection = f"{CATEGORIES[st.session_state.temp_cat]} {st.session_state.temp_cat}"
                except: pass
            
            # 使用 pills (標籤按鈕)
            sel_full = st.pills("類別選擇", all_options, selection_mode="single", default=default_selection)
            
            # 如果使用者沒選，就用預設的
            chosen = sel_full if sel_full else default_selection
            current_cat_name = chosen.split(" ")[1]

            st.markdown("#### 💰 3. 輸入金額")
            ac1, ac2, ac3, ac4 = st.columns(4)
            if 'temp_amt' not in st.session_state: st.session_state.temp_amt = 0.0
            if ac1.button("+50"): st.session_state.temp_amt += 50
            if ac2.button("+100"): st.session_state.temp_amt += 100
            if ac3.button("+500"): st.session_state.temp_amt += 500
            if ac4.button("重設"): st.session_state.temp_amt = 0.0

            final_amt = st.number_input("金額確認", value=st.session_state.temp_amt, step=10.0)
            item_note = st.text_input("備註 (選填)")

            if st.button("✅ 確認紀錄支出", type="primary", use_container_width=True):
                if final_amt > 0:
                    wks.append_row([str(input_date), f"{CATEGORIES[current_cat_name]} {current_cat_name}", item_note if item_note else current_cat_name, final_amt, "支出", fixed_val, pocket_val - final_amt])
                    st.session_state.temp_amt = 0.0
                    st.rerun()

        # --- 以下分頁保持一致功能 ---
        with tabs[1]:
            if not df.empty:
                df_exp_plot = df[df['類型'] == '支出'].copy()
                if not df_exp_plot.empty:
                    df_exp_plot['金額'] = pd.to_numeric(df_exp_plot['金額'])
                    fig = px.pie(df_exp_plot, values='金額', names='類別', hole=0.5)
                    st.plotly_chart(fig, use_container_width=True)
        
        with tabs[2]:
            if not df.empty:
                for i in range(len(df)-1, -1, -1):
                    row = df.iloc[i]
                    edit_key = f"edit_mode_{i}"
                    with st.expander(f"{row['日期']} | {row['類別']} | ${row['金額']}", expanded=st.session_state.get(edit_key, False)):
                        if not st.session_state.get(edit_key, False):
                            c1, c2 = st.columns([4, 1])
                            c1.write(f"項目: {row['項目']} ({row['類型']})")
                            if c2.button("✏️", key=f"be_{i}"):
                                st.session_state[edit_key] = True
                                st.rerun()
                        else:
                            nd = st.date_input("日期", datetime.strptime(str(row['日期']), '%Y-%m-%d'), key=f"d_{i}")
                            ni = st.text_input("項目", value=row['項目'], key=f"it_{i}")
                            na = st.number_input("金額", value=float(row['金額']), key=f"am_{i}")
                            ec1, ec2, ec3 = st.columns(3)
                            if ec1.button("💾 儲存", key=f"sv_{i}"):
                                diff = float(row['金額']) - na
                                adj = diff
