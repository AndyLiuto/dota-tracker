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
    .match-row { background-color: #16191c; border: 1px solid #23272b; border-radius: 4px; padding: 10px; margin-bottom: 6px; display: flex; align-items: center; min-height: 90px; }
    .win-bar { flex: 0 0 4px; height: 60px; background-color: #2ecc71; border-radius: 2px; margin-right: 15px; }
    .loss-bar { flex: 0 0 4px; height: 60px; background-color: #e74c3c; border-radius: 2px; margin-right: 15px; }
    .col-img { flex: 0 0 85px; margin-right: 15px; }
    .col-res { flex: 0 0 100px; margin-right: 15px; }
    .col-hero { flex: 0 0 220px; margin-right: 15px; }
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

def get_display_name(hid, h_info):
    cn = HERO_ID_CHINESE.get(str(hid), h_info.get("localized_name", "未知英雄"))
    en = h_info.get("name", "").replace("npc_dota_hero_", "").replace("_", " ").title()
    return f"{cn} ({en})" if cn != en else cn

def get_rank_name_cn(tier):
    if not tier: return "未入榜"
    ranks = ["先锋", "卫士", "中坚", "主宰", "传奇", "万古流芳", "超凡入圣", "冠绝一世"]
    main_tier, star = (tier // 10) - 1, tier % 10
    if main_tier >= 7: return "冠绝一世 (Immortal)"
    return f"{ranks[max(0, main_tier)]} {star} 星"

heroes, items = get_data()

with st.sidebar:
    account_id = st.text_input("Account ID", value="109799796")
    if 'mmr_base' not in st.session_state: st.session_state.mmr_base = 4500
    st.session_state.mmr_base = st.number_input("MMR 基点:", value=st.session_state.mmr_base)
    if st.button("刷新"): st.cache_data.clear()

if account_id:
    player = requests.get(f"{OPENDOTA_API}/players/{account_id}").json()
    matches = requests.get(f"{OPENDOTA_API}/players/{account_id}/recentMatches").json()
    
    if 'profile' in player:
        win_c = sum(1 for m in matches if (m['player_slot'] < 128) == m['radiant_win'])
        net_c = (win_c - (len(matches)-win_c)) * 25
        
        # Header
        c1, c2 = st.columns([1, 6])
        with c1: st.markdown(f'<img src="{player["profile"]["avatarfull"]}" style="width:90px; border-radius:8px;">', unsafe_allow_html=True)
        with c2: st.markdown(f'<h2>{player["profile"]["personaname"]}</h2><p>{get_rank_name_cn(player.get("rank_tier"))} | 地区: {player["profile"].get("loccountrycode", "Unknown")}</p>', unsafe_allow_html=True)
        
        # MMR 仪表盘
        m1, m2, m3 = st.columns([1, 1, 2])
        m1.markdown(f'<div class="meta-card"><div class="meta-value">{st.session_state.mmr_base + net_c}</div><div class="meta-label">当前 MMR</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="meta-card"><div class="meta-value" style="color:{"#2ecc71" if net_c>=0 else "#e74c3c"}">{net_c}</div><div class="meta-label">积分变动</div></div>', unsafe_allow_html=True)
        
        pts, cur = [], st.session_state.mmr_base - net_c
        for m in reversed(matches):
            cur += 25 if (m['player_slot'] < 128) == m['radiant_win'] else -25
            pts.append(cur)
        fig = px.area(pd.DataFrame({"M": range(len(pts)), "MMR": pts}), x="M", y="MMR")
        fig.update_layout(height=120, margin=dict(l=40,r=0,t=20,b=20), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        fig.update_traces(line_color='#2ecc71' if net_c>=0 else '#e74c3c', fillcolor='rgba(46, 204, 113, 0.1)')
        m3.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        for m in matches[:15]:
            win = (m['player_slot'] < 128) == m['radiant_win']
            h_info = heroes.get(str(m['hero_id']), {})
            dt = datetime.fromtimestamp(m["start_time"], tz=pytz.UTC).astimezone(BEIJING_TZ)
            
            item_html = ""
            try:
                det = requests.get(f"{OPENDOTA_API}/matches/{m['match_id']}", timeout=2).json()
                p_det = next((p for p in det.get('players', []) if p.get('account_id') == int(account_id)), {})
                item_html = '<div style="display:flex; gap:2px;">'
                for i in range(6):
                    iid = p_det.get(f'item_{i}')
                    if iid and iid > 0:
                        url = None
                        for k, v in items.items():
                            if v.get('id') == iid: url = DOTA_ASSET_URL + v.get('img', '')
                        if url: item_html += f'<img src="{url}" class="item-icon">'
                item_html += '</div>'
            except: pass
            
            card = (
                f'<div class="match-row"><div class="{"win-bar" if win else "loss-bar"}"></div>'
                f'<div class="col-img"><img src="{DOTA_ASSET_URL + h_info.get("img","")}" style="width:75px; border-radius:4px;"></div>'
                f'<div class="col-res"><div class="stat-desc">结果</div><div class="{"win-text" if win else "loss-text"}">{"胜利" if win else "失败"}</div><div style="font-size:0.7rem; color:#888;">{dt.strftime("%m-%d %H:%M")}</div></div>'
                f'<div class="col-hero"><div class="stat-desc">英雄 / 出装</div><div class="stat-num">{get_display_name(m["hero_id"], h_info)}</div>{item_html}</div>'
                f'<div class="col-stat"><div class="stat-desc">KDA</div><div class="stat-num">{m["kills"]}/{m["deaths"]}/{m["assists"]}</div></div>'
                f'<div class="col-info"><div class="stat-desc">时长 / ID</div><div class="stat-num" style="font-size:0.8rem;">{m["duration"]//60}m</div><div style="font-size:0.6rem; color:#555;">{m["match_id"]}</div></div>'
                f'<div class="col-action"><a href="https://www.opendota.com/matches/{m["match_id"]}" target="_blank" class="view-btn">详情</a></div></div>'
            )
            st.markdown(card, unsafe_allow_html=True)
