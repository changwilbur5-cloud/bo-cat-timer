import os
import re
import time
import random
import json
import datetime
import requests
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import streamlit as st

# ==================== 設定密碼與匿名雲端庫 ====================
SECURITY_PASSWORD = "b1771016"

# 匿名雲端資料庫 API (免費免登入 JSONBin)
JSONBIN_URL = "https://api.jsonbin.io/v3/b/65d1d898dc74654018a56201" 

# ==================== 工具函式 ====================
def round_half_up(val, decimals=2):
    try:
        d = Decimal(str(val))
        fmt = '0.' + '0' * decimals if decimals > 0 else '0'
        return float(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))
    except Exception:
        try:
            return round(float(val), decimals)
        except Exception:
            return 0.0

def safe_float(val_str):
    try:
        s = str(val_str).strip()
        parts = s.split('.')
        if len(parts) > 2:
            s = f"{parts[0]}.{parts[1]}"
        return float(s)
    except Exception:
        return 0.0

# ==================== 雲端資料庫自動讀寫 ====================
def load_cloud_data():
    """從雲端載入波幣與歷史紀錄"""
    try:
        resp = requests.get(JSONBIN_URL + "/latest", headers={"X-Bin-Meta": "false"}, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("bo_coins", 0.0), data.get("history", [])
    except Exception:
        pass
    return 0.0, []

def save_cloud_data(bo_coins, history):
    """將波幣與歷史紀錄同步至雲端"""
    try:
        payload = {
            "bo_coins": round_half_up(bo_coins),
            "history": history
        }
        headers = {"Content-Type": "application/json"}
        requests.put(JSONBIN_URL, json=payload, headers=headers, timeout=3)
    except Exception:
        pass

def get_random_coin_amount():
    prizes = [(3.00, 0.5), (2.00, 2.5), (1.00, 7.0), (0.50, 15.0), (0.10, 25.0), (0.03, 50.0)]
    amounts = [p[0] for p in prizes]
    weights = [p[1] for p in prizes]
    return random.choices(amounts, weights=weights, k=1)[0]

# ==================== Session State 初始化 ====================
st.set_page_config(
    page_title="波貓計時與收銀系統", 
    page_icon="🐱", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 啟動時自動從雲端同步資料
if "data_loaded" not in st.session_state:
    cloud_coins, cloud_history = load_cloud_data()
    st.session_state.bo_coins = cloud_coins
    st.session_state.history = cloud_history
    st.session_state.data_loaded = True

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

def get_elapsed_seconds():
    if st.session_state.timer_running and st.session_state.start_time:
        return st.session_state.accumulated_sec + (time.time() - st.session_state.start_time)
    return st.session_state.accumulated_sec

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
        save_cloud_data(st.session_state.bo_coins, st.session_state.history)
        st.toast(f"🎉 計時獎勵發放！獲得 +{won:.2f} 波幣！", icon="🪙")

check_lottery()

# 全螢幕 JavaScript 元件
fullscreen_js = """
<script>
function toggleFullScreen() {
  var doc = window.parent.document;
  var docEl = doc.documentElement;

  if (!doc.fullscreenElement && !doc.mozFullScreenElement && !doc.webkitFullscreenElement && !doc.msFullscreenElement) {
    if (docEl.requestFullscreen) {
      docEl.requestFullscreen();
    } else if (docEl.msRequestFullscreen) {
      docEl.msRequestFullscreen();
    } else if (docEl.mozRequestFullScreen) {
      docEl.mozRequestFullScreen();
    } else if (docEl.webkitRequestFullscreen) {
      docEl.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
    }
  } else {
    if (doc.exitFullscreen) {
      doc.exitFullscreen();
    } else if (doc.msExitFullscreen) {
      doc.msExitFullscreen();
    } else if (doc.mozCancelFullScreen) {
      doc.mozCancelFullScreen();
    } else if (doc.webkitExitFullscreen) {
      doc.webkitExitFullscreen();
    }
  }
}
</script>
<button onclick="toggleFullScreen()" style="
    width: 100%;
    padding: 10px;
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    font-size: 16px;
    cursor: pointer;
    margin-bottom: 5px;">
    📺 切換全螢幕 / 退出全螢幕
</button>
"""

# ==================== 頁面導航 ====================
st.title("🐾 波貓計時與收銀系統")

tab1, tab2, tab3 = st.tabs(["⏱️ 計時器模式", "✎ 算式與紀錄", "💵 收銀結帳"])

# -------------------- TAB 1: 計時器模式 --------------------
with tab1:
    st.components.v1.html(fullscreen_js, height=55)
    st.subheader("▶ 計時與即時計費")
    
    elapsed = get_elapsed_seconds()
    hrs = int(elapsed // 3600)
    mins = int((elapsed % 3600) // 60)
    secs = int(elapsed % 60)
    time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

    multiplier = 2 if st.session_state.is_double else 1
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
                save_cloud_data(st.session_state.bo_coins, st.session_state.history)
                st.success(f"已成功存檔並同步至雲端：{minutes_used:.2f} 分鐘 / {cost:.2f} 元！")
            else:
                st.warning("時間為 0，無需存檔！")

    if st.session_state.timer_running:
        time.sleep(1)
        st.rerun()

# -------------------- TAB 2: 算式與紀錄 --------------------
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
                    save_cloud_data(st.session_state.bo_coins, st.session_state.history)
                    st.success(f"已手動增加 {amt} 波幣並同步至雲端！")
                except Exception:
                    st.error("語法錯誤，請輸入 addcoin 10")
            elif inp == "resetcoin":
                st.session_state.bo_coins = 0.0
                save_cloud_data(0.0, st.session_state.history)
                st.success("波幣已歸零並同步至雲端！")
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
    
    st.write("##### ✍️ 手動新增單筆紀錄")
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
                rec = {"time": dt_now, "minutes": round_half_up(m_mins), "cost": round_half_up(m_cost), "note": "手動紀錄"}
                st.session_state.history.append(rec)
                save_cloud_data(st.session_state.bo_coins, st.session_state.history)
                st.success("手動紀錄已新增並同步至雲端！")
                st.rerun()

    st.markdown("---")
    # ==================== 超強防錯 TXT/CSV 解析引擎 ====================
    st.write("##### 📂 上傳/匯入歷史備份檔 (全自動辨識)")
    uploaded_file = st.file_uploader("選擇上傳手機裡的舊備份檔案 (TXT 或 CSV):", type=["txt", "csv"])
    
    if uploaded_file is not None:
        file_name = uploaded_file.name
        content = uploaded_file.read().decode("utf-8", errors="ignore").strip()
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        is_coin_file = False
        coin_val = 0.0

        if "bo_coins" in file_name or (len(lines) == 1 and safe_float(lines[0]) > 0 and "年" not in lines[0] and "-" not in lines[0]):
            coin_val = safe_float(lines[0])
            if coin_val >= 0:
                is_coin_file = True

        if is_coin_file and "billing_history" not in file_name:
            st.info(f"🪙 **自動偵測結果：波幣備份檔**！找到數值 **{coin_val}** 波幣")
            if st.button("🪙 匯入並更新波幣餘額", type="primary"):
                st.session_state.bo_coins = coin_val
                save_cloud_data(st.session_state.bo_coins, st.session_state.history)
                st.success(f"已成功將波幣餘額更新為：{coin_val} 並同步至雲端！")
                st.rerun()
        
        elif file_name.endswith(".csv"):
            try:
                uploaded_file.seek(0)
                df_uploaded = pd.read_csv(uploaded_file)
                new_records = []
                for _, row in df_uploaded.iterrows():
                    time_val = str(row.get("時間", ""))
                    if "資產" in time_val or "摘要" in time_val or "當前" in time_val or "歷史" in time_val:
                        continue
                    try:
                        mins_v = safe_float(row.get("分鐘", 0))
                        cost_v = safe_float(row.get("金額(元)", 0))
                        note_v = str(row.get("備註", "CSV匯入"))
                        new_records.append({
                            "time": time_val,
                            "minutes": mins_v,
                            "cost": cost_v,
                            "note": note_v
                        })
                    except Exception:
                        pass
                st.info(f"📊 **自動偵測結果：CSV 歷史紀錄檔**！共找到 {len(new_records)} 筆紀錄")
                if st.button("📥 確認匯入此 CSV 紀錄", type="primary"):
                    st.session_state.history.extend(new_records)
                    save_cloud_data(st.session_state.bo_coins, st.session_state.history)
                    st.success(f"成功匯入 {len(new_records)} 筆紀錄並同步至雲端！")
                    st.rerun()
            except Exception:
                st.error("CSV 格式解析失敗！")

        else:
            st.info("📋 **自動偵測結果：TXT 歷史紀錄檔**！正在解析內容...")
            parsed_records = []
            
            for line in lines:
                time_match = re.search(r'(\d{4}[年-]\d{2}[月-]\d{2}[日]?\s+\d{2}:\d{2}:\d{2})', line)
                time_str = time_match.group(1) if time_match else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                mins_v = 0.0
                cost_v = 0.0
                note_v = "歷史備份"

                # 1. 嘗試比對標準計時器格式： 11.89 分鐘 -> 1.19 元
                mins_match = re.search(r'([\d.]+)\s*分鐘', line)
                cost_match = re.search(r'(?:等於|金額:|->)\s*([\d.]+)\s*元', line)

                if mins_match:
                    mins_v = safe_float(mins_match.group(1))
                    if cost_match:
                        cost_v = safe_float(cost_match.group(1))
                    else:
                        cost_v = round_half_up(mins_v * 0.1)
                    if "算式" in line:
                        note_v = "算式計算"
                    else:
                        note_v = "計時器存檔"
                else:
                    # 2. 比對手動格式： [手動] 71.18 或 [手動] 5.02.79
                    manual_match = re.search(r'\[手動\]\s*([\d.]+)', line)
                    if manual_match:
                        raw_num = manual_match.group(1)
                        mins_v = safe_float(raw_num)
                        cost_v = round_half_up(mins_v * 0.1)
                        note_v = "手動紀錄"

                if mins_v > 0 or cost_v > 0:
                    parsed_records.append({
                        "time": time_str,
                        "minutes": round_half_up(mins_v),
                        "cost": round_half_up(cost_v),
                        "note": note_v
                    })

            if parsed_records:
                st.success(f"🎉 成功解析出 **{len(parsed_records)}** 筆歷史紀錄！")
                st.dataframe(pd.DataFrame(parsed_records)[["time", "minutes", "cost", "note"]])
                if st.button("📥 確認匯入這些歷史紀錄", type="primary", use_container_width=True):
                    st.session_state.history.extend(parsed_records)
                    save_cloud_data(st.session_state.bo_coins, st.session_state.history)
                    st.success("歷史紀錄已順利匯入完成並同步至雲端！")
                    st.rerun()
            else:
                st.warning("⚠️ 無法識別此檔案內容，請確認是否為正確的備份檔。")

    st.markdown("---")
    st.write("##### 📋 歷史紀錄與下載報表")

    total_mins = sum(item.get("minutes", 0) for item in st.session_state.history)
    total_cost = sum(item.get("cost", 0) for item in st.session_state.history)
    
    st.write(f"📊 **歷史加總**：總時間 **{total_mins:.2f}** 分鐘 | 總金額 **{total_cost:.2f}** 元")

    export_list = list(st.session_state.history)
    df_export = pd.DataFrame(export_list)
    if not df_export.empty:
        df_export.columns = ["時間", "分鐘", "金額(元)", "備註"]
    
    summary_data = pd.DataFrame([
        {"時間": "--- 資產摘要 ---", "分鐘": "", "金額(元)": "", "備註": ""},
        {"時間": "當前波幣總額", "分鐘": f"{st.session_state.bo_coins:.2f} 幣", "金額(元)": f"{st.session_state.bo_coins*0.1:.2f} 元", "備註": "1波幣=1分鐘"},
        {"時間": "歷史總計分鐘", "分鐘": f"{total_mins:.2f} 分", "金額(元)": f"{total_cost:.2f} 元", "備註": "未折抵前總額"}
    ])
    
    df_combined = pd.concat([df_export, summary_data], ignore_index=True) if not df_export.empty else summary_data
    csv_data = df_combined.to_csv(index=False, encoding='utf-8-sig')

    txt_content = f"=========================================\n"
    txt_content += f"   🐾 波貓系統完整報表 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
    txt_content += f"=========================================\n"
    txt_content += f"🪙 目前波幣資產：{st.session_state.bo_coins:.2f} 波幣\n"
    txt_content += f"⏱️ 歷史累計總時間：{total_mins:.2f} 分鐘\n"
    txt_content += f"💰 歷史累計總金額：{total_cost:.2f} 元\n"
    txt_content += f"-----------------------------------------\n"
    
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
    st.write("##### 🔒 管理員操作區 (需要刪除密碼)")
    
    del_pwd = st.text_input("輸入刪除管理密碼:", type="password", key="del_pwd_input")

    records_to_keep = []
    has_deleted = False

    for idx, item in enumerate(st.session_state.history):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.write(f"🕒 {item['time']}")
        c2.write(f"⏱️ {item['minutes']} 分")
        c3.write(f"💰 {item['cost']} 元")
        del_btn = c4.button("🗑️", key=f"del_{idx}")
        
        if del_btn:
            if del_pwd == SECURITY_PASSWORD:
                has_deleted = True
            else:
                st.error("🔒 密碼錯誤，無法刪除！")
                records_to_keep.append(item)
        else:
            records_to_keep.append(item)

    if has_deleted:
        st.session_state.history = records_to_keep
        save_cloud_data(st.session_state.bo_coins, st.session_state.history)
        st.success("已成功刪除該筆紀錄並更新雲端！")
        st.rerun()

    if st.button("🗑️ 清空所有歷史紀錄", type="secondary"):
        if del_pwd == SECURITY_PASSWORD:
            st.session_state.history = []
            save_cloud_data(st.session_state.bo_coins, [])
            st.success("紀錄已清空並更新雲端！")
            st.rerun()
        else:
            st.error("🔒 密碼錯誤，無法清空紀錄！")

# -------------------- TAB 3: 全螢幕/獨立收銀畫面 --------------------
with tab3:
    st.components.v1.html(fullscreen_js, height=55)
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

    st.markdown("---")
    checkout_pwd = st.text_input("🔑 請輸入收銀確認密碼:", type="password", key="checkout_pwd_input")

    if st.button("✅ 確定完成結帳（扣除波幣並清空紀錄）", type="primary", use_container_width=True):
        if checkout_pwd != SECURITY_PASSWORD:
            st.error("🔒 收銀密碼錯誤，無法進行結帳！")
        elif use_coins > st.session_state.bo_coins:
            st.error("波幣不足，無法完成結帳！")
        else:
            st.session_state.bo_coins -= use_coins
            st.session_state.history = []
            
            # 同步更新雲端
            save_cloud_data(st.session_state.bo_coins, [])
            
            st.success("🎉 結帳完畢！波幣已扣除，歷史紀錄已自動歸零並同步至雲端！")
            st.rerun()
