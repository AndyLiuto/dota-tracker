import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import plotly.express as px
from constants import HERO_ID_CHINESE

# --- 配置与工具 ---
st.set_page_config(page_title="Dota 2 Pro Tracker", layout="wide", page_icon="⚔️")
OPENDOTA_API = "https://api.opendota.com/api"
DOTA_ASSET_URL = "https://cdn.cloudflare.steamstatic.com"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# --- CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0b0d0f; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    .meta-card { background: #16191c; border: 1px solid #2d3238; border-radius: 6px; padding: 15px; text-align: center; }
    .meta-value { font-size: 1.8rem; font-weight: 800; color: #fff; }
    .meta-label { font-size: 0.7rem; color: #666; text-transform: uppercase; margin-top: 5px; }
    .match-row { background-color: #16191c; border: 1px solid #23272b; border-radius: 4px; padding: 12px; margin-bottom: 6px; display: flex; align-items: center; min-height: 95px; }
    .win-bar { flex: 0 0 4px; height: 70px; background-color: #2ecc71; border-radius: 2px; margin-right: 15px; }
    .loss-bar { flex: 0 0 4px; height: 70px; background-color: #e74c3c; border-radius: 2px; margin-right: 15px; }
    .col-img { flex: 0 0 90px; margin-right: 20px; }
    .col-res { flex: 0 0 120px; margin-right: 15px; }
    .col-hero { flex: 0 0 200px; margin-right: 15px; }
    .col-stat { flex: 0 0 100px; margin-right: 15px; }
    .col-info { flex: 0 0 120px; margin-right: 15px; }
    .col-action { flex-grow: 1; text-align: right; }
    .stat-desc { font-size: 0.7rem; color: #666; text-transform: uppercase; }
    .stat-num { font-size: 1.05rem; font-weight: 600; color: #fff; }
    .view-btn { background: #23272b; border: 1px solid #3d444b; color: #888; padding: 5px 15px; border-radius: 4px; font-size: 0.8rem; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_constants():
    h = requests.get(f"{OPENDOTA_API}/constants/heroes").json()
    return h

def get_d2pt_url(h_info):
    name = h_info.get("name", "").replace("npc_dota_hero_", "").replace("_", " ").title()
    return f"https://dota2protracker.com/hero/{name.replace(' ', '%20')}"

# --- 侧边栏 ---
with st.sidebar:
    account_id = st.text_input("Account ID", value="109799796")
    if 'mmr_base' not in st.session_state: st.session_state.mmr_base = 4500
    st.session_state.mmr_base = st.number_input("当前 MMR 基点:", value=st.session_state.mmr_base)
    if st.button("刷新数据"): st.cache_data.clear()

# --- 主逻辑 ---
heroes = get_constants()
if account_id:
    player = requests.get(f"{OPENDOTA_API}/players/{account_id}").json()
    matches = requests.get(f"{OPENDOTA_API}/players/{account_id}/recentMatches").json()
    
    if 'profile' in player:
        # 仪表盘计算
        win_c = sum(1 for m in matches if (m['player_slot'] < 128) == m['radiant_win'])
        net_c = (win_c - (len(matches)-win_c)) * 25
        
        # UI
        st.header(player['profile']['personaname'])
        c1, c2 = st.columns(2)
        c1.markdown(f'<div class="meta-card"><div class="meta-value">{st.session_state.mmr_base + net_c}</div><div class="meta-label">实时 MMR</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="meta-card"><div class="meta-value" style="color:{"#2ecc71" if net_c>=0 else "#e74c3c"}">{net_c}</div><div class="meta-label">积分变动</div></div>', unsafe_allow_html=True)
        
        st.divider()
        for m in matches[:15]:
            win = (m['player_slot'] < 128) == m['radiant_win']
            h_info = heroes.get(str(m['hero_id']), {})
            dt = datetime.fromtimestamp(m["start_time"], tz=pytz.UTC).astimezone(BEIJING_TZ)
            
            card = (
                f'<div class="match-row"><div class="{"win-bar" if win else "loss-bar"}"></div>'
                f'<div class="col-img"><a href="{get_d2pt_url(h_info)}" target="_blank"><img src="{DOTA_ASSET_URL + h_info.get("img","")}" style="width:85px; border-radius:4px;"></a></div>'
                f'<div class="col-res"><div class="stat-desc">结果</div><div class="{"win-text" if win else "loss-text"}">{"胜利" if win else "失败"}</div><div style="font-size:0.7rem; color:#888;">{dt.strftime("%m-%d %H:%M")}</div></div>'
                f'<div class="col-hero"><div class="stat-desc">英雄</div><div class="stat-num">{HERO_ID_CHINESE.get(str(m["hero_id"]), h_info.get("localized_name"))}</div></div>'
                f'<div class="col-stat"><div class="stat-desc">KDA</div><div class="stat-num">{m["kills"]}/{m["deaths"]}/{m["assists"]}</div></div>'
                f'<div class="col-info"><div class="stat-desc">时长 / ID</div><div class="stat-num" style="font-size:0.8rem;">{m["duration"]//60}m</div><div style="font-size:0.6rem; color:#555;">{m["match_id"]}</div></div>'
                f'<div class="col-action"><a href="https://www.opendota.com/matches/{m["match_id"]}" target="_blank" class="view-btn">详情</a></div></div>'
            )
            st.markdown(card, unsafe_allow_html=True)
