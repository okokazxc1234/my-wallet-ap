import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. Google Sheets 連線設定 ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_gs_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 無法讀取金鑰，請檢查 Secrets 設定: {e}")
        return None

# --- 2. 分類與圖示定義 ---
CATEGORIES = {
    "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", 
    "點心": "🍰", "酒類": "🍺", "交通": "🚗", "購物": "🛍️", 
    "娛樂": "🎮", "日用品": "🧻", "房租": "🏠", "醫療": "🏥", 
    "社交": "👥", "禮物": "🎁", "數位": "💻", "其他": "✨"
}

# --- 3. App 主邏輯 ---
st.set_page_config(page_title="Wallet Pro Max", layout="centered")

client = get_gs_client()

if client:
    try:
        # 開啟試算表 (請確保檔名正確)
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        
        # 讀取現有資料
        all_records = wks.get_all_records()
        df = pd.DataFrame(all_records)
        
        # 處理初始餘額與常用習慣
        if df.empty:
            fixed_val, pocket_val = 50000.0, 5000.0
            fav_list = list(CATEGORIES.keys())[:4]
        else:
            # 取最後一行的數值作為當前餘額
            fixed_val = float(df.iloc[-1]['定存總額'])
            pocket_val = float(df.iloc[-1]['零用總額'])
            
            # 根據歷史自動學習常用習慣
            df_exp = df[df['類型'] == '支出'].copy()
            if not df_exp.empty:
                # 統計出現頻率最高的類別
                df_exp['pure_cat'] = df_exp['類別'].apply(lambda x: x.split(" ")[-1] if " " in str(x) else x)
                top_cats = df_exp['pure_cat'].value_counts().index.tolist()
                fav_list = top_cats + [c for c in CATEGORIES.keys() if c not in top_cats]
            else:
                fav_list = list(CATEGORIES.keys())[:4]

        # 頂部儀表板
        st.markdown(f"### 🍎 帳戶總覽")
        c1, c2 = st.columns(2)
        c1.metric("🔒 定存金庫", f"${fixed_val:,.0f}")
        c2.metric("💳 零用預算", f"${pocket_val:,.0f}")

        tabs = st.tabs(["📝 快速記帳", "📊 統計分析", "📜 歷史明細", "⚙️ 管理與薪水"])

        # --- Tab 1: 記帳 ---
        with tabs[0]:
            st.markdown("#### 1. 常用類別")
            fav_cols = st.columns(4)
            for i, cat in enumerate(fav_list[:4]):
                icon = CATEGORIES.get(cat, '✨')
                if fav_cols[i].button(f"{icon}\n{cat}", key=f"f_{cat}"):
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

            if st.button("✅ 確認紀錄支出", type="primary"):
                if final_amt > 0:
                    new_pocket = pocket_val - final_amt
                    # 寫入 Google Sheets: 日期, 類別, 項目, 金額, 類型, 定存總額, 零用總額
                    wks.append_row([
                        str(datetime.now().date()), 
                        f"{CATEGORIES[current_cat_name]} {current_cat_name}", 
                        item_note if item_note else current_cat_name, 
                        final_amt, "支出", fixed_val, new_pocket
                    ])
                    st.session_state.temp_amt = 0.0
                    st.balloons()
                    st.rerun()

        # --- Tab 2: 統計 ---
        with tabs[1]:
            if not df.empty:
                df_exp_plot = df[df['類型'] == '支出'].copy()
                if not df_exp_plot.empty:
                    df_exp_plot['金額'] = pd.to_numeric(df_exp_plot['金額'])
                    fig = px.pie(df_exp_plot, values='金額', names='類別', hole=0.5)
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("尚無支出數據")
            else: st.info("尚無數據")

        # --- Tab 3: 明細與刪除 ---
        with tabs[2]:
            if not df.empty:
                for i in range(len(df)-1, -1, -1):
                    row = df.iloc[i]
                    c_a, c_b, c_c = st.columns([2, 2, 1])
                    with c_a:
                        st.write(f"**{row['日期']}**")
                        st.write(f"{row['類別']} | {row['項目']}")
                    with c_b:
                        color = "red" if row['類型'] == "支出" else "green"
                        st.markdown(f"<h4 style='color:{color}; text-align:right;'>${row['金額']}</h4>", unsafe_allow_html=True)
                    with c_c:
                        if st.button("🗑️", key=f"del_{i}"):
                            wks.delete_rows(i + 2)
                            st.rerun()
                    st.divider()
            else: st.info("尚無紀錄")

        # --- Tab 4: 薪水與校正 ---
        with tabs[3]:
            st.markdown("#### 💰 薪水發放")
            salary = st.number_input("薪水總額", value=30000.0)
            ratio = st.slider("存入定存 %", 0, 100, 30)
            if st.button("🚀 撥款入帳"):
                to_f = salary * (ratio / 100)
                to_p = salary - to_f
                wks.append_row([
                    str(datetime.now().date()), "💰 薪水", "薪水入帳", 
                    salary, "收入", fixed_val + to_f, pocket_val + to_p
                ])
                st.balloons()
                st.rerun()
            
            st.markdown("---")
            st.markdown("#### 🔗 資料連結")
            st.info(f"當前連線試算表：[點我打開 Google Sheets](https://docs.google.com/spreadsheets/d/{sh.id})")

    except Exception as e:
        st.error(f"❌ 發生錯誤: {e}")
