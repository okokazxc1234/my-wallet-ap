import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. 頁面與終極 CSS ---
st.set_page_config(page_title="🍎 永久小金庫 Pro", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 隱藏不想看到的 Streamlit 元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 鍵盤網格佈局 */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-top: 5px;
    }
    .grid-item {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 12px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: bold;
        color: #333;
        cursor: pointer;
        user-select: none;
        -webkit-tap-highlight-color: transparent;
    }
    .grid-item:active { background-color: #e2e6ea; transform: scale(0.95); }
    .grid-item.special { background-color: #e9ecef; color: #007bff; }
    
    /* 螢幕樣式 */
    #display {
        background-color: #1e1e23;
        color: #00ff41;
        padding: 15px;
        border-radius: 15px;
        text-align: right;
        font-family: 'monospace';
        font-size: 42px;
        font-weight: bold;
        margin-bottom: 10px;
        min-height: 70px;
        border: 2px solid #3d3d4d;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
    }

    /* 餘額卡片 */
    .balance-container { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 15px; }
    .balance-card { background: #fff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 12px; width: 48%; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .balance-label { font-size: 14px; color: #666; margin-bottom: 4px;}
    .balance-value { font-size: 22px; font-weight: bold; color: #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Google Sheets 連線 ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gs_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except: return None

client = get_gs_client()
fixed_val, pocket_val = 0.0, 0.0
records = []

if client:
    try:
        sh = client.open("my_wallet_db")
        wks = sh.get_worksheet(0)
        records = wks.get_all_records()
        if records:
            last_row = records[-1]
            fixed_val = float(last_row.get('定存總額', 0))
            pocket_val = float(last_row.get('零用總額', 0))

        st.markdown(f"### 🍎 目前資產狀態")
        st.markdown(f"""
            <div class="balance-container">
                <div class="balance-card"><div class="balance-label">🔒 定存</div><div class="balance-value">${fixed_val:,.0f}</div></div>
                <div class="balance-card"><div class="balance-label">💳 零用</div><div class="balance-value">${pocket_val:,.0f}</div></div>
            </div>
        """, unsafe_allow_html=True)

        tabs = st.tabs(["📝 快速記帳", "📜 明細管理", "⚙️ 設定"])

        # --- Tab 1: 記帳 ---
        with tabs[0]:
            input_date = st.date_input("日期", datetime.now())
            CATEGORIES = {
                "早餐": "🥪", "午餐": "🍱", "晚餐": "🍽️", "飲品": "☕", "點心": "🍰", 
                "酒類": "🍺", "交通": "🚗", "購物": "🛍️", "娛樂": "🎮", "日用品": "🧻", 
                "房租": "🏠", "醫療": "🏥", "社交": "👥", "禮物": "🎁", "數位": "💻", "其他": "✨"
            }
            all_opts = [f"{v} {k}" for k, v in CATEGORIES.items()]
            sel_full = st.pills("類別", all_opts, selection_mode="single", default=all_opts[0], label_visibility="collapsed")
            current_cat = (sel_full if sel_full else all_opts[0]).split(" ")[1]

            # 螢幕與流暢鍵盤
            st.markdown('<div id="display">0</div>', unsafe_allow_html=True)
            
            calc_html = """
            <div class="grid-container">
                <div class="grid-item" onclick="press('7')">7</div><div class="grid-item" onclick="press('8')">8</div><div class="grid-item" onclick="press('9')">9</div><div class="grid-item special" onclick="press('DEL')">⌫</div>
                <div class="grid-item" onclick="press('4')">4</div><div class="grid-item" onclick="press('5')">5</div><div class="grid-item" onclick="press('6')">6</div><div class="grid-item special" onclick="press('*')">×</div>
                <div class="grid-item" onclick="press('1')">1</div><div class="grid-item" onclick="press('2')">2</div><div class="grid-item" onclick="press('3')">3</div><div class="grid-item special" onclick="press('-')">-</div>
                <div class="grid-item" onclick="press('0')">0</div><div class="grid-item" onclick="press('.')">.</div><div class="grid-item special" onclick="press('AC')">AC</div><div class="grid-item special" onclick="press('+')">+</div>
            </div>

            <script>
            function press(key) {
                const display = window.parent.document.getElementById('display');
                const hiddenInput = window.parent.document.querySelector('input[aria-label="amt_input"]');
                let current = display.innerText;

                if (key === 'AC') { current = '0'; }
                else if (key === 'DEL') { current = current.length > 1 ? current.slice(0, -1) : '0'; }
                else {
                    if (current === '0' && key !== '.') { current = key; }
                    else { current += key; }
                }
                display.innerText = current;
                hiddenInput.value = current;
                hiddenInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
            </script>
            """
            components.html(calc_html, height=300)

            # 隱藏輸入框接收 JS 數據
            final_amount_str = st.text_input("amt_input", value="0", label_visibility="collapsed")
            note = st.text_input("備註 (選填)")
            
            if st.button("🚀 確認存入金庫", type="primary", use_container_width=True):
                try:
                    # eval 處理連算，如 100+50
                    amt = float(eval(final_amount_str))
                    if amt > 0:
                        wks.append_row([str(input_date), f"{CATEGORIES[current_cat]} {current_cat}", note if note else current_cat, amt, "支出", fixed_val, pocket_val - amt])
                        st.balloons()
                        st.rerun()
                except:
                    st.error("計算出錯")

        # --- Tab 2: 明細 ---
        with tabs[1]:
            if records:
                df = pd.DataFrame(records)
                for i in range(len(df)-1, -1, -1):
                    row = df.iloc[i]
                    with st.expander(f"{row['日期']} | {row['類別']} | ${row['金額']}"):
                        st.write(f"項目: {row['項目']}")
                        if st.button("🗑️ 刪除", key=f"del_{i}"):
                            adj = float(row['金額']) if row['類型'] == "支出" else -float(row['金額'])
                            wks.delete_rows(i + 2)
                            wks.append_row([str(datetime.now().date()), "🔄 系統", "刪除校正", 0, "校正", fixed_val, pocket_val + adj])
                            st.rerun()
            else: st.info("目前尚無資料")

        # --- Tab 3: 設定 ---
        with tabs[2]:
            st.markdown("#### 💰 薪資入帳比例設定")
            s_amt = st.number_input("本月入帳金額", value=0.0)
            s_ratio = st.slider("存入定存比例 %", 0, 100, 30)
            if st.button("🚀 執行撥款", use_container_width=True):
                to_f, to_p = s_amt * (s_ratio / 100), s_amt * (1 - s_ratio / 100)
                wks.append_row([str(datetime.now().date()), "💰 收入", "薪資入帳", s_amt, "收入", fixed_val + to_f, pocket_val + to_p])
                st.rerun()
            
            st.markdown("---")
            st.markdown("#### ⚙️ 餘額強制校正")
            f_new = st.number_input("校正定存總額", value=fixed_val)
            p_new = st.number_input("校正零用預算", value=pocket_val)
            if st.button("💾 更新資料庫餘額"):
                wks.append_row([str(datetime.now().date()), "⚙️ 系統", "手動校正", 0, "校正", f_new, p_new])
                st.rerun()

    except Exception as e: st.error(f"連線錯誤: {e}")
