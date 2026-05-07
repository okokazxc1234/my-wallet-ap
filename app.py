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
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        records = wks.get_all_records()
        return wks, records
    except Exception as e:
        st.error(f"連線失敗：{e}")
        return None, None

# 定義分類圖示
CATEGORIES = {"早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "交通": "🚗", "購物": "🛍️", "其他": "✨"}

wks, records = get_data()

if wks is not None:
    df = pd.DataFrame(records)
    
    # 讀取餘額 (若空表則給初始值)
    if df.empty:
        fixed, pocket = 50000.0, 5000.0
    else:
        fixed = float(df.iloc[-1]['定存總額'])
        pocket = float(df.iloc[-1]['零用總額'])

    st.markdown(f"### 🔒 定存: ${fixed:,.0f} | 💳 零用: ${pocket:,.0f}")
    
    tab1, tab2, tab3 = st.tabs(["📝 記帳", "📜 歷史", "💰 薪水"])

    with tab1:
        cat = st.selectbox("選擇類別", list(CATEGORIES.keys()))
        amt = st.number_input("輸入金額", min_value=0.0, step=10.0)
        note = st.text_input("備註")
        if st.button("確認支出"):
            new_pocket = pocket - amt
            wks.append_row([str(datetime.now().date()), f"{CATEGORIES[cat]} {cat}", note if note else cat, amt, "支出", fixed, new_pocket])
            st.success("存入試算表成功！")
            st.rerun()

    with tab2:
        if not df.empty:
            st.dataframe(df.iloc[::-1], use_container_width=True)
        else:
            st.info("目前沒有資料")

    with tab3:
        salary = st.number_input("本月薪水", value=30000.0)
        if st.button("發放薪水"):
            wks.append_row([str(datetime.now().date()), "💰 薪水", "薪水入帳", salary, "收入", fixed, pocket + salary])
            st.balloons()
            st.rerun()
