import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import pytz
import plotly.express as px
from constants import HERO_ID_CHINESE

# --- 页面配置 ---
st.set_page_config(page_title="Dota 2 Pro Tracker Real-time", layout="wide", page_icon="⚔️")

# --- 样式加固 ---
st.markdown("""
<style>
    .stApp { background-color: #0b0d0f; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    .meta-card { background: #16191c; border: 1px solid #2d3238; border-radius: 6px; padding: 15px; text-align: center; height: 100%; }
    .meta-value { font-size: 1.8rem; font-weight: 800; color: #fff; }
    .meta-label { font-size: 0.7rem; color: #666; text-transform: uppercase; margin-top: 5px; }
    .hero-stat-table { width: 100%; border-collapse: collapse; margin-top: 10px; background: #16191c; border-radius: 6px; overflow: hidden; }
    .hero-stat-table th { background: #1e2227; color: #666; font-size: 0.7rem; text-align: left; padding: 10px; text-transform: uppercase; }
    .hero-stat-table td { padding: 8px 10px; border-bottom: 1px solid #23272b; font-size: 0.9rem; }
    .mini-hero-img { width: 35px; border-radius: 3px; vertical-align: middle; margin-right: 10px; transition: transform 0.2s; }
    .mini-hero-img:hover { transform: scale(1.1); }
    .match-row { background-color: #16191c; border: 1px solid #23272b; border-radius: 4px; padding: 12px; margin-bottom: 6px; display: flex; align-items: center; min-height: 95px; }
    .win-bar { flex: 0 0 4px; height: 65px; background-color: #2ecc71; border-radius: 2px; margin-right: 15px; }
    .loss-bar { flex: 0 0 4px; height: 65px; background-color: #e74c3c; border-radius: 2px; margin-right: 15px; }
    .col-hero-img { flex: 0 0 90px; margin-right: 20px; }
    .col-result { flex: 0 0 110px; margin-right: 15px; }
    .col-build { flex: 0 0 230px; margin-right: 15px; }
    .col-stats { flex: 0 0 95px; margin-right: 15px; }
    .col-spacer { flex: 0 0 120px; margin-right: 15px; }
    .col-action { flex-grow: 1; text-align: right; }
    .item-icon { width: 38px; height: 28px; border-radius: 2px; border: 1px solid #333; background: #000; margin-right: 2px; }
    .stat-desc { font-size: 0.7rem; color: #666; text-transform: uppercase; white-space: nowrap; margin-bottom: 2px; }
    .stat-num { font-size: 1.05rem; font-weight: 600; color: #fff; white-space: nowrap; }
    .win-text { color: #2ecc71; font-weight: bold; }
    .loss-text { color: #e74c3c; font-weight: bold; }
    .view-btn { display: inline-block; background: #23272b; border: 1px solid #3d444b; color: #888; padding: 5px 15px; border-radius: 4px; font-size: 0.8rem; text-decoration: none; }
    .view-btn:hover { background: #3d444b; color: #fff; }
</style>
""", unsafe_allow_html=True)

# --- 常量 ---
OPENDOTA_API = "https://api.opendota.com/api"
DOTA_ASSET_URL = "https://cdn.cloudflare.steamstatic.com"
CONFIG_FILE = "dota_tracker/user_config.csv"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# --- 工具函数 ---
@st.cache_data(ttl=3600)
def get_constants():
    h = requests.get(f"{OPENDOTA_API}/constants/heroes").json()
    i = requests.get(f"{OPENDOTA_API}/constants/items").json()
    return h, i

def get_base_mmr():
    if os.path.exists(CONFIG_FILE):
        try: return int(pd.read_csv(CONFIG_FILE).iloc[0]['base_mmr'])
        except: return 4500
    return 4500

def set_base_mmr(val):
    pd.DataFrame([[val]], columns=['base_mmr']).to_csv(CONFIG_FILE, index=False)

def get_display_name(hid, h_info):
    hid_str = str(hid)
    cn_name = HERO_ID_CHINESE.get(hid_str, h_info.get("localized_name", "未知英雄"))
    raw = h_info.get("name", "")
    en = raw.replace("npc_dota_hero_", "").replace("_", " ").title()
    return f"{cn_name} ({en})" if cn_name != en else cn_name

def get_d2pt_url(h_info):
    raw_en = h_info.get("name", "").replace("npc_dota_hero_", "")
    special_cases = {"necrolyte": "Necrophos", "zuus": "Zeus", "shredder": "Timbersaw", "obsidian_destroyer": "Outworld Destroyer"}
    hero_name = special_cases.get(raw_en, raw_en.replace("_", " ").title())
    return f"https://dota2protracker.com/hero/{hero_name.replace(' ', '%20')}"

def get_rank_name_cn(tier):
    if not tier: return "未入榜"
    ranks = ["先锋", "卫士", "中坚", "主宰", "传奇", "万古流芳", "超凡入圣", "冠绝一世"]
    main_tier, star = (tier // 10) - 1, tier % 10
    if main_tier >= 7: return "冠绝一世 (Immortal)"
    return f"{ranks[max(0, main_tier)]} {star} 星"

heroes_const, items_const = get_constants()

# --- 侧边栏 ---
with st.sidebar:
    st.markdown("### 🔎 核心配置")
    account_id = st.text_input("Account ID", value="109799796")
    st.divider()
    st.markdown("### 🏆 MMR 校准")
    new_mmr = st.number_input("当前 MMR 基点:", value=get_base_mmr())
    if st.button("更新并同步"):
        set_base_mmr(new_mmr)
        st.rerun()
    st.divider()
    auto_refresh = st.checkbox("开启自动刷新 (5min)", value=True)
    match_limit = st.slider("装备加载深度", 0, 20, 10)
    if st.button("清空缓存"):
        st.cache_data.clear()
        st.rerun()

if auto_refresh:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=300 * 1000, key="data_refresh")

# --- 主界面 ---
if account_id:
    player = requests.get(f"{OPENDOTA_API}/players/{account_id}").json()
    matches = requests.get(f"{OPENDOTA_API}/players/{account_id}/recentMatches").json()
    
    if 'profile' in player:
        profile = player['profile']
        base_mmr = get_base_mmr()
        
        # 头部个人资料
        c_head1, c_head2 = st.columns([1, 6])
        with c_head1: st.markdown(f'<img src="{profile["avatarfull"]}" style="width:90px; border-radius:8px; border:2px solid #2d3238;">', unsafe_allow_html=True)
        with c_head2: st.markdown(f"""<div style="margin-left:10px;"><h2 style="margin-bottom:0;">{profile['personaname']}</h2><div style="color:#888; font-size:1rem; margin-top:5px;"><span style="color:#fff; font-weight:bold;">{get_rank_name_cn(player.get("rank_tier"))}</span> | 地区: <span style="color:#fff;">{profile.get("loccountrycode", "Unknown")}</span></div></div>""", unsafe_allow_html=True)
        
        st.divider()
        
        # 仪表盘数据计算
        win_c = sum(1 for m in matches if (m['player_slot'] < 128) == m['radiant_win'])
        net_c = (win_c - (len(matches)-win_c)) * 25
        
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: st.markdown(f'<div class="meta-card"><div class="meta-value">{base_mmr + net_c}</div><div class="meta-label">实时 MMR (估算)</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="meta-card"><div class="meta-value" style="color:{"#2ecc71" if net_c>=0 else "#e74c3c"}">{"+" if net_c>=0 else ""}{net_c}</div><div class="meta-label">最近积分变动</div></div>', unsafe_allow_html=True)
        with c3:
            pts, cur = [], base_mmr - net_c
            for m in reversed(matches):
                cur += 25 if (m['player_slot'] < 128) == m['radiant_win'] else -25
                pts.append(cur)
            fig = px.area(pd.DataFrame({"M": range(len(pts)), "MMR": pts}), x="M", y="MMR")
            fig.update_layout(height=130, margin=dict(l=0,r=0,t=10,b=0), template="plotly_dark", xaxis_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig.update_traces(line_color='#2ecc71' if net_c>=0 else '#e74c3c', fillcolor='rgba(46, 204, 113, 0.15)')
            st.plotly_chart(fig, use_container_width=True)

        # 英雄统计 (带跳转)
        st.markdown("#### 🏆 英雄表现统计")
        hero_groups = {}
        for m in matches:
            hid = m['hero_id']
            if hid not in hero_groups: hero_groups[hid] = []
            hero_groups[hid].append(m)
        rows = ""
        for hid, hm in sorted(hero_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            hw = sum(1 for m in hm if (m['player_slot'] < 128) == m['radiant_win'])
            h_info = heroes_const.get(str(hid)) or next((v for v in heroes_const.values() if v.get('id') == hid), {})
            d2pt_link = get_d2pt_url(h_info)
            rows += f'<tr><td><a href="{d2pt_link}" target="_blank"><img src="{DOTA_ASSET_URL + h_info.get("img","")}" class="mini-hero-img"></a><b>{get_display_name(hid, h_info)}</b></td><td>{len(hm)}</td><td style="color:{"#2ecc71" if (hw/len(hm))>=0.5 else "#e74c3c"}; font-weight:bold;">{(hw/len(hm)*100):.1f}%</td><td>{len(hm)} 场实战</td></tr>'
        st.markdown(f'<table class="hero-stat-table"><thead><tr><th>英雄 (点击看大触出装)</th><th>场次</th><th>胜率</th><th>备注</th></tr></thead><tbody>{rows}</tbody></table>', unsafe_allow_html=True)

        st.divider()
        # 比赛列表
        st.markdown("#### 🕒 实时比赛流")
        for idx, m in enumerate(matches[:15]):
            h_id, win = str(m['hero_id']), (m['player_slot'] < 128) == m['radiant_win']
            h_info = heroes_const.get(h_id, {})
            d2pt_link = get_d2pt_url(h_info)
            # 北京时间转换
            dt_utc = datetime.fromtimestamp(m["start_time"], tz=pytz.UTC)
            dt_beijing = dt_utc.astimezone(BEIJING_TZ)
            time_str = dt_beijing.strftime("%m-%d %H:%M")
            duration = f"{m['duration'] // 60}m {m['duration'] % 60}s"
            
            item_html = ""
            if idx < match_limit:
                try:
                    details = requests.get(f"{OPENDOTA_API}/matches/{m['match_id']}").json()
                    p_detail = next((p for p in details['players'] if p.get('account_id') == int(account_id)), None)
                    if p_detail:
                        item_html = '<div style="display:flex; gap:2px; margin-top:5px;">'
                        for i in range(6):
                            iid = p_detail.get(f'item_{i}')
                            if iid: item_html += f'<img src="{DOTA_ASSET_URL + items_const.get(next((k for k,v in items_const.items() if v.get("id")==iid), ""), {}).get("img","")}" class="item-icon">'
                        item_html += '</div>'
                except: pass
            
            card = (
                f'<div class="match-row"><div class="{"win-bar" if win else "loss-bar"}"></div>'
                f'<div class="col-hero-img"><a href="{d2pt_link}" target="_blank"><img src="{DOTA_ASSET_URL + h_info.get("img","")}" style="width:85px; border-radius:4px;" title="查看 D2PT 出装"></a></div>'
                f'<div class="col-result"><div class="stat-desc">结果 / 时间</div><div class="{"win-text" if win else "loss-text"}">{"胜利" if win else "失败"}</div><div style="font-size: 0.75rem; color: #888;">{time_str}</div></div>'
                f'<div class="col-build"><div class="stat-desc">英雄与出装</div><div class="stat-num" style="font-size: 0.9rem;">{get_display_name(h_id, h_info)}</div>{item_html}</div>'
                f'<div class="col-stats"><div class="stat-desc">K / D / A</div><div class="stat-num">{m["kills"]} / {m["deaths"]} / {m["assists"]}</div></div>'
                f'<div class="col-spacer"><div class="stat-desc">时长 / 比赛ID</div><div class="stat-num" style="font-size:0.85rem;">{duration}</div><div style="font-size:0.65rem; color:#555;">ID: {m["match_id"]}</div></div>'
                f'<div class="col-action"><a href="https://www.opendota.com/matches/{m["match_id"]}" target="_blank" class="view-btn">详细分析</a></div></div>'
            )
            st.markdown(card, unsafe_allow_html=True)
else: st.info("输入 Account ID 开始追踪")
