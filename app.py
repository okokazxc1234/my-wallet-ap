import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. Google Sheets 連線設定 ---
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

        # 讀取餘額與常用習慣
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

        tabs = st.tabs(["📝 快速記帳", "📊 分析", "📜 明細", "⚙️ 設定"])

        with tabs[0]:
            # --- 新增日期選擇功能 ---
            st.markdown("#### 1. 選擇日期與類別")
            input_date = st.date_input("記帳日期", datetime.now())
            
            fav_cols = st.columns(4)
            for i, cat in enumerate(fav_list[:4]):
                if fav_cols[i].button(f"{CATEGORIES.get(cat, '✨')}\n{cat}", key=f"f_{cat}"):
                    st.session_state.temp_cat = cat

            st.markdown("---")
            all_opts = [f"{v} {k}" for k, v in CATEGORIES.items()]
            default_idx = 0
            if 'temp_cat' in st.session_state:
                try: default_idx = list(CATEGORIES.keys()).index(st.session_state.temp_cat)
                except: pass
            
            sel_full = st.selectbox("或從清單選擇", all_opts, index=default_idx)
            current_cat_name = sel_full.split(" ")[1]

            st.markdown("#### 2. 輸入金額")
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
                    new_pocket = pocket_val - final_amt
                    # 使用使用者選擇的 input_date 進行儲存
                    wks.append_row([
                        str(input_date), 
                        f"{CATEGORIES[current_cat_name]} {current_cat_name}", 
                        item_note if item_note else current_cat_name, 
                        final_amt, "支出", fixed_val, new_pocket
                    ])
                    st.session_state.temp_amt = 0.0
                    st.success(f"已紀錄 {input_date} 的帳目！")
                    st.balloons()
                    st.rerun()

        # --- 以下分頁保持不變 ---
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
                    col_a, col_b, col_c = st.columns([3, 2, 1])
                    col_a.write(f"**{row['日期']}**\n{row['類別']} | {row['項目']}")
                    color = "red" if row['類型'] == "支出" else "green"
                    col_b.markdown(f"<h4 style='color:{color}; text-align:right;'>${row['金額']}</h4>", unsafe_allow_html=True)
                    if col_c.button("🗑️", key=f"del_{i}"):
                        wks.delete_rows(i + 2)
                        st.rerun()
                    st.divider()

        with tabs[3]:
            st.markdown("#### 💰 薪水發放")
            salary_date = st.date_input("入帳日期", datetime.now())
            salary = st.number_input("薪水總額", value=30000.0)
            ratio = st.slider("存入定存比例 %", 0, 100, 30)
            if st.button("🚀 撥款入帳", use_container_width=True):
                to_f = salary * (ratio / 100)
                to_p = salary - to_f
                wks.append_row([
                    str(salary_date), "💰 薪水", "薪水入帳", 
                    salary, "收入", fixed_val + to_f, pocket_val + to_p
                ])
                st.balloons()
                st.rerun()

    except Exception as e:
        st.error(f"❌ 讀取錯誤: {e}")
