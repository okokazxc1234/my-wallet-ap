import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from datetime import datetime

# --- 資料處理 ---
DB_FILE = 'data_db.json'

CATEGORIES = {
    "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", 
    "點心": "🍰", "酒類": "🍺", "交通": "🚗", "購物": "🛍️", 
    "娛樂": "🎮", "日用品": "🧻", "房租": "🏠", "醫療": "🏥", 
    "社交": "👥", "禮物": "🎁", "數位": "💻", "其他": "✨"
}

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "favorites" not in data: data["favorites"] = list(CATEGORIES.keys())[:4]
            return data
    return None

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state:
    st.session_state.db = load_data()

# --- CSS 樣式 ---
st.set_page_config(page_title="Wallet Pro", layout="centered")
st.markdown("""
    <style>
    .stButton>button { border-radius: 15px; height: 3em; }
    .delete-btn button { background-color: #FF3B30 !important; color: white !important; height: 2em !important; }
    </style>
    """, unsafe_allow_html=True)

if st.session_state.db is None:
    st.title("🍎 Wallet Setup")
    init_f = st.number_input("定存總額", value=50000.0)
    init_p = st.number_input("零用金額", value=5000.0)
    if st.button("啟動小金庫"):
        st.session_state.db = {"fixed_savings": init_f, "pocket_money": init_p, "history": [], "favorites": ["午餐", "交通", "飲品", "日用品"]}
        save_data(st.session_state.db)
        st.rerun()
else:
    db = st.session_state.db
    
    # 頂部儀表板
    st.markdown("### 帳戶總覽")
    c1, c2 = st.columns(2)
    c1.metric("🔒 定存金庫", f"${db['fixed_savings']:,.0f}")
    c2.metric("💳 零用預算", f"${db['pocket_money']:,.0f}")

    tabs = st.tabs(["📝 快速記帳", "📊 統計分析", "📜 歷史明細", "⚙️ 管理與薪水"])

    # --- Tab 1: 記帳 (保持原樣) ---
    with tabs[0]:
        st.markdown("#### 1. 常用類別")
        fav_cols = st.columns(4)
        for i, cat in enumerate(db['favorites'][:4]):
            icon = CATEGORIES.get(cat, "✨")
            if fav_cols[i].button(f"{icon}\n{cat}", key=f"fav_{cat}"):
                st.session_state.temp_cat = cat

        st.markdown("---")
        all_options = [f"{v} {k}" for k, v in CATEGORIES.items()]
        default_idx = 0
        if 'temp_cat' in st.session_state:
            try: default_idx = list(CATEGORIES.keys()).index(st.session_state.temp_cat)
            except: pass
        
        selected_full = st.selectbox("選擇完整類別", all_options, index=default_idx)
        current_cat = selected_full.split(" ")[1]

        st.markdown("#### 2. 輸入金額")
        ac1, ac2, ac3, ac4 = st.columns(4)
        if 'temp_amt' not in st.session_state: st.session_state.temp_amt = 0.0
        if ac1.button("+50"): st.session_state.temp_amt += 50
        if ac2.button("+100"): st.session_state.temp_amt += 100
        if ac3.button("+500"): st.session_state.temp_amt += 500
        if ac4.button("重置"): st.session_state.temp_amt = 0.0

        final_amt = st.number_input("金額確認", value=st.session_state.temp_amt, step=10.0)
        item_note = st.text_input("備註 (選填)", placeholder="例如：巷口乾麵...")

        if st.button("✅ 確認紀錄支出", type="primary"):
            if final_amt > 0 and db['pocket_money'] >= final_amt:
                db['pocket_money'] -= final_amt
                new_rec = {
                    "ID": datetime.now().strftime("%Y%m%d%H%M%S"), # 新增 ID 方便刪除
                    "日期": str(datetime.now().date()), 
                    "類別": f"{CATEGORIES[current_cat]} {current_cat}", 
                    "項目": item_note if item_note else current_cat, 
                    "金額": final_amt,
                    "類型": "支出"
                }
                db['history'].append(new_rec)
                save_data(db)
                st.session_state.temp_amt = 0.0
                st.rerun()

    # --- Tab 2: 統計 ---
    with tabs[1]:
        if db['history']:
            df = pd.DataFrame(db['history'])
            df_exp = df[df["類型"] == "支出"]
            if not df_exp.empty:
                fig = px.pie(df_exp, values='金額', names='類別', hole=0.5)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("尚無支出數據")

    # --- Tab 3: 歷史明細 (新增刪除功能！) ---
    with tabs[2]:
        st.markdown("#### 交易明細 (由新到舊)")
        if db['history']:
            # 倒序顯示，最新在上面
            for i in range(len(db['history'])-1, -1, -1):
                item = db['history'][i]
                col_a, col_b, col_c = st.columns([2, 2, 1])
                
                with col_a:
                    st.write(f"**{item['日期']}**")
                    st.write(f"{item['類別']} | {item['項目']}")
                
                with col_b:
                    color = "red" if item.get("類型") == "支出" else "green"
                    st.markdown(f"<h4 style='color:{color}; text-align:right;'>${item['金額']}</h4>", unsafe_allow_html=True)
                
                with col_c:
                    # 刪除按鈕
                    if st.button("🗑️", key=f"del_{i}"):
                        # 退還金額邏輯
                        amt = float(item['金額'])
                        if item.get("類型") == "支出":
                            db['pocket_money'] += amt
                        else: # 薪水或收入
                            # 這裡是簡易邏輯，實際可能更複雜，我們先設定薪水刪除會扣回零用錢
                            db['pocket_money'] -= amt 
                        
                        db['history'].pop(i)
                        save_data(db)
                        st.toast("已刪除紀錄並退還金額")
                        st.rerun()
                st.divider()
        else:
            st.info("尚無紀錄")

    # --- Tab 4: 設定與薪水 ---
    with tabs[3]:
        st.markdown("#### 💰 薪水發放")
        salary_amt = st.number_input("薪水總額", value=30000.0)
        save_ratio = st.slider("存入定存比例 (%)", 0, 100, 30)
        
        if st.button("🚀 撥款"):
            to_fixed = salary_amt * (save_ratio / 100)
            to_pocket = salary_amt - to_fixed
            db['fixed_savings'] += to_fixed
            db['pocket_money'] += to_pocket
            db['history'].append({
                "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                "日期": str(datetime.now().date()), 
                "類別": "💰 薪水", "項目": "薪水入帳", "金額": salary_amt, "類型": "收入"
            })
            save_data(db)
            st.balloons()
            st.rerun()

        st.markdown("---")
        # 帳戶校正
        st.markdown("#### 帳戶校正")
        db['fixed_savings'] = st.number_input("修正定存", value=db['fixed_savings'])
        db['pocket_money'] = st.number_input("修正零用", value=db['pocket_money'])
        if st.button("儲存校正"):
            save_data(db)
            st.rerun()    <style>
    .stButton>button { border-radius: 15px; height: 3em; font-size: 16px; }
    .category-card { text-align: center; padding: 10px; border-radius: 10px; background: white; margin: 5px; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #1C1C1E; }
    </style>
    """, unsafe_allow_html=True)

if st.session_state.db is None:
    st.title("🍎 Wallet Setup")
    init_f = st.number_input("定存總額", value=50000.0)
    init_p = st.number_input("零用金額", value=5000.0)
    if st.button("啟動小金庫"):
        st.session_state.db = {"fixed_savings": init_f, "pocket_money": init_p, "history": [], "favorites": ["午餐", "交通", "飲品", "日用品"]}
        save_data(st.session_state.db)
        st.rerun()
else:
    db = st.session_state.db
    
    # 頂部儀表板
    st.markdown("### 帳戶總覽")
    c1, c2 = st.columns(2)
    c1.metric("🔒 定存金庫", f"${db['fixed_savings']:,.0f}")
    c2.metric("💳 零用預算", f"${db['pocket_money']:,.0f}")

    tabs = st.tabs(["📝 快速記帳", "📊 統計分析", "📜 歷史明細", "⚙️ 管理與薪水"])

    with tabs[0]:
        st.markdown("#### 1. 常用類別")
        # 顯示前四個最常用的類別按鈕
        fav_cols = st.columns(4)
        for i, cat in enumerate(db['favorites'][:4]):
            icon = CATEGORIES.get(cat, "✨")
            if fav_cols[i].button(f"{icon}\n{cat}", key=f"fav_{cat}"):
                st.session_state.temp_cat = cat

        st.markdown("---")
        # 手動選擇完整清單
        all_options = [f"{v} {k}" for k, v in CATEGORIES.items()]
        default_idx = 0
        if 'temp_cat' in st.session_state:
            default_idx = list(CATEGORIES.keys()).index(st.session_state.temp_cat)
        
        selected_full = st.selectbox("選擇完整類別", all_options, index=default_idx)
        current_cat = selected_full.split(" ")[1] # 取得中文名稱

        st.markdown("#### 2. 輸入金額")
        ac1, ac2, ac3, ac4 = st.columns(4)
        if 'temp_amt' not in st.session_state: st.session_state.temp_amt = 0.0
        if ac1.button("+50"): st.session_state.temp_amt += 50
        if ac2.button("+100"): st.session_state.temp_amt += 100
        if ac3.button("+500"): st.session_state.temp_amt += 500
        if ac4.button("重設"): st.session_state.temp_amt = 0.0

        final_amt = st.number_input("金額確認", value=st.session_state.temp_amt, step=10.0)
        item_note = st.text_input("備註 (選填)", placeholder="例如：巷口乾麵...")

        if st.button("✅ 確認紀錄支出", type="primary"):
            if final_amt > 0 and db['pocket_money'] >= final_amt:
                db['pocket_money'] -= final_amt
                new_rec = {
                    "日期": str(datetime.now().date()), 
                    "類別": f"{CATEGORIES[current_cat]} {current_cat}", 
                    "項目": item_note if item_note else current_cat, 
                    "金額": final_amt
                }
                db['history'].append(new_rec)
                
                # 自動更新常用習慣
                df_hist = pd.DataFrame(db['history'])
                if not df_hist.empty:
                    # 移除圖示後統計
                    df_hist['pure_cat'] = df_hist['類別'].apply(lambda x: x.split(" ")[1] if " " in x else x)
                    top_list = df_hist['pure_cat'].value_counts().index.tolist()
                    db['favorites'] = top_list + [c for c in CATEGORIES.keys() if c not in top_list]
                
                save_data(db)
                st.session_state.temp_amt = 0.0
                st.toast(f"記帳成功！剩餘 ${db['pocket_money']}")
                st.rerun()
            else:
                st.error("金額不足或輸入錯誤")

    with tabs[1]:
        st.markdown("#### 消費分佈")
        if db['history']:
            df = pd.DataFrame(db['history'])
            df["金額"] = pd.to_numeric(df["金額"])
            fig = px.pie(df, values='金額', names='類別', hole=0.5, 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(showlegend=True, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("尚無數據")

    with tabs[2]:
        if db['history']:
            st.dataframe(pd.DataFrame(db['history']).iloc[::-1], use_container_width=True, hide_index=True)

    with tabs[3]:
        st.markdown("#### 💰 薪水發放")
        salary_amt = st.number_input("本月實領薪水", value=30000.0, step=1000.0)
        save_ratio = st.slider("存入定存比例 (%)", 0, 100, 30)
        
        if st.button("🚀 發放薪水並存檔"):
            to_fixed = salary_amt * (save_ratio / 100)
            to_pocket = salary_amt - to_fixed
            db['fixed_savings'] += to_fixed
            db['pocket_money'] += to_pocket
            
            db['history'].append({
                "日期": str(datetime.now().date()), 
                "類別": "💰 薪水", "項目": "薪水入帳", "金額": f"+{salary_amt}"
            })
            save_data(db)
            st.balloons()
            st.success(f"已撥入：定存 ${to_fixed:,.0f}，零用錢 ${to_pocket:,.0f}")
            st.rerun()

        st.markdown("---")
        st.markdown("#### 系統重置")
        if st.button("🚨 清空所有資料"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.session_state.db = None
            st.rerun()
