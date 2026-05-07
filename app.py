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

        # 讀取目前餘額
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

        tabs = st.tabs(["📝 快速記帳", "📊 分析", "📜 明細/退款", "⚙️ 設定"])

        # --- Tab 1: 記帳 ---
        with tabs[0]:
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

        # --- Tab 3: 明細與「智能刪除」 ---
        with tabs[2]:
            st.markdown("#### 📜 明細管理 (刪除會自動加回餘額)")
            if not df.empty:
                for i in range(len(df)-1, -1, -1):
                    row = df.iloc[i]
                    with st.container():
                        col_a, col_b, col_c = st.columns([3, 2, 1])
                        col_a.write(f"**{row['日期']}**\n{row['類別']} | {row['項目']}")
                        color = "red" if row['類型'] == "支出" else "green"
                        prefix = "-" if row['類型'] == "支出" else "+"
                        col_b.markdown(f"<h4 style='color:{color}; text-align:right;'>{prefix}${row['金額']}</h4>", unsafe_allow_html=True)
                        
                        if col_c.button("🗑️", key=f"del_{i}"):
                            # 1. 計算新的餘額
                            if row['類型'] == "支出":
                                # 刪除支出 -> 錢要加回來
                                new_pocket = pocket_val + float(row['金額'])
                                new_fixed = fixed_val
                                msg = f"已刪除支出，${row['金額']} 已退回零用金"
                            elif row['類型'] == "收入":
                                # 刪除收入 -> 錢要扣掉
                                # 注意：如果是薪水，要按比例扣掉定存和零用 (這邊簡化為直接扣除該筆總額)
                                new_pocket = pocket_val - float(row['金額'])
                                new_fixed = fixed_val
                                msg = f"已刪除收入，已扣除 ${row['金額']}"
                            else:
                                new_pocket, new_fixed = pocket_val, fixed_val
                                msg = "已刪除紀錄"

                            # 2. 執行刪除與校正
                            wks.delete_rows(i + 2)
                            wks.append_row([str(datetime.now().date()), "🔄 系統", "刪除校正", 0, "校正", new_fixed, new_pocket])
                            st.success(msg)
                            st.rerun()
                        st.divider()

        # --- Tab 4: 設定 ---
        with tabs[3]:
            st.markdown("#### 💰 領薪水 / 獎金")
            s_amt = st.number_input("入帳金額", value=30000.0)
            s_ratio = st.slider("存入定存比例 %", 0, 100, 30)
            if st.button("🚀 確認撥款", use_container_width=True):
                to_f = s_amt * (s_ratio / 100)
                to_p = s_amt - to_f
                wks.append_row([str(datetime.now().date()), "💰 收入", "薪水入帳", s_amt, "收入", fixed_val + to_f, pocket_val + to_p])
                st.rerun()
            
            st.markdown("---")
            st.markdown("#### ⚙️ 金額總校正")
            new_f = st.number_input("手動調整定存", value=fixed_val)
            new_p = st.number_input("手動調整零用", value=pocket_val)
            if st.button("💾 覆蓋目前金額"):
                wks.append_row([str(datetime.now().date()), "⚙️ 系統", "手動校正", 0, "校正", new_f, new_p])
                st.rerun()

    except Exception as e:
        st.error(f"❌ 錯誤: {e}")
