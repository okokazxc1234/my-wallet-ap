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

        fixed_val = float(df.iloc[-1]['定存總額']) if not df.empty else 50000.0
        pocket_val = float(df.iloc[-1]['零用總額']) if not df.empty else 5000.0

        st.markdown(f"### 🍎 帳戶總覽")
        c1, c2 = st.columns(2)
        c1.metric("🔒 定存金庫", f"${fixed_val:,.0f}")
        c2.metric("💳 零用預算", f"${pocket_val:,.0f}")

        tabs = st.tabs(["📝 快速記帳", "📊 分析", "📜 明細管理", "⚙️ 設定"])

        # --- Tab 1: 快速記帳 (含虛擬鍵盤) ---
        with tabs[0]:
            # 初始化虛擬鍵盤數值
            if 'calc_val' not in st.session_state: st.session_state.calc_val = "0"
            
            st.markdown("#### 📅 1. 選擇日期")
            input_date = st.date_input("日期", datetime.now(), label_visibility="collapsed")
            
            st.markdown("#### 🏷️ 2. 選擇分類")
            all_options = [f"{v} {k}" for k, v in CATEGORIES.items()]
            sel_full = st.pills("類別選擇", all_options, selection_mode="single", default=all_options[0])
            current_cat_name = (sel_full if sel_full else all_options[0]).split(" ")[1]

            st.markdown("---")
            st.markdown("#### ⌨️ 3. 輸入金額")
            
            # 顯示螢幕
            st.markdown(f"""
            <div style="background-color:#262730; padding:20px; border-radius:10px; text-align:right; margin-bottom:10px;">
                <span style="color:#ffffff; font-size:40px; font-family:monospace;">{st.session_state.calc_val}</span>
            </div>
            """, unsafe_allow_html=True)

            # 虛擬鍵盤排列
            def press(key):
                if key == "AC": st.session_state.calc_val = "0"
                elif key == "DEL": st.session_state.calc_val = st.session_state.calc_val[:-1] if len(st.session_state.calc_val) > 1 else "0"
                elif key == "=":
                    try: 
                        # 避免 eval 發生錯誤
                        res = str(eval(st.session_state.calc_val.replace('x', '*').replace('÷', '/')))
                        st.session_state.calc_val = res
                    except: st.session_state.calc_val = "Error"
                else:
                    if st.session_state.calc_val == "0": st.session_state.calc_val = str(key)
                    else: st.session_state.calc_val += str(key)

            k_col1, k_col2, k_col3, k_col4 = st.columns(4)
            if k_col1.button("7", use_container_width=True): press(7)
            if k_col2.button("8", use_container_width=True): press(8)
            if k_col3.button("9", use_container_width=True): press(9)
            if k_col4.button("÷", use_container_width=True): press("/")

            if k_col1.button("4", use_container_width=True): press(4)
            if k_col2.button("5", use_container_width=True): press(5)
            if k_col3.button("6", use_container_width=True): press(6)
            if k_col4.button("x", use_container_width=True): press("*")

            if k_col1.button("1", use_container_width=True): press(1)
            if k_col2.button("2", use_container_width=True): press(2)
            if k_col3.button("3", use_container_width=True): press(3)
            if k_col4.button("-", use_container_width=True): press("-")

            if k_col1.button("0", use_container_width=True): press(0)
            if k_col2.button(".", use_container_width=True): press(".")
            if k_col3.button("AC", use_container_width=True): press("AC")
            if k_col4.button("+", use_container_width=True): press("+")

            item_note = st.text_input("備註 (選填)")

            if st.button("🚀 確認送出帳單", type="primary", use_container_width=True):
                try:
                    # 送出前先計算一次
                    final_amt = float(eval(st.session_state.calc_val.replace('x', '*').replace('÷', '/')))
                    if final_amt > 0:
                        wks.append_row([str(input_date), f"{CATEGORIES[current_cat_name]} {current_cat_name}", item_note if item_note else current_cat_name, final_amt, "支出", fixed_val, pocket_val - final_amt])
                        st.session_state.calc_val = "0"
                        st.success(f"已紀錄支出 ${final_amt}")
                        st.rerun()
                except:
                    st.error("金額計算錯誤，請檢查輸入")

        # --- Tab 3: 明細管理 (保持原功能) ---
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
                            if st.button("💾 儲存修改", key=f"sv_{i}"):
                                adj = (float(row['金額']) - na) if row['類型'] == "支出" else (na - float(row['金額']))
                                wks.update_cell(i + 2, 1, str(nd)); wks.update_cell(i + 2, 3, ni); wks.update_cell(i + 2, 4, na)
                                wks.append_row([str(datetime.now().date()), "🔄 系統", "修改校正", 0, "校正", fixed_val, pocket_val + adj])
                                st.session_state[edit_key] = False
                                st.rerun()
                            if st.button("🗑️ 刪除", key=f"dl_{i}"):
                                adj = float(row['金額']) if row['類型'] == "支出" else -float(row['金額'])
                                wks.delete_rows(i + 2)
                                wks.append_row([str(datetime.now().date()), "🔄 系統", "刪除校正", 0, "校正", fixed_val, pocket_val + adj])
                                st.rerun()

        # --- Tab 4: 設定 ---
        with tabs[3]:
            st.markdown("#### 💰 領薪水 / 獎金")
            s_amt = st.number_input("入帳金額", value=30000.0)
            s_ratio = st.slider("存入定存比例 %", 0, 100, 30)
            if st.button("🚀 確認撥款", use_container_width=True):
                to_f = s_amt * (s_ratio / 100); to_p = s_amt - to_f
                wks.append_row([str(datetime.now().date()), "💰 收入", "薪水入帳", s_amt, "收入", fixed_val + to_f, pocket_val + to_p])
                st.rerun()

    except Exception as e:
        st.error(f"❌ 錯誤: {e}")
