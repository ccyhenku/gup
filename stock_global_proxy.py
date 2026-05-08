import streamlit as st
import akshare as ak
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import time

# --- 1. 页面配置 ---
st.set_page_config(page_title="A股全向决策中心", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #020617; color: #cbd5e1; }
    .neon-text { color: #f43f5e; font-weight: bold; text-shadow: 0 0 10px rgba(244, 63, 94, 0.3); }
    .stock-card { background: #1e293b; padding: 18px; border-radius: 12px; border-left: 5px solid #f43f5e; margin-bottom: 12px; border: 1px solid #334155; }
    .tag { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .tag-blue { background: #1e3a8a; color: #60a5fa; }
    .tag-green { background: #064e3b; color: #34d399; }
    .tag-gold { background: #451a03; color: #fbbf24; }
    .tag-purple { background: #4c1d95; color: #c084fc; } /* 抄底专用色 */
</style>
""", unsafe_allow_html=True)

# --- 2. 核心数据函数 ---
def get_safe_hist(code, start_d, end_d):
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_d, end_date=end_d, adjust="qfq")
        if df is None or df.empty: return None
        col_map = {'收盘': 'close', '开盘': 'open', '最高': 'high', '最低': 'low', 'Close': 'close', '成交量': 'volume'}
        df.rename(columns=col_map, inplace=True)
        return df
    except: return None

def main_engine(sectors, mode_name, strategy_type="趋势追踪"):
    recommend_list = []
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=150)).strftime("%Y%m%d")
    
    msg = st.empty()
    bar = st.progress(0)
    
    for i, sector in enumerate(sectors):
        msg.write(f"正在扫描【{sector}】板块中的{strategy_type}机会...")
        bar.progress((i + 1) / len(sectors))
        try:
            stocks = ak.stock_board_industry_cons_em(symbol=sector)
            if stocks is None or stocks.empty: continue
            
            for _, row in stocks.head(20).iterrows():
                code, name = row['代码'], row['名称']
                hist = get_safe_hist(code, start_date, end_date)
                
                if hist is not None and len(hist) >= 30:
                    hist['ma20'] = hist['close'].rolling(20).mean()
                    last = hist.iloc[-1]
                    
                    if strategy_type == "趋势追踪":
                        # 逻辑：站稳均线
                        prev_ma20 = hist['ma20'].iloc[-2]
                        if last['close'] > last['ma20'] and last['ma20'] >= prev_ma20:
                            recommend_list.append({
                                "代码": code, "名称": name, "现价": round(last['close'], 2),
                                "当日涨幅": row['涨跌幅'], "所属板块": sector, "形态": "上升通道"
                            })
                    
                    elif strategy_type == "极低抄底 (超跌反弹)":
                        # 逻辑：RSI超卖 + 负乖离率大
                        # 计算 RSI (14)
                        hist['rsi'] = ta.rsi(hist['close'], length=14)
                        # 计算乖离率 (Bias) = (现价 - MA20) / MA20
                        bias = (last['close'] - last['ma20']) / last['ma20'] * 100
                        
                        rsi_val = hist['rsi'].iloc[-1]
                        
                        # 判定标准：RSI < 35 且 价格偏离均线超过 8%
                        if rsi_val < 35 or bias < -8:
                            recommend_list.append({
                                "代码": code, "名称": name, "现价": round(last['close'], 2),
                                "当日涨幅": row['涨跌幅'], "所属板块": sector, 
                                "形态": f"超跌 (RSI:{int(rsi_val)}/Bias:{int(bias)}%)"
                            })
                time.sleep(0.02)
        except: continue
    msg.empty()
    bar.empty()
    return pd.DataFrame(recommend_list)

# --- 3. 侧边栏策略配置 ---
with st.sidebar:
    st.markdown('<h2 class="neon-text">🧭 投资地图</h2>', unsafe_allow_html=True)
    
    strategy_type = st.selectbox("核心选股逻辑", ["趋势追踪", "极低抄底 (超跌反弹)"])
    
    STRATEGY_MAP = {
        "全球科技映射": {"tag": "tag-blue", "sectors": ["半导体", "通信设备", "软件开发", "互联网服务"]},
        "国内政策风口": {"tag": "tag-green", "sectors": ["航天航空", "通用设备", "汽车零部件", "电机"]},
        "避险红利资产": {"tag": "tag-gold", "sectors": ["煤炭行业", "银行", "电力行业", "石油行业", "公路铁路运输"]},
        "大消费复苏": {"tag": "tag-purple", "sectors": ["酿酒行业", "家电行业", "食品饮料", "旅游酒店"]}
    }
    
    choice = st.radio("选择覆盖行业", list(STRATEGY_MAP.keys()))
    current_sectors = STRATEGY_MAP[choice]["sectors"]
    current_tag = STRATEGY_MAP[choice]["tag"] if strategy_type == "趋势追踪" else "tag-purple"

# --- 4. 主界面 ---
st.markdown(f'<h1 class="neon-text">📈 A股决策中心 · {strategy_type}</h1>', unsafe_allow_html=True)

if st.button("🚀 启动深度扫描", use_container_width=True):
    with st.spinner(f"正在分析市场数据，寻找{strategy_type}机会..."):
        df_res = main_engine(current_sectors, choice, strategy_type)
        
        if not df_res.empty:
            st.success(f"扫描完毕！找到 {len(df_res)} 只符合【{strategy_type}】特征的个股。")
            df_res = df_res.sort_values("当日涨幅", ascending=False)
            
            for _, row in df_res.iterrows():
                st.markdown(f"""
                <div class="stock-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:20px; font-weight:bold;">{row['名称']} <small style="color:#64748b;">{row['代码']}</small></span>
                        <span style="color:#ef4444; font-size:22px; font-weight:bold;">{row['当日涨幅']}%</span>
                    </div>
                    <div style="margin-top:10px; font-size:14px;">
                        <span class="tag {current_tag}">{strategy_type}</span>
                        <span style="margin-left:10px; color:#94a3b8;">板块: {row['所属板块']} | 现价: {row['现价']}</span>
                        <span style="float:right; color:#4ade80;">特征: {row['形态']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with st.expander("📊 查看完整统计表"):
                st.dataframe(df_res, use_container_width=True)
        else:
            st.warning(f"⚠️ 暂未发现符合{strategy_type}条件的个股。如果是抄底模式，说明目前市场整体不处于超跌状态，或者跌幅还不够深。")

st.divider()
st.info("💡 **抄底建议**：抄底逻辑属于‘左侧交易’，风险高于趋势模式。建议配合‘缩量’特征使用，即股价不再大跌且成交量极小。")