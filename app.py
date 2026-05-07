import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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

CATEGORIES = {"早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "交通": "🚗", "購物": "🛍️", "其他": "✨"}

wks, records = get_data()

if wks is not None:
    df = pd.DataFrame(records)
    
    # 讀取餘額邏輯：如果沒資料，顯示 0；如果有，取最後一行
    if df.empty:
        fixed, pocket = 0.0, 0.0
        st.warning("⚠️ 偵測到試算表為空，請先在「薪水/初始化」分頁設定初始金額，或手動在 Google 試算表填入資料。")
    else:
        fixed = float(df.iloc[-1].get('定存總額', 0))
        pocket = float(df.iloc[-1].get('零用總額', 0))

    st.markdown(f"### 🔒 定存: ${fixed:,.0f} | 💳 零用: ${pocket:,.0f}")
    
    tab1, tab2, tab3 = st.tabs(["📝 快速記帳", "📜 歷史明細", "⚙️ 初始化/薪水"])

    with tab1:
        cat = st.selectbox("選擇類別", list(CATEGORIES.keys()))
        amt = st.number_input("輸入金額", min_value=0.0, step=10.0)
        note = st.text_input("備註")
        if st.button("✅ 確認支出"):
            if amt > 0:
                new_pocket = pocket - amt
                wks.append_row([str(datetime.now().date()), f"{CATEGORIES[cat]} {cat}", note if note else cat, amt, "支出", fixed, new_pocket])
                st.success("同步成功！")
                st.rerun()

    with tab2:
        if not df.empty:
            # 增加刪除功能：顯示每一行並附帶刪除鈕
            for i, row in df.iloc[::-1].iterrows():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"{row['日期']} {row['類別']}")
                c2.write(f"${row['金額']} ({row['類型']})")
                if c3.button("🗑️", key=f"del_{i}"):
                    wks.delete_rows(i + 2) # +2 是因為從 1 開始且有標題列
                    st.rerun()
                st.divider()
        else:
            st.info("尚無紀錄")

    with tab3:
        st.markdown("#### 💰 初始化帳戶 / 發放薪水")
        init_f = st.number_input("設定定存金額", value=fixed)
        init_p = st.number_input("設定零用金額", value=pocket)
        if st.button("💾 儲存並更新金額"):
            wks.append_row([str(datetime.now().date()), "⚙️ 系統", "金額校正", 0, "校正", init_f, init_p])
            st.success("金額已更新！")
            st.rerun()
