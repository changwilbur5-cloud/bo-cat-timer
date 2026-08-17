import os
import re
import time
import random
import json
import datetime
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import streamlit as st

# ==================== 工具函式 ====================
def round_half_up(val, decimals=2):
    """標準四捨五入"""
    try:
        d = Decimal(str(val))
        fmt = '0.' + '0' * decimals if decimals > 0 else '0'
        return float(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))
    except Exception:
        return round(float(val), decimals)

HISTORY_FILE = "history_records.json"
WALLET_FILE = "bo_coins.json"

def load_wallet():
    if os.path.exists(WALLET_FILE):
        try:
            with open(WALLET_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("bo_coins", 0.0)
        except Exception:
            return 0.0
    return 0.0

def save_wallet(amount):
    with open(WALLET_FILE, "w", encoding="utf-8") as f:
        json.dump({"bo_coins": round_half_up(amount)}, f, ensure_ascii=False, indent=2)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(records):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def get_random_coin_amount():
    prizes = [(3.00, 0.5), (2.00, 2.5), (1.00, 7.0), (0.50, 15.0), (0.10, 25.0), (0.03, 50.0)]
    amounts = [p[0] for p in prizes]
    weights = [p[1] for p in prizes]
    return random.choices(amounts, weights=weights, k=1)[0]

# ==================== Session State 初始化 ====================
st.set_page_config(page_title="波貓計時與收銀系統", page_icon="🐱", layout="centered")

if "bo_coins" not in st.session_state:
    st.session_state.bo_coins = load_wallet()

if "history" not in st.session_state:
    st.session_state.history = load_history()

if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "accumulated_sec" not in st.session_state:
    st.session_state.accumulated_sec = 0.0
if "is_double" not in st.session_state:
    st.session_state.is_double = False
if "last_lottery_time" not in st.session_state:
    st.session_state.last_lottery_time = time.time()
if "lottery_stage" not in st.session_state:
    st.session_state.lottery_stage = 0

# ==================== 計算當前累積秒數 ====================
def get_elapsed_seconds():
    if st.session_state.timer_running and st.session_state.start_time:
        return st.session_state.accumulated_sec + (time.time() - st.session_state.start_time)
    return st.session_state.accumulated_sec

# 檢查波幣背景抽獎
def check_lottery():
    if not st.session_state.timer_running:
        st.session_state.last_lottery_time = time.time()
        return

    now = time.time()
    intervals = [300.0, 600.0, 900.0]
    needed_sec = intervals[min(st.session_state.lottery_stage, 2)]

    if now - st.session_state.last_lottery_time >= needed_sec:
        st.session_state.last_lottery_time = now
        if st.session_state.lottery_stage < 2:
            st.session_state.lottery_stage += 1
        
        won = get_random_coin_amount()
        st.session_state.bo_coins += won
        save_wallet(st.session_state.bo_coins)
        st.toast(f"🎉 計時獎勵發放！獲得 +{won:.2f} 波幣！", icon="🪙")

check_lottery()

# ==================== 頁面導航 ====================
st.title("🐾 波貓計時與收銀系統")

tab1, tab2, tab3 = st.tabs(["⏱️ 計時器模式", "✎ 算式與紀錄", "💵 收銀結帳"])

# -------------------- TAB 1: 計時器模式 --------------------
with tab1:
    st.subheader("▶ 計時與即時計費")
    
    elapsed = get_elapsed_seconds()
    hrs = int(elapsed // 3600)
    mins = int((elapsed % 3600) // 60)
    secs = int(elapsed % 60)
    time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

    multiplier = 2 if st.session_state.is_double else 1
    # 0.1 元 / 分鐘
    cost = round_half_up((Decimal(elapsed) * Decimal('0.1') / Decimal('60')) * Decimal(multiplier))

    st.metric(label="累積時間", value=time_str)
    st.metric(label="已使用金額 (0.1元/分)", value=f"{cost:.2f} 元", delta="2x 雙倍計費中" if st.session_state.is_double else None)

    st.session_state.is_double = st.checkbox("啟用雙倍計費 (2x)", value=st.session_state.is_double)

    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not st.session_state.timer_running:
            if st.button("▶ 開始計時", type="primary", use_container_width=True):
                st.session_state.timer_running = True
                st.session_state.start_time = time.time()
                st.rerun()
        else:
            if st.button("❚❚ 暫停計時", use_container_width=True):
                st.session_state.accumulated_sec = get_elapsed_seconds()
                st.session_state.timer_running = False
                st.session_state.start_time = None
                st.rerun()

    with col2:
        if st.button("◼ 歸零", use_container_width=True):
            st.session_state.timer_running = False
            st.session_state.start_time = None
            st.session_state.accumulated_sec = 0.0
            st.session_state.lottery_stage = 0
            st.rerun()

    with col3:
        if st.button("★ 存檔紀錄", type="secondary", use_container_width=True):
            if elapsed > 0:
                dt_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                minutes_used = round_half_up(elapsed / 60.0)
                record = {
                    "time": dt_now,
                    "minutes": minutes_used,
                    "cost": cost,
                    "note": "計時器存檔" + (" (雙倍)" if st.session_state.is_double else "")
                }
                st.session_state.history.append(record)
                save_history(st.session_state.history)
                st.success(f"已成功存檔：{minutes_used:.2f} 分鐘 / {cost:.2f} 元！")
            else:
                st.warning("時間為 0，無需存檔！")

# -------------------- TAB 2: 算式、手動寫入與紀錄 --------------------
with tab2:
    st.subheader("✎ 算式計算與歷史紀錄")
    st.info(f"🪙 目前波幣資產：**{st.session_state.bo_coins:.2f}** 波幣 (1波幣 = 1分鐘 = 可折抵 {st.session_state.bo_coins*0.1:.2f} 元)")

    calc_input = st.text_input("輸入算式 (例如 30+15*2)，或輸入指令 (addcoin 10 / resetcoin):", placeholder="15*2")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        calc_mode = st.radio("計算模式", ["分鐘 ➔ 元", "元 ➔ 分鐘"], horizontal=True)
    with col_c2:
        if st.button("算式轉換 / 執行指令", use_container_width=True):
            inp = calc_input.strip()
            if inp.startswith("addcoin"):
                try:
                    amt = float(inp.split()[1])
                    st.session_state.bo_coins += amt
                    save_wallet(st.session_state.bo_coins)
                    st.success(f"已手動增加 {amt} 波幣！")
                except Exception:
                    st.error("語法錯誤，請輸入 addcoin 10")
            elif inp == "resetcoin":
                st.session_state.bo_coins = 0.0
                save_wallet(0.0)
                st.success("波幣已歸零！")
            else:
                try:
                    val = float(eval(inp))
                    if calc_mode == "分鐘 ➔ 元":
                        res_cost = round_half_up(val * 0.1)
                        st.success(f"計算結果：{val} 分鐘 = **{res_cost:.2f} 元**")
                    else:
                        res_mins = round_half_up(val / 0.1)
                        st.success(f"計算結果：{val} 元 = **{res_mins:.2f} 分鐘**")
                except Exception:
                    st.error("算式格式錯誤！")

    st.markdown("---")
    
    st.write("##### ✍️ 手動寫入紀錄")
    m_col1, m_col2, m_col3 = st.columns([2, 2, 1])
    with m_col1:
        m_mins = st.number_input("時間 (分鐘)", min_value=0.0, step=1.0)
    with m_col2:
        m_cost = st.number_input("金額 (元)", min_value=0.0, step=0.1, value=m_mins*0.1)
    with m_col3:
        st.write(" ")
        st.write(" ")
        if st.button("新增紀錄", use_container_width=True):
            if m_mins > 0 or m_cost > 0:
                dt_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rec = {"time": dt_now, "minutes": round_half_up(m_mins), "cost": round_half_up(m_cost), "note": "手動寫入"}
                st.session_state.history.append(rec)
                save_history(st.session_state.history)
                st.success("手動紀錄新增成功！")
                st.rerun()

    st.markdown("---")
    st.write("##### 📋 歷史紀錄與波幣資產下載")

    total_mins = sum(item.get("minutes", 0) for item in st.session_state.history)
    total_cost = sum(item.get("cost", 0) for item in st.session_state.history)
    
    st.write(f"📊 **歷史加總**：總時間 **{total_mins:.2f}** 分鐘 | 總金額 **{total_cost:.2f}** 元")

    # ==================== 下載功能區塊 (包含波幣) ====================
    # 建立包含波幣資訊的資料清單
    export_list = list(st.session_state.history)
    
    # 1. 匯出 CSV (加上波幣資訊列)
    df_export = pd.DataFrame(export_list)
    if not df_export.empty:
        df_export.columns = ["時間", "分鐘", "金額(元)", "備註"]
    
    # 建立包含資產摘要的 CSV
    summary_data = pd.DataFrame([
        {"時間": "--- 資產摘要 ---", "分鐘": "", "金額(元)": "", "備註": ""},
        {"時間": "當前波幣總額", "分鐘": f"{st.session_state.bo_coins:.2f} 幣", "金額(元)": f"{st.session_state.bo_coins*0.1:.2f} 元", "備註": "1波幣=1分鐘"},
        {"時間": "歷史總計分鐘", "分鐘": f"{total_mins:.2f} 分", "金額(元)": f"{total_cost:.2f} 元", "備註": "未折抵前總額"}
    ])
    
    df_combined = pd.concat([df_export, summary_data], ignore_index=True) if not df_export.empty else summary_data
    csv_data = df_combined.to_csv(index=False, encoding='utf-8-sig')

    # 2. 匯出 TXT 文字檔 (包含波幣資產)
    txt_content = f"=========================================\n"
    txt_content += f"   🐾 波貓系統完整報表 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
    txt_content += f"=========================================\n"
    txt_content += f"🪙 目前波幣資產：{st.session_state.bo_coins:.2f} 波幣 (可折抵 {st.session_state.bo_coins*0.1:.2f} 元)\n"
    txt_content += f"⏱️ 歷史累計總時間：{total_mins:.2f} 分鐘\n"
    txt_content += f"💰 歷史累計總金額：{total_cost:.2f} 元\n"
    txt_content += f"-----------------------------------------\n"
    txt_content += f"【歷史明細紀錄】\n"
    
    if st.session_state.history:
        for item in st.session_state.history:
            txt_content += f"[{item['time']}] {item['minutes']}分鐘 | {item['cost']}元 | {item.get('note', '')}\n"
    else:
        txt_content += " (無歷史消費紀錄)\n"
    txt_content += f"=========================================\n"

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            label="📥 下載完整報表 (CSV 檔)",
            data=csv_data,
            file_name=f"波貓完整報表_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with dl_col2:
        st.download_button(
            label="📄 下載完整報表 (TXT 檔)",
            data=txt_content,
            file_name=f"波貓完整報表_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.markdown("---")

    # 紀錄清單列表與個別刪除
    records_to_keep = []
    has_deleted = False

    for idx, item in enumerate(st.session_state.history):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.write(f"🕒 {item['time']}")
        c2.write(f"⏱️ {item['minutes']} 分")
        c3.write(f"💰 {item['cost']} 元")
        del_btn = c4.button("🗑️", key=f"del_{idx}")
        
        if del_btn:
            has_deleted = True
        else:
            records_to_keep.append(item)

    if has_deleted:
        st.session_state.history = records_to_keep
        save_history(st.session_state.history)
        st.rerun()

    if st.button("🗑️ 清空所有歷史紀錄", type="secondary"):
        st.session_state.history = []
        save_history([])
        st.success("紀錄已清空！")
        st.rerun()

# -------------------- TAB 3: 全螢幕/獨立收銀畫面 --------------------
with tab3:
    st.subheader("💵 收銀結帳頁面")
    
    total_checkout_cost = sum(item.get("cost", 0) for item in st.session_state.history)
    st.metric(label="應付總金額 (來自歷史紀錄)", value=f"{total_checkout_cost:.2f} 元")
    st.info(f"🪙 當前持有波幣：**{st.session_state.bo_coins:.2f}** 波幣 (1波幣 = 1分鐘 = 折抵 0.1 元)")

    pay_col1, pay_col2 = st.columns(2)
    with pay_col1:
        paid_amount = st.number_input("輸入顧客實付金額 (元):", min_value=0.0, step=10.0)
    with pay_col2:
        use_coins = st.number_input("輸入折抵波幣 (1幣 = 1分):", min_value=0.0, max_value=float(st.session_state.bo_coins), step=1.0)

    coin_discount_cost = round_half_up(use_coins * 0.1)
    final_need = max(0.0, total_checkout_cost - coin_discount_cost)
    change = paid_amount - final_need

    st.markdown("---")
    st.write(f"🏷️ **波幣折抵金額**：-{coin_discount_cost:.2f} 元")
    st.write(f"🏷️ **折抵後最終應付**：**{final_need:.2f}** 元")
    
    if change >= 0:
        st.success(f"💵 **應找零金額**：**{change:.2f}** 元")
    else:
        st.error(f"⚠️ **尚欠金額**：**{abs(change):.2f}** 元")

    if st.button("✅ 確定完成結帳（扣除波幣並清空紀錄）", type="primary", use_container_width=True):
        if use_coins <= st.session_state.bo_coins:
            st.session_state.bo_coins -= use_coins
            save_wallet(st.session_state.bo_coins)
            
            st.session_state.history = []
            save_history([])
            
            st.success("🎉 結帳完畢！波幣已扣除，歷史紀錄已自動歸零！")
            st.rerun()
        else:
            st.error("波幣不足，無法完成結帳！")
      
