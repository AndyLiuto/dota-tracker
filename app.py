import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px
from constants import HERO_ID_CHINESE

# --- 页面配置 ---
st.set_page_config(page_title="Dota 2 Real-time Tracker", layout="wide", page_icon="⚔️")

# --- CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0b0d0f; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    .meta-card { background: #16191c; border: 1px solid #2d3238; border-radius: 6px; padding: 15px; text-align: center; height: 100%; }
    .meta-value { font-size: 1.8rem; font-weight: 800; color: #fff; }
    .meta-label { font-size: 0.7rem; color: #666; text-transform: uppercase; margin-top: 5px; }
    .match-row { background-color: #16191c; border: 1px solid #23272b; border-radius: 4px; padding: 12px; margin-bottom: 6px; display: flex; align-items: center; min-height: 95px; }
    .win-bar { flex: 0 0 4px; height: 65px; background-color: #2ecc71; border-radius: 2px; margin-right: 15px; }
    .loss-bar { flex: 0 0 4px; height: 65px; background-color: #e74c3c; border-radius: 2px; margin-right: 15px; }
    .col-hero-img { flex: 0 0 90px; margin-right: 20px; }
    .col-result { flex: 0 0 110px; margin-right: 15px; }
    .col-build { flex: 0 0 230px; margin-right: 15px; }
    .col-stats { flex: 0 0 95px; margin-right: 15px; }
    .col-spacer { flex-grow: 1; }
    .col-action { flex: 0 0 80px; text-align: right; }
    .item-icon { width: 38px; height: 28px; border-radius: 2px; border: 1px solid #333; background: #000; margin-right: 2px; }
    .stat-desc { font-size: 0.7rem; color: #666; text-transform: uppercase; white-space: nowrap; margin-bottom: 2px; }
    .stat-num { font-size: 1.05rem; font-weight: 600; color: #fff; white-space: nowrap; }
    .win-text { color: #2ecc71; font-weight: bold; }
    .loss-text { color: #e74c3c; font-weight: bold; }
    .view-btn { display: inline-block; background: #23272b; border: 1px solid #3d444b; color: #888; padding: 5px 15px; border-radius: 4px; font-size: 0.8rem; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# --- 常量 ---
OPENDOTA_API = "https://api.opendota.com/api"
DOTA_ASSET_URL = "https://cdn.cloudflare.steamstatic.com"

@st.cache_data(ttl=3600)
def get_constants():
    h = requests.get(f"{OPENDOTA_API}/constants/heroes").json()
    i = requests.get(f"{OPENDOTA_API}/constants/items").json()
    return h, i

def get_display_name(hid, h_info):
    cn_name = HERO_ID_CHINESE.get(str(hid), h_info.get("localized_name", "未知英雄"))
    raw = h_info.get("name", "")
    en = raw.replace("npc_dota_hero_", "").replace("_", " ").title()
    return f"{cn_name} ({en})" if cn_name != en else cn_name

# --- 初始化状态 ---
if 'base_mmr' not in st.session_state: st.session_state.base_mmr = 4500

heroes_const, items_const = get_constants()

# --- 侧边栏 ---
with st.sidebar:
    st.markdown("### 🔎 核心配置")
    account_id = st.text_input("Account ID", value="109799796")
    st.session_state.base_mmr = st.number_input("MMR 基点:", value=st.session_state.base_mmr)
    if st.button("清空缓存"): st.cache_data.clear()

# --- 主逻辑 ---
if account_id:
    player = requests.get(f"{OPENDOTA_API}/players/{account_id}").json()
    matches = requests.get(f"{OPENDOTA_API}/players/{account_id}/recentMatches").json()
    
    if 'profile' in player:
        profile = player['profile']
        win_c = sum(1 for m in matches if (m['player_slot'] < 128) == m['radiant_win'])
        net_c = (win_c - (len(matches)-win_c)) * 25
        
        # 头部
        c1, c2 = st.columns([1, 6])
        with c1: st.markdown(f'<img src="{profile["avatarfull"]}" style="width:90px; border-radius:8px;">', unsafe_allow_html=True)
        with c2: st.markdown(f'<h2>{profile["personaname"]}</h2>', unsafe_allow_html=True)
        
        # 仪表盘
        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="meta-card"><div class="meta-value">{st.session_state.base_mmr + net_c}</div><div class="meta-label">实时 MMR</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="meta-card"><div class="meta-value">{net_c}</div><div class="meta-label">净胜分</div></div>', unsafe_allow_html=True)
        
        st.divider()
        st.markdown("#### 最近实战")
        for m in matches[:15]:
            win = (m['player_slot'] < 128) == m['radiant_win']
            h_info = heroes_const.get(str(m['hero_id']), {})
            card = (
                f'<div class="match-row"><div class="{"win-bar" if win else "loss-bar"}"></div>'
                f'<div class="col-hero-img"><img src="{DOTA_ASSET_URL + h_info.get("img","")}" style="width:85px; border-radius:4px;"></div>'
                f'<div class="col-result"><div class="stat-desc">结果</div><div class="{"win-text" if win else "loss-text"}">{"胜利" if win else "失败"}</div></div>'
                f'<div class="col-build"><div class="stat-desc">英雄</div><div class="stat-num">{get_display_name(m["hero_id"], h_info)}</div></div>'
                f'<div class="col-stats"><div class="stat-desc">KDA</div><div class="stat-num">{m["kills"]}/{m["deaths"]}/{m["assists"]}</div></div>'
                f'<div class="col-action"><a href="https://www.opendota.com/matches/{m["match_id"]}" target="_blank" class="view-btn">详情</a></div></div>'
            )
            st.markdown(card, unsafe_allow_html=True)
    else: st.error("无法获取数据")
