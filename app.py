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
            return json.load(f)
    return None

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state:
    st.session_state.db = load_data()

# --- Apple 風格 CSS 注入 ---
st.set_page_config(page_title="Pocket Wallet", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'SF Pro Display', sans-serif; background-color: #F2F2F7; }
    
    /* 卡片設計 */
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 18px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    
    /* 進度條美化 */
    .stProgress > div > div > div > div { background-color: #34C759; }

    /* 按鈕 */
    .stButton>button {
        border-radius: 12px;
        background-color: #007AFF;
        color: white;
        border: none;
        width: 100%;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 介面邏輯 ---
if st.session_state.db is None:
    st.title("🍎 Wallet")
    st.subheader("設定您的起始資產")
    c1, c2 = st.columns(2)
    init_f = c1.number_input("定存總額", value=50000.0)
    init_p = c2.number_input("零用金額", value=5000.0)
    if st.button("啟動小金庫"):
        st.session_state.db = {"fixed_savings": init_f, "pocket_money": init_p, "history": [], "monthly_budget": init_p}
        save_data(st.session_state.db)
        st.rerun()
else:
    db = st.session_state.db
    
    # 頂部狀態列
    st.markdown("### 我的帳戶")
    col1, col2 = st.columns(2)
    col1.metric("🔒 定存", f"${db['fixed_savings']:,.0f}")
    col2.metric("💳 零用", f"${db['pocket_money']:,.0f}")

    # 預算進度條
    if "monthly_budget" not in db: db["monthly_budget"] = 5000.0 # 舊版相容
    progress = max(0.0, min(1.0, db['pocket_money'] / db['monthly_budget']))
    st.write(f"💸 本月餘額可用率：{progress:.0%}")
    st.progress(progress)

    st.write("")
    tabs = st.tabs(["📝 記帳", "📊 分析", "📜 歷史", "⚙️ 設定"])

    # --- Tab 1: 記帳 ---
    with tabs[0]:
        st.markdown("#### 新增支出")
        date = st.date_input("日期", datetime.now())
        cat = st.selectbox("類別", ["美食", "交通", "購物", "娛樂", "醫療", "其他"])
        item = st.text_input("項目名稱", placeholder="e.g. 晚餐")
        amount = st.number_input("金額", min_value=0.0, step=10.0)
        
        if st.button("確認儲存"):
            if item and db['pocket_money'] >= amount:
                db['pocket_money'] -= amount
                db['history'].append({
                    "日期": str(date), "類別": cat, "項目": item, "金額": amount
                })
                save_data(db)
                st.toast("已成功儲存！", icon='✅')
                st.rerun()
            else:
                st.error("資訊不足或餘額不夠！")

    # --- Tab 2: 分析 (新功能！) ---
    with tabs[1]:
        st.markdown("#### 支出結構分析")
        if db['history']:
            df = pd.DataFrame(db['history'])
            # 僅統計支出
            df_pie = df.groupby("類別")["金額"].sum().reset_index()
            fig = px.pie(df_pie, values='金額', names='類別', 
                         hole=0.4, # 甜甜圈圖
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            # 列出最高支出
            max_cat = df_pie.loc[df_pie['金額'].idxmax()]
            st.info(f"💡 本月花費最多在：**{max_cat['類別']}** (${max_cat['金額']:,.0f})")
        else:
            st.info("尚無資料可供分析")

    # --- Tab 3: 歷史 ---
    with tabs[2]:
        st.markdown("#### 交易清單")
        if db['history']:
            df = pd.DataFrame(db['history']).iloc[::-1]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.write("目前沒有紀錄")

    # --- Tab 4: 設定 ---
    with tabs[3]:
        st.markdown("#### 帳戶管理")
        db['monthly_budget'] = st.number_input("設定每月預算上限", value=db.get('monthly_budget', 5000.0))
        st.write("---")
        new_f = st.number_input("校正定存金額", value=db['fixed_savings'])
        new_p = st.number_input("校正零用金額", value=db['pocket_money'])
        if st.button("更新數據"):
            db['fixed_savings'], db['pocket_money'] = new_f, new_p
            save_data(db)
            st.rerun()
        
        if st.button("🚨 清空所有並重置"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.session_state.db = None
            st.rerun()