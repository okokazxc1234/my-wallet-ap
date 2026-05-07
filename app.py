import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- 1. 連線設定 ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered")

# 初始化計算機 Session State
if 'calc_display' not in st.session_state:
    st.session_state.calc_display = "0"

scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
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

# --- 鍵盤邏輯函數 ---
def press_key(key):
    if key == "AC":
        st.session_state.calc_display = "0"
    elif key == "DEL":
        st.session_state.calc_display = st.session_state.calc_display[:-1] if len(st.session_state.calc_display) > 1 else "0"
    elif key == "=":
        try:
            # 使用 eval 計算結果
            result = eval(st.session_state.calc_display.replace('×', '*').replace('÷', '/'))
            st.session_state.calc_display = str(round(float(result), 2))
        except:
            st.session_state.calc_display = "Error"
    else:
        if st.session_state.calc_display in ["0", "Error"]:
            st.session_state.calc_display = str(key)
        else:
            st.session_state.calc_display += str(key)

# --- 主程式 ---
client = get_gs_client()

if client:
    try:
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        all_records = wks.get_all_records()
        df = pd.DataFrame(all_records)

        # 基礎餘額計算
        if df.empty:
            fixed_val, pocket_val = 50000.0, 5000.0
        else:
            fixed_val = float(df.iloc[-1]['定存總額'])
            pocket_val = float(df.iloc[-1]['零用總額'])

        st.markdown(f"### 🍎 帳戶總覽")
        c1, c2 = st.columns(2)
        c1.metric("🔒 定存金庫", f"${fixed_val:,.0f}")
        c2.metric("💳 零用預算", f"${pocket_val:,.0f}")

        tabs = st.tabs(["📝 快速記帳", "📊 分析", "📜 明細管理", "⚙️ 設定"])

        with tabs[0]:
            input_date = st.date_input("📅 選擇日期", datetime.now())
            
            all_options = [f"{v} {k}" for k, v in CATEGORIES.items()]
            sel_full = st.pills("🏷️ 選擇分類", all_options, selection_mode="single", default=all_options[0])
            current_cat_name = (sel_full if sel_full else all_options[0]).split(" ")[1]

            st.markdown("#### 💰 輸入金額")
            
            # --- 彈窗數字鍵盤 (Popover) ---
            with st.popover(f"🔢 點擊輸入金額: {st.session_state.calc_display}", use_container_width=True):
                st.markdown(f"### `{st.session_state.calc_display}`")
                
                # CSS 強制按鈕橫向排版
                st.markdown("""<style> div[data-testid="column"] { display: flex; justify-content: center; } </style>""", unsafe_allow_html=True)
                
                # 計算機按鈕佈局
                row1 = st.columns(4)
                if row1[0].button("7"): press_key("7"); st.rerun()
                if row1[1].button("8"): press_key("8"); st.rerun()
                if row1[2].button("9"): press_key("9"); st.rerun()
                if row1[3].button("÷"): press_key("/"); st.rerun()

                row2 = st.columns(4)
                if row2[0].button("4"): press_key("4"); st.rerun()
                if row2[1].button("5"): press_key("5"); st.rerun()
                if row2[2].button("6"): press_key("6"); st.rerun()
                if row2[3].button("×"): press_key("*"); st.rerun()

                row3 = st.columns(4)
                if row3[0].button("1"): press_key("1"); st.rerun()
                if row3[1].button("2"): press_key("2"); st.rerun()
                if row3[2].button("3"): press_key("3"); st.rerun()
                if row3[3].button("-"): press_key("-"); st.rerun()

                row4 = st.columns(4)
                if row4[0].button("0"): press_key("0"); st.rerun()
                if row4[1].button("."): press_key("."); st.rerun()
                if row4[2].button("AC", type="secondary"): press_key("AC"); st.rerun()
                if row4[3].button("+"): press_key("+"); st.rerun()

                row5 = st.columns(2)
                if row5[0].button("⌫ 退格", use_container_width=True): press_key("DEL"); st.rerun()
                if row5[1].button("＝ 計算", type="primary", use_container_width=True): press_key("="); st.rerun()

            item_note = st.text_input("📝 備註 (選填)")

            if st.button("🚀 確認送出並存入後台", type="primary", use_container_width=True):
                try:
                    # 先計算最後結果
                    final_amt = float(eval(st.session_state.calc_display))
                    if final_amt > 0:
                        wks.append_row([
                            str(input_date), 
                            f"{CATEGORIES[current_cat_name]} {current_cat_name}", 
                            item_note if item_note else current_cat_name, 
                            final_amt, 
                            "支出", 
                            fixed_val, 
                            pocket_val - final_amt
                        ])
                        st.session_state.calc_display = "0" # 歸零
                        st.success(f"成功記帳: ${final_amt}")
                        st.rerun()
                    else:
                        st.warning("金額必須大於 0")
                except:
                    st.error("金額格式錯誤，請檢查計算式")

        # --- 其他 Tab 保持原樣 ---
        with tabs[1]:
            if not df.empty:
                df_exp_plot = df[df['類型'] == '支出'].copy()
                if not df_exp_plot.empty:
                    df_exp_plot['金額'] = pd.to_numeric(df_exp_plot['金額'])
                    fig = px.pie(df_exp_plot, values='金額', names='類別', hole=0.5)
                    st.plotly_chart(fig, use_container_width=True)
        
        with tabs[2]:
            if not df.empty:
                st.write("顯示最近 10 筆明細：")
                st.dataframe(df.tail(10).iloc[::-1], use_container_width=True)

        with tabs[3]:
            st.info("設定功能已在後端就緒")

    except Exception as e:
        st.error(f"❌ 系統錯誤: {e}")
