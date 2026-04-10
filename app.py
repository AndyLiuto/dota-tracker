import streamlit as st
import requests
from datetime import datetime
import pytz
import plotly.express as px
import pandas as pd
from constants import HERO_ID_CHINESE

st.set_page_config(page_title="Dota 2 Pro Tracker", layout="wide", page_icon="⚔️")

# --- CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0b0d0f; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    .meta-card { background: #16191c; border: 1px solid #2d3238; border-radius: 6px; padding: 15px; text-align: center; }
    .meta-value { font-size: 1.8rem; font-weight: 800; color: #fff; }
    .meta-label { font-size: 0.7rem; color: #666; text-transform: uppercase; margin-top: 5px; }
    .hero-stat-table { width: 100%; border-collapse: collapse; margin-top: 10px; background: #16191c; border-radius: 6px; overflow: hidden; }
    .hero-stat-table th { background: #1e2227; color: #666; font-size: 0.7rem; text-align: left; padding: 10px; text-transform: uppercase; }
    .hero-stat-table td { padding: 8px 10px; border-bottom: 1px solid #23272b; font-size: 0.9rem; }
    .mini-hero-img { width: 35px; border-radius: 3px; vertical-align: middle; margin-right: 10px; }
    .match-row { background-color: #16191c; border: 1px solid #23272b; border-radius: 4px; padding: 10px; margin-bottom: 6px; display: flex; align-items: center; min-height: 90px; }
    .win-bar { flex: 0 0 4px; height: 60px; background-color: #2ecc71; border-radius: 2px; margin-right: 15px; }
    .loss-bar { flex: 0 0 4px; height: 60px; background-color: #e74c3c; border-radius: 2px; margin-right: 15px; }
    .col-img { flex: 0 0 85px; margin-right: 15px; }
    .col-res { flex: 0 0 100px; margin-right: 15px; }
    .col-hero { flex: 0 0 200px; margin-right: 15px; }
    .col-stat { flex: 0 0 80px; margin-right: 15px; }
    .col-info { flex: 0 0 100px; margin-right: 15px; }
    .col-action { flex-grow: 1; text-align: right; }
    .item-icon { width: 34px; height: 24px; border-radius: 2px; border: 1px solid #333; background: #000; margin-right: 2px; }
    .stat-desc { font-size: 0.7rem; color: #666; text-transform: uppercase; white-space: nowrap; }
    .stat-num { font-size: 1.05rem; font-weight: 600; color: #fff; white-space: nowrap; }
    .view-btn { display:inline-block; background: #23272b; border: 1px solid #3d444b; color: #888; padding: 5px 12px; border-radius: 4px; font-size: 0.8rem; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

OPENDOTA_API = "https://api.opendota.com/api"
DOTA_ASSET_URL = "https://cdn.cloudflare.steamstatic.com"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

@st.cache_data(ttl=1800)
def get_data():
    h = requests.get(f"{OPENDOTA_API}/constants/heroes").json()
    i = requests.get(f"{OPENDOTA_API}/constants/items").json()
    return h, i

def get_d2pt_url(h_info):
    name = h_info.get("name", "").replace("npc_dota_hero_", "").replace("_", " ").title()
    return f"https://dota2protracker.com/hero/{name.replace(' ', '%20')}"

def get_display_name(hid, h_info):
    cn = HERO_ID_CHINESE.get(str(hid), h_info.get("localized_name", "未知英雄"))
    en = h_info.get("name", "").replace("npc_dota_hero_", "").replace("_", " ").title()
    return f"{cn} ({en})" if cn != en else cn

heroes, items = get_data()

# --- 逻辑 ---
account_id = st.sidebar.text_input("Account ID", value="109799796")
if 'mmr_base' not in st.session_state: st.session_state.mmr_base = 4500
st.session_state.mmr_base = st.sidebar.number_input("MMR 基点:", value=st.session_state.mmr_base)
if st.sidebar.button("刷新数据"): st.cache_data.clear()

if account_id:
    player = requests.get(f"{OPENDOTA_API}/players/{account_id}").json()
    matches = requests.get(f"{OPENDOTA_API}/players/{account_id}/recentMatches").json()
    
    if 'profile' in player:
        win_c = sum(1 for m in matches if (m['player_slot'] < 128) == m['radiant_win'])
        net_c = (win_c - (len(matches)-win_c)) * 25
        
        c1, c2 = st.columns([1, 6])
        with c1: st.markdown(f'<img src="{player["profile"]["avatarfull"]}" style="width:90px; border-radius:8px;">', unsafe_allow_html=True)
        with c2: st.markdown(f'<h2>{player["profile"]["personaname"]}</h2><p style="color:#aaa;">{player["profile"].get("loccountrycode", "Unknown")}</p>', unsafe_allow_html=True)
        
        m1, m2, m3 = st.columns([1, 1, 2])
        m1.markdown(f'<div class="meta-card"><div class="meta-value">{st.session_state.mmr_base + net_c}</div><div class="meta-label">实时 MMR</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="meta-card"><div class="meta-value" style="color:{"#2ecc71" if net_c>=0 else "#e74c3c"}">{net_c}</div><div class="meta-label">净胜分</div></div>', unsafe_allow_html=True)
        
        # 趋势图
        pts, cur = [], st.session_state.mmr_base - net_c
        for m in reversed(matches):
            cur += 25 if (m['player_slot'] < 128) == m['radiant_win'] else -25
            pts.append(cur)
        fig = px.area(pd.DataFrame({"M": range(len(pts)), "MMR": pts}), x="M", y="MMR")
        fig.update_layout(height=100, margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark", xaxis_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        m3.plotly_chart(fig, use_container_width=True)

        # 英雄统计表
        st.markdown("#### 🏆 英雄统计")
        hero_groups = {}
        for m in matches:
            if m['hero_id'] not in hero_groups: hero_groups[m['hero_id']] = []
            hero_groups[m['hero_id']].append(m)
        
        rows = ""
        for hid, hm in sorted(hero_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            h_info = heroes.get(str(hid), {})
            hw = sum(1 for m in hm if (m['player_slot'] < 128) == m['radiant_win'])
            rows += f'<tr><td><a href="{get_d2pt_url(h_info)}" target="_blank"><img src="{DOTA_ASSET_URL + h_info.get("img","")}" class="mini-hero-img"></a><b>{get_display_name(hid, h_info)}</b></td><td>{len(hm)}</td><td>{(hw/len(hm)*100):.1f}%</td><td>{(sum(m["kills"]+m["assists"] for m in hm)/max(1, sum(m["deaths"] for m in hm))):.2f}</td></tr>'
        st.markdown(f'<table class="hero-stat-table"><thead><tr><th>英雄</th><th>场次</th><th>胜率</th><th>KDA</th></tr></thead><tbody>{rows}</tbody></table>', unsafe_allow_html=True)
        
        st.divider()
        # 实战流
        for m in matches[:15]:
            win = (m['player_slot'] < 128) == m['radiant_win']
            h_info = heroes.get(str(m['hero_id']), {})
            dt = datetime.fromtimestamp(m["start_time"], tz=pytz.UTC).astimezone(BEIJING_TZ)
            item_html = ""
            try:
                det = requests.get(f"{OPENDOTA_API}/matches/{m['match_id']}", timeout=2).json()
                p_det = next((p for p in det.get('players', []) if p.get('account_id') == int(account_id)), {})
                for i in range(6):
                    iid = p_det.get(f'item_{i}')
                    if iid and iid > 0:
                        for k, v in items.items():
                            if v.get('id') == iid: item_html += f'<img src="{DOTA_ASSET_URL + v.get("img", "")}" class="item-icon">'
            except: pass
            
            st.markdown(f'<div class="match-row"><div class="{"win-bar" if win else "loss-bar"}"></div><div class="col-img"><a href="{get_d2pt_url(h_info)}" target="_blank"><img src="{DOTA_ASSET_URL + h_info.get("img","")}" style="width:75px; border-radius:4px;"></a></div><div class="col-res"><div class="stat-desc">结果</div><div class="{"win-text" if win else "loss-text"}">{"胜利" if win else "失败"}</div><div style="font-size:0.6rem; color:#888;">{dt.strftime("%m-%d %H:%M")}</div></div><div class="col-hero"><div class="stat-desc">英雄 / 出装</div><div class="stat-num">{get_display_name(m["hero_id"], h_info)}</div><div style="display:flex;">{item_html}</div></div><div class="col-stat"><div class="stat-desc">KDA</div><div class="stat-num">{m["kills"]}/{m["deaths"]}/{m["assists"]}</div></div><div class="col-info"><div class="stat-desc">时长/ID</div><div class="stat-num" style="font-size:0.8rem;">{m["duration"]//60}m</div><div style="font-size:0.6rem; color:#555;">{m["match_id"]}</div></div><div class="col-action"><a href="https://www.opendota.com/matches/{m["match_id"]}" target="_blank" class="view-btn">详情</a></div></div>', unsafe_allow_html=True)
