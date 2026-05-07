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

        # --- Tab 1: 快速記帳 (鎖定選擇) ---
        with tabs[0]:
            st.markdown("#### 1. 選擇日期")
            input_date = st.date_input("記帳日期", datetime.now(), label_visibility="collapsed")
            
            st.markdown("#### 2. 選擇分類")
            # 常用按鈕
            fav_cols = st.columns(4)
            for i, cat in enumerate(fav_list[:4]):
                if fav_cols[i].button(f"{CATEGORIES.get(cat, '✨')}\n{cat}", key=f"f_{cat}", use_container_width=True):
                    st.session_state.temp_cat = cat

            st.markdown("---")
            # 這裡改成單選按鈕(Radio)或嚴格的選擇框，防止手機跳出鍵盤
            all_opts = [f"{v} {k}" for k, v in CATEGORIES.items()]
            
            default_idx = 0
            if 'temp_cat' in st.session_state:
                try: 
                    # 找出對應圖示的完整字串
                    target = f"{CATEGORIES[st.session_state.temp_cat]} {st.session_state.temp_cat}"
                    default_idx = all_opts.index(target)
                except: pass
            
            # 使用 selectbox 但加上 placeholder 並確保它在手機上更像選單
            sel_full = st.selectbox("詳細類別清單", all_opts, index=default_idx)
            current_cat_name = sel_full.split(" ")[1]

            st.markdown("#### 3. 輸入金額")
            # 金額快捷鍵
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
                    st.success("紀錄成功！")
                    st.rerun()

        # --- 其他分頁保持與上次功能一致 (明細編輯、分析、校正) ---
        with tabs[1]:
            if not df.empty:
                df_exp_plot = df[df['類型'] == '支出'].copy()
                if not df_exp_plot.empty:
                    df_exp_plot['金額'] = pd.to_numeric(df_exp_plot['金額'])
                    fig = px.pie(df_exp_plot, values='金額', names='類別', hole=0.5)
                    st.plotly_chart(fig, use_container_width=True)
