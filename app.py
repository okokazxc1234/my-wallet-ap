import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from datetime import datetime

# --- 資料處理 ---
DB_FILE = 'data_db.json'

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 確保新欄位存在
            if "favorites" not in data: data["favorites"] = ["美食", "交通", "購物"]
            return data
    return None

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state:
    st.session_state.db = load_data()

# --- CSS 樣式 (Apple 簡約風) ---
st.set_page_config(page_title="Pocket Wallet", layout="centered")
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; font-weight: 600; }
    div[data-testid="column"] { padding: 5px; }
    .cate-btn button { background-color: #E5E5EA !important; color: #000 !important; border: none !important; }
    .amt-btn button { background-color: #F2F2F7 !important; color: #007AFF !important; border: 1px solid #007AFF !important; }
    </style>
    """, unsafe_allow_html=True)

if st.session_state.db is None:
    st.title("🍎 Wallet Setup")
    init_f = st.number_input("定存總額", value=50000.0)
    init_p = st.number_input("零用金額", value=5000.0)
    if st.button("啟動小金庫"):
        st.session_state.db = {"fixed_savings": init_f, "pocket_money": init_p, "history": [], "monthly_budget": init_p, "favorites": ["美食", "交通", "購物"]}
        save_data(st.session_state.db)
        st.rerun()
else:
    db = st.session_state.db
    
    # 頂部儀表板
    st.markdown("### 帳戶總覽")
    c1, c2 = st.columns(2)
    c1.metric("🔒 定存", f"${db['fixed_savings']:,.0f}")
    c2.metric("💳 零用", f"${db['pocket_money']:,.0f}")

    tabs = st.tabs(["📝 快速記帳", "📊 統計", "📜 紀錄", "⚙️ 設定"])

    with tabs[0]:
        st.markdown("#### 1. 選擇類別")
        # 這裡會記住你的習慣，顯示最常用的類別
        cols = st.columns(4)
        selected_cat = None
        
        # 顯示常用按鈕
        for i, cat in enumerate(db['favorites'][:4]):
            if cols[i].button(cat, key=f"cat_{i}"):
                st.session_state.temp_cat = cat

        # 也可以手動選
        all_cats = ["美食", "交通", "購物", "娛樂", "醫療", "其他"]
        current_cat = st.selectbox("或從清單選擇", all_cats, index=all_cats.index(st.session_state.get('temp_cat', '美食')))

        st.markdown("#### 2. 輸入金額")
        # 快捷金額按鈕
        ac1, ac2, ac3, ac4 = st.columns(4)
        if 'temp_amt' not in st.session_state: st.session_state.temp_amt = 0.0
        
        if ac1.button("+50"): st.session_state.temp_amt += 50
        if ac2.button("+100"): st.session_state.temp_amt += 100
        if ac3.button("+500"): st.session_state.temp_amt += 500
        if ac4.button("重置"): st.session_state.temp_amt = 0.0

        final_amt = st.number_input("最後確認金額", value=st.session_state.temp_amt, step=10.0)
        item_name = st.text_input("備註（選填）", placeholder="例如：午餐、手搖飲...")

        if st.button("💰 確認支出", type="primary"):
            if final_amt > 0 and db['pocket_money'] >= final_amt:
                db['pocket_money'] -= final_amt
                # 紀錄到歷史
                new_rec = {"日期": str(datetime.now().date()), "類別": current_cat, "項目": item_name if item_name else current_cat, "金額": final_amt}
                db['history'].append(new_rec)
                
                # 學習習慣：統計最常出現的類別
                df_temp = pd.DataFrame(db['history'])
                if '類別' in df_temp.columns:
                    top_cats = df_temp['類別'].value_counts().index.tolist()
                    db['favorites'] = top_cats + [c for c in all_cats if c not in top_cats]
                
                save_data(db)
                st.session_state.temp_amt = 0.0 # 清空暫存金額
                st.success(f"已記錄！零用錢剩餘 ${db['pocket_money']}")
                st.rerun()
            else:
                st.error("金額錯誤或餘額不足")

    # --- 後續 Tab 保持原樣但加入優化 ---
    with tabs[1]:
        if db['history']:
            df = pd.DataFrame(db['history'])
            df["金額"] = pd.to_numeric(df["金額"])
            fig = px.pie(df, values='金額', names='類別', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("尚無數據")

    with tabs[2]:
        if db['history']:
            st.dataframe(pd.DataFrame(db['history']).iloc[::-1], use_container_width=True, hide_index=True)

    with tabs[3]:
        st.markdown("#### 帳戶校正")
        new_f = st.number_input("校正定存", value=db['fixed_savings'])
        new_p = st.number_input("校正零用", value=db['pocket_money'])
        if st.button("保存設定"):
            db['fixed_savings'], db['pocket_money'] = new_f, new_p
            save_data(db)
            st.rerun()
