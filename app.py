import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. 連線設定 ---
st.set_page_config(page_title="我的永久小金庫", layout="centered")
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_data():
    try:
        # 從 Secrets 讀取金鑰
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # 務必確保你的 Google 試算表名稱叫 my_wallet_db
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        records = wks.get_all_records()
        return wks, records
    except Exception as e:
        st.error(f"連線失敗，請檢查 Secrets 或試算表名稱：{e}")
        return None, None

# 定義分類圖示
CATEGORIES = {
    "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", 
    "點心": "🍰", "酒類": "🍺", "交通": "🚗", "購物": "🛍️", 
    "娛樂": "🎮", "日用品": "🧻", "房租": "🏠", "醫療": "🏥", 
    "社交": "👥", "禮物": "🎁", "數位": "💻", "其他": "✨"
}

wks, records = get_data()

if wks is not None:
    df = pd.DataFrame(records)
    
    # 讀取餘額 (若試算表沒資料則給初始值)
    if df.empty:
        fixed, pocket = 50000.0, 5000.0
    else:
        # 確保取到的是最後一行的數字
        try:
            fixed = float(df.iloc[-1]['定存總額'])
            pocket = float(df.iloc[-1]['零用總額'])
        except:
            fixed, pocket = 50000.0, 5000.0

    st.markdown(f"### 🔒 定存: ${fixed:,.0f} | 💳 零用: ${pocket:,.0f}")
    
    tab1, tab2, tab3 = st.tabs(["📝 快速記帳", "📜 歷史明細", "💰 薪水發放"])

    with tab1:
        st.markdown("#### 新增支出")
        cat = st.selectbox("選擇類別", list(CATEGORIES.keys()))
        amt = st.number_input("輸入金額", min_value=0.0, step=10.0)
        note = st.text_input("備註 (可不填)")
        
        if st.button("✅ 確認存檔", type="primary"):
            if amt > 0:
                new_pocket = pocket - amt
                # 寫入 Google Sheets (順序要對)
                wks.append_row([
                    str(datetime.now().date()), 
                    f"{CATEGORIES[cat]} {cat}", 
                    note if note else cat, 
                    amt, "支出", fixed, new_pocket
                ])
                st.success("同步至 Google 成功！")
                st.rerun()

    with tab2:
        st.markdown("#### 歷史紀錄")
        if not df.empty:
            # 倒序顯示，最新在上面
            display_df = df[['日期', '類別', '項目', '金額', '類型']].iloc[::-1]
            st.dataframe(display_df, use_container_width=True)
            
            # 簡單圓餅圖
            df_exp = df[df['類型'] == '支出'].copy()
            if not df_exp.empty:
                df_exp['金額'] = pd.to_numeric(df_exp['金額'])
                fig = px.pie(df_exp, values='金額', names='類別', hole=0.4)
                st.plotly_chart(fig)
        else:
            st.info("目前尚無資料，請先記帳。")

    with tab3:
        st.markdown("#### 💰 領薪水囉")
        salary = st.number_input("薪水總額", value=30000.0)
        ratio = st.slider("存入定存的比例 %", 0, 100, 30)
        
        if st.button("🚀 撥款"):
            to_f = salary * (ratio / 100)
            to_p = salary - to_f
            wks.append_row([
                str(datetime.now().date()), "💰 薪水", "薪水入帳", 
                salary, "收入", fixed + to_f, pocket + to_p
            ])
            st.balloons()
            st.rerun()
