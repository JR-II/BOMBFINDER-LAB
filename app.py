import hashlib
import os
import re
import textwrap
from html import escape
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import time
import tempfile
import json
import math
import shutil
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="BF Data", layout="wide")

# ------------------------------------------------------------------
# BF DATA VISUAL THEME ENGINE
# UI-only. Prediction, ranking, lineup, tracker, combo, lock, weather,
# history, and model calculations are not changed.
# ------------------------------------------------------------------
BF_THEME_OPTIONS = {
    "BF Classic": {
        "icon": "🔵",
        "description": "The original BF Data blue identity, cleaned up and preserved.",
        "mode": "dark",
        "bg": "#07101B",
        "bg_2": "#040912",
        "panel": "#0D1724",
        "panel_2": "#111D2C",
        "panel_3": "#152235",
        "text": "#F4F7FB",
        "muted": "#9EABC0",
        "accent": "#78AEFC",
        "accent_soft": "rgba(120,174,252,.085)",
        "accent_line": "rgba(120,174,252,.27)",
        "border": "rgba(145,174,216,.16)",
        "border_strong": "rgba(145,174,216,.27)",
        "shadow": "rgba(0,0,0,.22)",
        "field": "#06100C",
        "glow": "rgba(73,126,208,.085)",
    },
    "BF Night": {
        "icon": "⚫",
        "description": "True black night mode with calm neutral surfaces and restrained BF blue.",
        "mode": "dark",
        "bg": "#030405",
        "bg_2": "#07090C",
        "panel": "#0C0F13",
        "panel_2": "#11151A",
        "panel_3": "#171C22",
        "text": "#F5F7FA",
        "muted": "#A0A8B3",
        "accent": "#8CAFD6",
        "accent_soft": "rgba(140,175,214,.075)",
        "accent_line": "rgba(140,175,214,.24)",
        "border": "rgba(224,230,238,.105)",
        "border_strong": "rgba(224,230,238,.18)",
        "shadow": "rgba(0,0,0,.34)",
        "field": "#030A07",
        "glow": "rgba(140,175,214,.035)",
    },
    "BF White": {
        "icon": "⚪",
        "description": "Clean white workspace with crisp contrast and restrained professional blue.",
        "mode": "light",
        "bg": "#F2F4F7",
        "bg_2": "#FFFFFF",
        "panel": "#FFFFFF",
        "panel_2": "#F7F8FA",
        "panel_3": "#ECEFF3",
        "text": "#17202B",
        "muted": "#667180",
        "accent": "#356A9F",
        "accent_soft": "rgba(53,106,159,.07)",
        "accent_line": "rgba(53,106,159,.23)",
        "border": "rgba(30,44,60,.105)",
        "border_strong": "rgba(30,44,60,.18)",
        "shadow": "rgba(24,39,56,.09)",
        "field": "#EAF1EC",
        "glow": "rgba(53,106,159,.028)",
    },
    "BF Light": {
        "icon": "☀️",
        "description": "Soft off-white mode built to reduce glare during long daytime sessions.",
        "mode": "light",
        "bg": "#F4F1EB",
        "bg_2": "#FAF8F4",
        "panel": "#FFFEFC",
        "panel_2": "#F6F3EE",
        "panel_3": "#ECE8E1",
        "text": "#20252B",
        "muted": "#6D737A",
        "accent": "#557895",
        "accent_soft": "rgba(85,120,149,.065)",
        "accent_line": "rgba(85,120,149,.22)",
        "border": "rgba(53,59,65,.105)",
        "border_strong": "rgba(53,59,65,.18)",
        "shadow": "rgba(48,43,36,.075)",
        "field": "#E9EFE9",
        "glow": "rgba(85,120,149,.022)",
    },
}

if (
    "bf_visual_theme" not in st.session_state
    or st.session_state.bf_visual_theme not in BF_THEME_OPTIONS
):
    st.session_state.bf_visual_theme = "BF Classic"

with st.sidebar:
    st.markdown("### 🎨 Appearance")
    selected_theme = st.selectbox(
        "BF Data theme",
        options=list(BF_THEME_OPTIONS.keys()),
        index=list(BF_THEME_OPTIONS.keys()).index(st.session_state.bf_visual_theme),
        key="bf_theme_selector",
        help="Appearance only. Predictions, rankings, tracker results, and locks never change.",
    )
    st.session_state.bf_visual_theme = selected_theme
    _selected_theme_meta = BF_THEME_OPTIONS[selected_theme]
    st.caption(
        f"{_selected_theme_meta['icon']} "
        f"{_selected_theme_meta['description']}"
    )

BF_ACTIVE_THEME = BF_THEME_OPTIONS[st.session_state.bf_visual_theme]

st.markdown("""
<style>
:root {
    --bf-bg: #050608;
    --bf-panel: #0e1116;
    --bf-panel-2: #151922;
    --bf-border: rgba(255,255,255,0.10);
    --bf-border-strong: rgba(255,255,255,0.18);
    --bf-text: #f5f5f5;
    --bf-muted: #a8adb5;
    --bf-red: #ff5555;
    --bf-yellow: #ffd166;
    --bf-green: #35d07f;
}
.stApp { background: linear-gradient(180deg, #050608 0%, #090b10 54%, #050608 100%); color: var(--bf-text); }
.block-container { padding-top: .75rem; padding-bottom: 2rem; max-width: 1560px; }
[data-testid="stMetric"] { background: #10141b; border: 1px solid var(--bf-border); border-radius: 12px; padding: 7px 10px; box-shadow: none; }
[data-testid="stMetricLabel"] p { color: var(--bf-muted) !important; font-size: .76rem !important; }
[data-testid="stMetricValue"] { color: #fff !important; font-size: 1.12rem !important; font-weight: 850; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { background: #0f131a; border: 1px solid var(--bf-border); border-radius: 999px; padding: 7px 11px; }
.stTabs [aria-selected="true"] { background: #151922 !important; border-color: rgba(255,209,102,.65) !important; color: #ffffff !important; font-weight: 850; }
.bf-hero { border: 1px solid var(--bf-border-strong); border-radius: 18px; padding: 14px 16px; margin-bottom: 10px; background: #0f1319; box-shadow: none; }
.bf-kicker { color: var(--bf-yellow); font-size: .72rem; font-weight: 850; letter-spacing: .15em; text-transform: uppercase; }
.bf-title { font-size: clamp(1.45rem, 3vw, 2.85rem); font-weight: 950; line-height: 1; margin: 5px 0 5px 0; }
.bf-subtitle { color: var(--bf-muted); font-size: .9rem; max-width: 900px; }
.bf-key { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 6px; margin-top: 2px; margin-bottom: 3px; }
.bf-chip, .bf-key-chip { display: inline-flex; align-items: center; gap: 5px; border-radius: 999px; padding: 3px 8px; font-size: .72rem; font-weight: 800; border: 1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.035); color: #ececec; white-space: nowrap; }
.bf-chip-green, .bf-key-green { color: #bcffd6; border-color: rgba(53,208,127,.55); background: rgba(53,208,127,.09); }
.bf-chip-yellow, .bf-key-yellow { color: #ffe4a3; border-color: rgba(255,209,102,.55); background: rgba(255,209,102,.10); }
.bf-chip-red, .bf-key-red { color: #ffb8b8; border-color: rgba(255,85,85,.55); background: rgba(255,85,85,.09); }
.bf-chip-gray { color: #c4c8cf; border-color: rgba(255,255,255,.12); background: rgba(255,255,255,.04); }
.bf-mini-row { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; margin: 4px 0 5px 0; }
.bf-signal-line { font-size: .82rem; line-height: 1.3; margin: 3px 0 5px 0; color: #e9e9e9; }
.bf-signal-line strong { color: #ffffff; }
.bf-signal-value-green { color: var(--bf-green); font-weight: 900; }
.bf-signal-value-yellow { color: var(--bf-yellow); font-weight: 900; }
.bf-signal-value-red { color: var(--bf-red); font-weight: 900; }
.bf-bar-wrap { margin: 7px 0 9px 0; }
.bf-bar-head { display: flex; justify-content: space-between; gap: 8px; font-size: .78rem; font-weight: 850; color: #e8e8e8; margin-bottom: 4px; }
.bf-track { height: 8px; border-radius: 999px; overflow: hidden; background: #252a33; border: 1px solid rgba(255,255,255,.08); }
.bf-fill { height: 100%; border-radius: 999px; }
.bf-fill-green { background: var(--bf-green); }
.bf-fill-yellow { background: var(--bf-yellow); }
.bf-fill-red { background: var(--bf-red); }
div[data-testid="stDataFrame"] { border: 1px solid rgba(255,255,255,.12); border-radius: 14px; overflow:hidden; }
div[data-testid="stExpander"] { background: rgba(255,255,255,.018); border-radius: 12px; }
hr { margin-top: .38rem !important; margin-bottom: .38rem !important; }

.bf-quick-list { display: flex; flex-direction: column; gap: 6px; }
.bf-quick-row { display: grid; grid-template-columns: minmax(150px, 1.2fr) minmax(120px, .8fr) repeat(3, 58px); gap: 8px; align-items: center; padding: 8px 10px; border: 1px solid rgba(255,255,255,.10); background:#0d1118; border-radius: 11px; margin-bottom: 6px; }
.bf-quick-player { font-weight: 950; color:#f8fbff; font-size: .92rem; }
.bf-quick-sub { color:#95a0b2; font-size:.72rem; margin-top:2px; }
.bf-mini-score { text-align:center; border-radius:8px; padding:4px 5px; background:#111823; border:1px solid rgba(255,255,255,.09); }
.bf-mini-score b { display:block; color:#6da2ff; font-size:.58rem; letter-spacing:.08em; }
.bf-mini-score span { display:block; font-weight:950; font-size:.9rem; }

.bf-reason-strip { grid-column:1 / -1; margin-top:-1px; padding-top:3px; border-top:1px solid rgba(255,255,255,.06); color:#aeb9ca; font-size:.58rem; font-weight:800; line-height:1.2; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.bf-reason-strip b { color:#6da2ff; font-size:.52rem; letter-spacing:.04em; }
.bf-match-card { border:1px solid #263040; border-radius:14px; overflow:hidden; background:#080d14; margin:6px 0 10px 0; box-shadow:0 0 0 1px rgba(0,0,0,.35) inset; }
.bf-match-topline { display:grid; grid-template-columns:minmax(180px,1.2fr) minmax(170px,1fr) 70px 70px 70px; gap:0; align-items:stretch; background:#141b28; border-bottom:1px solid #2b3547; }
.bf-cell-head { padding:10px 12px; border-right:1px solid rgba(255,255,255,.08); }
.bf-head-label { color:#4e83ff; font-size:.62rem; font-weight:950; letter-spacing:.13em; text-transform:uppercase; }
.bf-head-main { color:#f7f9ff; font-size:1.02rem; font-weight:950; margin-top:5px; line-height:1.08; }
.bf-hand-badge { display:inline-flex; align-items:center; justify-content:center; margin-left:5px; padding:1px 4px; border-radius:4px; background:rgba(255,85,85,.22); color:#ff9d9d; border:1px solid rgba(255,85,85,.45); font-size:.58rem; font-weight:950; vertical-align:middle; }
.bf-score-box { display:flex; flex-direction:column; align-items:center; justify-content:center; border-right:1px solid rgba(255,255,255,.08); min-height:58px; }
.bf-score-box .lab { color:#4e83ff; font-size:.58rem; letter-spacing:.12em; font-weight:950; }
.bf-score-box .num { margin-top:5px; font-size:1.03rem; font-weight:950; padding:5px 9px; border-radius:7px; min-width:36px; text-align:center; }
.bf-num-green { color:#00f2a0; background:rgba(0,242,160,.12); border:1px solid rgba(0,242,160,.22); }
.bf-num-yellow { color:#ffd166; background:rgba(255,209,102,.15); border:1px solid rgba(255,209,102,.22); }
.bf-num-red { color:#ff6666; background:rgba(255,85,85,.14); border:1px solid rgba(255,85,85,.22); }
.bf-card-body { display:grid; grid-template-columns:210px 1fr; gap:16px; padding:12px; }
.bf-side-panel { border-right:1px solid rgba(255,255,255,.08); padding-right:12px; }
.bf-section-title { color:#7e9bd3; font-size:.62rem; font-weight:950; letter-spacing:.16em; text-transform:uppercase; margin:4px 0 9px 0; }
.bf-score-line { display:grid; grid-template-columns:1fr 48px; gap:8px; align-items:center; font-size:.78rem; margin-bottom:8px; color:#dfe8ff; }
.bf-pill-num { display:inline-flex; justify-content:center; align-items:center; padding:4px 7px; border-radius:7px; background:#141b25; font-weight:950; }
.bf-pitcher-stat { display:grid; grid-template-columns:1fr 58px; gap:8px; align-items:center; color:#dfe8ff; font-size:.78rem; margin-bottom:8px; }
.bf-arsenal-grid { display:grid; grid-template-columns:repeat(3,minmax(110px,1fr)); gap:8px; }
.bf-pitch-tile { background:#0e141d; border:1px solid #263040; border-radius:10px; padding:9px 10px; min-height:92px; }
.bf-pitch-name { color:#f0f5ff; font-weight:950; font-size:.7rem; text-transform:uppercase; }
.bf-pitch-score { font-weight:950; font-size:1.45rem; line-height:1; margin-top:6px; }
.bf-usage-label { color:#e8f1ff; font-size:.58rem; font-weight:950; margin-top:6px; text-transform:uppercase; }
.bf-usage-track { height:5px; background:#1e2632; border-radius:999px; overflow:hidden; margin-top:4px; }
.bf-usage-fill { height:100%; background:#3c82ff; border-radius:999px; }
.bf-pitch-note { color:#aab4c4; font-size:.66rem; line-height:1.25; margin-top:5px; }
.bf-bvp-title { margin-top:14px; border-top:1px solid rgba(255,255,255,.08); padding-top:10px; color:#7e9bd3; font-size:.62rem; font-weight:950; letter-spacing:.16em; text-transform:uppercase; }
.bf-bvp-grid { display:grid; grid-template-columns:repeat(6, minmax(78px,1fr)); gap:5px; margin-top:8px; }
.bf-bvp-cell { background:#0e141d; border:1px solid rgba(255,255,255,.08); border-radius:5px; padding:7px 8px; }
.bf-bvp-label { color:#c5d0e4; font-size:.58rem; font-weight:900; text-transform:uppercase; }
.bf-bvp-values { margin-top:5px; font-size:.77rem; font-weight:950; }
.bf-green-txt { color:#00f2a0; } .bf-red-txt { color:#ff6262; } .bf-yellow-txt { color:#ffd166; }
.bf-card-foot { padding:0 12px 12px 12px; color:#aab4c4; font-size:.72rem; line-height:1.35; }
@media(max-width: 900px){
  .bf-quick-row { grid-template-columns:1fr 1fr 46px 46px 46px; gap:5px; padding:7px; }
  .bf-quick-player { font-size:.82rem; }
  .bf-quick-sub { font-size:.65rem; }
  .bf-mini-score { padding:3px; }
  .bf-mini-score b { font-size:.48rem; }
  .bf-mini-score span { font-size:.74rem; }
  .bf-reason-strip { padding-top:2px; font-size:.50rem; }
  .bf-reason-strip b { font-size:.45rem; }
  .bf-match-topline { grid-template-columns:1fr 1fr 50px 50px 50px; }
  .bf-cell-head { padding:8px 7px; }
  .bf-head-label { font-size:.5rem; }
  .bf-head-main { font-size:.78rem; overflow-wrap:anywhere; }
  .bf-score-box .lab { font-size:.48rem; }
  .bf-score-box .num { font-size:.78rem; min-width:28px; padding:4px 5px; }
  .bf-card-body { grid-template-columns:1fr; gap:8px; padding:8px; }
  .bf-side-panel { border-right:0; border-bottom:1px solid rgba(255,255,255,.08); padding-right:0; padding-bottom:7px; }
  .bf-arsenal-grid { grid-template-columns:repeat(2,minmax(95px,1fr)); }
  .bf-bvp-grid { grid-template-columns:repeat(3, minmax(76px,1fr)); }
}

@media (max-width: 760px) {
    .block-container { padding-left: .65rem; padding-right: .65rem; padding-top: .35rem; }
    .bf-hero { padding: 10px 11px; border-radius: 14px; margin-bottom: 6px; }
    .bf-title { font-size: 1.45rem !important; letter-spacing: -0.02em; }
    .bf-subtitle { font-size: .76rem; line-height: 1.25; }
    .bf-kicker { font-size: .62rem; }
    .bf-chip, .bf-key-chip { font-size: .62rem; padding: 2px 6px; }
    .bf-mini-row { gap: 4px; margin: 2px 0 3px 0; }
    .bf-signal-line { font-size: .74rem; line-height: 1.22; margin: 1px 0 3px 0; }
    div[data-testid="stExpander"] summary { font-size: .82rem !important; }
    hr { margin-top: .25rem !important; margin-bottom: .25rem !important; }
}


/* BF DATA FIT-ONLY PATCH: matchup arsenal readability.
   Data, scoring, tracker, ranking, and platform logic untouched. */
.bf-match-card{
    max-width:100%;
    overflow:hidden;
}
.bf-card-body{
    min-width:0;
}
.bf-card-body > div,
.bf-side-panel,
.bf-arsenal-grid,
.bf-bvp-grid{
    min-width:0;
}
.bf-arsenal-grid{
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:6px !important;
}
.bf-pitch-tile{
    min-width:0 !important;
    min-height:78px !important;
    padding:7px 8px !important;
    overflow:hidden !important;
}
.bf-pitch-name{
    font-size:.58rem !important;
    line-height:1.05 !important;
    overflow-wrap:anywhere !important;
}
.bf-pitch-score{
    font-size:1.08rem !important;
    margin-top:4px !important;
}
.bf-usage-label{
    font-size:.48rem !important;
    margin-top:4px !important;
}
.bf-usage-track{
    height:4px !important;
    margin-top:3px !important;
}
.bf-pitch-note{
    font-size:.50rem !important;
    line-height:1.08 !important;
    margin-top:3px !important;
    overflow-wrap:anywhere !important;
}
@media(max-width: 1100px){
    .bf-card-body{
        grid-template-columns:180px 1fr !important;
        gap:10px !important;
        padding:9px !important;
    }
    .bf-side-panel{
        padding-right:9px !important;
    }
    .bf-arsenal-grid{
        grid-template-columns:repeat(3,minmax(0,1fr)) !important;
        gap:5px !important;
    }
    .bf-pitch-tile{
        padding:6px 7px !important;
        min-height:72px !important;
    }
    .bf-pitch-note{
        font-size:.48rem !important;
    }
}
@media(max-width: 900px){
    .bf-card-body{
        grid-template-columns:1fr !important;
        gap:8px !important;
        padding:8px !important;
    }
    .bf-side-panel{
        border-right:0 !important;
        border-bottom:1px solid rgba(255,255,255,.08) !important;
        padding-right:0 !important;
        padding-bottom:7px !important;
    }
    .bf-arsenal-grid{
        grid-template-columns:repeat(3,minmax(0,1fr)) !important;
        gap:5px !important;
    }
    .bf-pitch-tile{
        padding:6px !important;
        min-height:68px !important;
    }
    .bf-pitch-name{
        font-size:.52rem !important;
    }
    .bf-pitch-score{
        font-size:.98rem !important;
    }
    .bf-pitch-note{
        font-size:.46rem !important;
        line-height:1.05 !important;
    }
}
@media(max-width: 640px){
    .bf-match-topline{
        grid-template-columns:1fr 1fr 42px 42px 42px !important;
    }
    .bf-arsenal-grid{
        grid-template-columns:repeat(2,minmax(0,1fr)) !important;
        gap:5px !important;
    }
    .bf-pitch-tile{
        min-height:auto !important;
        padding:6px !important;
    }
    .bf-pitch-score{
        font-size:.92rem !important;
    }
    .bf-pitch-note{
        font-size:.44rem !important;
    }
}
@media(max-width: 390px){
    .bf-arsenal-grid{
        grid-template-columns:1fr !important;
    }
    .bf-pitch-note{
        font-size:.50rem !important;
    }
}


/* BF DATA REAL-STATS FIT PATCH: no clipping, responsive BVP, readable real arsenal tiles */
.bf-match-card{
    max-width:100% !important;
    overflow-x:auto !important;
    overflow-y:visible !important;
}
.bf-card-body{
    min-width:0 !important;
}
.bf-card-body > div,
.bf-side-panel,
.bf-arsenal-grid,
.bf-bvp-grid{
    min-width:0 !important;
}
.bf-arsenal-grid{
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:6px !important;
}
.bf-pitch-tile{
    min-width:0 !important;
    min-height:72px !important;
    padding:7px 8px !important;
    overflow:visible !important;
}
.bf-pitch-name{
    font-size:.58rem !important;
    line-height:1.05 !important;
    overflow-wrap:anywhere !important;
}
.bf-pitch-score{
    font-size:1.03rem !important;
    margin-top:4px !important;
    white-space:nowrap !important;
}
.bf-usage-label{
    font-size:.46rem !important;
    margin-top:4px !important;
}
.bf-pitch-note{
    font-size:.48rem !important;
    line-height:1.08 !important;
    margin-top:3px !important;
    overflow-wrap:anywhere !important;
}
.bf-bvp-grid{
    grid-template-columns:repeat(auto-fit,minmax(86px,1fr)) !important;
    gap:5px !important;
}
.bf-bvp-cell{
    min-width:0 !important;
    padding:6px 7px !important;
    overflow:visible !important;
}
.bf-bvp-label, .bf-bvp-values{
    overflow-wrap:anywhere !important;
}
@media(max-width:900px){
    .bf-arsenal-grid{grid-template-columns:repeat(3,minmax(0,1fr)) !important;}
    .bf-bvp-grid{grid-template-columns:repeat(3,minmax(0,1fr)) !important;}
}
@media(max-width:640px){
    .bf-arsenal-grid{grid-template-columns:repeat(2,minmax(0,1fr)) !important;}
    .bf-bvp-grid{grid-template-columns:repeat(2,minmax(0,1fr)) !important;}
}
@media(max-width:390px){
    .bf-arsenal-grid{grid-template-columns:1fr !important;}
    .bf-bvp-grid{grid-template-columns:1fr 1fr !important;}
}


/* BF DATA FINAL VISIBILITY PATCH: keep open matchup cards readable without touching data/scoring. */
.bf-match-card, .bf-match-card *{box-sizing:border-box;}
.bf-match-card{max-width:100% !important; overflow-x:auto !important; overflow-y:visible !important;}
.bf-card-body,.bf-card-body>div,.bf-side-panel,.bf-arsenal-grid,.bf-bvp-grid{min-width:0 !important;}
.bf-pitch-tile,.bf-bvp-cell{min-width:0 !important; overflow:visible !important;}
.bf-pitch-name,.bf-pitch-note,.bf-bvp-label,.bf-bvp-values{overflow-wrap:anywhere !important; word-break:normal !important;}
.bf-bvp-grid{grid-template-columns:repeat(auto-fit,minmax(82px,1fr)) !important;}
@media(max-width:640px){.bf-bvp-grid{grid-template-columns:repeat(2,minmax(0,1fr)) !important;}.bf-pitch-note{font-size:.46rem !important;}}


/* BF DATA V2 DECISION CARDS */
.bf-v2-card{border:1px solid rgba(255,255,255,.12);border-radius:14px;background:#0c1119;padding:10px 11px;margin:7px 0 8px}
.bf-v2-card.primary{border-color:rgba(53,208,127,.72)}
.bf-v2-card.strong{border-color:rgba(74,135,255,.62)}
.bf-v2-card.sleeper{border-color:rgba(195,107,255,.60)}
.bf-v2-card.early{border-color:rgba(255,209,102,.58);background:linear-gradient(90deg,#11151d,#0c1119)}
.bf-v2-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:start}
.bf-v2-name{font-weight:950;font-size:.98rem;line-height:1.08;color:#f7f9ff}
.bf-live-hr-badge{
    display:inline-flex;align-items:center;gap:4px;margin-left:6px;padding:2px 6px;
    border-radius:999px;font-size:.56rem;font-weight:950;vertical-align:middle;
    white-space:nowrap;border:1px solid rgba(255,255,255,.14);background:#151b25;color:#aeb8c8;
}
.bf-live-hr-badge.zero{color:#aeb8c8;border-color:rgba(174,184,200,.28);background:rgba(174,184,200,.06)}
.bf-live-hr-badge.hit{color:#59f0a2;border-color:rgba(53,208,127,.70);background:rgba(53,208,127,.13)}
.bf-live-hr-badge.multi{color:#ffd166;border-color:rgba(255,209,102,.75);background:rgba(255,209,102,.13)}
.bf-live-result-strip{
    margin:0;padding:7px 12px;border-bottom:1px solid rgba(255,255,255,.08);
    font-size:.72rem;font-weight:900;letter-spacing:.02em;
}
.bf-live-result-strip.zero{color:#8f9bad;background:rgba(255,255,255,.018)}
.bf-live-result-strip.hit{color:#35d07f;background:rgba(53,208,127,.07)}
.bf-live-result-strip.multi{color:#ffd166;background:rgba(255,209,102,.08)}
.bf-v2-meta{font-size:.68rem;color:#97a2b5;margin-top:3px}
.bf-v2-role-row{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-top:7px}
.bf-v2-role{display:inline-flex;align-items:center;border-radius:999px;padding:3px 8px;font-size:.61rem;font-weight:950;letter-spacing:.08em}
.bf-v2-role.primary{color:#61f1a3;border:1px solid #2bd17f;background:rgba(43,209,127,.10)}
.bf-v2-role.strong{color:#79a9ff;border:1px solid #4d85e6;background:rgba(77,133,230,.10)}
.bf-v2-role.alt{color:#d3d6dd;border:1px solid #747b88;background:rgba(116,123,136,.10)}
.bf-v2-role.sleeper{color:#d995ff;border:1px solid #9c57c6;background:rgba(156,87,198,.11)}
.bf-v2-role.early{color:#ffe08a;border:1px solid #d7a92c;background:rgba(215,169,44,.10)}
.bf-v2-grade{display:inline-flex;align-items:center;border-radius:7px;padding:3px 7px;font-weight:950;font-size:.76rem;background:#151b25;border:1px solid rgba(255,255,255,.13)}
.bf-v2-delta{font-size:.60rem;color:#929caf;font-weight:850}
.bf-v2-scores{display:grid;grid-template-columns:repeat(3,58px);gap:5px}
.bf-v2-score{background:#111824;border:1px solid rgba(255,255,255,.10);border-radius:9px;text-align:center;padding:4px}
.bf-v2-score b{display:block;color:#6d9cff;font-size:.50rem;letter-spacing:.10em}
.bf-v2-score span{display:block;font-size:.88rem;font-weight:950;margin-top:2px}
.bf-v2-badges{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px;color:#aeb8c8;font-size:.61rem;font-weight:800}
.bf-v2-why{margin-top:7px;padding-top:6px;border-top:1px solid rgba(255,255,255,.07);font-size:.64rem;color:#b8c1cf;line-height:1.3}
.bf-v2-why b{color:#75a6ff;letter-spacing:.07em;font-size:.56rem}
.bf-v2-advanced{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px;margin-top:7px}
.bf-v2-advanced>div{background:#101722;border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:5px;text-align:center}
.bf-v2-advanced small{display:block;color:#8090a8;font-size:.47rem;letter-spacing:.08em;font-weight:900}
.bf-v2-advanced strong{display:block;color:#f4f7fb;font-size:.74rem;margin-top:2px}
.bf-v2-confidence{margin-top:7px}
.bf-v2-confidence-head{display:flex;justify-content:space-between;font-size:.56rem;font-weight:900;color:#aeb8c8;margin-bottom:3px}
.bf-v2-confidence-track{height:5px;border-radius:999px;background:#202938;overflow:hidden}
.bf-v2-confidence-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#4f83ff,#35d07f)}
.bf-v2-attack-panel{margin-top:8px;padding:8px 9px;border:1px solid rgba(255,255,255,.10);border-radius:10px;background:linear-gradient(90deg,#101722,#0b1119)}
.bf-v2-attack-head{display:flex;justify-content:space-between;align-items:end;gap:8px}
.bf-v2-attack-kicker{font-size:.50rem;letter-spacing:.13em;font-weight:950;color:#8299bf}
.bf-v2-attack-label{font-size:.83rem;font-weight:950;margin-top:2px}
.bf-v2-attack-score{font-size:1.10rem;font-weight:950}
.bf-v2-attack-track{height:9px;border-radius:999px;background:#202938;overflow:hidden;margin-top:7px}
.bf-v2-attack-fill{height:100%;border-radius:999px}
.bf-v2-signal-grid{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:7px}
.bf-v2-signal{border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:5px 7px;color:#aeb8c8;font-size:.55rem;line-height:1.25}
.bf-v2-signal b{display:block;font-size:.46rem;letter-spacing:.10em;margin-bottom:2px}
.bf-v2-signal.green b{color:#35d07f}.bf-v2-signal.red b{color:#ff6666}
.bf-v2-compare{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;margin-top:7px}
.bf-v2-compare>div{background:#101722;border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:6px;text-align:center}
.bf-v2-compare small{display:block;color:#7f90aa;font-size:.45rem;letter-spacing:.08em;font-weight:950}
.bf-v2-compare strong{display:block;color:#f4f7fb;font-size:.78rem;margin-top:3px}
.bf-v2-pair{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center;margin-top:7px;padding:7px 8px;border:1px solid rgba(105,167,255,.32);border-radius:9px;background:rgba(105,167,255,.055)}
.bf-v2-pair small{display:block;color:#75a6ff;font-size:.47rem;letter-spacing:.10em;font-weight:950}
.bf-v2-pair strong{display:block;color:#f5f7fb;font-size:.71rem;margin-top:2px}
.bf-v2-pair-score{font-size:.93rem;font-weight:950;color:#8fc0ff;white-space:nowrap}
.bf-v2-rankline{display:flex;flex-wrap:wrap;gap:5px;margin-top:5px}
.bf-v2-rankchip{border:1px solid rgba(255,255,255,.10);border-radius:999px;padding:2px 6px;color:#aeb8c8;font-size:.50rem;font-weight:900}
.bf-v2-rankchip.primary{color:#61f1a3;border-color:rgba(53,208,127,.45)}
@media(max-width:640px){.bf-v2-compare{grid-template-columns:repeat(2,minmax(0,1fr))}.bf-v2-pair{grid-template-columns:1fr}.bf-v2-pair-score{font-size:.78rem}}
.bf-v2-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.bf-v2-expand-summary{margin:5px 0 8px;padding:7px 8px;border:1px solid rgba(255,255,255,.09);border-radius:9px;background:#0e141e}
@media(max-width:900px){.bf-v2-grid{grid-template-columns:1fr}}
@media(max-width:640px){
.bf-v2-card{padding:8px 9px;margin:6px 0}.bf-v2-name{font-size:.86rem}.bf-v2-meta{font-size:.59rem}
.bf-live-hr-badge{font-size:.49rem;padding:2px 5px;margin-left:4px}
.bf-live-result-strip{font-size:.62rem;padding:6px 8px}
.bf-v2-scores{grid-template-columns:repeat(3,48px)}.bf-v2-score span{font-size:.76rem}.bf-v2-score b{font-size:.43rem}
.bf-v2-role{font-size:.52rem;padding:2px 6px}.bf-v2-grade{font-size:.66rem;padding:2px 6px}
.bf-v2-badges{font-size:.53rem}.bf-v2-why{font-size:.56rem}.bf-v2-advanced{gap:3px}
.bf-v2-advanced small{font-size:.39rem}.bf-v2-advanced strong{font-size:.62rem}}


/* BF DATA 10/10 LAB POLISH */
.bf-scout-panel{border:1px solid rgba(105,167,255,.45);border-radius:13px;background:linear-gradient(135deg,#101826,#0b1018);padding:10px 11px;margin:8px 0 12px}
.bf-scout-title{color:#75a6ff;font-size:.62rem;font-weight:950;letter-spacing:.14em}
.bf-scout-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin-top:8px}
.bf-scout-grid>div{background:#0d131d;border:1px solid rgba(255,255,255,.08);border-radius:9px;padding:8px}
.bf-scout-grid small{display:block;color:#8190a7;font-size:.48rem;font-weight:950;letter-spacing:.09em}
.bf-scout-grid strong{display:block;color:#f4f7fb;font-size:.82rem;margin-top:4px}
.bf-scout-grid span{display:block;color:#aeb8c8;font-size:.58rem;margin-top:3px}
.bf-scout-note{color:#8290a4;font-size:.55rem;margin-top:7px}
.bf-v2-card{transition:border-color .15s ease,transform .15s ease}
.bf-v2-card:hover{transform:translateY(-1px);border-color:rgba(105,167,255,.55)}
.bf-v2-why{min-height:31px}
@media(max-width:760px){
  .bf-scout-grid{grid-template-columns:1fr}
  .bf-scout-panel{padding:8px}
  .bf-v2-advanced{grid-template-columns:repeat(5,minmax(42px,1fr))}
  .bf-v2-card{border-radius:11px}
}


/* BF DATA FIRST-BOARD CALIBRATION + READABILITY */
.bf-v2-verdict{
    display:flex;
    align-items:center;
    gap:8px;
    margin-top:7px;
    padding:6px 8px;
    border:1px solid;
    border-radius:8px;
    background:rgba(255,255,255,.018);
}
.bf-v2-verdict strong{
    font-size:.57rem;
    letter-spacing:.08em;
    white-space:nowrap;
}
.bf-v2-verdict span{
    color:#aeb8c8;
    font-size:.58rem;
    line-height:1.2;
}
.bf-v2-card .bf-v2-advanced strong{font-size:.78rem}
.bf-v2-card .bf-v2-confidence{margin-top:6px}
.bf-v2-card .bf-v2-why{min-height:0}
@media(max-width:640px){
    .bf-v2-verdict{display:block;padding:6px}
    .bf-v2-verdict strong{display:block;margin-bottom:3px}
    .bf-v2-verdict span{font-size:.52rem}
}


/* BF DATA GUIDE */
.bf-guide-quick{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin:7px 0 10px}
.bf-guide-quick>div,.bf-guide-card{border:1px solid rgba(255,255,255,.09);border-radius:9px;background:#0e141d;padding:7px 8px}
.bf-guide-quick small{display:block;color:#759de8;font-size:.49rem;font-weight:950;letter-spacing:.09em}
.bf-guide-quick strong{display:block;color:#f4f7fb;font-size:.77rem;margin-top:3px}
.bf-guide-quick span{display:block;color:#9ca8ba;font-size:.55rem;line-height:1.2;margin-top:3px}
.bf-guide-panel{border:1px solid rgba(105,167,255,.32);background:linear-gradient(135deg,#101722,#0a0f17);border-radius:13px;padding:11px 12px;margin:8px 0 11px}
.bf-guide-title{color:#75a6ff;font-size:.65rem;font-weight:950;letter-spacing:.14em}
.bf-guide-sub{color:#aab4c4;font-size:.69rem;line-height:1.35;margin-top:5px}
.bf-guide-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin-top:9px}
.bf-guide-card h4{margin:0 0 5px;font-size:.77rem;color:#f5f7fb}.bf-guide-card p{margin:0;color:#aab4c4;font-size:.63rem;line-height:1.35}
.bf-color-key{display:flex;flex-wrap:wrap;gap:6px;margin:7px 0}.bf-color-key span{border:1px solid rgba(255,255,255,.11);border-radius:999px;padding:4px 8px;font-size:.61rem;font-weight:900}
.bf-guide-table{display:grid;grid-template-columns:180px 1fr;border:1px solid rgba(255,255,255,.09);border-radius:10px;overflow:hidden}
.bf-guide-table>div{padding:7px 9px;border-bottom:1px solid rgba(255,255,255,.07);color:#aeb8c8;font-size:.65rem;line-height:1.3}
.bf-guide-table>div:nth-child(odd){color:#f2f5fa;font-weight:900;background:#101722}.bf-guide-table>div:nth-last-child(-n+2){border-bottom:0}
.bf-onboard{border:1px solid rgba(255,209,102,.45);border-radius:12px;background:rgba(255,209,102,.07);padding:10px 11px;margin:7px 0 10px}
.bf-onboard strong{color:#ffd166}.bf-onboard p{margin:4px 0 0;color:#b8c1cf;font-size:.68rem;line-height:1.35}
@media(max-width:900px){.bf-guide-quick{grid-template-columns:repeat(2,minmax(0,1fr))}.bf-guide-grid{grid-template-columns:1fr}}
@media(max-width:640px){.bf-guide-table{grid-template-columns:115px 1fr}.bf-guide-table>div{padding:6px;font-size:.57rem}}


/* ================================================================
   BF DATA RESPONSIVE FIT PATCH
   UI-only: no prediction, lineup, tracker, combo, lock, or history logic changed.
   Designed for comfortable use at browser zoom 100% on desktop and iPhone.
   ================================================================ */

/* Use more of the available desktop viewport without stretching cards excessively. */
.block-container{
    width:min(96vw, 1720px) !important;
    max-width:1720px !important;
    padding-left:clamp(.70rem,1.25vw,1.25rem) !important;
    padding-right:clamp(.70rem,1.25vw,1.25rem) !important;
    padding-top:.45rem !important;
}

/* Keep the app navigation on one compact, horizontally-scrollable line. */
.stTabs [data-baseweb="tab-list"]{
    gap:2px !important;
    overflow-x:auto !important;
    overflow-y:hidden !important;
    flex-wrap:nowrap !important;
    scrollbar-width:thin;
    padding-bottom:2px;
}
.stTabs [data-baseweb="tab"]{
    flex:0 0 auto !important;
    padding:5px 8px !important;
    min-height:30px !important;
    border-radius:7px !important;
}
.stTabs [data-baseweb="tab"] p{
    font-size:.70rem !important;
    white-space:nowrap !important;
}

/* More compact page headings and Streamlit spacing. */
h1{font-size:1.65rem !important;margin:.35rem 0 .45rem !important}
h2{font-size:1.30rem !important;margin:.35rem 0 .40rem !important}
h3{font-size:1.05rem !important;margin:.28rem 0 .34rem !important}
[data-testid="stVerticalBlock"]{gap:.52rem !important}
[data-testid="stHorizontalBlock"]{gap:.65rem !important}
div[data-testid="stExpander"] summary{
    min-height:35px !important;
    padding:.35rem .65rem !important;
    font-size:.76rem !important;
}

/* Desktop decision cards: same information, tighter vertical rhythm. */
.bf-v2-grid{gap:7px !important}
.bf-v2-card{
    padding:8px 9px !important;
    margin:5px 0 6px !important;
    border-radius:11px !important;
}
.bf-v2-head{gap:6px !important}
.bf-v2-name{font-size:.88rem !important}
.bf-v2-meta{font-size:.58rem !important;margin-top:2px !important}
.bf-v2-role-row{gap:4px !important;margin-top:5px !important}
.bf-v2-role{font-size:.50rem !important;padding:2px 6px !important}
.bf-v2-grade{font-size:.64rem !important;padding:2px 6px !important}
.bf-v2-delta{font-size:.50rem !important}
.bf-v2-scores{grid-template-columns:repeat(3,52px) !important;gap:4px !important}
.bf-v2-score{padding:3px !important;border-radius:7px !important}
.bf-v2-score b{font-size:.42rem !important}
.bf-v2-score span{font-size:.76rem !important}
.bf-v2-rankline{gap:4px !important;margin-top:4px !important}
.bf-v2-rankchip{font-size:.43rem !important;padding:2px 5px !important}
.bf-v2-badges{gap:4px !important;margin-top:5px !important;font-size:.51rem !important}
.bf-v2-attack-panel{
    margin-top:6px !important;
    padding:6px 7px !important;
    border-radius:8px !important;
}
.bf-v2-attack-kicker{font-size:.43rem !important}
.bf-v2-attack-label{font-size:.69rem !important}
.bf-v2-attack-score{font-size:.90rem !important}
.bf-v2-attack-track{height:7px !important;margin-top:5px !important}
.bf-v2-signal-grid{gap:4px !important;margin-top:5px !important}
.bf-v2-signal{padding:4px 6px !important;font-size:.47rem !important}
.bf-v2-signal b{font-size:.39rem !important}
.bf-v2-verdict{
    margin-top:5px !important;
    padding:4px 6px !important;
    gap:6px !important;
}
.bf-v2-verdict strong{font-size:.48rem !important}
.bf-v2-verdict span{font-size:.49rem !important}
.bf-v2-compare{gap:4px !important;margin-top:5px !important}
.bf-v2-compare>div{padding:4px !important;border-radius:7px !important}
.bf-v2-compare small{font-size:.38rem !important}
.bf-v2-compare strong{font-size:.67rem !important;margin-top:2px !important}
.bf-v2-pair{
    margin-top:5px !important;
    padding:5px 6px !important;
    border-radius:7px !important;
}
.bf-v2-pair small{font-size:.39rem !important}
.bf-v2-pair strong{font-size:.61rem !important}
.bf-v2-pair-score{font-size:.79rem !important}
.bf-v2-confidence{margin-top:5px !important}
.bf-v2-confidence-head{font-size:.47rem !important;margin-bottom:2px !important}
.bf-v2-confidence-track{height:4px !important}
.bf-v2-why{
    margin-top:5px !important;
    padding-top:4px !important;
    font-size:.52rem !important;
    line-height:1.22 !important;
}
.bf-v2-why b{font-size:.44rem !important}

/* Compact expanded matchup card on normal laptop/desktop screens. */
.bf-match-card{margin:4px 0 7px !important;border-radius:11px !important}
.bf-match-topline{
    grid-template-columns:minmax(145px,1.1fr) minmax(135px,.95fr) 54px 54px 54px !important;
}
.bf-cell-head{padding:7px 8px !important}
.bf-head-label{font-size:.49rem !important}
.bf-head-main{font-size:.82rem !important;margin-top:3px !important}
.bf-score-box{min-height:48px !important}
.bf-score-box .lab{font-size:.46rem !important}
.bf-score-box .num{font-size:.80rem !important;padding:4px 6px !important}
.bf-live-result-strip{padding:5px 9px !important;font-size:.60rem !important}
.bf-card-body{
    grid-template-columns:165px minmax(0,1fr) !important;
    gap:9px !important;
    padding:8px !important;
}
.bf-side-panel{padding-right:8px !important}
.bf-section-title{font-size:.50rem !important;margin:3px 0 6px !important}
.bf-score-line,.bf-pitcher-stat{
    font-size:.63rem !important;
    margin-bottom:5px !important;
}
.bf-pill-num{padding:3px 5px !important}
.bf-arsenal-grid{gap:4px !important}
.bf-pitch-tile{padding:5px 6px !important;min-height:62px !important}
.bf-pitch-name{font-size:.49rem !important}
.bf-pitch-score{font-size:.88rem !important}
.bf-pitch-note{font-size:.41rem !important}
.bf-bvp-title{margin-top:8px !important;padding-top:7px !important;font-size:.49rem !important}
.bf-bvp-grid{gap:4px !important;margin-top:5px !important}
.bf-bvp-cell{padding:5px 6px !important}
.bf-bvp-label{font-size:.47rem !important}
.bf-bvp-values{font-size:.64rem !important;margin-top:3px !important}
.bf-card-foot{padding:0 8px 8px !important;font-size:.57rem !important}

/* Laptop widths: retain two cards per row, but reduce unused margins. */
@media (min-width:901px) and (max-width:1450px){
    .block-container{
        width:98vw !important;
        padding-left:.55rem !important;
        padding-right:.55rem !important;
    }
    .bf-v2-grid{grid-template-columns:repeat(2,minmax(0,1fr)) !important}
}

/* Tablet / narrow browser: one clean card column. */
@media (max-width:900px){
    .block-container{
        width:100% !important;
        max-width:none !important;
        padding-left:.50rem !important;
        padding-right:.50rem !important;
    }
    .bf-v2-grid{grid-template-columns:1fr !important}
    .bf-card-body{grid-template-columns:1fr !important}
}

/* iPhone/mobile: deliberately compact, no forced desktop-width elements. */
@media (max-width:640px){
    html,body,.stApp{font-size:14px !important}
    .block-container{
        padding:.25rem .38rem 1.2rem !important;
        width:100% !important;
    }
    h1{font-size:1.28rem !important}
    h2{font-size:1.08rem !important}
    h3{font-size:.92rem !important}

    .bf-hero{padding:7px 8px !important;margin-bottom:4px !important;border-radius:10px !important}
    .bf-title{font-size:1.18rem !important}
    .bf-subtitle{font-size:.64rem !important}
    .bf-kicker{font-size:.50rem !important}

    .stTabs [data-baseweb="tab-list"]{gap:1px !important}
    .stTabs [data-baseweb="tab"]{padding:4px 6px !important;min-height:27px !important}
    .stTabs [data-baseweb="tab"] p{font-size:.59rem !important}

    [data-testid="stVerticalBlock"]{gap:.36rem !important}
    [data-testid="stHorizontalBlock"]{gap:.35rem !important}

    .bf-v2-card{padding:6px 7px !important;margin:4px 0 5px !important;border-radius:9px !important}
    .bf-v2-name{font-size:.78rem !important}
    .bf-v2-head{grid-template-columns:minmax(0,1fr) auto !important;gap:4px !important}
    .bf-v2-scores{grid-template-columns:repeat(3,43px) !important}
    .bf-v2-score span{font-size:.66rem !important}
    .bf-v2-score b{font-size:.35rem !important}
    .bf-v2-role-row{margin-top:4px !important}
    .bf-v2-role{font-size:.45rem !important}
    .bf-v2-meta{font-size:.51rem !important}
    .bf-v2-rankchip{font-size:.38rem !important}
    .bf-v2-badges{font-size:.45rem !important}
    .bf-v2-attack-panel{padding:5px 6px !important}
    .bf-v2-attack-label{font-size:.61rem !important}
    .bf-v2-attack-score{font-size:.78rem !important}
    .bf-v2-signal-grid{grid-template-columns:1fr 1fr !important}
    .bf-v2-signal{font-size:.42rem !important;padding:3px 4px !important}
    .bf-v2-verdict span{font-size:.44rem !important}
    .bf-v2-compare{grid-template-columns:repeat(4,minmax(0,1fr)) !important}
    .bf-v2-compare>div{padding:3px 2px !important}
    .bf-v2-compare small{font-size:.31rem !important}
    .bf-v2-compare strong{font-size:.58rem !important}
    .bf-v2-pair{
        grid-template-columns:1fr auto !important;
        padding:4px 5px !important;
    }
    .bf-v2-pair strong{font-size:.54rem !important}
    .bf-v2-pair-score{font-size:.68rem !important}
    .bf-v2-why{font-size:.45rem !important}

    div[data-testid="stExpander"] summary{
        min-height:31px !important;
        padding:.28rem .48rem !important;
        font-size:.67rem !important;
    }

    .bf-match-topline{
        grid-template-columns:minmax(92px,1fr) minmax(88px,1fr) 37px 37px 37px !important;
    }
    .bf-cell-head{padding:5px 4px !important}
    .bf-head-label{font-size:.39rem !important}
    .bf-head-main{font-size:.65rem !important}
    .bf-score-box .lab{font-size:.35rem !important}
    .bf-score-box .num{font-size:.62rem !important;padding:3px !important;min-width:24px !important}
    .bf-card-body{padding:6px !important;gap:6px !important}
    .bf-arsenal-grid{grid-template-columns:repeat(2,minmax(0,1fr)) !important}
    .bf-bvp-grid{grid-template-columns:repeat(3,minmax(0,1fr)) !important}
    .bf-pitch-tile{padding:4px !important}
    .bf-pitch-note{font-size:.39rem !important}
    .bf-card-foot{font-size:.50rem !important;padding:0 6px 6px !important}

    /* Prevent wide tables/cards from forcing the whole mobile page wider. */
    .bf-match-card,.bf-v2-card,.bf-weather-card,
    div[data-testid="stDataFrame"]{
        max-width:100% !important;
    }
}

/* Very small iPhones. */
@media (max-width:390px){
    .block-container{padding-left:.28rem !important;padding-right:.28rem !important}
    .bf-v2-scores{grid-template-columns:repeat(3,39px) !important}
    .bf-v2-compare small{letter-spacing:.03em !important}
    .bf-bvp-grid{grid-template-columns:repeat(2,minmax(0,1fr)) !important}
}

/* BF DATA COMPACT SCAN CARDS — UI only */
.bf-scan-card{border:1px solid rgba(255,255,255,.12);border-radius:10px;background:#0c1119;padding:7px 8px;margin:4px 0 5px}
.bf-scan-card.primary{border-color:rgba(53,208,127,.72)}
.bf-scan-card.strong{border-color:rgba(74,135,255,.62)}
.bf-scan-card.sleeper{border-color:rgba(195,107,255,.60)}
.bf-scan-card.early{border-color:rgba(255,209,102,.58)}
.bf-scan-top{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px;align-items:center}
.bf-scan-name{color:#f7f9ff;font-size:.84rem;font-weight:950;line-height:1.05}
.bf-scan-matchup{margin-top:2px;color:#96a2b4;font-size:.52rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bf-scan-actions{display:grid;grid-template-columns:repeat(3,48px);gap:4px}
.bf-scan-action{background:#111824;border:1px solid rgba(255,255,255,.09);border-radius:7px;text-align:center;padding:3px 2px}
.bf-scan-action small{display:block;color:#6d9cff;font-size:.36rem;font-weight:950;letter-spacing:.08em}
.bf-scan-action strong{display:block;color:#f5f7fb;font-size:.68rem;font-weight:950;margin-top:1px}
.bf-scan-roleline{display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-top:4px}
.bf-scan-role{border-radius:999px;padding:2px 6px;font-size:.42rem;font-weight:950;letter-spacing:.06em}
.bf-scan-role.primary{color:#61f1a3;border:1px solid #2bd17f;background:rgba(43,209,127,.10)}
.bf-scan-role.strong{color:#79a9ff;border:1px solid #4d85e6;background:rgba(77,133,230,.10)}
.bf-scan-role.alt{color:#d3d6dd;border:1px solid #747b88;background:rgba(116,123,136,.10)}
.bf-scan-role.sleeper{color:#d995ff;border:1px solid #9c57c6;background:rgba(156,87,198,.11)}
.bf-scan-grade{color:#f2f5fa;border:1px solid rgba(255,255,255,.12);border-radius:6px;padding:2px 5px;font-size:.48rem;font-weight:950}
.bf-scan-confidence{color:#aeb8c8;font-size:.45rem;font-weight:900}
.bf-scan-rank{color:#9ba7b8;font-size:.41rem;font-weight:850}
.bf-scan-attack{display:grid;grid-template-columns:auto minmax(70px,1fr) auto;gap:6px;align-items:center;margin-top:5px}
.bf-scan-attack-label{font-size:.45rem;font-weight:950;white-space:nowrap}
.bf-scan-track{height:5px;border-radius:999px;overflow:hidden;background:#202938}
.bf-scan-fill{height:100%;border-radius:999px}
.bf-scan-attack-score{font-size:.55rem;font-weight:950;white-space:nowrap}
.bf-scan-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;margin-top:5px}
.bf-scan-metric{background:#101722;border:1px solid rgba(255,255,255,.07);border-radius:6px;padding:3px 4px;text-align:center}
.bf-scan-metric small{display:block;color:#7f90aa;font-size:.31rem;letter-spacing:.06em;font-weight:950}
.bf-scan-metric strong{display:block;color:#f4f7fb;font-size:.59rem;margin-top:1px}
.bf-scan-bottom{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px;align-items:center;margin-top:5px;padding-top:4px;border-top:1px solid rgba(255,255,255,.06)}
.bf-scan-pair{color:#b8c2d0;font-size:.45rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bf-scan-pair b{color:#75a6ff}
.bf-scan-pair-score{color:#8fc0ff;font-size:.58rem;font-weight:950;white-space:nowrap}
div[data-testid="stExpander"] summary{min-height:29px !important;padding:.24rem .52rem !important}
@media(max-width:640px){
 .bf-scan-card{padding:6px;border-radius:8px;margin:3px 0 4px}
 .bf-scan-name{font-size:.75rem}.bf-scan-matchup{font-size:.46rem}
 .bf-scan-actions{grid-template-columns:repeat(3,42px);gap:3px}
 .bf-scan-action small{font-size:.31rem}.bf-scan-action strong{font-size:.60rem}
 .bf-scan-role{font-size:.37rem;padding:2px 5px}
 .bf-scan-grade,.bf-scan-confidence,.bf-scan-rank{font-size:.39rem}
 .bf-scan-attack{gap:4px;margin-top:4px}.bf-scan-attack-label{font-size:.39rem}.bf-scan-attack-score{font-size:.48rem}
 .bf-scan-metrics{gap:3px;margin-top:4px}.bf-scan-metric{padding:3px 2px}
 .bf-scan-metric small{font-size:.27rem}.bf-scan-metric strong{font-size:.53rem}
 .bf-scan-bottom{margin-top:4px;padding-top:3px}.bf-scan-pair{font-size:.40rem}.bf-scan-pair-score{font-size:.50rem}
}

/* ================================================================
   BF DATA COMPACT CARD READABILITY + SIGNAL BADGES
   UI-only. Ranking/model/tracker/lock/combo logic is unchanged.
   ================================================================ */
.bf-scan-name{font-size:.95rem !important}
.bf-scan-matchup{font-size:.62rem !important}
.bf-scan-role{font-size:.52rem !important;padding:3px 7px !important}
.bf-scan-grade{font-size:.58rem !important;padding:3px 6px !important}
.bf-scan-confidence{font-size:.55rem !important}
.bf-scan-rank{
    display:inline-flex !important;
    align-items:center;
    gap:3px;
    color:#b7c3d5 !important;
    font-size:.52rem !important;
    font-weight:900 !important;
}
.bf-scan-actions{grid-template-columns:repeat(3,54px) !important}
.bf-scan-action small{font-size:.43rem !important}
.bf-scan-action strong{font-size:.78rem !important}
.bf-scan-attack-label{font-size:.55rem !important}
.bf-scan-attack-score{font-size:.63rem !important}
.bf-scan-metric small{font-size:.39rem !important}
.bf-scan-metric strong{font-size:.68rem !important}
.bf-scan-pair{font-size:.54rem !important}
.bf-scan-pair-score{font-size:.66rem !important}

.bf-scan-badges{
    display:flex;
    flex-wrap:wrap;
    gap:4px;
    margin-top:5px;
}
.bf-scan-badge{
    display:inline-flex;
    align-items:center;
    border:1px solid rgba(255,255,255,.11);
    border-radius:999px;
    padding:3px 7px;
    background:#111824;
    color:#d7deea;
    font-size:.48rem;
    font-weight:900;
    white-space:nowrap;
}
.bf-scan-badge.good{
    color:#73efad;
    border-color:rgba(53,208,127,.42);
    background:rgba(53,208,127,.08);
}
.bf-scan-badge.weather{
    color:#8fc0ff;
    border-color:rgba(105,167,255,.42);
    background:rgba(105,167,255,.08);
}
.bf-scan-badge.hot{
    color:#ffd166;
    border-color:rgba(255,209,102,.42);
    background:rgba(255,209,102,.08);
}
.bf-research-signals{
    display:flex;
    flex-wrap:wrap;
    gap:6px;
    margin:2px 0 8px;
    padding:7px 8px;
    border:1px solid rgba(105,167,255,.25);
    border-radius:9px;
    background:#0d141f;
}
.bf-research-signals .label{
    width:100%;
    color:#75a6ff;
    font-size:.58rem;
    font-weight:950;
    letter-spacing:.10em;
}
.bf-research-signals .signal{
    border:1px solid rgba(255,255,255,.10);
    border-radius:999px;
    padding:4px 8px;
    color:#d7deea;
    background:#111824;
    font-size:.58rem;
    font-weight:900;
}
.bf-rank-help{
    color:#8f9bad;
    font-size:.55rem;
    line-height:1.3;
    margin-top:4px;
}

@media(max-width:640px){
    .bf-scan-name{font-size:.84rem !important}
    .bf-scan-matchup{font-size:.55rem !important}
    .bf-scan-role{font-size:.45rem !important;padding:2px 6px !important}
    .bf-scan-grade{font-size:.49rem !important}
    .bf-scan-confidence,.bf-scan-rank{font-size:.45rem !important}
    .bf-scan-actions{grid-template-columns:repeat(3,45px) !important}
    .bf-scan-action small{font-size:.35rem !important}
    .bf-scan-action strong{font-size:.66rem !important}
    .bf-scan-badge{font-size:.42rem !important;padding:2px 6px !important}
    .bf-scan-metric small{font-size:.32rem !important}
    .bf-scan-metric strong{font-size:.58rem !important}
    .bf-scan-pair{font-size:.45rem !important}
    .bf-research-signals .signal{font-size:.49rem !important;padding:3px 6px !important}
}

/* ================================================================
   BF DATA PRO PLATFORM POLISH
   Visual/UX only — no prediction, tracker, combo, lineup, lock,
   ranking, probability, or historical-storage logic is changed.
   ================================================================ */
:root{
    --bf-bg:#07101b;
    --bf-bg-deep:#040912;
    --bf-surface:#0d1724;
    --bf-surface-2:#111d2c;
    --bf-surface-3:#152235;
    --bf-line:rgba(145,174,216,.17);
    --bf-line-strong:rgba(145,174,216,.28);
    --bf-blue:#78aefc;
    --bf-blue-bright:#9bc5ff;
    --bf-text:#f4f7fb;
    --bf-muted:#9eabc0;
    --bf-green:#35d07f;
    --bf-yellow:#ffd166;
    --bf-red:#ff6b6b;
}
.stApp{
    background:
      radial-gradient(circle at 12% 0%,rgba(73,126,208,.12),transparent 28rem),
      linear-gradient(180deg,var(--bf-bg-deep) 0%,var(--bf-bg) 48%,#050b13 100%) !important;
}
.block-container{padding-top:.38rem !important}
header[data-testid="stHeader"]{background:rgba(6,12,21,.94) !important;border-bottom:1px solid rgba(145,174,216,.10)}
#MainMenu{visibility:hidden}

/* Premium hero/header */
.bf-hero{
    background:
      linear-gradient(135deg,rgba(18,35,56,.98),rgba(9,18,30,.98)) !important;
    border:1px solid rgba(120,174,252,.28) !important;
    border-radius:15px !important;
    box-shadow:0 14px 36px rgba(0,0,0,.24),inset 0 1px 0 rgba(255,255,255,.025) !important;
    padding:12px 15px !important;
}
.bf-kicker{color:var(--bf-blue-bright) !important}
.bf-title{
    color:#f7faff !important;
    letter-spacing:-.025em !important;
    text-shadow:0 1px 0 rgba(255,255,255,.04);
}
.bf-subtitle{color:#aebbd0 !important}

/* Streamlit controls */
button[kind="secondary"],.stButton>button{
    background:linear-gradient(180deg,#152235,#101a28) !important;
    border:1px solid rgba(120,174,252,.25) !important;
    color:#f3f7ff !important;
    border-radius:9px !important;
    box-shadow:0 4px 12px rgba(0,0,0,.14) !important;
    transition:transform .12s ease,border-color .12s ease,background .12s ease !important;
}
button[kind="secondary"]:hover,.stButton>button:hover{
    transform:translateY(-1px);
    border-color:rgba(120,174,252,.58) !important;
    background:linear-gradient(180deg,#1a2b42,#132135) !important;
}
[data-testid="stMetric"]{
    background:linear-gradient(145deg,#111c2b,#0d1622) !important;
    border:1px solid var(--bf-line) !important;
    border-radius:10px !important;
    box-shadow:0 7px 18px rgba(0,0,0,.13) !important;
}
[data-testid="stMetricLabel"] p{color:#91a1ba !important}
[data-testid="stMetricValue"]{color:#f8fbff !important}

/* Cleaner navigation: blue active state instead of the generic red underline */
.stTabs [data-baseweb="tab-list"]{
    border-bottom:1px solid rgba(145,174,216,.13) !important;
}
.stTabs [data-baseweb="tab"]{
    background:transparent !important;
    border:0 !important;
    border-radius:7px 7px 0 0 !important;
    color:#aeb9ca !important;
}
.stTabs [aria-selected="true"]{
    color:#fff !important;
    background:rgba(120,174,252,.10) !important;
    border-bottom:2px solid var(--bf-blue) !important;
}
.stTabs [data-baseweb="tab-highlight"]{background-color:var(--bf-blue) !important}

/* Section headings */
h1,h2,h3{color:#f4f8ff !important;letter-spacing:-.015em}
.bf-team-header{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:8px;
    margin:3px 0 5px;
    padding:7px 9px;
    border:1px solid rgba(120,174,252,.20);
    border-left:3px solid var(--bf-blue);
    border-radius:8px;
    background:linear-gradient(90deg,rgba(120,174,252,.10),rgba(120,174,252,.025));
}
.bf-team-header strong{font-size:.88rem;color:#f5f8ff}
.bf-team-header span{font-size:.56rem;color:#92a5c2;font-weight:800;letter-spacing:.06em}

/* Premium compact player cards */
.bf-scan-card{
    position:relative;
    background:linear-gradient(145deg,#0e1927,#0a131f) !important;
    border-color:rgba(145,174,216,.20) !important;
    box-shadow:0 8px 22px rgba(0,0,0,.16),inset 0 1px 0 rgba(255,255,255,.018) !important;
    overflow:hidden;
    transition:transform .14s ease,border-color .14s ease,box-shadow .14s ease;
}
.bf-scan-card:hover{
    transform:translateY(-1px);
    border-color:rgba(120,174,252,.46) !important;
    box-shadow:0 11px 28px rgba(0,0,0,.22),0 0 0 1px rgba(120,174,252,.07) !important;
}
.bf-scan-card.primary{
    border-color:rgba(53,208,127,.56) !important;
    box-shadow:0 8px 22px rgba(0,0,0,.16),0 0 18px rgba(53,208,127,.045) !important;
}
.bf-scan-card.strong{
    border-color:rgba(120,174,252,.48) !important;
    box-shadow:0 8px 22px rgba(0,0,0,.16),0 0 18px rgba(120,174,252,.045) !important;
}
.bf-scan-card.sleeper{border-color:rgba(187,123,255,.46) !important}
.bf-scan-name{color:#f8fbff !important;letter-spacing:-.012em}
.bf-scan-matchup{color:#93a3ba !important}
.bf-scan-action{
    background:linear-gradient(180deg,#162338,#111b2a) !important;
    border-color:rgba(120,174,252,.16) !important;
}
.bf-scan-action small{color:#81b3ff !important}
.bf-scan-rank{color:#9eb0c9 !important}
.bf-scan-metric{
    background:linear-gradient(180deg,#121e2e,#0f1926) !important;
    border-color:rgba(145,174,216,.12) !important;
}
.bf-scan-metric small{color:#8ea1bd !important}
.bf-scan-track{
    height:7px !important;
    background:#202c3d !important;
    box-shadow:inset 0 1px 2px rgba(0,0,0,.35);
}
.bf-scan-badges{gap:5px !important}
.bf-scan-badge{
    background:#111d2c !important;
    border-color:rgba(145,174,216,.16) !important;
}
.bf-scan-badge.good{box-shadow:inset 0 0 0 1px rgba(53,208,127,.035)}
.bf-scan-badge.weather{box-shadow:inset 0 0 0 1px rgba(120,174,252,.04)}
.bf-scan-badge.hot{box-shadow:inset 0 0 0 1px rgba(255,209,102,.04)}
.bf-scan-bottom{
    background:rgba(120,174,252,.045);
    border:1px solid rgba(120,174,252,.15) !important;
    border-radius:7px;
    padding:5px 7px !important;
    margin-top:6px !important;
}
.bf-scan-pair b{color:#91bdff !important}
.bf-scan-pair-score{color:#9bc5ff !important}
.bf-scan-why{
    margin-top:5px;
    color:#b3bfd0;
    font-size:.53rem;
    line-height:1.24;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}
.bf-scan-why b{
    color:#7fb2ff;
    letter-spacing:.07em;
    font-size:.46rem;
}

/* Research expanders should feel connected to the card */
div[data-testid="stExpander"]{
    border:1px solid rgba(145,174,216,.14) !important;
    background:rgba(10,18,29,.66) !important;
    box-shadow:none !important;
}
div[data-testid="stExpander"] summary:hover{background:rgba(120,174,252,.05) !important}
.bf-research-signals{
    background:linear-gradient(145deg,#101c2b,#0c1521) !important;
    border-color:rgba(120,174,252,.26) !important;
}
.bf-research-signals .label{color:#85b7ff !important}

/* Matchup research surfaces */
.bf-match-card{
    background:#09131f !important;
    border-color:rgba(120,174,252,.24) !important;
    box-shadow:0 10px 26px rgba(0,0,0,.20) !important;
}
.bf-match-topline{background:linear-gradient(90deg,#16243a,#111c2d) !important}
.bf-pitch-tile,.bf-bvp-cell{
    background:linear-gradient(145deg,#101c2a,#0c1622) !important;
    border-color:rgba(145,174,216,.14) !important;
}

/* Tables */
div[data-testid="stDataFrame"]{
    border-color:rgba(120,174,252,.20) !important;
    box-shadow:0 8px 20px rgba(0,0,0,.14);
}

/* Weather page uses the same premium surface language */
.bf-weather-card{
    background:linear-gradient(145deg,#0d1826,#09121d) !important;
    border-color:rgba(120,174,252,.25) !important;
    box-shadow:0 12px 30px rgba(0,0,0,.18) !important;
}
.bf-weather-head{background:linear-gradient(90deg,#17263c,#101a29) !important}
.bf-weather-summary>div,.bf-dim-panel,.bf-env-card{
    background:linear-gradient(145deg,#121f30,#0e1825) !important;
    border-color:rgba(145,174,216,.13) !important;
}

/* Mobile: retain density, improve touch feel */
@media(max-width:640px){
    .bf-hero{padding:9px 10px !important}
    .bf-scan-card{box-shadow:0 5px 14px rgba(0,0,0,.14) !important}
    .bf-scan-why{font-size:.47rem}
    .bf-scan-bottom{padding:4px 5px !important}
    .stTabs [data-baseweb="tab"]{min-height:30px !important}
}

</style>
<div class="bf-hero">
    <div class="bf-kicker">BF DATA PRO LAB</div>
    <div class="bf-title">JR Daily HR Predictions</div>
    <div class="bf-subtitle">Premium MLB home run intelligence — fast slate scanning, matchup signals, lineup awareness, and locked accuracy tracking.</div>
</div>
""", unsafe_allow_html=True)

# Late-loading theme layer. This intentionally overrides legacy hard-coded
# colors without changing any card content or application logic.
_t = BF_ACTIVE_THEME
_light = _t["mode"] == "light"
_light_css = """
html, body, .stApp, [data-testid="stAppViewContainer"] {
    color-scheme: light !important;
}
.stMarkdown, .stCaption, label, p, li,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p {
    color: var(--bf-text) !important;
}
[data-testid="stSidebar"] {
    color-scheme: light !important;
}
[data-testid="stSidebar"] * {
    color: var(--bf-text);
}
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
    background: var(--bf-panel) !important;
    color: var(--bf-text) !important;
    border-color: var(--bf-border-strong) !important;
}
[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"] {
    background: var(--bf-panel) !important;
    color: var(--bf-text) !important;
}
[data-baseweb="menu"] li,
[role="option"] {
    color: var(--bf-text) !important;
}
[data-baseweb="menu"] li:hover,
[role="option"]:hover {
    background: var(--bf-accent-soft) !important;
}
.bf-chip, .bf-key-chip,
.bf-scan-badge, .bf-research-signals .signal,
.bf-v2-grade, .bf-v2-rankchip {
    color: var(--bf-text) !important;
}
.bf-field-svg .dim {
    fill: #182331 !important;
    stroke: rgba(255,255,255,.92) !important;
}
.bf-field-svg .windtxt {
    fill: var(--bf-accent) !important;
    stroke: rgba(255,255,255,.94) !important;
}
""" if _light else ""

st.markdown(
    f"""
    <style>
    :root {{
        --bf-bg:{_t['bg']} !important;
        --bf-bg-deep:{_t['bg_2']} !important;
        --bf-panel:{_t['panel']} !important;
        --bf-panel-2:{_t['panel_2']} !important;
        --bf-surface:{_t['panel']} !important;
        --bf-surface-2:{_t['panel_2']} !important;
        --bf-surface-3:{_t['panel_3']} !important;
        --bf-text:{_t['text']} !important;
        --bf-muted:{_t['muted']} !important;
        --bf-blue:{_t['accent']} !important;
        --bf-blue-bright:{_t['accent']} !important;
        --bf-accent:{_t['accent']} !important;
        --bf-accent-soft:{_t['accent_soft']} !important;
        --bf-accent-line:{_t['accent_line']} !important;
        --bf-border:{_t['border']} !important;
        --bf-border-strong:{_t['border_strong']} !important;
        --bf-line:{_t['border']} !important;
        --bf-line-strong:{_t['border_strong']} !important;
    }}

    html,body,.stApp,[data-testid="stAppViewContainer"] {{
        background:
          radial-gradient(circle at 10% -5%, {_t['glow']}, transparent 27rem),
          linear-gradient(180deg,{_t['bg_2']} 0%,{_t['bg']} 50%,{_t['bg_2']} 100%) !important;
        color:{_t['text']} !important;
    }}
    [data-testid="stAppViewContainer"] > .main {{
        background:transparent !important;
    }}
    header[data-testid="stHeader"] {{
        background:{_t['bg_2']}F2 !important;
        border-bottom:1px solid {_t['border']} !important;
    }}
    [data-testid="stSidebar"] {{
        background:linear-gradient(180deg,{_t['panel']} 0%,{_t['bg_2']} 100%) !important;
        border-right:1px solid {_t['border']} !important;
    }}

    h1,h2,h3,h4,h5,h6,
    .bf-title,.bf-scan-name,.bf-head-main,.bf-weather-game,
    .bf-dim-title,.bf-dim-values {{
        color:{_t['text']} !important;
    }}
    p,.bf-subtitle,.bf-scan-matchup,.bf-scan-pair,
    .bf-weather-venue,.bf-weather-source,.bf-env-disclaimer,
    .bf-card-foot,.bf-pitch-note,.bf-v2-meta {{
        color:{_t['muted']} !important;
    }}

    .bf-hero {{
        background:linear-gradient(135deg,{_t['panel_2']},{_t['panel']}) !important;
        border-color:{_t['border_strong']} !important;
        box-shadow:0 14px 34px {_t['shadow']} !important;
    }}
    .bf-kicker,.bf-scan-action small,.bf-scan-pair b,
    .bf-scan-pair-score,.bf-research-signals .label,
    .bf-head-label,.bf-score-box .lab,.bf-section-title,
    .bf-bvp-title,.bf-env-kicker,.bf-weather-badge,
    .bf-guide-title,.bf-scout-title {{
        color:{_t['accent']} !important;
    }}

    button[kind="secondary"],.stButton>button {{
        background:linear-gradient(180deg,{_t['panel_3']},{_t['panel_2']}) !important;
        border-color:{_t['border_strong']} !important;
        color:{_t['text']} !important;
        box-shadow:0 4px 12px {_t['shadow']} !important;
    }}
    button[kind="secondary"]:hover,.stButton>button:hover {{
        background:{_t['panel_3']} !important;
        border-color:{_t['accent_line']} !important;
    }}

    [data-testid="stMetric"],
    .bf-scan-action,.bf-scan-metric,.bf-pitch-tile,.bf-bvp-cell,
    .bf-weather-summary>div,.bf-dim-panel,.bf-env-card,
    .bf-hour,.bf-guide-card,.bf-guide-quick>div {{
        background:{_t['panel_2']} !important;
        border-color:{_t['border']} !important;
        color:{_t['text']} !important;
    }}
    [data-testid="stMetricLabel"] p,
    .bf-scan-metric small,.bf-bvp-label,.bf-env-index {{
        color:{_t['muted']} !important;
    }}
    [data-testid="stMetricValue"],
    .bf-scan-action strong,.bf-scan-metric strong,
    .bf-bvp-values,.bf-pitch-name {{
        color:{_t['text']} !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        border-bottom-color:{_t['border']} !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        color:{_t['muted']} !important;
    }}
    .stTabs [aria-selected="true"] {{
        color:{_t['text']} !important;
        background:{_t['accent_soft']} !important;
        border-bottom-color:{_t['accent']} !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color:{_t['accent']} !important;
    }}

    .bf-team-header {{
        border-color:{_t['border_strong']} !important;
        border-left-color:{_t['accent']} !important;
        background:linear-gradient(90deg,{_t['accent_soft']},transparent) !important;
    }}
    .bf-team-header strong {{ color:{_t['text']} !important; }}
    .bf-team-header span {{ color:{_t['muted']} !important; }}

    .bf-scan-card,.bf-v2-card {{
        background:linear-gradient(145deg,{_t['panel_2']},{_t['panel']}) !important;
        border-color:{_t['border']} !important;
        box-shadow:0 8px 22px {_t['shadow']} !important;
    }}
    .bf-scan-card:hover,.bf-v2-card:hover {{
        border-color:{_t['accent_line']} !important;
        box-shadow:0 11px 28px {_t['shadow']} !important;
    }}
    .bf-scan-card.primary,.bf-v2-card.primary {{
        border-color:rgba(53,208,127,.58) !important;
    }}
    .bf-scan-card.strong,.bf-v2-card.strong {{
        border-color:{_t['accent_line']} !important;
    }}
    .bf-scan-card.sleeper,.bf-v2-card.sleeper {{
        border-color:rgba(187,123,255,.48) !important;
    }}
    .bf-scan-badge,.bf-research-signals .signal {{
        background:{_t['panel_3']} !important;
        border-color:{_t['border']} !important;
        color:{_t['text']} !important;
    }}
    .bf-scan-bottom,.bf-v2-pair {{
        background:{_t['accent_soft']} !important;
        border-color:{_t['accent_line']} !important;
    }}
    .bf-scan-track,.bf-track,.bf-v2-attack-track,
    .bf-v2-confidence-track,.bf-env-track,.bf-usage-track {{
        background:{_t['panel_3']} !important;
    }}
    .bf-scan-why b,.bf-v2-why b,.bf-v2-pair small,
    .bf-v2-pair-score,.bf-reason-strip b {{
        color:{_t['accent']} !important;
    }}

    div[data-testid="stExpander"] {{
        background:{_t['panel']}E8 !important;
        border-color:{_t['border']} !important;
    }}
    div[data-testid="stExpander"] summary:hover {{
        background:{_t['accent_soft']} !important;
    }}
    .bf-research-signals,.bf-v2-expand-summary,
    .bf-guide-panel,.bf-scout-panel {{
        background:linear-gradient(145deg,{_t['panel_2']},{_t['panel']}) !important;
        border-color:{_t['accent_line']} !important;
    }}

    .bf-match-card,.bf-weather-card {{
        background:{_t['panel']} !important;
        border-color:{_t['border_strong']} !important;
        box-shadow:0 10px 26px {_t['shadow']} !important;
    }}
    .bf-match-topline,.bf-weather-head {{
        background:linear-gradient(90deg,{_t['panel_3']},{_t['panel_2']}) !important;
        border-color:{_t['border']} !important;
    }}
    .bf-side-panel,.bf-cell-head,.bf-score-box {{
        border-color:{_t['border']} !important;
    }}
    .bf-pill-num {{
        background:{_t['panel_3']} !important;
        color:{_t['text']} !important;
    }}
    .bf-usage-fill {{
        background:{_t['accent']} !important;
    }}

    .bf-field-wrap {{
        background:{_t['field']} !important;
        border-color:{_t['border']} !important;
    }}
    .bf-weather-badge {{
        border-color:{_t['accent_line']} !important;
    }}

    div[data-testid="stDataFrame"] {{
        border-color:{_t['border_strong']} !important;
        box-shadow:0 8px 20px {_t['shadow']} !important;
    }}

    a {{ color:{_t['accent']} !important; }}
    hr {{ border-color:{_t['border']} !important; }}

    /* Calm premium hierarchy: surfaces remain neutral while the accent is
       reserved for active navigation, information labels, and interactions. */
    .bf-hero,
    .bf-scan-card,.bf-v2-card,
    .bf-match-card,.bf-weather-card,
    [data-testid="stMetric"] {{
        backdrop-filter:none !important;
    }}
    .bf-scan-card:not(.primary):not(.sleeper),
    .bf-v2-card:not(.primary):not(.sleeper) {{
        border-color:{_t['border']} !important;
    }}
    .bf-scan-card.strong,.bf-v2-card.strong {{
        border-left:2px solid {_t['accent']} !important;
    }}
    .bf-scan-bottom,.bf-v2-pair {{
        background:{_t['panel_2']} !important;
    }}
    .stTabs [aria-selected="true"] {{
        box-shadow:none !important;
    }}

    {_light_css}
    </style>
    """,
    unsafe_allow_html=True,
)

# Final 100%-zoom desktop/laptop fit layer.
# Presentation only: no board generation, ranking, model, tracker, lock,
# lineup, weather, or combo-generation calculations are changed.
st.markdown(
    """
    <style>
    /* A predictable content width that fits older 1366px laptops and modern displays. */
    .block-container{
        width:100% !important;
        max-width:1680px !important;
        padding-top:.30rem !important;
        padding-left:clamp(.45rem,1vw,.90rem) !important;
        padding-right:clamp(.45rem,1vw,.90rem) !important;
        padding-bottom:1.35rem !important;
    }

    html,body,.stApp{
        font-size:14px !important;
    }
    [data-testid="stVerticalBlock"]{gap:.36rem !important}
    [data-testid="stHorizontalBlock"]{gap:.48rem !important}

    .bf-hero{
        padding:8px 11px !important;
        margin-bottom:5px !important;
        border-radius:11px !important;
        box-shadow:0 6px 18px rgba(0,0,0,.14) !important;
    }
    .bf-title{font-size:clamp(1.28rem,2.1vw,2rem) !important}
    .bf-subtitle{font-size:.70rem !important}
    .bf-kicker{font-size:.50rem !important}

    [data-testid="stMetric"]{
        padding:5px 8px !important;
        min-height:52px !important;
        border-radius:8px !important;
        box-shadow:none !important;
    }
    [data-testid="stMetricLabel"] p{font-size:.60rem !important}
    [data-testid="stMetricValue"]{font-size:.88rem !important}

    .stTabs [data-baseweb="tab"]{
        padding:4px 7px !important;
        min-height:27px !important;
    }
    .stTabs [data-baseweb="tab"] p{font-size:.61rem !important}

    h1{font-size:1.35rem !important}
    h2{font-size:1.12rem !important}
    h3{font-size:.92rem !important}
    h1,h2,h3{margin:.22rem 0 .28rem !important}

    /* Compact scan cards: readable at 100%, but no oversized padding. */
    .bf-scan-card{
        padding:6px 7px !important;
        margin:3px 0 4px !important;
        border-radius:8px !important;
        box-shadow:0 4px 13px rgba(0,0,0,.12) !important;
    }
    .bf-scan-top{gap:5px !important}
    .bf-scan-name{font-size:.82rem !important}
    .bf-scan-matchup{font-size:.50rem !important}
    .bf-scan-actions{grid-template-columns:repeat(3,45px) !important;gap:3px !important}
    .bf-scan-action{padding:2px !important;border-radius:6px !important}
    .bf-scan-action small{font-size:.32rem !important}
    .bf-scan-action strong{font-size:.64rem !important}
    .bf-scan-roleline{gap:3px !important;margin-top:3px !important}
    .bf-scan-role{font-size:.40rem !important;padding:2px 5px !important}
    .bf-scan-grade{font-size:.43rem !important;padding:2px 5px !important}
    .bf-scan-confidence,.bf-scan-rank{font-size:.40rem !important}
    .bf-scan-badges{gap:3px !important;margin-top:3px !important}
    .bf-scan-badge{font-size:.38rem !important;padding:2px 5px !important}
    .bf-scan-attack{margin-top:4px !important;gap:4px !important}
    .bf-scan-attack-label{font-size:.40rem !important}
    .bf-scan-attack-score{font-size:.47rem !important}
    .bf-scan-track{height:5px !important}
    .bf-scan-metrics{gap:3px !important;margin-top:4px !important}
    .bf-scan-metric{padding:2px 3px !important}
    .bf-scan-metric small{font-size:.28rem !important}
    .bf-scan-metric strong{font-size:.53rem !important}
    .bf-scan-why{font-size:.42rem !important;margin-top:3px !important}
    .bf-scan-bottom{padding:3px 5px !important;margin-top:4px !important}
    .bf-scan-pair{font-size:.41rem !important}
    .bf-scan-pair-score{font-size:.49rem !important}

    div[data-testid="stExpander"] summary{
        min-height:28px !important;
        padding:.20rem .48rem !important;
        font-size:.67rem !important;
    }

    /* Expanded matchup view fits a standard HP 1366x768 laptop at 100% zoom. */
    .bf-match-topline{
        grid-template-columns:minmax(130px,1.05fr) minmax(125px,.92fr) 47px 47px 47px !important;
    }
    .bf-cell-head{padding:6px 7px !important}
    .bf-head-label{font-size:.42rem !important}
    .bf-head-main{font-size:.72rem !important;margin-top:2px !important}
    .bf-score-box{min-height:43px !important}
    .bf-score-box .lab{font-size:.38rem !important}
    .bf-score-box .num{font-size:.68rem !important;padding:3px 5px !important}
    .bf-card-body{
        grid-template-columns:145px minmax(0,1fr) !important;
        gap:7px !important;
        padding:6px !important;
    }
    .bf-section-title{font-size:.43rem !important;margin:2px 0 5px !important}
    .bf-score-line,.bf-pitcher-stat{font-size:.55rem !important;margin-bottom:4px !important}
    .bf-pitch-tile{padding:4px 5px !important;min-height:55px !important}
    .bf-pitch-name{font-size:.43rem !important}
    .bf-pitch-score{font-size:.76rem !important}
    .bf-pitch-note{font-size:.36rem !important}
    .bf-bvp-title{font-size:.43rem !important;margin-top:6px !important;padding-top:5px !important}
    .bf-bvp-cell{padding:4px 5px !important}
    .bf-bvp-label{font-size:.39rem !important}
    .bf-bvp-values{font-size:.54rem !important}

    /* Combo command center */
    .bf-combo-status{
        display:flex;justify-content:space-between;align-items:center;gap:10px;
        padding:8px 10px;margin:5px 0 7px;border:1px solid var(--bf-border);
        border-radius:9px;background:var(--bf-panel);
    }
    .bf-combo-status strong{font-size:.72rem;color:var(--bf-text)}
    .bf-combo-status span{font-size:.55rem;color:var(--bf-muted)}
    .bf-combo-zero{
        color:#ffb0b0 !important;border:1px solid rgba(255,85,85,.32);
        background:rgba(255,85,85,.06);border-radius:999px;padding:3px 7px;
        font-size:.50rem !important;font-weight:900;white-space:nowrap;
    }
    .bf-combo-picks{
        display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
        gap:6px;margin:6px 0 9px;
    }
    .bf-combo-pick{
        border:1px solid var(--bf-border);border-radius:9px;
        background:var(--bf-panel-2);padding:7px 8px;min-width:0;
    }
    .bf-combo-pick.featured{border-color:rgba(53,208,127,.44)}
    .bf-combo-pick.value{border-color:var(--bf-accent-line)}
    .bf-combo-pick.safe{border-color:rgba(255,209,102,.38)}
    .bf-combo-pick small{
        display:block;font-size:.43rem;font-weight:950;letter-spacing:.09em;
        color:var(--bf-accent);margin-bottom:4px;
    }
    .bf-combo-pick strong{
        display:block;color:var(--bf-text);font-size:.65rem;line-height:1.25;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .bf-combo-pick span{
        display:block;color:var(--bf-muted);font-size:.48rem;margin-top:4px;
    }
    .bf-combo-section{
        display:flex;justify-content:space-between;align-items:center;
        margin:7px 0 4px;padding:0 2px;
    }
    .bf-combo-section strong{font-size:.72rem;color:var(--bf-text)}
    .bf-combo-section span{font-size:.48rem;color:var(--bf-muted)}
    .bf-combo-card{
        display:grid;
        grid-template-columns:34px minmax(220px,1.7fr) repeat(4,minmax(62px,.45fr)) minmax(130px,.85fr);
        gap:0;border:1px solid var(--bf-border);border-radius:8px;
        background:var(--bf-panel);margin:3px 0;overflow:hidden;
    }
    .bf-combo-cell{
        padding:6px 7px;border-right:1px solid var(--bf-border);
        min-width:0;display:flex;flex-direction:column;justify-content:center;
    }
    .bf-combo-cell:last-child{border-right:0}
    .bf-combo-cell small{
        color:var(--bf-muted);font-size:.37rem;font-weight:900;
        letter-spacing:.07em;text-transform:uppercase;
    }
    .bf-combo-cell strong{
        color:var(--bf-text);font-size:.58rem;margin-top:2px;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .bf-combo-rank{align-items:center;text-align:center}
    .bf-combo-label strong{font-size:.62rem}
    .bf-combo-tag{
        display:inline-flex;align-self:flex-start;margin-top:3px;border-radius:999px;
        padding:2px 5px;font-size:.37rem;font-weight:950;
        color:var(--bf-accent);border:1px solid var(--bf-accent-line);
    }

    @media(max-width:1100px){
        .bf-combo-card{
            grid-template-columns:30px minmax(190px,1.6fr) repeat(4,minmax(54px,.42fr)) minmax(105px,.72fr);
        }
        .bf-combo-cell{padding:5px}
        .bf-combo-cell strong{font-size:.53rem}
    }
    @media(max-width:900px){
        .bf-card-body{grid-template-columns:1fr !important}
        .bf-combo-picks{grid-template-columns:1fr}
        .bf-combo-card{
            grid-template-columns:28px minmax(180px,1fr) 58px 58px 70px;
        }
        .bf-combo-card .bf-hide-narrow{display:none}
    }
    @media(max-width:640px){
        html,body,.stApp{font-size:13px !important}
        .block-container{padding:.22rem .32rem 1rem !important}
        .bf-combo-status{align-items:flex-start;flex-direction:column}
        .bf-combo-card{grid-template-columns:25px minmax(145px,1fr) 48px 55px}
        .bf-combo-card .bf-hide-mobile{display:none}
        .bf-combo-cell{padding:5px 4px}
        .bf-combo-label strong{font-size:.52rem}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Final readability correction for 100% browser zoom.
# UI-only: no prediction, ranking, lineup, tracker, lock, weather,
# history, or combo-generation calculations are changed.
st.markdown(
    """
    <style>
    /* ------------------------------------------------------------
       GLOBAL LAPTOP READABILITY
       Restore a comfortable middle ground: compact, but clearly readable.
       ------------------------------------------------------------ */
    html, body, .stApp{
        font-size:15px !important;
    }

    .block-container{
        width:100% !important;
        max-width:1640px !important;
        padding-top:.40rem !important;
        padding-left:clamp(.60rem,1.15vw,1.05rem) !important;
        padding-right:clamp(.60rem,1.15vw,1.05rem) !important;
        padding-bottom:1.50rem !important;
    }

    [data-testid="stVerticalBlock"]{gap:.46rem !important}
    [data-testid="stHorizontalBlock"]{gap:.58rem !important}

    .bf-hero{
        padding:10px 13px !important;
        margin-bottom:7px !important;
        border-radius:12px !important;
    }
    .bf-title{font-size:clamp(1.48rem,2.35vw,2.25rem) !important}
    .bf-subtitle{font-size:.79rem !important;line-height:1.35 !important}
    .bf-kicker{font-size:.57rem !important}

    [data-testid="stMetric"]{
        padding:7px 10px !important;
        min-height:58px !important;
    }
    [data-testid="stMetricLabel"] p{font-size:.68rem !important}
    [data-testid="stMetricValue"]{font-size:1rem !important}

    .stTabs [data-baseweb="tab"]{
        padding:5px 9px !important;
        min-height:31px !important;
    }
    .stTabs [data-baseweb="tab"] p{
        font-size:.69rem !important;
    }

    h1{font-size:1.50rem !important}
    h2{font-size:1.24rem !important}
    h3{font-size:1rem !important}

    /* ------------------------------------------------------------
       PLAYER CARDS
       Increase actual reading text without returning to oversized cards.
       ------------------------------------------------------------ */
    .bf-scan-card{
        padding:8px 9px !important;
        margin:5px 0 6px !important;
        border-radius:10px !important;
    }
    .bf-scan-top{gap:7px !important}
    .bf-scan-name{font-size:.97rem !important}
    .bf-scan-matchup{font-size:.61rem !important}

    .bf-scan-actions{
        grid-template-columns:repeat(3,51px) !important;
        gap:4px !important;
    }
    .bf-scan-action{
        padding:4px 3px !important;
        border-radius:7px !important;
    }
    .bf-scan-action small{font-size:.39rem !important}
    .bf-scan-action strong{font-size:.74rem !important}

    .bf-scan-roleline{gap:4px !important;margin-top:5px !important}
    .bf-scan-role{font-size:.48rem !important;padding:3px 7px !important}
    .bf-scan-grade{font-size:.52rem !important;padding:3px 6px !important}
    .bf-scan-confidence,.bf-scan-rank{font-size:.49rem !important}

    .bf-scan-badges{gap:4px !important;margin-top:5px !important}
    .bf-scan-badge{font-size:.46rem !important;padding:3px 7px !important}

    .bf-scan-attack{margin-top:6px !important;gap:6px !important}
    .bf-scan-attack-label{font-size:.49rem !important}
    .bf-scan-attack-score{font-size:.57rem !important}
    .bf-scan-track{height:6px !important}

    .bf-scan-metrics{gap:4px !important;margin-top:6px !important}
    .bf-scan-metric{padding:4px 5px !important}
    .bf-scan-metric small{font-size:.34rem !important}
    .bf-scan-metric strong{font-size:.64rem !important}

    .bf-scan-why{
        font-size:.50rem !important;
        line-height:1.30 !important;
        margin-top:5px !important;
    }
    .bf-scan-bottom{
        padding:5px 7px !important;
        margin-top:6px !important;
    }
    .bf-scan-pair{font-size:.50rem !important}
    .bf-scan-pair-score{font-size:.59rem !important}

    div[data-testid="stExpander"] summary{
        min-height:32px !important;
        padding:.30rem .60rem !important;
        font-size:.76rem !important;
    }

    /* Expanded research: readable labels and stats while retaining density. */
    .bf-match-topline{
        grid-template-columns:minmax(150px,1.05fr) minmax(140px,.92fr) 54px 54px 54px !important;
    }
    .bf-cell-head{padding:8px 9px !important}
    .bf-head-label{font-size:.49rem !important}
    .bf-head-main{font-size:.84rem !important;margin-top:3px !important}
    .bf-score-box{min-height:49px !important}
    .bf-score-box .lab{font-size:.44rem !important}
    .bf-score-box .num{font-size:.78rem !important;padding:4px 6px !important}

    .bf-card-body{
        grid-template-columns:170px minmax(0,1fr) !important;
        gap:10px !important;
        padding:9px !important;
    }
    .bf-section-title{font-size:.49rem !important;margin:3px 0 7px !important}
    .bf-score-line,.bf-pitcher-stat{font-size:.65rem !important;margin-bottom:6px !important}
    .bf-pitch-tile{padding:6px 7px !important;min-height:68px !important}
    .bf-pitch-name{font-size:.52rem !important}
    .bf-pitch-score{font-size:.92rem !important}
    .bf-pitch-note{font-size:.46rem !important;line-height:1.18 !important}
    .bf-bvp-title{font-size:.50rem !important;margin-top:8px !important;padding-top:7px !important}
    .bf-bvp-cell{padding:6px 7px !important}
    .bf-bvp-label{font-size:.47rem !important}
    .bf-bvp-values{font-size:.65rem !important}

    /* ------------------------------------------------------------
       COMBO BOARD STRUCTURE FIX
       The prior grid defined 7 columns for 8 cells. That forced the Games
       cell to wrap into an unreadable strip on the left. This uses 8 columns.
       ------------------------------------------------------------ */
    .bf-combo-status{
        padding:10px 12px !important;
    }
    .bf-combo-status strong{font-size:.82rem !important}
    .bf-combo-status span{font-size:.64rem !important;line-height:1.35 !important}
    .bf-combo-zero{font-size:.58rem !important;padding:4px 8px !important}

    .bf-combo-picks{
        gap:8px !important;
        margin:8px 0 11px !important;
    }
    .bf-combo-pick{
        padding:9px 10px !important;
    }
    .bf-combo-pick small{font-size:.50rem !important}
    .bf-combo-pick strong{
        font-size:.75rem !important;
        white-space:normal !important;
        overflow:visible !important;
    }
    .bf-combo-pick span{font-size:.57rem !important;line-height:1.3 !important}

    .bf-combo-section{
        margin:10px 0 5px !important;
    }
    .bf-combo-section strong{font-size:.83rem !important}
    .bf-combo-section span{font-size:.56rem !important}

    .bf-combo-card{
        grid-template-columns:
            40px
            minmax(260px,2.10fr)
            minmax(72px,.52fr)
            minmax(72px,.52fr)
            minmax(72px,.52fr)
            minmax(78px,.56fr)
            minmax(92px,.66fr)
            minmax(150px,1.05fr) !important;
        width:100% !important;
        margin:5px 0 !important;
        min-height:70px !important;
        overflow:hidden !important;
    }
    .bf-combo-cell{
        padding:8px 9px !important;
        min-width:0 !important;
        overflow:hidden !important;
    }
    .bf-combo-cell small{
        font-size:.43rem !important;
        line-height:1.1 !important;
    }
    .bf-combo-cell strong{
        font-size:.67rem !important;
        margin-top:4px !important;
        line-height:1.25 !important;
    }
    .bf-combo-label strong{
        font-size:.72rem !important;
        white-space:normal !important;
        overflow:visible !important;
        text-overflow:clip !important;
    }
    .bf-combo-tag{
        font-size:.43rem !important;
        padding:3px 6px !important;
        margin-top:5px !important;
    }

    /* Keep every combo cell inside the card. */
    .bf-combo-card > .bf-combo-cell:nth-child(1){grid-column:1}
    .bf-combo-card > .bf-combo-cell:nth-child(2){grid-column:2}
    .bf-combo-card > .bf-combo-cell:nth-child(3){grid-column:3}
    .bf-combo-card > .bf-combo-cell:nth-child(4){grid-column:4}
    .bf-combo-card > .bf-combo-cell:nth-child(5){grid-column:5}
    .bf-combo-card > .bf-combo-cell:nth-child(6){grid-column:6}
    .bf-combo-card > .bf-combo-cell:nth-child(7){grid-column:7}
    .bf-combo-card > .bf-combo-cell:nth-child(8){grid-column:8}

    @media (min-width:901px) and (max-width:1450px){
        .block-container{
            width:100% !important;
            padding-left:.65rem !important;
            padding-right:.65rem !important;
        }
        .bf-scan-name{font-size:.91rem !important}
        .bf-scan-matchup{font-size:.56rem !important}
        .bf-combo-card{
            grid-template-columns:
                36px
                minmax(225px,1.85fr)
                64px
                64px
                66px
                70px
                84px
                minmax(120px,.95fr) !important;
        }
        .bf-combo-cell{padding:7px !important}
        .bf-combo-cell strong{font-size:.61rem !important}
        .bf-combo-label strong{font-size:.67rem !important}
    }

    @media(max-width:1000px){
        .bf-combo-card{
            grid-template-columns:
                34px
                minmax(210px,1.7fr)
                66px
                66px
                70px
                minmax(110px,.9fr) !important;
        }
        .bf-combo-card > .bf-combo-cell:nth-child(6),
        .bf-combo-card > .bf-combo-cell:nth-child(7){
            display:none !important;
        }
        .bf-combo-card > .bf-combo-cell:nth-child(8){
            grid-column:6 !important;
        }
    }

    @media(max-width:900px){
        .bf-card-body{grid-template-columns:1fr !important}
        .bf-combo-picks{grid-template-columns:1fr !important}
        .bf-combo-card{
            grid-template-columns:32px minmax(190px,1fr) 64px 68px !important;
        }
        .bf-combo-card > .bf-combo-cell:nth-child(5),
        .bf-combo-card > .bf-combo-cell:nth-child(6),
        .bf-combo-card > .bf-combo-cell:nth-child(7),
        .bf-combo-card > .bf-combo-cell:nth-child(8){
            display:none !important;
        }
    }

    @media(max-width:640px){
        html,body,.stApp{font-size:14px !important}
        .block-container{padding:.28rem .40rem 1.15rem !important}

        .bf-scan-name{font-size:.86rem !important}
        .bf-scan-matchup{font-size:.53rem !important}
        .bf-scan-actions{grid-template-columns:repeat(3,45px) !important}
        .bf-scan-action strong{font-size:.66rem !important}
        .bf-scan-role{font-size:.42rem !important}
        .bf-scan-badge{font-size:.41rem !important}
        .bf-scan-metric strong{font-size:.58rem !important}

        .bf-combo-status{align-items:flex-start !important;flex-direction:column !important}
        .bf-combo-card{
            grid-template-columns:29px minmax(155px,1fr) 54px !important;
        }
        .bf-combo-card > .bf-combo-cell:nth-child(4),
        .bf-combo-card > .bf-combo-cell:nth-child(5),
        .bf-combo-card > .bf-combo-cell:nth-child(6),
        .bf-combo-card > .bf-combo-cell:nth-child(7),
        .bf-combo-card > .bf-combo-cell:nth-child(8){
            display:none !important;
        }
        .bf-combo-label strong{font-size:.59rem !important}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <style>
    /* BF DATA DECISION SUPPORT LAYER — presentation only */
    .bf-conviction-chip{
        display:inline-flex;align-items:center;border-radius:999px;
        padding:3px 7px;font-size:.45rem;font-weight:950;letter-spacing:.04em;
        border:1px solid var(--bf-border-strong);white-space:nowrap;
    }
    .bf-conviction-chip.hammer{color:#35d07f;border-color:rgba(53,208,127,.55);background:rgba(53,208,127,.09)}
    .bf-conviction-chip.strong{color:var(--bf-accent);border-color:var(--bf-accent-line);background:var(--bf-accent-soft)}
    .bf-conviction-chip.consider{color:#ffd166;border-color:rgba(255,209,102,.45);background:rgba(255,209,102,.08)}
    .bf-conviction-chip.pair{color:#c7b5ff;border-color:rgba(173,139,255,.42);background:rgba(173,139,255,.08)}
    .bf-conviction-chip.pass{color:#ff8f8f;border-color:rgba(255,107,107,.42);background:rgba(255,107,107,.07)}

    .bf-decision-hero{
        display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:center;
        padding:13px 14px;margin:7px 0 11px;border:1px solid var(--bf-border-strong);
        border-radius:13px;background:linear-gradient(135deg,var(--bf-panel-2),var(--bf-panel));
    }
    .bf-decision-hero.easy{border-left:4px solid #35d07f}
    .bf-decision-hero.medium{border-left:4px solid #ffd166}
    .bf-decision-hero.hard{border-left:4px solid #ff6b6b}
    .bf-decision-hero small,.bf-trust-ring small{
        display:block;color:var(--bf-muted);font-size:.53rem;font-weight:950;letter-spacing:.11em;
    }
    .bf-decision-hero>div>strong{display:block;color:var(--bf-text);font-size:1.02rem;margin-top:4px}
    .bf-decision-hero>div>span{display:block;color:var(--bf-muted);font-size:.67rem;margin-top:4px;line-height:1.35}
    .bf-trust-ring{
        min-width:90px;text-align:center;padding:8px 10px;border:1px solid var(--bf-accent-line);
        border-radius:10px;background:var(--bf-accent-soft);
    }
    .bf-trust-ring strong{font-size:1.42rem !important;color:var(--bf-accent) !important}
    .bf-trust-ring span{display:inline !important;font-size:.58rem !important}

    .bf-today-pick{
        display:grid;grid-template-columns:36px minmax(0,1fr) 78px;gap:10px;align-items:center;
        padding:10px 11px;margin:5px 0;border:1px solid var(--bf-border);
        border-radius:10px;background:var(--bf-panel);
    }
    .bf-today-pick.hammer{border-color:rgba(53,208,127,.48)}
    .bf-today-pick.strong{border-color:var(--bf-accent-line)}
    .bf-today-rank{font-size:1.05rem;font-weight:950;color:var(--bf-accent);text-align:center}
    .bf-today-main small{display:block;font-size:.50rem;color:var(--bf-accent);font-weight:950;letter-spacing:.06em}
    .bf-today-main strong{display:block;color:var(--bf-text);font-size:.86rem;margin-top:3px}
    .bf-today-main span{display:block;color:var(--bf-muted);font-size:.56rem;margin-top:2px}
    .bf-today-main p{margin:4px 0 0 !important;color:var(--bf-muted) !important;font-size:.55rem !important;line-height:1.3}
    .bf-today-score{text-align:center;padding:7px;border:1px solid var(--bf-border);border-radius:8px;background:var(--bf-panel-2)}
    .bf-today-score small{display:block;font-size:.40rem;color:var(--bf-muted);font-weight:950}
    .bf-today-score strong{display:block;font-size:1rem;color:var(--bf-text);margin-top:3px}

    .bf-why-one{
        display:grid;grid-template-columns:minmax(150px,.7fr) minmax(0,1.5fr) auto;
        gap:10px;align-items:center;padding:10px 11px;border:1px solid var(--bf-accent-line);
        border-radius:10px;background:linear-gradient(135deg,var(--bf-panel-2),var(--bf-panel));
    }
    .bf-why-one small{display:block;color:var(--bf-accent);font-size:.46rem;font-weight:950;letter-spacing:.09em}
    .bf-why-one strong{display:block;color:var(--bf-text);font-size:.84rem;margin-top:3px}
    .bf-why-one p{margin:2px 0 0 !important;color:var(--bf-muted) !important;font-size:.54rem !important}
    .bf-why-chips{display:flex;flex-wrap:wrap;gap:5px}
    .bf-why-chips span{border:1px solid var(--bf-border);border-radius:999px;padding:4px 7px;color:var(--bf-text);background:var(--bf-panel-3);font-size:.49rem;font-weight:850}
    .bf-why-score{text-align:right;white-space:nowrap}
    .bf-why-score strong{font-size:.92rem;color:var(--bf-accent)}

    .bf-today-combos{
        display:grid;
        grid-template-columns:repeat(3,minmax(0,1fr));
        gap:10px;
        width:100%;
        align-items:stretch;
        margin-bottom:8px;
    }
    .bf-today-combos>div{
        box-sizing:border-box;
        min-width:0;
        width:100%;
        height:100%;
        overflow:hidden;
        padding:10px 11px;
        border:1px solid var(--bf-border);
        border-radius:10px;
        background:var(--bf-panel);
    }
    .bf-today-combos small{
        display:block;
        color:var(--bf-accent);
        font-size:.45rem;
        font-weight:950;
        letter-spacing:.09em;
    }
    .bf-today-combos strong{
        display:block;
        min-width:0;
        color:var(--bf-text);
        font-size:.66rem;
        line-height:1.35;
        margin-top:4px;
        white-space:normal;
        overflow-wrap:anywhere;
        word-break:normal;
    }
    .bf-today-combos span{
        display:block;
        min-width:0;
        color:var(--bf-muted);
        font-size:.51rem;
        line-height:1.35;
        margin-top:6px;
        white-space:normal;
        overflow-wrap:anywhere;
    }


    /* BF DATA MARKET EDGE — additive price/value layer */
    .bf-market-audit{
        display:grid;grid-template-columns:minmax(0,1.5fr) .55fr .55fr;
        gap:8px;align-items:stretch;margin:7px 0 11px;
    }
    .bf-market-audit>div{
        border:1px solid var(--bf-border);border-radius:10px;
        background:var(--bf-panel);padding:9px 10px;min-width:0;
    }
    .bf-market-audit small,.bf-market-card small{
        display:block;color:var(--bf-muted);font-size:.44rem;
        font-weight:950;letter-spacing:.09em;
    }
    .bf-market-audit strong{
        display:block;color:var(--bf-text);font-size:.84rem;margin-top:3px;
    }
    .bf-market-audit strong.good,.bf-market-head b.good{color:#35d07f}
    .bf-market-audit strong.slight,.bf-market-head b.slight{color:#ffd166}
    .bf-market-audit strong.neutral,.bf-market-head b.neutral{color:var(--bf-accent)}
    .bf-market-audit span{
        display:block;color:var(--bf-muted);font-size:.53rem;
        line-height:1.3;margin-top:4px;
    }
    .bf-market-grid{
        display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
        gap:8px;margin:6px 0 9px;
    }
    .bf-market-card{
        min-width:0;border:1px solid var(--bf-border);border-radius:10px;
        background:linear-gradient(145deg,var(--bf-panel-2),var(--bf-panel));
        padding:9px 10px;
    }
    .bf-market-head{
        display:grid;grid-template-columns:minmax(0,1fr) auto;
        gap:7px;align-items:start;
    }
    .bf-market-head strong{
        display:block;color:var(--bf-text);font-size:.76rem;margin-top:3px;
    }
    .bf-market-head span{
        display:block;color:var(--bf-muted);font-size:.49rem;margin-top:2px;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .bf-market-head b{
        border:1px solid var(--bf-border);border-radius:999px;
        padding:3px 6px;font-size:.42rem;white-space:nowrap;
    }
    .bf-market-head b.good{border-color:rgba(53,208,127,.42);background:rgba(53,208,127,.07)}
    .bf-market-head b.slight{border-color:rgba(255,209,102,.42);background:rgba(255,209,102,.07)}
    .bf-market-head b.bad{color:#ff8f8f;border-color:rgba(255,107,107,.42);background:rgba(255,107,107,.07)}
    .bf-market-stats{
        display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
        gap:4px;margin-top:8px;
    }
    .bf-market-stats>div{
        min-width:0;border:1px solid var(--bf-border);border-radius:7px;
        background:var(--bf-panel-2);padding:5px;text-align:center;
    }
    .bf-market-stats strong{
        display:block;color:var(--bf-text);font-size:.65rem;margin-top:2px;
    }
    .bf-market-ev{
        display:flex;justify-content:space-between;align-items:center;
        gap:8px;margin-top:7px;padding-top:6px;border-top:1px solid var(--bf-border);
    }
    .bf-market-ev span{color:var(--bf-muted);font-size:.49rem}
    .bf-market-ev strong{color:var(--bf-accent);font-size:.72rem}

    @media(max-width:1050px){
        .bf-market-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
    }
    @media(max-width:760px){
        .bf-market-audit{grid-template-columns:1fr}
        .bf-market-grid{grid-template-columns:1fr}
    }


    .bf-market-move{
        margin-top:7px;padding:5px 7px;border-radius:7px;
        border:1px solid var(--bf-border);font-size:.50rem;font-weight:900;
    }
    .bf-market-move.steam{color:#35d07f;border-color:rgba(53,208,127,.35);background:rgba(53,208,127,.06)}
    .bf-market-move.drift{color:#ffd166;border-color:rgba(255,209,102,.35);background:rgba(255,209,102,.06)}
    .bf-market-move.flat{color:var(--bf-muted)}
    .bf-market-books{
        display:grid;grid-template-columns:repeat(5,minmax(0,1fr));
        gap:4px;margin-top:7px;
    }
    .bf-market-books>div{
        min-width:0;text-align:center;padding:5px 3px;border:1px solid var(--bf-border);
        border-radius:7px;background:var(--bf-panel-2);
    }
    .bf-market-books small{
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        font-size:.36rem;
    }
    .bf-market-books strong{display:block;color:var(--bf-text);font-size:.63rem;margin-top:2px}

    /* Live sportsbook information embedded directly into every player card. */
    .bf-card-market{
        display:grid;
        grid-template-columns:auto minmax(0,1fr) auto auto;
        gap:6px;
        align-items:center;
        margin-top:5px;
        padding:5px 7px;
        border:1px solid var(--bf-border);
        border-radius:7px;
        background:var(--bf-panel-2);
        min-width:0;
    }
    .bf-card-market.no-data{
        grid-template-columns:auto minmax(0,1fr);
        opacity:.82;
    }
    .bf-card-market-label{
        color:var(--bf-accent);
        font-size:.40rem;
        font-weight:950;
        letter-spacing:.08em;
        white-space:nowrap;
    }
    .bf-card-market-book{
        min-width:0;
        color:var(--bf-muted);
        font-size:.43rem;
        font-weight:850;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
    }
    .bf-card-market-price{
        color:var(--bf-text);
        font-size:.64rem;
        font-weight:950;
        white-space:nowrap;
    }
    .bf-card-market-move{
        border-radius:999px;
        padding:2px 5px;
        font-size:.37rem;
        font-weight:950;
        white-space:nowrap;
        border:1px solid var(--bf-border);
    }
    .bf-card-market-move.steam{
        color:#35d07f;
        border-color:rgba(53,208,127,.38);
        background:rgba(53,208,127,.07);
    }
    .bf-card-market-move.drift{
        color:#ffd166;
        border-color:rgba(255,209,102,.38);
        background:rgba(255,209,102,.07);
    }
    .bf-card-market-move.flat{color:var(--bf-muted)}
    .bf-card-market-edge{
        color:var(--bf-accent);
        font-size:.43rem;
        font-weight:950;
        white-space:nowrap;
    }

    /* Keep the help expander visually separate from the combo cards. */
    .bf-today-combos + div[data-testid="stExpander"]{
        margin-top:4px !important;
    }

    @media(max-width:760px){
        .bf-decision-hero{grid-template-columns:1fr}
        .bf-trust-ring{width:100%}
        .bf-today-combos{grid-template-columns:1fr}
        .bf-why-one{grid-template-columns:1fr}
        .bf-why-score{text-align:left}
    }
    @media(max-width:640px){
        .bf-conviction-chip{font-size:.38rem;padding:2px 5px}
        .bf-today-pick{grid-template-columns:28px minmax(0,1fr) 60px;padding:8px 7px;gap:6px}
        .bf-today-main strong{font-size:.75rem}
        .bf-today-main span,.bf-today-main p{font-size:.48rem !important}
        .bf-today-score{padding:5px}
        .bf-today-score strong{font-size:.82rem}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Final BF Data compact-fit correction.
# UI-only: restores the smaller 100%-zoom laptop/iPhone layout.
st.markdown(
    """
    <style>
    html,body,.stApp{font-size:14px !important}
    .block-container{
        width:100% !important;
        max-width:1680px !important;
        padding:.28rem clamp(.42rem,.85vw,.82rem) 1.15rem !important;
    }
    [data-testid="stVerticalBlock"]{gap:.34rem !important}
    [data-testid="stHorizontalBlock"]{gap:.44rem !important}

    .bf-hero{padding:8px 10px !important;margin-bottom:4px !important}
    .bf-title{font-size:clamp(1.25rem,2vw,1.90rem) !important}
    .bf-subtitle{font-size:.68rem !important}
    .bf-kicker{font-size:.48rem !important}

    .stTabs [data-baseweb="tab"]{padding:4px 7px !important;min-height:27px !important}
    .stTabs [data-baseweb="tab"] p{font-size:.60rem !important}

    h1{font-size:1.32rem !important}
    h2{font-size:1.08rem !important}
    h3{font-size:.88rem !important}

    .bf-scan-card{padding:6px 7px !important;margin:3px 0 4px !important}
    .bf-scan-name{font-size:.82rem !important}
    .bf-scan-matchup{font-size:.50rem !important}
    .bf-scan-actions{grid-template-columns:repeat(3,44px) !important}
    .bf-scan-action small{font-size:.31rem !important}
    .bf-scan-action strong{font-size:.63rem !important}
    .bf-scan-role{font-size:.39rem !important;padding:2px 5px !important}
    .bf-scan-grade,.bf-scan-confidence,.bf-scan-rank{font-size:.39rem !important}
    .bf-scan-badge{font-size:.37rem !important;padding:2px 5px !important}
    .bf-scan-attack-label{font-size:.39rem !important}
    .bf-scan-attack-score{font-size:.46rem !important}
    .bf-scan-metric small{font-size:.27rem !important}
    .bf-scan-metric strong{font-size:.52rem !important}
    .bf-scan-why{font-size:.41rem !important}
    .bf-scan-pair{font-size:.40rem !important}
    .bf-scan-pair-score{font-size:.48rem !important}

    div[data-testid="stExpander"] summary{
        min-height:28px !important;padding:.20rem .48rem !important;font-size:.67rem !important;
    }

    .bf-market-audit{margin:5px 0 7px !important;gap:6px !important}
    .bf-market-audit>div{padding:7px 8px !important}
    .bf-market-grid{gap:6px !important}
    .bf-market-card{padding:7px 8px !important}
    .bf-market-head strong{font-size:.69rem !important}
    .bf-market-stats{margin-top:6px !important}
    .bf-market-stats>div{padding:4px !important}
    .bf-market-stats strong{font-size:.58rem !important}
    .bf-market-books>div{padding:4px 2px !important}
    .bf-market-books strong{font-size:.56rem !important}

    @media(min-width:901px) and (max-width:1450px){
        .block-container{padding-left:.46rem !important;padding-right:.46rem !important}
        .bf-market-grid{grid-template-columns:repeat(3,minmax(0,1fr)) !important}
    }
    @media(max-width:900px){
        .bf-market-grid{grid-template-columns:repeat(2,minmax(0,1fr)) !important}
    }
    @media(max-width:640px){
        html,body,.stApp{font-size:13px !important}
        .block-container{padding:.20rem .30rem .95rem !important}
        .bf-market-grid{grid-template-columns:1fr !important}
        .bf-market-books{grid-template-columns:repeat(3,minmax(0,1fr)) !important}
        .bf-market-audit{grid-template-columns:1fr !important}
        .bf-card-market{
            grid-template-columns:auto minmax(0,1fr) auto !important;
            padding:4px 5px !important;
            gap:4px !important;
        }
        .bf-card-market-edge{display:none !important}
        .bf-card-market-label{font-size:.35rem !important}
        .bf-card-market-book{font-size:.38rem !important}
        .bf-card-market-price{font-size:.56rem !important}
        .bf-card-market-move{font-size:.32rem !important}
        .bf-title{font-size:1.12rem !important}
        .stTabs [data-baseweb="tab"] p{font-size:.56rem !important}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

AUTO_REFRESH_SECONDS = 120

# Speed control: regular board loads avoid the heavy play-by-play L10 BBE pull.
# Use Deep L10 Refresh only when you intentionally want the slower research pass.
DEFAULT_DEEP_L10_BBE = False


if "last_refresh_time" not in st.session_state:
    st.session_state.last_refresh_time = time.time()

if time.time() - st.session_state.last_refresh_time > AUTO_REFRESH_SECONDS:
    st.session_state.last_refresh_time = time.time()
    st.session_state.force_tracker_refresh = True
else:
    st.session_state.force_tracker_refresh = False
BF_DATA_DIR = os.environ.get("BF_DATA_DIR", ".bf_data")
os.makedirs(BF_DATA_DIR, exist_ok=True)

TRACKER_FILE = os.path.join(BF_DATA_DIR, "hr_tracker.csv")
COMBO_TRACKER_FILE = os.path.join(BF_DATA_DIR, "hr_combo_tracker.csv")
LOCK_FILE = os.path.join(BF_DATA_DIR, "daily_hr_board_lock.csv")

# Additive market layer. Odds never feed the BF prediction engine, rankings,
# eligibility, lineup locks, tracker, weather, or combo generation.
MARKET_ODDS_FILE = os.path.join(BF_DATA_DIR, "market_hr_odds.csv")
CURRENT_SEASON = datetime.now().year

SNAPSHOT_DIR = os.path.join(BF_DATA_DIR, "tracker_snapshots")
LEGACY_SNAPSHOT_DIR = "tracker_snapshots"
LEGACY_TRACKER_FILE = "hr_tracker.csv"
LEARNING_PROFILE_FILE = os.path.join(BF_DATA_DIR, "bf_learning_profile.json")
TRACKER_AUDIT_VERSION = "2.1"
BACKUP_DIR = os.path.join(BF_DATA_DIR, "history_backups")
os.makedirs(BACKUP_DIR, exist_ok=True)
_BACKED_UP_PATHS = set()


def _backup_file_before_write(path: str, label: str):
    if not path or path in _BACKED_UP_PATHS or not os.path.exists(path):
        return
    try:
        stamp = datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, os.path.join(BACKUP_DIR, f"{label}_{stamp}_{os.path.basename(path)}"))
        _BACKED_UP_PATHS.add(path)
    except Exception:
        pass



# Resource protection for Streamlit Community Cloud.
# Consolidated tracker/lock files are preserved. Only redundant dated recovery
# snapshots are pruned.
BF_SNAPSHOT_RETENTION_DAYS = int(os.environ.get("BF_SNAPSHOT_RETENTION_DAYS", "30"))
BF_BOARD_SNAPSHOT_RETENTION_DAYS = int(os.environ.get("BF_BOARD_SNAPSHOT_RETENTION_DAYS", "14"))
BF_MAX_LOCAL_DATA_MB = int(os.environ.get("BF_MAX_LOCAL_DATA_MB", "250"))


def ensure_snapshot_folder():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def save_daily_tracker_snapshot(tracker_df: pd.DataFrame, snapshot_date: str):
    """Persist the day's tracker state so historical results never disappear."""
    ensure_snapshot_folder()
    tracker_path = os.path.join(SNAPSHOT_DIR, f"hr_tracker_{snapshot_date}.csv")
    existing = _read_tracker_csv(tracker_path)
    merged = _basic_tracker_dedupe(
        pd.concat([existing, tracker_df], ignore_index=True)
        if not existing.empty else tracker_df
    )
    _atomic_write_csv(merged, tracker_path)


def save_daily_board_snapshot(board_df: pd.DataFrame, snapshot_date: str):
    """Persist surfaced prediction rows without rewriting earlier rankings.

    Important: this app has separate sections (CORE_BOARD, TOP12, GAME_HR).
    Older saves may be missing TOP12 rows, so do not simply return when the
    snapshot exists.  Merge in newly surfaced section rows by a stable key while
    preserving the existing row order and original predictions.
    """
    ensure_snapshot_folder()
    board_path = os.path.join(SNAPSHOT_DIR, f"hr_board_{snapshot_date}.csv")
    clean_board = board_df.copy()
    if "Actual HR Today" in clean_board.columns:
        clean_board = clean_board.drop(columns=["Actual HR Today"])

    if clean_board.empty:
        return

    key_cols = [c for c in ["Tracker Source", "Player", "Team", "Game", "game_pk"] if c in clean_board.columns]
    if len(key_cols) < 4:
        clean_board.to_csv(board_path, index=False)
        return

    if os.path.exists(board_path):
        try:
            old_board = pd.read_csv(board_path)
        except Exception:
            old_board = pd.DataFrame()
        if not old_board.empty and all(c in old_board.columns for c in key_cols):
            old_keys = set(zip(*[old_board[c].astype(str).map(normalize_name if c == "Player" else str) for c in key_cols]))
            add_rows = []
            for _, r in clean_board.iterrows():
                k = tuple(normalize_name(r[c]) if c == "Player" else str(r[c]) for c in key_cols)
                if k not in old_keys:
                    add_rows.append(r)
                    old_keys.add(k)
            if add_rows:
                merged = pd.concat([old_board, pd.DataFrame(add_rows)], ignore_index=True)
                merged.to_csv(board_path, index=False)
            return

    clean_board.to_csv(board_path, index=False)
    try:
        cleanup_bf_recovery_snapshots()
        enforce_bf_local_storage_ceiling()
    except Exception:
        pass


def load_daily_board_snapshot(snapshot_date: str) -> pd.DataFrame:
    ensure_snapshot_folder()
    board_path = os.path.join(SNAPSHOT_DIR, f"hr_board_{snapshot_date}.csv")
    if os.path.exists(board_path):
        try:
            return pd.read_csv(board_path)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def available_tracker_dates(tracker_df: pd.DataFrame) -> list[str]:
    dates = set()
    if tracker_df is not None and not tracker_df.empty and "date" in tracker_df.columns:
        dates.update(tracker_df["date"].dropna().astype(str).tolist())
    for folder in _snapshot_directories():
        if os.path.exists(folder):
            for name in os.listdir(folder):
                m = re.match(r"hr_board_(\d{4}-\d{2}-\d{2})\.csv", name)
                if m:
                    dates.add(m.group(1))
    dates.add(today_str())
    return sorted(dates, reverse=True)


TEAM_ABBR = {
    "Arizona Diamondbacks": "ARI",
    "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC",
    "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN",
    "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA",
    "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "New York Mets": "NYM",
    "New York Yankees": "NYY",
    "Athletics": "ATH",
    "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SD",
    "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA",
    "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSH",
}

PARK_FACTORS = {
    "ARI": 1.02, "ATL": 1.04, "BAL": 0.99, "BOS": 1.03, "CHC": 1.01,
    "CWS": 1.02, "CIN": 1.08, "CLE": 0.97, "COL": 1.20, "DET": 0.95,
    "HOU": 1.01, "KC": 0.96, "LAA": 0.99, "LAD": 1.01, "MIA": 0.94,
    "MIL": 1.03, "MIN": 1.00, "NYM": 0.98, "NYY": 1.05, "ATH": 0.93,
    "PHI": 1.06, "PIT": 0.95, "SD": 0.98, "SF": 0.92, "SEA": 0.95,
    "STL": 1.00, "TB": 0.97, "TEX": 1.07, "TOR": 1.04, "WSH": 1.00,
}

PARK_COORDS = {
    "ARI": (33.4455, -112.0667),
    "ATL": (33.8907, -84.4677),
    "BAL": (39.2840, -76.6217),
    "BOS": (42.3467, -71.0972),
    "CHC": (41.9484, -87.6553),
    "CWS": (41.8300, -87.6339),
    "CIN": (39.0979, -84.5082),
    "CLE": (41.4962, -81.6852),
    "COL": (39.7561, -104.9942),
    "DET": (42.3390, -83.0485),
    "HOU": (29.7573, -95.3555),
    "KC": (39.0517, -94.4803),
    "LAA": (33.8003, -117.8827),
    "LAD": (34.0739, -118.2400),
    "MIA": (25.7781, -80.2197),
    "MIL": (43.0280, -87.9712),
    "MIN": (44.9817, -93.2776),
    "NYM": (40.7571, -73.8458),
    "NYY": (40.8296, -73.9262),
    "ATH": (38.2270, -107.6720),
    "PHI": (39.9057, -75.1665),
    "PIT": (40.4469, -80.0057),
    "SD": (32.7073, -117.1573),
    "SF": (37.7786, -122.3893),
    "SEA": (47.5914, -122.3325),
    "STL": (38.6226, -90.1928),
    "TB": (27.7682, -82.6534),
    "TEX": (32.7473, -97.0842),
    "TOR": (43.6414, -79.3894),
    "WSH": (38.8730, -77.0074),
}


# Ballpark geometry used by the visual weather field (LF / LCF / CF / RCF / RF, feet).
PARK_DIMENSIONS = {
    "ARI": (330,376,407,376,335), "ATL": (335,385,400,375,325), "BAL": (333,384,400,373,318),
    "BOS": (310,379,390,380,302), "CHC": (355,368,400,368,353), "CWS": (330,375,400,375,335),
    "CIN": (328,379,404,370,325), "CLE": (325,370,400,375,325), "COL": (347,390,415,375,350),
    "DET": (345,370,420,365,330), "HOU": (315,366,409,370,326), "KC": (330,379,410,379,330),
    "LAA": (347,390,396,370,350), "LAD": (330,375,395,375,330), "MIA": (344,386,407,392,335),
    "MIL": (344,371,400,374,345), "MIN": (339,377,404,367,328), "NYM": (335,358,408,375,330),
    "NYY": (318,399,408,385,314), "ATH": (330,375,400,375,325), "PHI": (329,374,401,369,330),
    "PIT": (325,383,399,375,320), "SD": (334,390,396,391,322), "SF": (339,404,391,421,309),
    "SEA": (331,378,401,381,326), "STL": (336,375,400,375,335), "TB": (315,370,404,370,322),
    "TEX": (329,372,407,374,326), "TOR": (328,375,400,375,328), "WSH": (337,377,402,370,335),
}
PARK_TIMEZONES = {
    "ARI":"America/Phoenix","ATL":"America/New_York","BAL":"America/New_York","BOS":"America/New_York",
    "CHC":"America/Chicago","CWS":"America/Chicago","CIN":"America/New_York","CLE":"America/New_York",
    "COL":"America/Denver","DET":"America/Detroit","HOU":"America/Chicago","KC":"America/Chicago",
    "LAA":"America/Los_Angeles","LAD":"America/Los_Angeles","MIA":"America/New_York","MIL":"America/Chicago",
    "MIN":"America/Chicago","NYM":"America/New_York","NYY":"America/New_York","ATH":"America/Los_Angeles",
    "PHI":"America/New_York","PIT":"America/New_York","SD":"America/Los_Angeles","SF":"America/Los_Angeles",
    "SEA":"America/Los_Angeles","STL":"America/Chicago","TB":"America/New_York","TEX":"America/Chicago",
    "TOR":"America/Toronto","WSH":"America/New_York",
}
PARK_ROOFS = {"ARI":"RETRACTABLE","HOU":"RETRACTABLE","MIA":"RETRACTABLE","MIL":"RETRACTABLE","SEA":"RETRACTABLE","TEX":"RETRACTABLE","TOR":"RETRACTABLE","TB":"DOME"}

# Venue-first weather mapping for neutral-site, All-Star, Futures, and special-event games.
# The MLB home-team abbreviation can be non-standard (for example NAT/AME),
# so weather, dimensions, and roof data must resolve from the actual venue.
VENUE_TO_PARK_ABBR = {
    "Chase Field": "ARI",
    "Truist Park": "ATL",
    "Oriole Park at Camden Yards": "BAL",
    "Fenway Park": "BOS",
    "Wrigley Field": "CHC",
    "Rate Field": "CWS",
    "Guaranteed Rate Field": "CWS",
    "Great American Ball Park": "CIN",
    "Progressive Field": "CLE",
    "Coors Field": "COL",
    "Comerica Park": "DET",
    "Daikin Park": "HOU",
    "Minute Maid Park": "HOU",
    "Kauffman Stadium": "KC",
    "Angel Stadium": "LAA",
    "Dodger Stadium": "LAD",
    "loanDepot park": "MIA",
    "American Family Field": "MIL",
    "Target Field": "MIN",
    "Citi Field": "NYM",
    "Yankee Stadium": "NYY",
    "Sutter Health Park": "ATH",
    "Oakland Coliseum": "ATH",
    "Citizens Bank Park": "PHI",
    "PNC Park": "PIT",
    "Petco Park": "SD",
    "Oracle Park": "SF",
    "T-Mobile Park": "SEA",
    "Busch Stadium": "STL",
    "George M. Steinbrenner Field": "TB",
    "Tropicana Field": "TB",
    "Globe Life Field": "TEX",
    "Rogers Centre": "TOR",
    "Nationals Park": "WSH",
}

def resolve_game_park_abbr(game: dict) -> str:
    venue = str((game or {}).get("venue", "") or "").strip()
    if venue in VENUE_TO_PARK_ABBR:
        return VENUE_TO_PARK_ABBR[venue]
    # Tolerate sponsored-name changes and minor API variations.
    venue_norm = normalize_name(venue)
    for known_venue, abbr in VENUE_TO_PARK_ABBR.items():
        known_norm = normalize_name(known_venue)
        if venue_norm and (venue_norm == known_norm or venue_norm in known_norm or known_norm in venue_norm):
            return abbr
    return team_abbr((game or {}).get("home_team", ""))



def stable_float(key: str, low: float, high: float) -> float:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16) / 0xFFFFFFFF
    return low + (high - low) * value


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def ip_to_float(ip_value) -> float:
    if ip_value is None:
        return 0.0
    s = str(ip_value)
    if "." not in s:
        return safe_float(s, 0.0)
    whole, frac = s.split(".", 1)
    whole = safe_float(whole, 0.0)
    frac = safe_int(frac, 0)
    if frac == 0:
        return whole
    if frac == 1:
        return whole + (1 / 3)
    if frac == 2:
        return whole + (2 / 3)
    return safe_float(s, 0.0)


def team_abbr(name: str) -> str:
    return TEAM_ABBR.get(name, name[:3].upper())


def today_str() -> str:
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")


def now_et_string() -> str:
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S")


def parse_game_time_et(game_time_value: str):
    if not game_time_value:
        return None
    try:
        raw = str(game_time_value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        return None


def format_game_time_et(game_time_value: str) -> str:
    dt = parse_game_time_et(game_time_value)
    if dt is None:
        return "TBD ET"
    try:
        return dt.strftime("%-I:%M %p ET")
    except Exception:
        return dt.strftime("%I:%M %p ET").lstrip("0")


def sort_schedule_rows(schedule_rows: list[dict]) -> list[dict]:
    def _key(game: dict):
        dt = parse_game_time_et(game.get("game_time", ""))
        return (dt is None, dt or datetime.max.replace(tzinfo=ZoneInfo("America/New_York")), game.get("game_key", ""))
    return sorted(schedule_rows, key=_key)


def chunked(items, size):
    items = list(items)
    for i in range(0, len(items), size):
        yield items[i:i + size]


def display_lineup_spot(value):
    return value if value is not None else "—"


def normalize_name(name: str) -> str:
    if not name:
        return ""
    s = str(name).lower().strip()
    s = s.replace(".", "")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join([str(x) for x in col if str(x) != "nan"]).strip() for col in df.columns]
    else:
        df.columns = [str(c).strip() for c in df.columns]
    return df


def find_col(df: pd.DataFrame, candidates: list[str]):
    lowered = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        for key, original in lowered.items():
            if cand in key:
                return original
    return None


def read_html_best_table(urls: list[str], must_have_any: list[str]) -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in urls:
        try:
            html = requests.get(url, headers=headers, timeout=30).text
            tables = pd.read_html(html)
        except Exception:
            continue

        for table in tables:
            table = flatten_columns(table)
            cols = [str(c).lower() for c in table.columns]
            if any(any(needle in col for col in cols) for needle in must_have_any):
                return table

    return pd.DataFrame()



def _atomic_write_csv(df: pd.DataFrame, path: str):
    """Write a CSV atomically so interrupted Streamlit reruns cannot zero it out."""
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".bf_tmp_", suffix=".csv", dir=folder)
    os.close(fd)
    try:
        df.to_csv(tmp_path, index=False)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _tracker_columns() -> list[str]:
    """Permanent prediction-time snapshot used by Tracker Audit 2.0."""
    return [
        "date", "player", "player_id", "team", "game", "game_pk",
        "hr_probability", "hr_tier", "hr_eligible", "tracker_source",
        "board_rank", "on_core_board", "on_top12", "on_per_game",
        "quality_grade", "moonshot_score", "two_hr_score", "nuke_score",
        "stack_score", "slate_confidence",
        "weather_score", "park_factor", "pitcher_attackability",
        "ev", "barrel_pct", "hardhit_pct", "flyball_pct",
        "linedrive_pct", "groundball_pct", "air_pct", "xslg", "xwoba",
        "lineup_spot", "lineup_source", "pitcher", "pitcher_hr9",
        "matchup_advantage", "model_rank_score", "ranking_reasons",
        "audit_version", "prediction_locked_at",
        "result", "hr_count", "result_state", "game_state", "updated_at"
    ]


def _coerce_tracker_frame(df: pd.DataFrame) -> pd.DataFrame:
    columns = _tracker_columns()
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)
    work = df.copy()
    for col in columns:
        if col not in work.columns:
            work[col] = pd.NA
    work["tracker_source"] = (
        work["tracker_source"].fillna("CORE_BOARD")
        .astype(str).str.strip().str.upper()
    )
    work["player"] = work["player"].fillna("").astype(str)
    work["team"] = work["team"].fillna("").astype(str)
    work["game"] = work["game"].fillna("").astype(str)
    work["date"] = work["date"].fillna("").astype(str)
    work["hr_count"] = pd.to_numeric(work["hr_count"], errors="coerce").fillna(0).astype(int)
    return work[columns]


def _basic_tracker_dedupe(df: pd.DataFrame) -> pd.DataFrame:
    work = _coerce_tracker_frame(df)
    if work.empty:
        return work
    work["_player_key"] = work["player"].map(normalize_name)
    work["_game_pk_key"] = pd.to_numeric(work["game_pk"], errors="coerce").fillna(-1).astype(int)
    work["_result_key"] = pd.to_numeric(work["result"], errors="coerce").fillna(0).astype(int)
    work["_updated_key"] = work["updated_at"].fillna("").astype(str)
    work = work.sort_values(
        ["hr_count", "_result_key", "_updated_key"],
        ascending=[False, False, False],
    )
    work = work.drop_duplicates(
        subset=[
            "date", "_player_key", "team", "game",
            "_game_pk_key", "tracker_source"
        ],
        keep="first",
    )
    return work.drop(
        columns=["_player_key", "_game_pk_key", "_result_key", "_updated_key"]
    ).reset_index(drop=True)


def _read_tracker_csv(path: str) -> pd.DataFrame:
    if not path or not os.path.exists(path):
        return pd.DataFrame(columns=_tracker_columns())
    try:
        return _coerce_tracker_frame(pd.read_csv(path))
    except Exception:
        return pd.DataFrame(columns=_tracker_columns())


def _snapshot_directories() -> list[str]:
    folders = [SNAPSHOT_DIR]
    if LEGACY_SNAPSHOT_DIR not in folders:
        folders.append(LEGACY_SNAPSHOT_DIR)
    return folders


def _bf_directory_size_bytes(folder: str) -> int:
    total = 0
    if not folder or not os.path.isdir(folder):
        return total
    for root, _, files in os.walk(folder):
        for filename in files:
            path = os.path.join(root, filename)
            try:
                total += os.path.getsize(path)
            except OSError:
                continue
    return total


def cleanup_bf_recovery_snapshots(
    tracker_days: int = BF_SNAPSHOT_RETENTION_DAYS,
    board_days: int = BF_BOARD_SNAPSHOT_RETENTION_DAYS,
) -> dict:
    """Delete only old redundant dated snapshot files."""
    ensure_snapshot_folder()
    now = datetime.now()
    removed_files = 0
    removed_bytes = 0

    for folder in _snapshot_directories():
        if not os.path.isdir(folder):
            continue
        for filename in os.listdir(folder):
            tracker_match = re.fullmatch(r"hr_tracker_(\d{4}-\d{2}-\d{2})\.csv", filename)
            board_match = re.fullmatch(r"hr_board_(\d{4}-\d{2}-\d{2})\.csv", filename)
            if not tracker_match and not board_match:
                continue

            path = os.path.join(folder, filename)
            if not os.path.isfile(path):
                continue

            date_key = (tracker_match or board_match).group(1)
            try:
                file_date = datetime.strptime(date_key, "%Y-%m-%d")
            except ValueError:
                continue

            if tracker_match:
                continue
            retention = board_days
            if (now - file_date).days <= max(1, int(retention)):
                continue

            try:
                size = os.path.getsize(path)
                os.remove(path)
                removed_files += 1
                removed_bytes += size
            except OSError:
                continue

    return {
        "removed_files": removed_files,
        "removed_mb": round(removed_bytes / (1024 * 1024), 2),
        "local_mb": round(_bf_directory_size_bytes(BF_DATA_DIR) / (1024 * 1024), 2),
    }


def enforce_bf_local_storage_ceiling(max_mb: int = BF_MAX_LOCAL_DATA_MB) -> dict:
    """Remove oldest redundant snapshots if local BF data exceeds the ceiling."""
    ensure_snapshot_folder()
    ceiling = max(25, int(max_mb)) * 1024 * 1024
    current = _bf_directory_size_bytes(BF_DATA_DIR)
    removed_files = 0
    removed_bytes = 0

    if current <= ceiling:
        return {
            "removed_files": 0,
            "removed_mb": 0.0,
            "local_mb": round(current / (1024 * 1024), 2),
        }

    candidates = []
    for folder in _snapshot_directories():
        if not os.path.isdir(folder):
            continue
        for filename in os.listdir(folder):
            if not re.fullmatch(r"hr_board_\d{4}-\d{2}-\d{2}\.csv", filename):
                continue
            path = os.path.join(folder, filename)
            try:
                candidates.append((os.path.getmtime(path), path, os.path.getsize(path)))
            except OSError:
                continue

    for _, path, size in sorted(candidates):
        if current <= ceiling:
            break
        try:
            os.remove(path)
            current -= size
            removed_files += 1
            removed_bytes += size
        except OSError:
            continue

    return {
        "removed_files": removed_files,
        "removed_mb": round(removed_bytes / (1024 * 1024), 2),
        "local_mb": round(max(current, 0) / (1024 * 1024), 2),
    }


def _load_tracker_snapshot_files() -> pd.DataFrame:
    frames = []
    for folder in _snapshot_directories():
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if not re.fullmatch(r"hr_tracker_\d{4}-\d{2}-\d{2}\.csv", name):
                continue
            frame = _read_tracker_csv(os.path.join(folder, name))
            if not frame.empty:
                frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=_tracker_columns())
    return _basic_tracker_dedupe(pd.concat(frames, ignore_index=True))


def _recover_tracker_rows_from_board_snapshots() -> pd.DataFrame:
    """Recover surfaced picks from saved board snapshots after a reboot/deploy."""
    recovered = []
    for folder in _snapshot_directories():
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            match = re.fullmatch(r"hr_board_(\d{4}-\d{2}-\d{2})\.csv", name)
            if not match:
                continue
            date_key = match.group(1)
            try:
                board = pd.read_csv(os.path.join(folder, name))
            except Exception:
                continue
            if board.empty or "Player" not in board.columns:
                continue
            for _, row in board.iterrows():
                source = str(row.get("Tracker Source", "CORE_BOARD") or "CORE_BOARD").strip().upper()
                recovered.append({
                    "date": date_key,
                    "player": row.get("Player", ""),
                    "player_id": row.get("Player ID", pd.NA),
                    "team": row.get("Team", ""),
                    "game": row.get("Game", ""),
                    "game_pk": row.get("game_pk", pd.NA),
                    "hr_probability": row.get("HR Probability %", pd.NA),
                    "hr_tier": row.get("HR Tier", pd.NA),
                    "hr_eligible": int(bool(row.get("HR Eligible", True))),
                    "tracker_source": source,
                    "board_rank": row.get("Rank", pd.NA),
                    "on_core_board": int(source == "CORE_BOARD"),
                    "on_top12": int(source == "TOP12"),
                    "on_per_game": int(source == "GAME_HR"),
                    "quality_grade": row.get("Prediction Quality Grade", pd.NA),
                    "moonshot_score": row.get("Moonshot Score", pd.NA),
                    "two_hr_score": row.get("2 HR Score", pd.NA),
                    "nuke_score": row.get("Nuke Score", pd.NA),
                    "stack_score": row.get("Stack Score", pd.NA),
                    "slate_confidence": row.get("Slate Confidence", pd.NA),
                    "weather_score": row.get("WeatherBoost", pd.NA),
                    "park_factor": row.get("Park Factor", pd.NA),
                    "pitcher_attackability": row.get("HR Attackability Score", pd.NA),
                    "ev": row.get("EV", pd.NA),
                    "barrel_pct": row.get("Barrel%", pd.NA),
                    "hardhit_pct": row.get("HardHit%", pd.NA),
                    "flyball_pct": row.get("FlyBall%", pd.NA),
                    "linedrive_pct": row.get("LineDrive%", pd.NA),
                    "groundball_pct": row.get("GroundBall%", pd.NA),
                    "air_pct": row.get("AIR%", pd.NA),
                    "xslg": row.get("xSLG", pd.NA),
                    "xwoba": row.get("xwOBA", pd.NA),
                    "lineup_spot": row.get("Lineup Spot", pd.NA),
                    "lineup_source": row.get("Lineup Source", pd.NA),
                    "pitcher": row.get("Pitcher", pd.NA),
                    "pitcher_hr9": row.get("Pitcher_HR9_Last7", pd.NA),
                    "matchup_advantage": row.get("Matchup Advantage Score", pd.NA),
                    "model_rank_score": row.get("Model Rank Score", pd.NA),
                    "ranking_reasons": row.get("Ranking Reasons", pd.NA),
                    "audit_version": TRACKER_AUDIT_VERSION,
                    "prediction_locked_at": row.get("prediction_locked_at", now_et_string()),
                    "result": pd.NA,
                    "hr_count": 0,
                    "result_state": "RECOVERED_PENDING",
                    "game_state": row.get("game_state", pd.NA),
                    "updated_at": now_et_string(),
                })
    if not recovered:
        return pd.DataFrame(columns=_tracker_columns())
    return _basic_tracker_dedupe(pd.DataFrame(recovered))


@st.cache_data(ttl=86400, max_entries=500)
def _historical_game_homer_map(game_pk: int) -> dict:
    """Fetch final HR totals for a saved historical game."""
    try:
        response = requests.get(
            f"https://statsapi.mlb.com/api/v1/game/{int(game_pk)}/boxscore",
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return {}

    out = {}
    for side in ("away", "home"):
        players = (((payload.get("teams") or {}).get(side) or {}).get("players") or {})
        for pdata in players.values():
            person = pdata.get("person") or {}
            name = person.get("fullName")
            batting = ((pdata.get("stats") or {}).get("batting") or {})
            if not name:
                continue
            count = safe_int(batting.get("homeRuns", 0), 0)
            out[normalize_name(name)] = max(out.get(normalize_name(name), 0), count)
    return out


def _backfill_saved_tracker_results(df: pd.DataFrame) -> pd.DataFrame:
    """Fill recovered historical rows from MLB boxscores without changing predictions."""
    work = _basic_tracker_dedupe(df)
    if work.empty:
        return work

    today_key = today_str()
    game_pks = pd.to_numeric(work["game_pk"], errors="coerce")
    pending_mask = (
        work["date"].astype(str).lt(today_key)
        & game_pks.notna()
        & (
            work["result"].isna()
            | work["result_state"].astype(str).isin(["PENDING", "RECOVERED_PENDING", ""])
        )
    )
    unique_pks = sorted(set(game_pks[pending_mask].dropna().astype(int).tolist()))
    if not unique_pks:
        return work

    homer_maps = {}
    workers = min(3, len(unique_pks))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(_historical_game_homer_map, pk): pk for pk in unique_pks}
        for future in as_completed(futures):
            pk = futures[future]
            try:
                homer_maps[pk] = future.result()
            except Exception:
                homer_maps[pk] = {}

    for idx in work.index[pending_mask]:
        pk = safe_int(work.at[idx, "game_pk"], -1)
        homer_map = homer_maps.get(pk, {})
        player_key = normalize_name(work.at[idx, "player"])
        hr_count = safe_int(homer_map.get(player_key), 0)
        work.at[idx, "hr_count"] = hr_count
        work.at[idx, "result"] = 1 if hr_count > 0 else 0
        work.at[idx, "result_state"] = (
            "HOMERED" if hr_count == 1
            else f"HOMERED_{hr_count}X" if hr_count > 1
            else "FINAL_NO_HR"
        )
        work.at[idx, "game_state"] = "Final"
        work.at[idx, "updated_at"] = now_et_string()

    return _basic_tracker_dedupe(work)


def load_tracker() -> pd.DataFrame:
    """Load primary tracker plus daily snapshots and recover saved board rows."""
    frames = []

    primary = _read_tracker_csv(TRACKER_FILE)
    if not primary.empty:
        frames.append(primary)

    # Migrate the original root-level tracker automatically.
    if LEGACY_TRACKER_FILE != TRACKER_FILE:
        legacy = _read_tracker_csv(LEGACY_TRACKER_FILE)
        if not legacy.empty:
            frames.append(legacy)

    snapshots = _load_tracker_snapshot_files()
    if not snapshots.empty:
        frames.append(snapshots)

    recovered = _recover_tracker_rows_from_board_snapshots()
    if not recovered.empty:
        frames.append(recovered)

    if not frames:
        return pd.DataFrame(columns=_tracker_columns())

    tracker = _basic_tracker_dedupe(pd.concat(frames, ignore_index=True))
    tracker = _backfill_saved_tracker_results(tracker)

    # Consolidate recovered history into the primary file.
    _atomic_write_csv(tracker, TRACKER_FILE)
    return tracker

def dedupe_tracker_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep one tracker row per visible section pick and preserve the best result.

    A player can appear in CORE_BOARD, TOP12, and GAME_HR on the same date.
    Those must remain separate section records, but repeated refreshes must not
    inflate counts. Multi-HR games keep the highest hr_count found.
    """
    if df is None or df.empty:
        return df
    work = df.copy()
    for col in ["date", "player", "team", "game", "tracker_source"]:
        if col not in work.columns:
            work[col] = ""
    if "hr_count" not in work.columns:
        work["hr_count"] = 0
    if "result" not in work.columns:
        work["result"] = pd.NA

    work["_player_key"] = work["player"].astype(str).map(normalize_name)
    work["_hr_count_num"] = pd.to_numeric(work["hr_count"], errors="coerce").fillna(0).astype(int)
    work["_result_num"] = pd.to_numeric(work["result"], errors="coerce").fillna(0).astype(int)
    work["_updated_sort"] = work.get("updated_at", "").astype(str) if "updated_at" in work.columns else ""
    work = work.sort_values(["_hr_count_num", "_result_num", "_updated_sort"], ascending=[False, False, False])

    deduped = work.drop_duplicates(
        subset=[
            "date", "_player_key", "team", "game",
            *(["game_pk"] if "game_pk" in work.columns else []),
            "tracker_source"
        ],
        keep="first"
    ).copy()

    for c in ["_player_key", "_hr_count_num", "_result_num", "_updated_sort"]:
        if c in deduped.columns:
            deduped = deduped.drop(columns=[c])
    return deduped.reset_index(drop=True)


def save_tracker(df: pd.DataFrame):
    _backup_file_before_write(TRACKER_FILE, "tracker")
    tracker = _basic_tracker_dedupe(df)
    _atomic_write_csv(tracker, TRACKER_FILE)

    if tracker.empty or "date" not in tracker.columns:
        return

    ensure_snapshot_folder()
    for date_key, date_frame in tracker.groupby(tracker["date"].astype(str)):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date_key)):
            continue
        snapshot_path = os.path.join(SNAPSHOT_DIR, f"hr_tracker_{date_key}.csv")
        existing = _read_tracker_csv(snapshot_path)
        merged = _basic_tracker_dedupe(
            pd.concat([existing, date_frame], ignore_index=True)
            if not existing.empty else date_frame
        )
        _atomic_write_csv(merged, snapshot_path)

    try:
        cleanup_bf_recovery_snapshots()
        enforce_bf_local_storage_ceiling()
    except Exception:
        pass

def load_combo_tracker() -> pd.DataFrame:
    columns = [
        "date", "combo_id", "combo_label", "combo_size", "legs", "games",
        "avg_leg_probability", "combined_score", "source_pool", "result",
        "result_state", "legs_hit", "total_legs", "updated_at"
    ]
    if os.path.exists(COMBO_TRACKER_FILE):
        try:
            df = pd.read_csv(COMBO_TRACKER_FILE)
            for col in columns:
                if col not in df.columns:
                    df[col] = pd.NA
            return df[columns]
        except Exception:
            pass
    return pd.DataFrame(columns=columns)


def save_combo_tracker(df: pd.DataFrame):
    _backup_file_before_write(COMBO_TRACKER_FILE, "combo_tracker")
    _atomic_write_csv(df, COMBO_TRACKER_FILE)


def load_board_locks() -> pd.DataFrame:
    if os.path.exists(LOCK_FILE):
        try:
            return pd.read_csv(LOCK_FILE)
        except Exception:
            pass
    return pd.DataFrame()


def save_board_locks(df: pd.DataFrame):
    _backup_file_before_write(LOCK_FILE, "board_locks")
    _atomic_write_csv(df, LOCK_FILE)


def get_locked_board_for_date(date_key: str) -> pd.DataFrame:
    locks = load_board_locks()
    if locks.empty or "date" not in locks.columns:
        return pd.DataFrame()
    locked = locks[locks["date"].astype(str) == str(date_key)].copy()
    return locked.reset_index(drop=True)


def ensure_daily_board_lock(live_df: pd.DataFrame, schedule: list[dict]) -> pd.DataFrame:
    """Freeze confirmed teams independently for each MLB game_pk.

    Doubleheaders must never share locks merely because the team matchup text is
    identical. Every lock identity is (game_pk, team), with Game retained only
    as a display label.
    """
    if live_df.empty:
        return live_df.copy()

    date_key = today_str()
    locks = load_board_locks()
    if "game_pk" not in locks.columns:
        locks["game_pk"] = pd.NA

    if not locks.empty and "lock_scope" in locks.columns:
        locks_today = locks[locks["date"].astype(str) == str(date_key)].copy()
    else:
        locks_today = pd.DataFrame(columns=list(live_df.columns) + ["lock_created_at", "lock_scope"])

    confirmed_keys = set()
    pregame_confirmed_keys = set()
    for game in schedule:
        game_pk = safe_int(game.get("game_pk"), -1)
        game_state = str(game.get("game_state", "Preview"))
        away_team = team_abbr(game["away_team"])
        home_team = team_abbr(game["home_team"])
        if game.get("away_confirmed_count", 0) >= 9:
            confirmed_keys.add((game_pk, away_team))
            if game_state == "Preview":
                pregame_confirmed_keys.add((game_pk, away_team))
        if game.get("home_confirmed_count", 0) >= 9:
            confirmed_keys.add((game_pk, home_team))
            if game_state == "Preview":
                pregame_confirmed_keys.add((game_pk, home_team))

    rebuild_confirmed = bool(st.session_state.get("manual_refresh_trigger", False))

    def _row_lock_key(r):
        return (safe_int(r.get("game_pk"), -1), str(r.get("Team", "")))

    if rebuild_confirmed and not locks_today.empty:
        locks_today = locks_today[~locks_today.apply(lambda r: _row_lock_key(r) in pregame_confirmed_keys, axis=1)].copy()
        if not locks.empty:
            date_mask = locks["date"].astype(str).eq(str(date_key))
            drop_mask = date_mask & locks.apply(lambda r: _row_lock_key(r) in pregame_confirmed_keys, axis=1)
            locks = locks[~drop_mask].copy()

    existing_locked_keys = set()
    if not locks_today.empty:
        existing_locked_keys = {_row_lock_key(r) for _, r in locks_today.iterrows()}

    new_lock_frames = []
    for game_pk, team in confirmed_keys:
        if (game_pk, team) in existing_locked_keys:
            continue
        row_pks = pd.to_numeric(live_df.get("game_pk"), errors="coerce").fillna(-1).astype(int)
        team_rows = live_df[row_pks.eq(game_pk) & live_df["Team"].astype(str).eq(team)].copy()
        if team_rows.empty:
            continue
        team_rows["lock_created_at"] = now_et_string()
        team_rows["lock_scope"] = "CONFIRMED_TEAM"
        new_lock_frames.append(team_rows)

    if new_lock_frames:
        append_df = pd.concat(new_lock_frames, ignore_index=True)
        locks = pd.concat([locks, append_df], ignore_index=True)
        locks_today = pd.concat([locks_today, append_df], ignore_index=True)
        save_board_locks(locks)
    elif rebuild_confirmed:
        save_board_locks(locks)

    output_frames = []
    used_locked_keys = set()
    if not locks_today.empty:
        lock_pks = pd.to_numeric(locks_today.get("game_pk"), errors="coerce").fillna(-1).astype(int)
        for game_pk, team in confirmed_keys:
            locked_rows = locks_today[lock_pks.eq(game_pk) & locks_today["Team"].astype(str).eq(team)].copy()
            if not locked_rows.empty:
                output_frames.append(locked_rows)
                used_locked_keys.add((game_pk, team))

    live_rows = []
    for _, row in live_df.iterrows():
        key = (safe_int(row.get("game_pk"), -1), str(row.get("Team", "")))
        if key in confirmed_keys and key in used_locked_keys:
            continue
        live_rows.append(row)
    if live_rows:
        output_frames.append(pd.DataFrame(live_rows))

    if not output_frames:
        return live_df.copy().reset_index(drop=True)
    return pd.concat(output_frames, ignore_index=True).reset_index(drop=True)


def isolate_primary_pitch(pitch_mix: dict):
    if not pitch_mix:
        return None

    sorted_mix = sorted(
        pitch_mix.items(),
        key=lambda x: x[1],
        reverse=True
    )

    top_pitch, top_usage = sorted_mix[0]

    if top_usage >= 50:
        return top_pitch

    if len(sorted_mix) > 1:
        second_usage = sorted_mix[1][1]
        if (top_usage - second_usage) >= 20:
            return top_pitch

    return None


def normalize_hand_code(raw_value, default="") -> str:
    txt = str(raw_value or "").strip().upper()
    if txt in {"L", "LEFT", "LEFTY", "LHP", "LHB"}:
        return "L"
    if txt in {"R", "RIGHT", "RIGHTY", "RHP", "RHB"}:
        return "R"
    if txt in {"S", "SH", "SHB", "SWITCH", "B"}:
        return "S"
    return default


def extract_people_hand_maps(people_payload: dict) -> dict:
    hand_map = {}
    for person in (people_payload or {}).get("people", []):
        pid = person.get("id")
        if pid is None:
            continue
        bat_code = normalize_hand_code(((person.get("batSide") or {}).get("code") or (person.get("batSide") or {}).get("description")), "")
        pitch_code = normalize_hand_code(((person.get("pitchHand") or {}).get("code") or (person.get("pitchHand") or {}).get("description")), "")
        hand_map[int(pid)] = {"bat": bat_code, "throw": pitch_code}
    return hand_map


@st.cache_data(ttl=21600, max_entries=24)
def fetch_people_hand_map(person_ids_tuple: tuple) -> dict:
    ids = [str(int(x)) for x in person_ids_tuple if pd.notna(x)]
    if not ids:
        return {}
    out = {}
    for chunk in chunked(ids, 50):
        try:
            resp = requests.get(
                "https://statsapi.mlb.com/api/v1/people",
                params={"personIds": ",".join(chunk)},
                timeout=20,
            )
            resp.raise_for_status()
            out.update(extract_people_hand_maps(resp.json()))
        except Exception:
            continue
    return out


def get_true_batter_hand(player_id, hand_map: dict) -> str:
    try:
        pid = int(player_id)
    except Exception:
        return ""
    return normalize_hand_code((hand_map.get(pid) or {}).get("bat"), "")


def get_true_pitcher_hand(pitcher_id, hand_map: dict) -> str:
    try:
        pid = int(pitcher_id)
    except Exception:
        return ""
    return normalize_hand_code((hand_map.get(pid) or {}).get("throw"), "")


@st.cache_data(ttl=21600, max_entries=3)
def fetch_mlb_people_directory() -> dict:
    """Name -> MLBAM ID directory from MLB Stats API for current/prior seasons."""
    directory = {}
    for season in [CURRENT_SEASON, CURRENT_SEASON - 1, CURRENT_SEASON - 2]:
        try:
            resp = requests.get(
                "https://statsapi.mlb.com/api/v1/sports/1/players",
                params={"season": season},
                timeout=25,
            )
            resp.raise_for_status()
            for person in (resp.json() or {}).get("people", []) or []:
                pid = person.get("id")
                full = person.get("fullName")
                if pid and full:
                    directory.setdefault(normalize_name(full), int(pid))
                    # Useful for accent/name inconsistencies.
                    directory.setdefault(normalize_name(str(full).encode("ascii", "ignore").decode("ascii")), int(pid))
        except Exception:
            continue
    return directory


@st.cache_data(ttl=21600, max_entries=180)
def lookup_mlb_person_id_by_name(name: str):
    """Resolve a player/pitcher name to MLBAM ID without guessing."""
    clean = str(name or "").strip()
    if not clean or clean in {"—", "Starter Pending"}:
        return None

    target = normalize_name(clean)
    directory = fetch_mlb_people_directory()
    if target in directory:
        return directory[target]

    ascii_target = normalize_name(clean.encode("ascii", "ignore").decode("ascii"))
    if ascii_target in directory:
        return directory[ascii_target]

    try:
        resp = requests.get(
            "https://statsapi.mlb.com/api/v1/people/search",
            params={"names": clean},
            timeout=12,
        )
        resp.raise_for_status()
        people = (resp.json() or {}).get("people", []) or []
        if people:
            for person in people:
                if normalize_name(person.get("fullName", "")) == target:
                    return person.get("id")
            return people[0].get("id")
    except Exception:
        pass

    # Last exact-ish directory pass: only accept unique contains match, never guess.
    matches = [pid for n, pid in directory.items() if target and (target == n or target in n or n in target)]
    matches = list(dict.fromkeys(matches))
    return matches[0] if len(matches) == 1 else None


def estimate_handedness_from_name(name: str, role: str = "batter") -> str:
    # Kept only as a final emergency fallback for missing MLB IDs.
    # Normal app flow now uses MLB person batSide/pitchHand, not name guessing.
    return ""


def _is_swing(row) -> bool:
    desc = str(row.get("description", "") or "").lower()
    events = str(row.get("events", "") or "").lower()
    return (
        "swing" in desc
        or "foul" in desc
        or "hit_into_play" in desc
        or "hit_into_play" in events
        or "foul" in events
    )


def _is_whiff(row) -> bool:
    desc = str(row.get("description", "") or "").lower()
    return "swinging_strike" in desc or "missed_bunt" in desc


def _is_contact(row) -> bool:
    return _is_swing(row) and not _is_whiff(row)


def _is_bbe(row) -> bool:
    return pd.notna(row.get("launch_speed")) or pd.notna(row.get("launch_angle")) or str(row.get("bb_type", "") or "").strip() != ""


def _barrel_like(row) -> bool:
    ev = safe_float(row.get("launch_speed"), None)
    la = safe_float(row.get("launch_angle"), None)
    return ev is not None and la is not None and ev >= 98.0 and 8.0 <= la <= 50.0


def _statcast_date_range(days_back: int = 730):
    # True pitch mix needs enough history. Do NOT clamp to only this season;
    # that caused many starters/relievers to return no arsenal early in the year.
    end_dt = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=1)
    start_dt = end_dt - timedelta(days=int(days_back))
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


def _read_statcast_csv(params: dict, timeout: int = 18) -> pd.DataFrame:
    """Read Baseball Savant Statcast CSV with the full filter payload.

    Baseball Savant often returns an empty page when the short/minimal query is
    used.  This wrapper keeps the query truthful but supplies the same neutral
    filter fields Savant's own CSV export uses. No estimated or fictional pitch
    mix is created here.
    """
    base_params = {
        "all": "true",
        "hfPT": "",
        "hfAB": "",
        "hfGT": "R|",
        "hfPR": "",
        "hfZ": "",
        "stadium": "",
        "hfBBT": "",
        "hfNewZones": "",
        "hfPull": "",
        "hfC": "",
        "hfSea": "",
        "hfSit": "",
        "hfOuts": "",
        "opponent": "",
        "pitcher_throws": "",
        "batter_stands": "",
        "hfSA": "",
        "type": "details",
        "min_pitches": "0",
        "min_results": "0",
        "group_by": "name",
        "sort_col": "pitches",
        "sort_order": "desc",
    }
    q = dict(base_params)
    q.update({k: v for k, v in (params or {}).items() if v is not None})
    try:
        resp = requests.get(
            "https://baseballsavant.mlb.com/statcast_search/csv",
            params=q,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/csv,application/csv,text/plain,*/*",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        raw = resp.text or ""
        if "pitch_type" not in raw:
            return pd.DataFrame()
        df = pd.read_csv(StringIO(raw), low_memory=False)
        return df if "pitch_type" in df.columns else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=21600, max_entries=100)
def fetch_true_pitcher_arsenal(pitcher_id, days_back: int = 730, cache_version: str = "bf-real-arsenal-v8") -> dict:
    empty = {"found": False, "mix": {}, "tiles": []}
    try:
        pid = int(pitcher_id)
    except Exception:
        return empty

    start_date, end_date = _statcast_date_range(days_back)
    base = {
        "all": "true",
        "player_type": "pitcher",
        "game_date_gt": start_date,
        "game_date_lt": end_date,
        "hfSea": f"{CURRENT_SEASON}|{CURRENT_SEASON - 1}|{CURRENT_SEASON - 2}|",
        "type": "details",
        "min_pitches": "0",
        "min_results": "0",
    }
    # Savant CSV has changed filter names over time. Try all truth-preserving
    # pitcher ID filters, then verify the returned rows belong to this pitcher.
    variants = [
        {**base, "pitcher": str(pid)},
        {**base, "pitchers_lookup[]": str(pid)},
        {**base, "pitcher_lookup[]": str(pid)},
        {**base, "player_lookup[]": str(pid)},
    ]
    df = pd.DataFrame()
    for params in variants:
        df = _read_statcast_csv(params, timeout=18)
        if not df.empty and "pitch_type" in df.columns:
            break
    if df.empty or "pitch_type" not in df.columns:
        return empty

    if "pitcher" in df.columns:
        df = df[pd.to_numeric(df["pitcher"], errors="coerce") == int(pid)].copy()
    df = df[df["pitch_type"].notna()].copy()
    if df.empty:
        return empty

    total = len(df)
    tiles = []
    for pitch, sub in df.groupby("pitch_type"):
        count = len(sub)
        usage = round(count / total * 100, 1) if total else 0.0
        if usage < 0.5 and count < 3:
            continue
        swings = int(sub.apply(_is_swing, axis=1).sum())
        whiffs = int(sub.apply(_is_whiff, axis=1).sum())
        contact = int(sub.apply(_is_contact, axis=1).sum())
        bbe = sub[sub.apply(_is_bbe, axis=1)].copy()
        hard = int((pd.to_numeric(bbe.get("launch_speed"), errors="coerce") >= 95.0).sum()) if not bbe.empty else 0
        barrels = int(bbe.apply(_barrel_like, axis=1).sum()) if not bbe.empty else 0
        slg_allowed = safe_float(pd.to_numeric(sub.get("estimated_slg_using_speedangle"), errors="coerce").dropna().mean(), 0.0) if "estimated_slg_using_speedangle" in sub.columns else 0.0
        woba_allowed = safe_float(pd.to_numeric(sub.get("estimated_woba_using_speedangle"), errors="coerce").dropna().mean(), 0.0) if "estimated_woba_using_speedangle" in sub.columns else 0.0
        contact_pct = round(contact / swings * 100, 1) if swings else None
        whiff_pct = round(whiffs / swings * 100, 1) if swings else None
        xslg_allowed = round(slg_allowed, 3) if slg_allowed else None
        tile = {
            "pitch": str(pitch),
            "usage": usage,
            "count": int(count),
            "swings": swings,
            "contact_pct": contact_pct,
            "whiff_pct": whiff_pct,
            "bbe": int(len(bbe)),
            "hardhit_allowed_pct": round(hard / len(bbe) * 100, 1) if len(bbe) else None,
            "barrel_allowed_pct": round(barrels / len(bbe) * 100, 1) if len(bbe) else None,
            "xslg_allowed": xslg_allowed,
            "xwoba_allowed": round(woba_allowed, 3) if woba_allowed else None,
        }
        tiles.append(tile)
    tiles = sorted(tiles, key=lambda x: x.get("usage", 0.0), reverse=True)
    return {"found": bool(tiles), "mix": {t["pitch"]: t["usage"] for t in tiles}, "tiles": tiles}


@st.cache_data(ttl=21600, max_entries=100)
def fetch_true_batter_pitch_arsenal(batter_id, days_back: int = 730) -> dict:
    empty = {"found": False, "by_pitch": {}}
    try:
        pid = int(batter_id)
    except Exception:
        return empty
    start_date, end_date = _statcast_date_range(days_back)
    params = {
        "all": "true",
        "player_type": "batter",
        "batter": str(pid),
        "game_date_gt": start_date,
        "game_date_lt": end_date,
        "hfSea": f"{CURRENT_SEASON}|{CURRENT_SEASON - 1}|",
        "type": "details",
        "min_pitches": "0",
        "min_results": "0",
    }
    df = _read_statcast_csv(params, timeout=9)
    if df.empty or "pitch_type" not in df.columns:
        return empty
    df = df[df["pitch_type"].notna()].copy()
    by_pitch = {}
    for pitch, sub in df.groupby("pitch_type"):
        swings = int(sub.apply(_is_swing, axis=1).sum())
        whiffs = int(sub.apply(_is_whiff, axis=1).sum())
        contact = int(sub.apply(_is_contact, axis=1).sum())
        bbe = sub[sub.apply(_is_bbe, axis=1)].copy()
        if swings < 3 and len(bbe) < 2:
            continue
        hard = int((pd.to_numeric(bbe.get("launch_speed"), errors="coerce") >= 95.0).sum()) if not bbe.empty else 0
        barrels = int(bbe.apply(_barrel_like, axis=1).sum()) if not bbe.empty else 0
        slg = safe_float(pd.to_numeric(sub.get("estimated_slg_using_speedangle"), errors="coerce").dropna().mean(), 0.0) if "estimated_slg_using_speedangle" in sub.columns else 0.0
        woba = safe_float(pd.to_numeric(sub.get("estimated_woba_using_speedangle"), errors="coerce").dropna().mean(), 0.0) if "estimated_woba_using_speedangle" in sub.columns else 0.0
        by_pitch[str(pitch)] = {
            "swings": swings,
            "contact_pct": round(contact / swings * 100, 1) if swings else None,
            "whiff_pct": round(whiffs / swings * 100, 1) if swings else None,
            "bbe": int(len(bbe)),
            "hardhit_pct": round(hard / len(bbe) * 100, 1) if len(bbe) else None,
            "barrel_pct": round(barrels / len(bbe) * 100, 1) if len(bbe) else None,
            "xslg": round(slg, 3) if slg else None,
            "xwoba": round(woba, 3) if woba else None,
        }
    return {"found": bool(by_pitch), "by_pitch": by_pitch}


def build_pitch_mix_profile(pitcher_name: str, pitcher_id, *args, **kwargs) -> dict:
    # Real-only pitcher pitch mix. No fictional fallback pitches.
    if pitcher_id is None or (isinstance(pitcher_id, float) and pd.isna(pitcher_id)):
        pitcher_id = lookup_mlb_person_id_by_name(pitcher_name)
    arsenal = fetch_true_pitcher_arsenal(pitcher_id)
    return arsenal.get("mix", {}) if arsenal.get("found") else {}


def build_matchup_arsenal_tiles(pitcher_id, batter_id, pitch_matchup_score: float, authority_score: float, include_batter: bool = False) -> list[dict]:
    """Build truthful pitch tiles without slowing the whole board.

    Normal fast board load uses TRUE pitcher pitch types/usage/contact only.
    Batter-vs-pitch Statcast CSV pulls are intentionally reserved for Deep L10
    Refresh because doing one CSV pull per hitter is what made the app crawl.
    """
    pitcher_arsenal = fetch_true_pitcher_arsenal(pitcher_id)
    batter_arsenal = fetch_true_batter_pitch_arsenal(batter_id) if include_batter else {"found": False, "by_pitch": {}}
    if not pitcher_arsenal.get("found"):
        return []
    batter_by_pitch = batter_arsenal.get("by_pitch", {}) if batter_arsenal.get("found") else {}
    tiles = []
    for p in pitcher_arsenal.get("tiles", []):
        code = p.get("pitch")
        b = batter_by_pitch.get(code, {})
        batter_contact = b.get("contact_pct")
        pitcher_contact = p.get("contact_pct")
        batter_xslg = b.get("xslg")
        pitcher_xslg = p.get("xslg_allowed")
        batter_barrel = b.get("barrel_pct")
        pitcher_barrel = p.get("barrel_allowed_pct")
        # Score is a transparent matchup grade using true pitch usage + true batter/pitcher pitch-type data.
        score = 50.0
        if batter_xslg is not None:
            score += (safe_float(batter_xslg, 0.0) - 0.380) * 70
        if pitcher_xslg is not None:
            score += (safe_float(pitcher_xslg, 0.0) - 0.380) * 45
        if batter_barrel is not None:
            score += (safe_float(batter_barrel, 0.0) - 7.0) * 1.2
        if pitcher_barrel is not None:
            score += (safe_float(pitcher_barrel, 0.0) - 7.0) * 0.8
        if batter_contact is not None:
            score += (safe_float(batter_contact, 0.0) - 70.0) * 0.35
        score += min(safe_float(p.get("usage"), 0.0), 55.0) * 0.18
        tiles.append({
            "pitch": code,
            "usage": p.get("usage", 0.0),
            "score": round(clip(score, 5, 99), 0),
            "pitcher_contact_pct": pitcher_contact,
            "pitcher_whiff_pct": p.get("whiff_pct"),
            "pitcher_hardhit_allowed_pct": p.get("hardhit_allowed_pct"),
            "pitcher_barrel_allowed_pct": p.get("barrel_allowed_pct"),
            "pitcher_xslg_allowed": pitcher_xslg,
            "batter_contact_pct": batter_contact,
            "batter_whiff_pct": b.get("whiff_pct"),
            "batter_hardhit_pct": b.get("hardhit_pct"),
            "batter_barrel_pct": batter_barrel,
            "batter_xslg": batter_xslg,
            "note": (
                f"B Contact {batter_contact if batter_contact is not None else 'Deep'}% / "
                f"P Contact {pitcher_contact if pitcher_contact is not None else '—'}%"
            ),
        })
    return tiles

def compute_pitch_matchup_score(
    primary_pitch: str | None,
    primary_pitch_usage: float,
    bats: str,
    pitcher_throws: str,
    barrel: float,
    hard_hit: float,
    air_pct: float,
    launch_angle: float,
    xslg: float,
    xwoba: float,
    ground_ball: float,
):
    if primary_pitch is None:
        return 0.0, "No pitch edge", 0.0

    opposite_hand = bats != pitcher_throws
    shape_bonus = max(0.0, (barrel - 8) * 0.35) + max(0.0, (hard_hit - 38) * 0.12)
    lift_bonus = max(0.0, (air_pct - 52) * 0.08) + max(0.0, (18 - abs(launch_angle - 18)) * 0.18)
    contact_quality_bonus = max(0.0, (xslg - 0.430) * 20) + max(0.0, (xwoba - 0.320) * 12)
    gb_penalty = max(0.0, (ground_ball - 48) * 0.16)

    pitch_type_score = 0.0
    pitch_label = "Neutral pitch fit"

    if primary_pitch == "FF":
        pitch_type_score = shape_bonus + lift_bonus + contact_quality_bonus
        if barrel >= 11 and air_pct >= 55:
            pitch_label = "Fastball lift edge"
        else:
            pitch_label = "Fastball contact look"
    elif primary_pitch == "SL":
        pitch_type_score = (shape_bonus * 0.85) + (contact_quality_bonus * 0.85) + (2.0 if opposite_hand else 0.8)
        if opposite_hand and hard_hit >= 42:
            pitch_label = "Opposite-hand slider edge"
        else:
            pitch_label = "Slider damage path"
    elif primary_pitch == "CH":
        pitch_type_score = (contact_quality_bonus * 0.90) + (1.8 if opposite_hand else 0.5) + max(0.0, (launch_angle - 10) * 0.10)
        if opposite_hand and xwoba >= 0.340:
            pitch_label = "Changeup split edge"
        else:
            pitch_label = "Changeup contact path"
    elif primary_pitch == "CU":
        pitch_type_score = (shape_bonus * 0.75) + lift_bonus + max(0.0, (barrel - 9) * 0.22)
        if launch_angle >= 14 and barrel >= 10:
            pitch_label = "Curveball loft edge"
        else:
            pitch_label = "Curveball lift look"

    usage_multiplier = 0.85 + min(primary_pitch_usage, 65.0) / 100.0
    handedness_bonus = 1.4 if opposite_hand else -0.4

    final_score = (pitch_type_score * usage_multiplier) + handedness_bonus - gb_penalty

    if final_score >= 8.0:
        pitch_label = f"Strong {pitch_label.lower()}"
    elif final_score <= 1.5:
        pitch_label = "Weak pitch edge"

    return round(final_score, 2), pitch_label, round(handedness_bonus, 2)


def get_relevant_pitch_context(pitch_mix: dict):
    if not pitch_mix:
        return "BALANCED", [], "Mix"

    sorted_mix = sorted(pitch_mix.items(), key=lambda x: x[1], reverse=True)
    top_usage = sorted_mix[0][1]
    second_usage = sorted_mix[1][1] if len(sorted_mix) > 1 else 0.0
    gap = top_usage - second_usage

    if top_usage >= 50:
        mode = "HARD"
        relevant = sorted_mix[:1]
    elif gap > 20:
        mode = "HARD"
        relevant = sorted_mix[:2]
    elif gap >= 10 or top_usage >= 38:
        mode = "SOFT"
        relevant = sorted_mix[:2]
    else:
        mode = "BALANCED"
        relevant = sorted_mix[:3]

    total = sum(v for _, v in relevant) or 1.0
    weighted = [(p, round(v / total, 4), v) for p, v in relevant]
    label = " + ".join([p for p, _, _ in weighted])
    return mode, weighted, label


def compute_relevant_pitch_matchup(
    pitch_mix: dict,
    bats: str,
    pitcher_throws: str,
    barrel: float,
    hard_hit: float,
    air_pct: float,
    launch_angle: float,
    xslg: float,
    xwoba: float,
    ground_ball: float,
):
    mode, weighted_pitches, label = get_relevant_pitch_context(pitch_mix)
    if not weighted_pitches:
        return {
            "mode": "BALANCED",
            "label": "Mix",
            "score": 0.0,
            "usage": 0.0,
            "gap": 0.0,
            "handedness_edge": 0.0,
            "reason": "No pitch edge",
            "primary_pitch": None,
        }

    weighted_score = 0.0
    weighted_hand = 0.0
    reason_bits = []
    top_usage = weighted_pitches[0][2]
    second_usage = weighted_pitches[1][2] if len(weighted_pitches) > 1 else 0.0

    for pitch, weight, raw_usage in weighted_pitches:
        score, reason, hand = compute_pitch_matchup_score(
            pitch,
            raw_usage,
            bats,
            pitcher_throws,
            barrel,
            hard_hit,
            air_pct,
            launch_angle,
            xslg,
            xwoba,
            ground_ball,
        )
        weighted_score += score * weight
        weighted_hand += hand * weight
        if score >= 1.5:
            reason_bits.append(reason)

    reason = reason_bits[0] if reason_bits else "Weak pitch edge"
    if mode == "SOFT" and weighted_score >= 3.0:
        reason = f"Soft isolate: {label}"
    elif mode == "BALANCED" and weighted_score >= 3.0:
        reason = f"Balanced mix: {label}"
    elif mode == "HARD" and weighted_score >= 4.0:
        reason = f"Hard isolate: {label}"

    return {
        "mode": mode,
        "label": label,
        "score": round(weighted_score, 2),
        "usage": round(top_usage, 1),
        "gap": round(top_usage - second_usage, 1),
        "handedness_edge": round(weighted_hand, 2),
        "reason": reason,
        "primary_pitch": weighted_pitches[0][0],
    }




def compute_statcast_authority(
    ev: float,
    barrel: float,
    hard_hit: float,
    air_pct: float,
    launch_angle: float,
    xslg: float,
    ground_ball: float,
):
    launch_window = max(0.0, 26.0 - abs(launch_angle - 18.0))

    authority_score = (
        max(0.0, barrel - 8.0) * 4.0 +
        max(0.0, hard_hit - 38.0) * 1.8 +
        max(0.0, air_pct - 50.0) * 1.0 +
        max(0.0, ev - 88.0) * 1.25 +
        max(0.0, xslg - 0.430) * 135.0 +
        launch_window * 0.65 -
        max(0.0, ground_ball - 46.0) * 1.4
    )

    if authority_score >= 36:
        return round(authority_score, 2), 1.00, "ELITE"
    if authority_score >= 26:
        return round(authority_score, 2), 0.85, "STRONG"
    if authority_score >= 17:
        return round(authority_score, 2), 0.55, "MEDIUM"
    if authority_score >= 9:
        return round(authority_score, 2), 0.15, "WEAK"
    return round(authority_score, 2), 0.00, "FAIL"


def summarize_tracker(df: pd.DataFrame):
    summary = {
        "today_total": 0,
        "today_hits": 0,
        "today_pct": 0.0,
        "all_total": 0,
        "all_hits": 0,
        "all_pct": 0.0,
        "today_core_total": 0,
        "today_core_hits": 0,
        "today_core_pct": 0.0,
        "all_core_total": 0,
        "all_core_hits": 0,
        "all_core_pct": 0.0,
        "today_top12_total": 0,
        "today_top12_hits": 0,
        "today_top12_pct": 0.0,
        "all_top12_total": 0,
        "all_top12_hits": 0,
        "all_top12_pct": 0.0,
    }
    if df.empty:
        return summary

    work = official_tracker_rows(df.copy())
    if "tracker_source" not in work.columns:
        work["tracker_source"] = "CORE_BOARD"
    work["tracker_source"] = work["tracker_source"].fillna("CORE_BOARD").astype(str).str.strip().str.upper()
    work["result_num"] = pd.to_numeric(work["result"], errors="coerce").fillna(0).astype(int)
    if "hr_count" in work.columns:
        work["result_num"] = (pd.to_numeric(work["hr_count"], errors="coerce").fillna(0).astype(int) > 0).astype(int)

    def _stats(sub: pd.DataFrame):
        total = len(sub)
        hits = int(sub["result_num"].sum()) if total else 0
        pct = round((hits / total) * 100, 2) if total else 0.0
        return total, hits, pct

    today_df = work[work["date"].astype(str) == today_str()].copy()
    summary["today_total"], summary["today_hits"], summary["today_pct"] = _stats(today_df)
    summary["all_total"], summary["all_hits"], summary["all_pct"] = _stats(work)

    today_core = today_df[today_df["tracker_source"].isin(["CORE_BOARD", "GAME_HR"])]
    all_core = work[work["tracker_source"].isin(["CORE_BOARD", "GAME_HR"])]
    summary["today_core_total"], summary["today_core_hits"], summary["today_core_pct"] = _stats(today_core)
    summary["all_core_total"], summary["all_core_hits"], summary["all_core_pct"] = _stats(all_core)

    today_top12 = today_df[today_df["tracker_source"] == "TOP12"]
    all_top12 = work[work["tracker_source"] == "TOP12"]
    summary["today_top12_total"], summary["today_top12_hits"], summary["today_top12_pct"] = _stats(today_top12)
    summary["all_top12_total"], summary["all_top12_hits"], summary["all_top12_pct"] = _stats(all_top12)
    return summary


def summarize_tracker_by_day(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            "date",
            "all_surfaced",
            "all_correct_hr",
            "all_hit_rate_pct",
            "core_surfaced",
            "core_correct_hr",
            "core_hit_rate_pct",
            "top12_surfaced",
            "top12_correct_hr",
            "top12_hit_rate_pct",
        ])

    work = official_tracker_rows(df.copy())
    if "tracker_source" not in work.columns:
        work["tracker_source"] = "CORE_BOARD"
    work["tracker_source"] = work["tracker_source"].fillna("CORE_BOARD").astype(str).str.strip().str.upper()
    work["result_num"] = pd.to_numeric(work["result"], errors="coerce").fillna(0).astype(int)

    all_daily = (
        work.groupby("date", as_index=False)
        .agg(
            all_surfaced=("player", "count"),
            all_correct_hr=("result_num", "sum"),
        )
    )
    all_daily["all_hit_rate_pct"] = all_daily.apply(
        lambda row: round((row["all_correct_hr"] / row["all_surfaced"]) * 100, 2) if row["all_surfaced"] else 0.0,
        axis=1
    )

    core_work = work[work["tracker_source"].isin(["CORE_BOARD", "GAME_HR"])].copy()
    if core_work.empty:
        core_daily = pd.DataFrame(columns=["date", "core_surfaced", "core_correct_hr", "core_hit_rate_pct"])
    else:
        core_daily = (
            core_work.groupby("date", as_index=False)
            .agg(
                core_surfaced=("player", "count"),
                core_correct_hr=("result_num", "sum"),
            )
        )
        core_daily["core_hit_rate_pct"] = core_daily.apply(
            lambda row: round((row["core_correct_hr"] / row["core_surfaced"]) * 100, 2) if row["core_surfaced"] else 0.0,
            axis=1
        )

    top12_work = work[work["tracker_source"] == "TOP12"].copy()
    if top12_work.empty:
        top12_daily = pd.DataFrame(columns=["date", "top12_surfaced", "top12_correct_hr", "top12_hit_rate_pct"])
    else:
        top12_daily = (
            top12_work.groupby("date", as_index=False)
            .agg(
                top12_surfaced=("player", "count"),
                top12_correct_hr=("result_num", "sum"),
            )
        )
        top12_daily["top12_hit_rate_pct"] = top12_daily.apply(
            lambda row: round((row["top12_correct_hr"] / row["top12_surfaced"]) * 100, 2) if row["top12_surfaced"] else 0.0,
            axis=1
        )

    daily = all_daily.merge(core_daily, on="date", how="left").merge(top12_daily, on="date", how="left")
    for col in ["core_surfaced", "core_correct_hr", "core_hit_rate_pct", "top12_surfaced", "top12_correct_hr", "top12_hit_rate_pct"]:
        if col not in daily.columns:
            daily[col] = 0
        daily[col] = daily[col].fillna(0)

    daily = daily.sort_values("date", ascending=False).reset_index(drop=True)
    return daily


def get_lineup_mode(schedule_rows: list[dict]) -> str:
    total = len(schedule_rows)
    confirmed = 0
    partial = 0

    for g in schedule_rows:
        away_c = g.get("away_confirmed_count", 0)
        home_c = g.get("home_confirmed_count", 0)

        if away_c >= 9 and home_c >= 9:
            confirmed += 1
        elif away_c > 0 or home_c > 0:
            partial += 1

    if confirmed == total and total > 0:
        return "CONFIRMED"
    if confirmed > 0 or partial > 0:
        return "MIXED"
    return "PROJECTED"


def add_rank_column(df: pd.DataFrame) -> pd.DataFrame:
    ranked = df.copy()
    if "Rank" in ranked.columns:
        ranked = ranked.drop(columns=["Rank"])
    ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    return ranked


def strict_statcast_ok(row: pd.Series) -> bool:
    return bool(
        row.get("Statcast Pass") == "Yes"
        and safe_float(row.get("GroundBall%", 999), 999) < 52
        and (
            safe_float(row.get("Barrel%", 0), 0) >= 10
            or safe_float(row.get("AIR%", 0), 0) >= 55
            or safe_float(row.get("xSLG", 0), 0) >= 0.450
        )
    )


def passes_air_authority_profile(
    hard_hit: float,
    fly_ball: float,
    line_drive: float,
    ground_ball: float,
    barrel: float,
    ev: float,
    xslg: float,
    recent_hr: int,
    recent_xbh: int,
    recent_iso: float,
) -> dict:
    air_total = fly_ball + line_drive
    air_authority_core = (
        hard_hit >= 40
        and air_total >= 48
        and ground_ball < 50
        and air_total > ground_ball
    )

    authority_override = (
        barrel >= 10
        or ev >= 91
        or xslg >= 0.470
        or recent_hr >= 1
        or recent_xbh >= 3
        or recent_iso >= 0.180
        or (hard_hit >= 45 and air_total >= 45)
    )

    hard_reject = ground_ball >= 55 and not authority_override
    survives = (air_authority_core or authority_override) and not hard_reject

    return {
        "air_authority_core": air_authority_core,
        "authority_override": authority_override,
        "hard_reject": hard_reject,
        "survives": survives,
        "air_total": round(air_total, 1),
    }


def elite_hr_look(row: pd.Series) -> bool:
    barrel = safe_float(row.get("Barrel%", 0), 0)
    hard_hit = safe_float(row.get("HardHit%", 0), 0)
    air_pct = safe_float(row.get("AIR%", 0), 0)
    xslg = safe_float(row.get("xSLG", 0), 0)
    ev = safe_float(row.get("EV", 0), 0)
    gb = safe_float(row.get("GroundBall%", 999), 999)
    return bool(
        (
            barrel >= 10 and hard_hit >= 45 and air_pct >= 55 and ev >= 91 and gb <= 52
        ) or (
            barrel >= 12 and xslg >= 0.490 and air_pct >= 50 and gb <= 54
        ) or (
            hard_hit >= 48 and xslg >= 0.470 and air_pct >= 52 and gb <= 52
        )
    )


def compute_multi_pitch_authority_score(
    pitch_mix_mode: str,
    pitch_matchup_score: float,
    barrel: float,
    hard_hit: float,
    air_pct: float,
    xslg: float,
    ev: float,
    lineup_spot,
    recent_trend: str,
) -> float:
    score = 0.0

    elite_like = (
        (barrel >= 10 and hard_hit >= 45 and air_pct >= 55 and ev >= 91)
        or (barrel >= 12 and xslg >= 0.490)
        or (hard_hit >= 48 and xslg >= 0.470)
    )

    if pitch_mix_mode == "BALANCED":
        if elite_like:
            score += 4.0
        if pitch_matchup_score >= 3.0:
            score += 1.8
        if recent_trend in ["HOT", "LIVE"]:
            score += 1.0
        if lineup_spot is not None and lineup_spot <= 5:
            score += 0.8

    elif pitch_mix_mode == "SOFT":
        if elite_like:
            score += 2.6
        if pitch_matchup_score >= 3.0:
            score += 1.2

    return round(score, 2)

def get_gb_explanation(ground_ball: float, barrel: float, air_pct: float, xslg: float) -> str:
    if ground_ball >= 55:
        return "Stay away: 55%+ GB"
    if ground_ball >= 50:
        if barrel >= 12 or xslg >= 0.500 or air_pct >= 60:
            return "Heavy GB, but real damage traits keep it in play"
        return "Heavy GB downgrade"
    if ground_ball >= 45:
        if barrel >= 11 or xslg >= 0.470 or air_pct >= 58:
            return "Borderline GB, but damage traits keep it alive"
        return "Borderline GB caution"
    return "Clean enough launch shape"


def compute_weather_boost(temp_f: float, wind_mph: float) -> tuple[float, str]:
    boost = 0.0
    notes = []

    if temp_f >= 85:
        boost += 2.4
        notes.append("hot carry weather")
    elif temp_f >= 75:
        boost += 1.4
        notes.append("warm carry weather")
    elif temp_f <= 50:
        boost -= 1.8
        notes.append("cold dense air")
    elif temp_f <= 60:
        boost -= 0.8
        notes.append("cool air")

    if wind_mph >= 15:
        boost += 1.6
        notes.append("strong wind")
    elif wind_mph >= 10:
        boost += 0.8
        notes.append("live wind")
    elif wind_mph <= 3:
        notes.append("neutral wind")

    if not notes:
        notes.append("neutral weather")

    return round(boost, 2), " | ".join(notes[:2])


@st.cache_data(ttl=1800, max_entries=40)
def fetch_weather_for_park(home_team_abbr: str):
    coords = PARK_COORDS.get(home_team_abbr)
    if not coords:
        return {
            "found": False,
            "TempF": None,
            "WindMPH": None,
            "WindDir": None,
            "Condition": "Unavailable",
            "source": "Unavailable",
        }

    lat, lon = coords
    timezone_name = PARK_TIMEZONES.get(home_team_abbr, "America/New_York")

    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,wind_speed_10m,wind_direction_10m,weather_code",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": timezone_name,
            },
            timeout=15,
        )
        response.raise_for_status()
        current = (response.json() or {}).get("current") or {}
        if current:
            label, _ = _weather_label(current.get("weather_code"))
            return {
                "found": True,
                "TempF": safe_float(current.get("temperature_2m"), None),
                "WindMPH": safe_float(current.get("wind_speed_10m"), None),
                "WindDir": safe_float(current.get("wind_direction_10m"), None),
                "Condition": label,
                "source": "Open-Meteo current conditions",
            }
    except Exception:
        pass

    try:
        headers = {"User-Agent": "BFData/1.0 weather fallback"}
        points = requests.get(
            f"https://api.weather.gov/points/{lat},{lon}",
            headers=headers,
            timeout=15,
        )
        points.raise_for_status()
        hourly_url = points.json()["properties"]["forecastHourly"]
        hourly = requests.get(hourly_url, headers=headers, timeout=15)
        hourly.raise_for_status()
        periods = hourly.json().get("properties", {}).get("periods", [])
        period = periods[0] if periods else {}
        if period:
            speed_match = re.search(r"(\d+(?:\.\d+)?)", str(period.get("windSpeed", "")))
            wind_speed = float(speed_match.group(1)) if speed_match else None
            compass = str(period.get("windDirection", "")).upper()
            direction_map = {
                "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
                "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
                "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5,
                "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
            }
            return {
                "found": True,
                "TempF": safe_float(period.get("temperature"), None),
                "WindMPH": wind_speed,
                "WindDir": direction_map.get(compass),
                "Condition": period.get("shortForecast", "Current conditions"),
                "source": "U.S. National Weather Service",
            }
    except Exception:
        pass

    return {
        "found": False,
        "TempF": None,
        "WindMPH": None,
        "WindDir": None,
        "Condition": "Weather providers unavailable",
        "source": "Unavailable",
    }


WEATHER_CODE_LABELS = {0:("Clear","☀️"),1:("Mostly clear","🌤️"),2:("Partly cloudy","⛅"),3:("Overcast","☁️"),45:("Fog","🌫️"),48:("Rime fog","🌫️"),51:("Light drizzle","🌦️"),53:("Drizzle","🌦️"),55:("Heavy drizzle","🌧️"),61:("Light rain","🌦️"),63:("Rain","🌧️"),65:("Heavy rain","🌧️"),80:("Rain showers","🌦️"),81:("Rain showers","🌧️"),82:("Heavy showers","⛈️"),95:("Thunderstorms","⛈️"),96:("Storms / hail","⛈️"),99:("Severe storms","⛈️")}

def _weather_label(code):
    return WEATHER_CODE_LABELS.get(safe_int(code,-1),("Conditions unavailable","•"))

def _compass_name(deg):
    if deg is None: return "—"
    names=["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return names[int((safe_float(deg,0)+11.25)//22.5)%16]

@st.cache_data(ttl=900, max_entries=60)
def fetch_game_weather_timeline(home_team_abbr: str, game_time_value: str):
    """Fetch resilient hourly game weather from Open-Meteo.

    The first request asks for the full weather panel. If Open-Meteo rejects a
    field or temporarily returns an incomplete payload, a smaller fallback
    request is attempted. If the scheduled game hour is outside the returned
    window, the nearest available hour is still used instead of showing a blank
    weather tab.
    """
    coords = PARK_COORDS.get(home_team_abbr)
    if not coords:
        return {
            "found": False,
            "hours": [],
            "source": "Open-Meteo",
            "error": "missing park coordinates",
        }

    tz_name = PARK_TIMEZONES.get(home_team_abbr, "America/New_York")
    base_params = {
        "latitude": coords[0],
        "longitude": coords[1],
        "timezone": tz_name,
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "forecast_days": 16,
    }

    hourly_sets = [
        "temperature_2m,relative_humidity_2m,precipitation_probability,pressure_msl,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m",
    ]

    payload = None
    last_error = ""
    for hourly_fields in hourly_sets:
        try:
            params = dict(base_params)
            params["hourly"] = hourly_fields
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params,
                timeout=18,
            )
            response.raise_for_status()
            candidate = response.json() or {}
            hourly = candidate.get("hourly") or {}
            if hourly.get("time"):
                payload = candidate
                break
            last_error = "hourly response contained no times"
        except Exception as exc:
            last_error = str(exc)

    if not payload:
        return {
            "found": False,
            "hours": [],
            "source": "Open-Meteo",
            "error": last_error or "forecast unavailable",
        }

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return {
            "found": False,
            "hours": [],
            "source": "Open-Meteo",
            "error": "forecast returned no hourly timestamps",
        }

    try:
        parsed = [
            datetime.fromisoformat(str(t)).replace(tzinfo=ZoneInfo(tz_name))
            for t in times
        ]
    except Exception as exc:
        return {
            "found": False,
            "hours": [],
            "source": "Open-Meteo",
            "error": f"could not parse forecast times: {exc}",
        }

    game_dt = parse_game_time_et(game_time_value)
    target = (
        game_dt.astimezone(ZoneInfo(tz_name))
        if game_dt is not None
        else datetime.now(ZoneInfo(tz_name))
    )

    center = min(
        range(len(parsed)),
        key=lambda i: abs((parsed[i] - target).total_seconds()),
    )
    start_idx = max(0, center - 2)
    end_idx = min(len(parsed), center + 4)

    def at(name, i):
        values = hourly.get(name) or []
        return values[i] if i < len(values) else None

    rows = []
    for i in range(start_idx, end_idx):
        weather_label, icon = _weather_label(at("weather_code", i))
        wind_dir = safe_float(at("wind_direction_10m", i), None)
        rows.append({
            "time": parsed[i],
            "label": weather_label,
            "icon": icon,
            "temp": safe_float(at("temperature_2m", i), None),
            "precip": safe_float(at("precipitation_probability", i), None),
            "humidity": safe_float(at("relative_humidity_2m", i), None),
            "pressure": safe_float(at("pressure_msl", i), None),
            "wind": safe_float(at("wind_speed_10m", i), None),
            "gust": safe_float(at("wind_gusts_10m", i), None),
            "wind_dir": wind_dir,
            "wind_compass": _compass_name(wind_dir),
            "is_game_hour": i == center,
        })

    game_hour = next((row for row in rows if row.get("is_game_hour")), rows[0] if rows else {})
    return {
        "found": bool(rows),
        "hours": rows,
        "game_hour": game_hour,
        "source": "Open-Meteo hourly forecast",
        "nearest_hour_used": bool(parsed[center] != target.replace(minute=0, second=0, microsecond=0)),
        "error": "",
    }


def _fmt_weather(v, suffix="", digits=0):
    return "—" if v is None else f"{safe_float(v, 0):.{digits}f}{suffix}"


def compute_hr_environment_effect(home_abbr: str, temp_f, wind_mph, roof_status=None):
    """Estimated park-and-weather effect, not literal player HR probability."""
    park_factor = safe_float(PARK_FACTORS.get(home_abbr), 1.0)
    temp = safe_float(temp_f, 72.0)
    roof = str(roof_status or PARK_ROOFS.get(home_abbr, "OPEN AIR")).upper()

    park_effect = clip((park_factor - 1.0) * 100.0, -12.0, 20.0)
    temp_effect = clip((temp - 72.0) * 0.32, -7.0, 8.0)
    wind_effect = 0.0

    if roof in {"DOME", "CLOSED", "CLOSED ROOF"}:
        temp_effect = 0.0

    total = clip(park_effect + temp_effect + wind_effect, -18.0, 28.0)
    index_score = int(round(clip(50.0 + total * 1.8, 10.0, 95.0)))

    if total >= 10:
        label, css_class = "STRONG BOOST", "boost"
    elif total >= 4:
        label, css_class = "FAVORABLE", "favorable"
    elif total > -4:
        label, css_class = "NEUTRAL", "neutral"
    elif total > -10:
        label, css_class = "SUPPRESSIVE", "suppressive"
    else:
        label, css_class = "STRONG SUPPRESSION", "strong-suppressive"

    return {
        "effect_pct": round(total, 1),
        "index": index_score,
        "label": label,
        "css": css_class,
        "park_effect": round(park_effect, 1),
        "temp_effect": round(temp_effect, 1),
    }


def _environment_meter_html(effect: dict) -> str:
    """Return compact HTML so Streamlit never treats nested markup as code."""
    pct = safe_float(effect.get("effect_pct"), 0.0)
    sign = "+" if pct > 0 else ""
    index_score = safe_int(effect.get("index"), 50)
    css_class = escape(str(effect.get("css", "neutral")))
    label = escape(str(effect.get("label", "NEUTRAL")))
    park_effect = safe_float(effect.get("park_effect"), 0.0)
    temp_effect = safe_float(effect.get("temp_effect"), 0.0)

    parts = [
        f'<div class="bf-env-card {css_class}">',
        '<div class="bf-env-top">',
        '<div>',
        '<div class="bf-env-kicker">HR ENVIRONMENT METER</div>',
        f'<div class="bf-env-label">{label}</div>',
        '</div>',
        f'<div class="bf-env-number">{sign}{pct:.1f}%</div>',
        '</div>',
        '<div class="bf-env-track">',
        f'<div class="bf-env-fill" style="width:{index_score}%"></div>',
        '</div>',
        f'<div class="bf-env-index">Environment Index: {index_score}/100</div>',
        '<div class="bf-env-components">',
        f'<span>Park {park_effect:+.1f}%</span>',
        f'<span>Temperature {temp_effect:+.1f}%</span>',
        '<span>Wind direction displayed on field</span>',
        '</div>',
        '<div class="bf-env-disclaimer">',
        "Estimated park-and-weather adjustment only. "
        "This is not a player's literal HR probability.",
        '</div>',
        '</div>',
    ]
    return "".join(parts)


def _stadium_svg(home_abbr, weather):
    """Draw a park-specific outfield shape scaled from LF/LCF/CF/RCF/RF."""
    dims = PARK_DIMENSIONS.get(home_abbr)
    if dims and len(dims) >= 5:
        lf, lcf, cf, rcf, rf = [safe_float(value, 0.0) for value in dims[:5]]
    else:
        lf, lcf, cf, rcf, rf = 330.0, 375.0, 400.0, 375.0, 330.0

    gh = weather.get("game_hour", {}) or {}
    direction = gh.get("wind_dir")
    rotation = (safe_float(direction, 0.0) + 180.0) % 360.0 if direction is not None else 0.0

    def radius(distance):
        # Shared scaling preserves real asymmetry while keeping every park visible.
        return 142.0 + clip((distance - 300.0) / 130.0, 0.0, 1.0) * 82.0

    home_x, home_y = 260.0, 304.0
    bearings = (-50.0, -25.0, 0.0, 25.0, 50.0)
    distances = (lf, lcf, cf, rcf, rf)
    points = []
    labels = []

    for angle_deg, distance in zip(bearings, distances):
        angle = math.radians(angle_deg)
        r = radius(distance)
        x = home_x + math.sin(angle) * r
        y = home_y - math.cos(angle) * r
        points.append((x, y))

        label_r = min(r + 15.0, 245.0)
        lx = home_x + math.sin(angle) * label_r
        ly = home_y - math.cos(angle) * label_r
        labels.append((lx, ly))

    # Smooth fence using cubic curves through the five measured points.
    p0, p1, p2, p3, p4 = points
    fence_path = (
        f"M {home_x:.1f} {home_y:.1f} "
        f"L {p0[0]:.1f} {p0[1]:.1f} "
        f"C {(p0[0]+p1[0])/2:.1f} {min(p0[1],p1[1])-8:.1f}, "
        f"{(p0[0]+p1[0])/2:.1f} {min(p0[1],p1[1])-8:.1f}, "
        f"{p1[0]:.1f} {p1[1]:.1f} "
        f"C {(p1[0]+p2[0])/2:.1f} {min(p1[1],p2[1])-10:.1f}, "
        f"{(p1[0]+p2[0])/2:.1f} {min(p1[1],p2[1])-10:.1f}, "
        f"{p2[0]:.1f} {p2[1]:.1f} "
        f"C {(p2[0]+p3[0])/2:.1f} {min(p2[1],p3[1])-10:.1f}, "
        f"{(p2[0]+p3[0])/2:.1f} {min(p2[1],p3[1])-10:.1f}, "
        f"{p3[0]:.1f} {p3[1]:.1f} "
        f"C {(p3[0]+p4[0])/2:.1f} {min(p3[1],p4[1])-8:.1f}, "
        f"{(p3[0]+p4[0])/2:.1f} {min(p3[1],p4[1])-8:.1f}, "
        f"{p4[0]:.1f} {p4[1]:.1f} "
        f"L {home_x:.1f} {home_y:.1f} Z"
    )

    fence_only = fence_path.split(f"L {home_x:.1f} {home_y:.1f} Z")[0]
    names = ("LF", "LCF", "CF", "RCF", "RF")
    label_svg = "".join(
        f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" class="dim">'
        f'{name} {int(round(distance))} ft</text>'
        for (lx, ly), name, distance in zip(labels, names, distances)
    )

    unique_id = re.sub(r"[^A-Za-z0-9_-]", "", str(home_abbr or "park"))
    wind_compass = escape(str(gh.get("wind_compass", "—")))
    wind_text = _fmt_weather(gh.get("wind"), " MPH")

    parts = [
        '<div class="bf-field-wrap">',
        '<svg class="bf-field-svg" viewBox="0 0 520 330" role="img" ',
        'aria-label="Dimension-scaled ballpark field and wind direction">',
        '<defs>',
        f'<linearGradient id="grass-{unique_id}" x1="0" y1="0" x2="0" y2="1">',
        '<stop offset="0" stop-color="#194a32"/>',
        '<stop offset="1" stop-color="#07140f"/>',
        '</linearGradient>',
        f'<linearGradient id="dirt-{unique_id}" x1="0" y1="0" x2="1" y2="0">',
        '<stop offset="0" stop-color="#76532e"/>',
        '<stop offset="1" stop-color="#9b7748"/>',
        '</linearGradient>',
        '</defs>',
        f'<path d="{fence_path}" fill="url(#grass-{unique_id})" stroke="#5c6d87" stroke-width="3"/>',
        f'<path d="{fence_only}" fill="none" stroke="#86a0c6" stroke-width="4"/>',
        f'<path d="M260 304 L174 218 L260 132 L346 218 Z" fill="url(#dirt-{unique_id})" opacity=".92" stroke="#d1b57c"/>',
        '<path d="M260 304 L260 132 M174 218 L346 218" stroke="#d9c59a" stroke-width="1.5" opacity=".55"/>',
        '<circle cx="260" cy="215" r="5" fill="#fff"/>',
        '<rect x="255" y="294" width="10" height="10" transform="rotate(45 260 299)" fill="#fff"/>',
        label_svg,
        f'<g transform="translate(260 154) rotate({rotation:.1f})">',
        '<line x1="0" y1="30" x2="0" y2="-38" stroke="#69a7ff" stroke-width="8" stroke-linecap="round"/>',
        '<path d="M0 -58 L-15 -30 L15 -30 Z" fill="#69a7ff"/>',
        '</g>',
        f'<text x="260" y="187" text-anchor="middle" class="windtxt">FROM {wind_compass} · {wind_text}</text>',
        '</svg>',
        '</div>',
    ]
    return "".join(parts)


def render_weather_game_card(game: dict, preliminary: bool = False):
    home_abbr = resolve_game_park_abbr(game)
    weather = fetch_game_weather_timeline(home_abbr, game.get("game_time", ""))
    gh = weather.get("game_hour", {}) or {}
    roof = PARK_ROOFS.get(home_abbr, "OPEN AIR")
    dims = PARK_DIMENSIONS.get(home_abbr)
    dim_text = " / ".join(str(x) for x in dims) if dims else "Not available"

    if not weather.get("found"):
        current = fetch_weather_for_park(home_abbr)
        gh = {
            "temp": current.get("TempF"),
            "wind": current.get("WindMPH"),
            "wind_dir": current.get("WindDir"),
            "wind_compass": _compass_name(current.get("WindDir")),
            "label": current.get("Condition", "Current conditions"),
            "icon": "🌤️",
            "precip": None,
            "humidity": None,
        }
        weather = {
            "found": bool(current.get("found", False)),
            "game_hour": gh,
            "hours": [],
            "source": current.get("source", "Unavailable"),
        }
        badge = "CURRENT CONDITIONS FALLBACK"
    else:
        badge = "PRELIMINARY" if preliminary else "GAME-TIME FORECAST"

    effect = compute_hr_environment_effect(
        home_abbr, gh.get("temp"), gh.get("wind"), roof
    )
    label = escape(str(gh.get("label", "Conditions unavailable")))
    icon = escape(str(gh.get("icon", "•")))
    game_key = escape(str(game.get("game_key", "")))
    venue = escape(str(game.get("venue", "TBD")))
    source_label = escape(str(weather.get("source", "Unavailable")))
    compass = escape(str(gh.get("wind_compass", "—")))

    card_parts = [
        '<div class="bf-weather-card">',
        '<div class="bf-weather-head">',
        '<div>',
        f'<div class="bf-weather-game">{game_key}</div>',
        f'<div class="bf-weather-venue">{venue} · {format_game_time_et(game.get("game_time",""))}</div>',
        '</div>',
        f'<div class="bf-weather-badge">{escape(badge)}</div>',
        '</div>',
        '<div class="bf-weather-summary">',
        f'<div><b>{icon} {label}</b><span>Condition</span></div>',
        f'<div><b>{_fmt_weather(gh.get("temp"),"°F")}</b><span>Temperature</span></div>',
        f'<div><b>{_fmt_weather(gh.get("precip"),"%")}</b><span>Precipitation</span></div>',
        f'<div><b>{_fmt_weather(gh.get("humidity"),"%")}</b><span>Humidity</span></div>',
        f'<div><b>{_fmt_weather(gh.get("wind")," MPH")}</b><span>From {compass} ({_fmt_weather(gh.get("wind_dir"),"°")})</span></div>',
        f'<div><b>{escape(roof)}</b><span>Roof type</span></div>',
        '</div>',
        '<div class="bf-weather-main">',
        _stadium_svg(home_abbr, weather),
        '<div class="bf-weather-side">',
        '<div class="bf-dim-panel">',
        '<div class="bf-dim-title">Stadium Dimensions</div>',
        '<div class="bf-dim-order">LF / LCF / CF / RCF / RF</div>',
        f'<div class="bf-dim-values">{escape(dim_text)}</div>',
        f'<div class="bf-weather-source">Source: {source_label} · wind direction is where the wind comes from.</div>',
        '</div>',
        _environment_meter_html(effect),
        '</div>',
        '</div>',
        '</div>',
    ]
    st.markdown("".join(card_parts), unsafe_allow_html=True)

    hours = weather.get("hours", [])
    if hours:
        cols = st.columns(len(hours))
        for col, hour in zip(cols, hours):
            border = (
                "2px solid #69a7ff"
                if hour.get("is_game_hour")
                else "1px solid rgba(255,255,255,.10)"
            )
            hour_html = "".join([
                f'<div class="bf-hour" style="border:{border}">',
                f'<div class="bf-hour-time">{hour["time"].strftime("%-I %p")}</div>',
                f'<div class="bf-hour-icon">{escape(str(hour.get("icon","•")))}</div>',
                f'<div class="bf-hour-temp">{_fmt_weather(hour.get("temp"),"°")}</div>',
                f'<div>{_fmt_weather(hour.get("precip"),"%")} rain</div>',
                f'<div>{_fmt_weather(hour.get("wind")," mph")} {escape(str(hour.get("wind_compass","—")))}</div>',
                '</div>',
            ])
            col.markdown(hour_html, unsafe_allow_html=True)


def render_live_weather_board(schedule_rows: list[dict], preliminary: bool = False):
    st.markdown(
        """
        <style>
        .bf-weather-card{border:1px solid #293446;border-radius:13px;background:#0b1018;margin:8px 0 12px;overflow:hidden;max-width:1120px}
        .bf-weather-head{display:flex;justify-content:space-between;gap:10px;padding:9px 11px;background:linear-gradient(90deg,#181b22,#10141b);border-bottom:1px solid rgba(255,255,255,.09)}
        .bf-weather-game{font-size:.92rem;font-weight:950}.bf-weather-venue{color:#9ca9bc;font-size:.67rem;margin-top:2px}
        .bf-weather-badge{align-self:center;border:1px solid #69a7ff;color:#9ac2ff;border-radius:999px;padding:3px 7px;font-size:.54rem;font-weight:900}
        .bf-weather-summary{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:5px;padding:8px}
        .bf-weather-summary>div{background:#111722;border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:6px;text-align:center}
        .bf-weather-summary b{display:block;font-size:.76rem}.bf-weather-summary span{display:block;color:#8996aa;font-size:.48rem;text-transform:uppercase;letter-spacing:.07em;margin-top:3px}
        .bf-weather-main{display:grid;grid-template-columns:minmax(420px,1.7fr) minmax(250px,.55fr);gap:10px;padding:0 8px 8px;align-items:start}
        .bf-field-wrap{border:1px solid rgba(255,255,255,.08);border-radius:10px;background:#050d0a;padding:5px;max-height:300px;overflow:hidden}
        .bf-field-svg{width:100%;height:286px;display:block}.bf-field-svg .dim{fill:#f2f5fa;font-size:12px;font-weight:900;paint-order:stroke;stroke:#07100d;stroke-width:3px;stroke-linejoin:round}.bf-field-svg .windtxt{fill:#9ac2ff;font-size:12px;font-weight:900;paint-order:stroke;stroke:#07100d;stroke-width:3px}
        .bf-weather-side{min-width:0}.bf-dim-panel,.bf-env-card{background:#111722;border:1px solid rgba(255,255,255,.08);border-radius:9px;padding:10px}
        .bf-dim-title{font-weight:950;font-size:.86rem}.bf-dim-order,.bf-weather-source{color:#8f9bad;font-size:.58rem;margin-top:5px}.bf-dim-values{font-size:.92rem;font-weight:950;margin-top:5px}
        .bf-env-card{margin-top:8px}.bf-env-top{display:flex;justify-content:space-between;gap:8px;align-items:center}
        .bf-env-kicker{color:#87aef8;font-size:.50rem;font-weight:950;letter-spacing:.11em}.bf-env-label{font-size:.82rem;font-weight:950;margin-top:3px}
        .bf-env-number{font-size:1.20rem;font-weight:950}.bf-env-track{height:8px;border-radius:999px;background:#202a38;overflow:hidden;margin-top:8px}
        .bf-env-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#ff6666,#ffd166,#35d07f)}
        .bf-env-index{font-size:.58rem;text-align:right;color:#aab4c4;margin-top:3px}
        .bf-env-components{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}.bf-env-components span{font-size:.53rem;border:1px solid rgba(255,255,255,.09);border-radius:999px;padding:3px 6px;color:#b7c0cf}
        .bf-env-disclaimer{font-size:.50rem;color:#7f8b9e;line-height:1.25;margin-top:6px}
        .bf-env-card.boost,.bf-env-card.favorable{border-color:rgba(53,208,127,.50)}
        .bf-env-card.boost .bf-env-label,.bf-env-card.boost .bf-env-number,.bf-env-card.favorable .bf-env-label,.bf-env-card.favorable .bf-env-number{color:#35d07f}
        .bf-env-card.neutral .bf-env-label,.bf-env-card.neutral .bf-env-number{color:#ffd166}
        .bf-env-card.suppressive,.bf-env-card.strong-suppressive{border-color:rgba(255,102,102,.52)}
        .bf-env-card.suppressive .bf-env-label,.bf-env-card.suppressive .bf-env-number,.bf-env-card.strong-suppressive .bf-env-label,.bf-env-card.strong-suppressive .bf-env-number{color:#ff6666}
        .bf-hour{background:#0f141d;border-radius:8px;padding:5px 3px;text-align:center;font-size:.56rem;min-height:78px}
        .bf-hour-time,.bf-hour-temp{font-weight:900}.bf-hour-icon{font-size:1rem;margin:2px}.bf-hour-temp{font-size:.76rem}
        @media(max-width:760px){
          .bf-weather-card{max-width:100%}.bf-weather-summary{grid-template-columns:repeat(3,1fr)}.bf-weather-main{grid-template-columns:1fr}
          .bf-weather-head{padding:8px}.bf-weather-game{font-size:.82rem}.bf-field-wrap{max-height:235px}.bf-field-svg{height:225px}
          .bf-hour{font-size:.48rem;padding:4px 1px;min-height:70px}.bf-field-svg .dim{font-size:11px}.bf-field-svg .windtxt{font-size:10px}
          .bf-dim-panel,.bf-env-card{padding:8px}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if not schedule_rows:
        st.info("No scheduled games are available for weather display.")
        return
    for game in sort_schedule_rows(schedule_rows):
        render_weather_game_card(game, preliminary=preliminary)


@st.cache_data(ttl=1800, max_entries=40)
def get_previous_team_game_pk(team_id: int):
    start_date = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    try:
        start_dt = datetime.now(ZoneInfo("America/New_York"))
        past_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        start_range = (past_dt - timedelta(days=7)).strftime("%Y-%m-%d")
        end_range = (past_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            "https://statsapi.mlb.com/api/v1/schedule"
            f"?sportId=1&teamId={team_id}&startDate={start_range}&endDate={end_range}"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None

    games = []
    for date_block in payload.get("dates", []):
        for game in date_block.get("games", []):
            game_date = game.get("gameDate", "")
            if game.get("status", {}).get("abstractGameState") != "Final":
                continue
            games.append((game_date, game.get("gamePk")))
    if not games:
        return None
    games = sorted(games, key=lambda x: x[0], reverse=True)
    return games[0][1]


@st.cache_data(ttl=1800, max_entries=40)
def fetch_bullpen_fatigue_for_team(team_id: int):
    game_pk = get_previous_team_game_pk(team_id)
    neutral = {
        "BullpenFatigueScore": 0.0,
        "BullpenFatigueNote": "Neutral bullpen rest",
        "BullpenIPPrev": 0.0,
        "BullpenArmsPrev": 0,
        "BullpenPitchesPrev": 0,
    }
    if game_pk is None:
        return neutral

    box = fetch_boxscore(game_pk)
    teams_block = box.get("teams", {}) or {}

    for side in ["away", "home"]:
        team_block = teams_block.get(side, {}) or {}
        team_info = team_block.get("team", {}) or {}
        if team_info.get("id") != team_id:
            continue

        players = team_block.get("players", {}) or {}
        starter_id = None
        for pdata in players.values():
            stats = ((pdata.get("stats") or {}).get("pitching") or {})
            if safe_int(stats.get("gamesStarted", 0)) > 0:
                starter_id = (pdata.get("person") or {}).get("id")
                break

        bullpen_ip = 0.0
        bullpen_pitches = 0
        bullpen_arms = 0

        for pdata in players.values():
            pos_type = ((pdata.get("position") or {}).get("type") or (pdata.get("primaryPosition") or {}).get("type") or "")
            if pos_type != "Pitcher":
                continue

            pid = (pdata.get("person") or {}).get("id")
            if starter_id is not None and pid == starter_id:
                continue

            stats = ((pdata.get("stats") or {}).get("pitching") or {})
            ip = ip_to_float(stats.get("inningsPitched", 0))
            pitches = safe_int(stats.get("numberOfPitches", 0))
            if ip <= 0 and pitches <= 0:
                continue

            bullpen_ip += ip
            bullpen_pitches += pitches
            bullpen_arms += 1

        fatigue_score = 0.0
        notes = []

        if bullpen_ip >= 5.0:
            fatigue_score += 2.1
            notes.append("heavy bullpen usage")
        elif bullpen_ip >= 3.5:
            fatigue_score += 1.1
            notes.append("live bullpen usage")
        else:
            notes.append("rested bullpen")

        if bullpen_arms >= 5:
            fatigue_score += 1.0
            notes.append("many bullpen arms used")
        elif bullpen_arms >= 3:
            fatigue_score += 0.4

        if bullpen_pitches >= 85:
            fatigue_score += 1.0
        elif bullpen_pitches >= 60:
            fatigue_score += 0.5

        if not notes:
            notes.append("neutral bullpen rest")

        return {
            "BullpenFatigueScore": round(fatigue_score, 2),
            "BullpenFatigueNote": " | ".join(notes[:2]),
            "BullpenIPPrev": round(bullpen_ip, 1),
            "BullpenArmsPrev": bullpen_arms,
            "BullpenPitchesPrev": bullpen_pitches,
        }

    return neutral


@st.cache_data(ttl=60, max_entries=4)
def fetch_schedule_payload():
    url = (
        "https://statsapi.mlb.com/api/v1/schedule"
        f"?sportId=1&date={today_str()}&hydrate=probablePitcher"
    )
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=300, max_entries=40)
def get_team_probable_pitcher(team_id: int):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}?hydrate=probablePitcher"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        teams = data.get("teams", [])
        if teams:
            probable = teams[0].get("probablePitcher") or {}
            full_name = probable.get("fullName")
            if full_name and str(full_name).strip():
                return full_name
    except Exception:
        pass
    return None


def resolve_pitcher_name(team_id: int, team_block: dict) -> str:
    probable = (team_block or {}).get("probablePitcher") or {}
    full_name = probable.get("fullName")

    if full_name and str(full_name).strip():
        return full_name

    fallback = get_team_probable_pitcher(team_id)
    if fallback:
        return fallback

    return "Starter Pending"


@st.cache_data(ttl=60, max_entries=4)
def get_today_schedule():
    data = fetch_schedule_payload()

    games = []
    for date in data.get("dates", []):
        for game in date.get("games", []):
            away_block = game["teams"]["away"]
            home_block = game["teams"]["home"]

            away = away_block["team"]["name"]
            home = home_block["team"]["name"]
            away_id = away_block["team"]["id"]
            home_id = home_block["team"]["id"]

            box = fetch_boxscore(game.get("gamePk"))
            away_players = (((box.get("teams") or {}).get("away") or {}).get("players") or {})
            home_players = (((box.get("teams") or {}).get("home") or {}).get("players") or {})
            away_confirmed = sum(1 for p in away_players.values() if str(p.get("battingOrder") or "").strip())
            home_confirmed = sum(1 for p in home_players.values() if str(p.get("battingOrder") or "").strip())

            status = game.get("status", {})
            game_state = status.get("abstractGameState", "Preview")
            detailed_state = status.get("detailedState", "Scheduled")

            away_pitcher_name = resolve_pitcher_name(away_id, away_block)
            home_pitcher_name = resolve_pitcher_name(home_id, home_block)
            away_pitcher_id = ((away_block.get("probablePitcher") or {}).get("id")) or lookup_mlb_person_id_by_name(away_pitcher_name)
            home_pitcher_id = ((home_block.get("probablePitcher") or {}).get("id")) or lookup_mlb_person_id_by_name(home_pitcher_name)

            games.append({
                "game_pk": game["gamePk"],
                "game_key": f"{team_abbr(away)} @ {team_abbr(home)}",
                "away_team": away,
                "home_team": home,
                "away_team_id": away_id,
                "home_team_id": home_id,
                "away_pitcher": away_pitcher_name,
                "home_pitcher": home_pitcher_name,
                "away_pitcher_id": away_pitcher_id,
                "home_pitcher_id": home_pitcher_id,
                "venue": game.get("venue", {}).get("name", "Unknown"),
                "game_time": game.get("gameDate", ""),
                "away_confirmed_count": away_confirmed,
                "home_confirmed_count": home_confirmed,
                "game_state": game_state,
                "detailed_state": detailed_state,
            })

    return sort_schedule_rows(games)


@st.cache_data(ttl=30, max_entries=48)
def fetch_boxscore(game_pk: int):
    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


@st.cache_data(ttl=1800, max_entries=40)
def get_team_hitters(team_id: int):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=active"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        hitters = []
        for row in data.get("roster", []):
            pos_type = row.get("position", {}).get("type", "")
            if pos_type != "Pitcher":
                hitters.append({
                    "player_id": row["person"]["id"],
                    "player_name": row["person"]["fullName"],
                    "position": row.get("position", {}).get("abbreviation", "")
                })

        return hitters
    except Exception:
        return []


@st.cache_data(ttl=1800, max_entries=24)
def fetch_people_stats(person_ids_tuple: tuple, group: str):
    person_ids = [str(x) for x in person_ids_tuple if pd.notna(x)]
    if not person_ids:
        return {}

    results = {}

    for chunk in chunked(person_ids, 40):
        params = {
            "personIds": ",".join(chunk),
            "hydrate": f"stats(group=[{group}],type=[season,gameLog],season={CURRENT_SEASON})"
        }
        try:
            resp = requests.get("https://statsapi.mlb.com/api/v1/people", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            continue

        for person in data.get("people", []):
            pid = person.get("id")
            stats = {"season": {}, "gamelog": []}

            for stat_block in person.get("stats", []):
                stat_type = ((stat_block.get("type") or {}).get("displayName") or "").lower()
                splits = stat_block.get("splits") or []

                if stat_type == "season" and splits:
                    stats["season"] = splits[0].get("stat", {}) or {}
                elif stat_type == "gamelog":
                    game_rows = []
                    for split in splits:
                        game_rows.append({
                            "date": split.get("date"),
                            "stat": split.get("stat", {}) or {}
                        })
                    game_rows = sorted(game_rows, key=lambda x: x.get("date") or "", reverse=True)
                    stats["gamelog"] = game_rows

            results[pid] = stats

    return results


@st.cache_data(ttl=21600, max_entries=4)
def fetch_savant_batter_map(year: int):
    expected_urls = [
        f"https://baseballsavant.mlb.com/leaderboard/expected_statistics?type=batter&year={year}",
        f"https://baseballsavant.mlb.com/leaderboard/expected_statistics?year={year}",
    ]
    percentile_urls = [
        f"https://baseballsavant.mlb.com/leaderboard/percentile-rankings?type=batter&year={year}",
        f"https://baseballsavant.mlb.com/leaderboard/percentile-rankings?year={year}",
    ]
    batted_urls = [
        f"https://baseballsavant.mlb.com/leaderboard/batted-ball?type=batter&year={year}",
        f"https://baseballsavant.mlb.com/leaderboard/batted-ball?year={year}",
    ]

    expected_df = read_html_best_table(expected_urls, ["player", "xslg", "xwoba"])
    percentile_df = read_html_best_table(percentile_urls, ["player", "brl", "ev", "hardhit"])
    batted_df = read_html_best_table(batted_urls, ["player", "air", "ground", "gb"])

    result = {}

    def upsert_row(df: pd.DataFrame, source: str):
        if df.empty:
            return

        player_col = find_col(df, ["player"])
        if player_col is None:
            return

        xslg_col = find_col(df, ["xslg"])
        xwoba_col = find_col(df, ["xwoba"])
        xiso_col = find_col(df, ["xiso"])
        brl_col = find_col(df, ["brl%"])
        ev_col = find_col(df, [" max ev", " ev "])
        hardhit_col = find_col(df, ["hardhit", "hard hit"])
        la_col = find_col(df, [" la ", "launch angle"])
        gb_col = find_col(df, ["gb%"])
        fb_col = find_col(df, ["fb%"])
        ld_col = find_col(df, ["ld%"])
        air_col = find_col(df, ["air%"])

        for _, row in df.iterrows():
            raw_name = row.get(player_col)
            name = normalize_name(raw_name)
            if not name:
                continue

            if name not in result:
                result[name] = {
                    "Savant_xSLG": pd.NA,
                    "Savant_xwOBA": pd.NA,
                    "Savant_xISO": pd.NA,
                    "Savant_Barrel%": pd.NA,
                    "Savant_EV": pd.NA,
                    "Savant_HardHit%": pd.NA,
                    "Savant_LA": pd.NA,
                    "Savant_GB%": pd.NA,
                    "Savant_FB%": pd.NA,
                    "Savant_LD%": pd.NA,
                    "Savant_AIR%": pd.NA,
                }

            if xslg_col is not None and pd.notna(row.get(xslg_col)):
                result[name]["Savant_xSLG"] = safe_float(row.get(xslg_col), pd.NA)
            if xwoba_col is not None and pd.notna(row.get(xwoba_col)):
                result[name]["Savant_xwOBA"] = safe_float(row.get(xwoba_col), pd.NA)
            if xiso_col is not None and pd.notna(row.get(xiso_col)):
                result[name]["Savant_xISO"] = safe_float(row.get(xiso_col), pd.NA)
            if brl_col is not None and pd.notna(row.get(brl_col)):
                result[name]["Savant_Barrel%"] = safe_float(row.get(brl_col), pd.NA)
            if ev_col is not None and pd.notna(row.get(ev_col)):
                result[name]["Savant_EV"] = safe_float(row.get(ev_col), pd.NA)
            if hardhit_col is not None and pd.notna(row.get(hardhit_col)):
                result[name]["Savant_HardHit%"] = safe_float(row.get(hardhit_col), pd.NA)
            if la_col is not None and pd.notna(row.get(la_col)):
                result[name]["Savant_LA"] = safe_float(row.get(la_col), pd.NA)
            if gb_col is not None and pd.notna(row.get(gb_col)):
                result[name]["Savant_GB%"] = safe_float(row.get(gb_col), pd.NA)
            if fb_col is not None and pd.notna(row.get(fb_col)):
                result[name]["Savant_FB%"] = safe_float(row.get(fb_col), pd.NA)
            if ld_col is not None and pd.notna(row.get(ld_col)):
                result[name]["Savant_LD%"] = safe_float(row.get(ld_col), pd.NA)
            if air_col is not None and pd.notna(row.get(air_col)):
                result[name]["Savant_AIR%"] = safe_float(row.get(air_col), pd.NA)

    upsert_row(expected_df, "expected")
    upsert_row(percentile_df, "percentile")
    upsert_row(batted_df, "batted")
    return result


@st.cache_data(ttl=21600, max_entries=80)
def fetch_l10_bbe_profile_from_savant_csv(player_id: int, days_back: int = 30) -> dict:
    """Fast true-L10 BBE pull for final board hitters only.

    This is intentionally cached and only called after the app has reduced the
    slate to real candidate hitters. Nothing about the source is shown on cards.
    """
    empty = {
        "found": False,
        "events": 0,
        "EV": None,
        "HardHit%": None,
        "Barrel%": None,
        "FlyBall%": None,
        "LineDrive%": None,
        "GroundBall%": None,
        "Popup%": None,
        "AIR%": None,
        "AvgLA": None,
    }
    try:
        pid = int(player_id)
    except Exception:
        return empty

    try:
        end_dt = datetime.now(ZoneInfo("America/New_York"))
        start_dt = end_dt - timedelta(days=int(days_back))
        params = {
            "all": "true",
            "player_type": "batter",
            "batter": str(pid),
            "game_date_gt": start_dt.strftime("%Y-%m-%d"),
            "game_date_lt": end_dt.strftime("%Y-%m-%d"),
            "type": "details",
            "min_pitches": "0",
            "min_results": "0",
        }
        resp = requests.get(
            "https://baseballsavant.mlb.com/statcast_search/csv",
            params=params,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        resp.raise_for_status()
        from io import StringIO
        raw = resp.text
        if not raw or "launch_speed" not in raw:
            return empty
        df = pd.read_csv(StringIO(raw))
    except Exception:
        return empty

    if df.empty:
        return empty

    for col in ["launch_speed", "launch_angle"]:
        if col not in df.columns:
            df[col] = pd.NA
    if "bb_type" not in df.columns:
        df["bb_type"] = ""

    bbe = df[
        df["launch_speed"].notna()
        | df["launch_angle"].notna()
        | df["bb_type"].astype(str).str.strip().ne("")
    ].copy()
    if bbe.empty:
        return empty

    sort_cols = [c for c in ["game_date", "game_pk", "at_bat_number", "pitch_number"] if c in bbe.columns]
    if sort_cols:
        bbe = bbe.sort_values(sort_cols, ascending=[False] * len(sort_cols))

    bbe = bbe.head(10).copy()
    if bbe.empty:
        return empty

    def classify_bbe(row):
        bb_type = str(row.get("bb_type", "") or "").lower().strip()
        if bb_type in {"ground_ball", "groundball", "grounder"}:
            return "GB"
        if bb_type in {"line_drive", "linedrive", "liner"}:
            return "LD"
        if bb_type in {"fly_ball", "flyball"}:
            return "FB"
        if bb_type in {"popup", "pop_up", "pop fly", "popfly"}:
            return "PU"
        la = safe_float(row.get("launch_angle"), None)
        if la is None:
            return None
        if la < 10:
            return "GB"
        if la < 25:
            return "LD"
        if la < 50:
            return "FB"
        return "PU"

    types = [classify_bbe(row) for _, row in bbe.iterrows()]
    types = [t for t in types if t is not None]
    if not types:
        return empty

    n = len(types)
    evs = pd.to_numeric(bbe.get("launch_speed"), errors="coerce").dropna().astype(float).tolist()
    las = pd.to_numeric(bbe.get("launch_angle"), errors="coerce").dropna().astype(float).tolist()

    hard = 0
    barrels = 0
    for _, row in bbe.iterrows():
        ev = safe_float(row.get("launch_speed"), None)
        la = safe_float(row.get("launch_angle"), None)
        if ev is not None and ev >= 95.0:
            hard += 1
        if ev is not None and la is not None and ev >= 98.0 and 8.0 <= la <= 50.0:
            barrels += 1

    gb = types.count("GB") / n * 100
    fb = types.count("FB") / n * 100
    ld = types.count("LD") / n * 100
    pu = types.count("PU") / n * 100

    return {
        "found": True,
        "events": n,
        "EV": round(sum(evs) / len(evs), 1) if evs else None,
        "HardHit%": round(hard / n * 100, 1),
        "Barrel%": round(barrels / n * 100, 1),
        "FlyBall%": round(fb, 1),
        "LineDrive%": round(ld, 1),
        "GroundBall%": round(gb, 1),
        "Popup%": round(pu, 1),
        "AIR%": round(fb + ld, 1),
        "AvgLA": round(sum(las) / len(las), 1) if las else None,
    }



def compute_hitter_live_metrics_from_map(player_id: int, stats_map: dict, use_true_bbe: bool = False):
    data = stats_map.get(player_id, {"season": {}, "gamelog": []})
    season_stat = data.get("season", {}) or {}
    gamelog = (data.get("gamelog", []) or [])[:10]

    if not gamelog:
        return None

    true_bbe = {"found": False}
    # SPEED FIX: only final board hitters should trigger this live CSV lookup.
    # Roster/projection screening calls this function with use_true_bbe=False.
    if use_true_bbe:
        true_bbe = fetch_l10_bbe_profile_from_savant_csv(player_id, days_back=30)
        if not isinstance(true_bbe, dict):
            true_bbe = {"found": False}

    ab = sum(safe_int(g["stat"].get("atBats", 0)) for g in gamelog)
    hits = sum(safe_int(g["stat"].get("hits", 0)) for g in gamelog)
    doubles = sum(safe_int(g["stat"].get("doubles", 0)) for g in gamelog)
    triples = sum(safe_int(g["stat"].get("triples", 0)) for g in gamelog)
    hrs = sum(safe_int(g["stat"].get("homeRuns", 0)) for g in gamelog)
    walks = sum(safe_int(g["stat"].get("baseOnBalls", 0)) for g in gamelog)
    strikeouts = sum(safe_int(g["stat"].get("strikeOuts", 0)) for g in gamelog)
    total_bases = sum(safe_int(g["stat"].get("totalBases", 0)) for g in gamelog)
    rbi = sum(safe_int(g["stat"].get("rbi", 0)) for g in gamelog)
    runs = sum(safe_int(g["stat"].get("runs", 0)) for g in gamelog)
    games_played_recent = len(gamelog)

    pa_proxy = max(ab + walks, 1)
    avg = hits / ab if ab else 0.0
    slg = total_bases / ab if ab else 0.0
    iso = max(slg - avg, 0.0)
    xbh = doubles + triples + hrs

    # Fast fallback shape from L10/season box stats. This keeps the app responsive
    # before true L10 BBE is applied to final board hitters.
    recent_ground_outs = sum(safe_int(g["stat"].get("groundOuts", 0)) for g in gamelog)
    recent_air_outs = sum(safe_int(g["stat"].get("airOuts", 0)) for g in gamelog)
    recent_shape_total = recent_ground_outs + recent_air_outs

    season_ground_outs = safe_int(season_stat.get("groundOuts", 0))
    season_air_outs = safe_int(season_stat.get("airOuts", 0))
    season_shape_total = season_ground_outs + season_air_outs

    ev = clip(86 + iso * 18 + (xbh / max(ab, 1)) * 45 + (hits / pa_proxy) * 8, 84, 99)
    hard_hit = clip(26 + iso * 85 + (xbh / pa_proxy) * 140 - (strikeouts / pa_proxy) * 10, 20, 60)
    barrel = clip(2 + iso * 35 + (hrs / pa_proxy) * 160, 1, 20)

    if recent_shape_total > 0:
        gb = clip((recent_ground_outs / recent_shape_total) * 100, 5, 70)
        air_total = clip(100 - gb, 30, 95)
    elif season_shape_total > 0:
        gb = clip((season_ground_outs / season_shape_total) * 100, 20, 65)
        air_total = clip(100 - gb, 35, 80)
    else:
        gb = stable_float(f"{player_id}-gb-fallback", 32, 48)
        air_total = clip(100 - gb, 35, 80)

    ld_share = clip(0.32 + (hard_hit - 40) / 140 + (xbh / max(pa_proxy, 1)) * 0.35 + (hrs / max(pa_proxy, 1)) * 0.45, 0.22, 0.68)
    ld = clip(air_total * ld_share, 10, 65)
    fb = clip(air_total - ld, 8, 65)
    if fb + ld > 0:
        scale = max(0.0, 100.0 - gb) / (fb + ld)
        fb = clip(fb * scale, 0, 80)
        ld = clip(ld * scale, 0, 80)

    if true_bbe.get("found") and safe_int(true_bbe.get("events"), 0) >= 4:
        if true_bbe.get("EV") is not None:
            ev = clip(safe_float(true_bbe.get("EV"), ev), 84, 105)
        hard_hit = clip(safe_float(true_bbe.get("HardHit%"), hard_hit), 0, 100)
        true_barrel = safe_float(true_bbe.get("Barrel%"), barrel)
        barrel = clip((true_barrel * 0.65) + (barrel * 0.35), 0, 30)
        fb = clip(safe_float(true_bbe.get("FlyBall%"), fb), 0, 100)
        ld = clip(safe_float(true_bbe.get("LineDrive%"), ld), 0, 100)
        gb = clip(safe_float(true_bbe.get("GroundBall%"), gb), 0, 100)
        total_shape = fb + ld + gb
        if total_shape > 0:
            scale = 100.0 / total_shape
            fb = round(fb * scale, 1)
            ld = round(ld * scale, 1)
            gb = round(gb * scale, 1)

    air_total = clip(fb + ld, 0, 100)
    l10_bbe_events = safe_int(true_bbe.get("events"), 0) if true_bbe.get("found") else max(1, min(10, ab - strikeouts + doubles + triples + hrs))
    l10_damage_per_bbe = (hrs * 4.0 + xbh * 1.6 + total_bases * 0.18) / max(l10_bbe_events, 1)
    l10_contact_rate = max(0.0, (ab - strikeouts) / max(ab, 1))

    if true_bbe.get("found"):
        l10_bbe_quality = clip(
            max(0.0, ev - 86.0) * 4.0 +
            hard_hit * 0.55 +
            barrel * 1.15 +
            max(0.0, air_total - 40.0) * 0.28 +
            max(0.0, 45.0 - gb) * 0.22 +
            (hrs * 3.0) +
            (xbh * 0.9),
            0.0,
            100.0,
        )
    else:
        l10_bbe_quality = clip(
            (l10_damage_per_bbe * 22.0) +
            (iso * 70.0) +
            (l10_contact_rate * 18.0) +
            (hrs * 4.0) +
            (xbh * 1.1),
            0.0,
            100.0,
        )

    if l10_bbe_quality >= 72:
        l10_bbe_trend = "ELITE"
    elif l10_bbe_quality >= 55:
        l10_bbe_trend = "STRONG"
    elif l10_bbe_quality >= 38:
        l10_bbe_trend = "MIXED"
    else:
        l10_bbe_trend = "COLD"

    season_games = safe_int(season_stat.get("gamesPlayed", 0))
    season_ab = safe_int(season_stat.get("atBats", 0))

    return {
        "EV": round(ev, 1),
        "HardHit%": round(hard_hit, 1),
        "FlyBall%": round(fb, 1),
        "LineDrive%": round(ld, 1),
        "GroundBall%": round(gb, 1),
        "Barrel%": round(barrel, 1),
        "recent_hr": hrs,
        "recent_xbh": xbh,
        "recent_iso": iso,
        "recent_avg": avg,
        "recent_rbi": rbi,
        "recent_runs": runs,
        "recent_pa": pa_proxy,
        "recent_games": games_played_recent,
        "L10_BBE_Events": int(l10_bbe_events),
        "L10_BBE_Quality": round(l10_bbe_quality, 1),
        "L10_BBE_Trend": l10_bbe_trend,
        "L10_BBE_Damage": round(l10_damage_per_bbe, 2),
        "L10_BBE_AvgLA": round(safe_float(true_bbe.get("AvgLA"), 14.0), 1) if true_bbe.get("found") else 14.0,
        "season_games": season_games,
        "season_ab": season_ab,
    }


def compute_pitcher_live_metrics_from_map(pitcher_id: int, pitcher_name: str, stats_map: dict):
    """HR-focused pitcher damage profile.

    This intentionally answers: can this pitcher be taken deep?
    It blends season HR leakage with the recent starter window so a pitcher who
    is generally good but still allows HR damage does not get incorrectly marked
    as a poor target.
    """
    if pd.isna(pitcher_id):
        return None

    data = stats_map.get(pitcher_id, {"season": {}, "gamelog": []})
    season_stat = data.get("season", {}) or {}
    gamelog = data.get("gamelog", []) or []

    season_ip = ip_to_float(season_stat.get("inningsPitched", 0))
    season_hr_allowed = safe_int(season_stat.get("homeRuns", 0))
    season_hits_allowed = safe_int(season_stat.get("hits", 0))
    season_walks_allowed = safe_int(season_stat.get("baseOnBalls", 0))

    season_hr9 = (season_hr_allowed * 9 / season_ip) if season_ip > 0 else stable_float(f"{pitcher_name}-season-hr9-fallback", 0.8, 1.6)
    season_hit9 = (season_hits_allowed * 9 / season_ip) if season_ip > 0 else stable_float(f"{pitcher_name}-season-hit9-fallback", 6.5, 10.5)
    season_whip = ((season_hits_allowed + season_walks_allowed) / season_ip) if season_ip > 0 else stable_float(f"{pitcher_name}-season-whip-fallback", 1.0, 1.5)

    if gamelog:
        starts_only = [g for g in gamelog if safe_int(g["stat"].get("gamesStarted", 0)) > 0]
        use_logs = starts_only[:7] if starts_only else gamelog[:7]
    else:
        use_logs = []

    if use_logs:
        recent_ip = sum(ip_to_float(g["stat"].get("inningsPitched", 0)) for g in use_logs)
        recent_hr_allowed = sum(safe_int(g["stat"].get("homeRuns", 0)) for g in use_logs)
        recent_hits_allowed = sum(safe_int(g["stat"].get("hits", 0)) for g in use_logs)
        recent_walks_allowed = sum(safe_int(g["stat"].get("baseOnBalls", 0)) for g in use_logs)

        recent_hr9 = (recent_hr_allowed * 9 / recent_ip) if recent_ip > 0 else season_hr9
        recent_hit9 = (recent_hits_allowed * 9 / recent_ip) if recent_ip > 0 else season_hit9
        recent_whip = ((recent_hits_allowed + recent_walks_allowed) / recent_ip) if recent_ip > 0 else season_whip
    else:
        recent_hr9 = season_hr9
        recent_hit9 = season_hit9
        recent_whip = season_whip

    # Blend recent with season. Use the higher HR leakage when it is meaningfully above the blend,
    # because HR props care about damage allowed more than real-life run prevention.
    blended_hr9 = (recent_hr9 * 0.55) + (season_hr9 * 0.45)
    hr9 = max(blended_hr9, season_hr9 * 0.92, recent_hr9 * 0.85)
    hit9 = (recent_hit9 * 0.50) + (season_hit9 * 0.50)
    whip = (recent_whip * 0.50) + (season_whip * 0.50)

    barrel_allowed = clip(2.2 + hr9 * 4.8 + (hit9 - 6) * 0.55, 3, 16)
    hard_hit_allowed = clip(25 + hr9 * 9.2 + (whip - 1.0) * 18, 25, 52)

    return {
        "Pitcher_HR9_Last7": round(hr9, 2),
        "Pitcher_Season_HR9": round(season_hr9, 2),
        "Pitcher_Recent_HR9": round(recent_hr9, 2),
        "Pitcher_Barrel_Allowed": round(barrel_allowed, 1),
        "Pitcher_HardHit_Allowed": round(hard_hit_allowed, 1),
    }



def extract_boxscore_team_hitters(game_pk: int, side: str):
    box = fetch_boxscore(game_pk)
    team_box = box.get("teams", {}).get(side, {}) or {}
    players = team_box.get("players", {}) or {}

    hitters = []
    for _, pdata in players.items():
        pos_type = ((pdata.get("position") or {}).get("type") or (pdata.get("primaryPosition") or {}).get("type") or "")
        if pos_type == "Pitcher":
            continue

        person = pdata.get("person", {}) or {}
        pid = person.get("id")
        full_name = person.get("fullName")
        batting_order = pdata.get("battingOrder")

        lineup_spot = None
        if batting_order:
            try:
                lineup_spot = int(str(batting_order)) // 100
            except Exception:
                lineup_spot = None

        hitters.append({
            "player_id": pid,
            "player_name": full_name,
            "lineup_spot": lineup_spot,
            "confirmed": lineup_spot is not None,
        })

    dedup = {}
    for h in hitters:
        if h["player_id"] is not None:
            dedup[h["player_id"]] = h

    return list(dedup.values())


def get_team_candidate_hitters(game_pk: int, team_id: int, side: str, savant_batter_map: dict, deep_bbe: bool = False):
    boxscore_hitters = extract_boxscore_team_hitters(game_pk, side)

    confirmed = [h for h in boxscore_hitters if h["confirmed"]]
    if confirmed:
        confirmed = sorted(confirmed, key=lambda x: x["lineup_spot"] or 99)
        return confirmed[:9], "CONFIRMED"

    candidate_pool = boxscore_hitters
    if not candidate_pool:
        roster_hitters = get_team_hitters(team_id)
        candidate_pool = [{
            "player_id": h["player_id"],
            "player_name": h["player_name"],
            "lineup_spot": None,
            "confirmed": False,
        } for h in roster_hitters]

    if not candidate_pool:
        return [], "PROJECTED"

    stats_map = fetch_people_stats(tuple(h["player_id"] for h in candidate_pool if h["player_id"]), "hitting")

    scored = []
    for h in candidate_pool:
        metrics = compute_hitter_live_metrics_from_map(h["player_id"], stats_map, use_true_bbe=False)
        if metrics is None:
            continue

        sav = savant_batter_map.get(normalize_name(h["player_name"]), {})
        sav_brl = safe_float(sav.get("Savant_Barrel%"), metrics["Barrel%"])
        sav_hh = safe_float(sav.get("Savant_HardHit%"), metrics["HardHit%"])
        sav_fb = safe_float(sav.get("Savant_FB%"), metrics["FlyBall%"])
        sav_ld = safe_float(sav.get("Savant_LD%"), metrics["LineDrive%"])
        sav_air = safe_float(sav.get("Savant_AIR%"), max(0.0, sav_fb + sav_ld))
        sav_xslg = safe_float(sav.get("Savant_xSLG"), 0.0)
        sav_xwoba = safe_float(sav.get("Savant_xwOBA"), 0.0)
        sav_la = safe_float(sav.get("Savant_LA"), 14.0)
        sav_ev = safe_float(sav.get("Savant_EV"), metrics["EV"])
        sav_gb = safe_float(sav.get("Savant_GB%"), metrics["GroundBall%"])

        profile_gate = passes_air_authority_profile(
            hard_hit=sav_hh,
            fly_ball=sav_fb,
            line_drive=sav_ld,
            ground_ball=sav_gb,
            barrel=sav_brl,
            ev=sav_ev,
            xslg=sav_xslg,
            recent_hr=metrics["recent_hr"],
            recent_xbh=metrics["recent_xbh"],
            recent_iso=metrics["recent_iso"],
        )

        projected_statcast_pass = (
            sav_brl >= 10 or
            (sav_hh >= 40 and (sav_air >= 55 or (sav_fb + sav_ld) >= 48)) or
            sav_xslg >= 0.450 or
            sav_xwoba >= 0.340 or
            profile_gate["survives"]
        )

        projected_recent_pass = (
            metrics["recent_hr"] >= 1 or
            metrics["recent_xbh"] >= 3 or
            metrics["recent_iso"] >= 0.180
        )

        gb_survival = (
            profile_gate["survives"]
            or sav_gb < 50
            or (
                sav_gb < 54 and (
                    sav_brl >= 11 or
                    sav_air >= 58 or
                    sav_xslg >= 0.470
                )
            )
        )

        elite_projection_override = (
            sav_brl >= 13
            or sav_xslg >= 0.500
            or sav_ev >= 91
            or (sav_xwoba >= 0.365 and sav_air >= 57)
            or (sav_la >= 15 and sav_la <= 24 and sav_brl >= 11)
            or profile_gate["authority_override"]
        )

        projected_authority_score, projected_authority_multiplier, projected_authority_tier = compute_statcast_authority(
            safe_float(sav.get("Savant_EV"), metrics["EV"]),
            sav_brl,
            sav_hh,
            sav_air,
            sav_la,
            sav_xslg,
            sav_gb,
        )

        strong_projected_candidate = (
            metrics["recent_pa"] >= 12 and
            metrics["season_games"] >= 3 and
            metrics["season_ab"] >= 8 and
            projected_statcast_pass and
            (
                projected_recent_pass
                or elite_projection_override
                or profile_gate["survives"]
                or projected_authority_tier in ["ELITE", "STRONG"]
                or (projected_authority_tier == "MEDIUM" and sav_brl >= 10)
            ) and
            gb_survival
        )

        if projected_authority_tier == "FAIL" and not elite_projection_override:
            strong_projected_candidate = False
        elif projected_authority_tier == "WEAK" and not (elite_projection_override or projected_recent_pass):
            strong_projected_candidate = False
        elif (
            projected_authority_tier == "MEDIUM"
            and sav_brl < 9
            and sav_hh < 39
            and sav_xslg < 0.440
            and not (elite_projection_override or projected_recent_pass or profile_gate["survives"])
        ):
            strong_projected_candidate = False

        if not strong_projected_candidate:
            continue

        lineup_likelihood = (
            sav_brl * 2.8 +
            sav_hh * 1.1 +
            sav_air * 0.50 +
            sav_xslg * 110 +
            sav_xwoba * 70 +
            max(0, 24 - abs(sav_la - 18)) * 0.6 +
            metrics["recent_hr"] * 5.5 +
            metrics["recent_xbh"] * 2.0 +
            metrics["recent_iso"] * 18 +
            projected_authority_score * 0.9
        )

        if projected_authority_tier == "ELITE":
            lineup_likelihood += 10.0
        elif projected_authority_tier == "STRONG":
            lineup_likelihood += 5.0
        elif projected_authority_tier == "MEDIUM":
            lineup_likelihood += 0.5
        elif projected_authority_tier == "WEAK":
            lineup_likelihood -= 8.0

        scored.append({
            **h,
            "lineup_likelihood": lineup_likelihood
        })

    scored = sorted(scored, key=lambda x: x["lineup_likelihood"], reverse=True)[:8]

    for hitter in scored:
        hitter["lineup_spot"] = None

    return scored, "PROJECTED"


def qualifies_hr_profile(
    barrel: float,
    hard_hit: float,
    air_pct: float,
    xslg: float,
    xwoba: float,
    ground_ball: float,
    recent_hr: int,
    recent_xbh: int,
    recent_iso: float,
    recent_pa: float,
    pitch_hr9: float,
    pitch_barrel_allowed: float,
    pitch_hard_hit_allowed: float,
    lineup_source: str,
    fly_ball: float = 0.0,
    line_drive: float = 0.0,
    ev: float = 0.0,
):
    profile_gate = passes_air_authority_profile(
        hard_hit=hard_hit,
        fly_ball=fly_ball,
        line_drive=line_drive,
        ground_ball=ground_ball,
        barrel=barrel,
        ev=ev,
        xslg=xslg,
        recent_hr=recent_hr,
        recent_xbh=recent_xbh,
        recent_iso=recent_iso,
    )

    elite_override = (
        barrel >= 14 or
        hard_hit >= 48 or
        (air_pct >= 65 and hard_hit >= 42) or
        xslg >= 0.520 or
        profile_gate["authority_override"]
    )

    statcast_pass = (
        barrel >= 10 or
        (hard_hit >= 40 and (air_pct >= 55 or profile_gate["air_total"] >= 48)) or
        xslg >= 0.450 or
        xwoba >= 0.340 or
        elite_override or
        profile_gate["survives"]
    )

    recent_form_pass = (
        recent_hr >= 1 or
        recent_xbh >= 3 or
        recent_iso >= 0.180
    )

    pitcher_attackable = (
        pitch_hr9 >= 1.3 or
        pitch_barrel_allowed >= 8 or
        pitch_hard_hit_allowed >= 40
    )

    awful_hr_shape = (
        ground_ball >= 58 or
        (ground_ball >= 55 and air_pct <= 35 and not profile_gate["authority_override"]) or
        (barrel < 5 and hard_hit < 30 and recent_hr == 0)
    )

    weak_recent_profile = (
        recent_hr == 0 and
        recent_xbh <= 1 and
        hard_hit < 35 and
        barrel < 8 and
        air_pct < 50 and
        not profile_gate["survives"]
    )

    projected_damage_profile = (
        statcast_pass and (
            recent_hr >= 1
            or recent_xbh >= 2
            or recent_iso >= 0.150
            or elite_override
            or profile_gate["survives"]
            or (barrel >= 10 and hard_hit >= 40)
            or (hard_hit >= 42 and air_pct >= 55)
            or xslg >= 0.470
        )
    )

    lineup_pass = (
        lineup_source == "CONFIRMED" or
        (lineup_source == "PROJECTED" and projected_damage_profile)
    )

    borderline_gb_survival = (
        profile_gate["survives"]
        or ground_ball < 50
        or elite_override
        or (
            ground_ball < 55 and pitcher_attackable and (
                barrel >= 11 or
                air_pct >= 58 or
                xslg >= 0.470
            )
        )
    )

    hr_eligible = True

    if recent_pa < 8:
        hr_eligible = False
    elif profile_gate["hard_reject"] and not elite_override:
        hr_eligible = False
    elif awful_hr_shape and not elite_override:
        hr_eligible = False
    elif ground_ball >= 55 and not elite_override and not profile_gate["survives"]:
        hr_eligible = False
    elif not borderline_gb_survival:
        hr_eligible = False
    elif not statcast_pass:
        hr_eligible = False
    elif not recent_form_pass and not elite_override and not profile_gate["survives"]:
        hr_eligible = False
    elif weak_recent_profile:
        hr_eligible = False
    elif not lineup_pass:
        hr_eligible = False

    return {
        "hr_eligible": hr_eligible,
        "elite_override": elite_override,
        "statcast_pass": statcast_pass,
        "recent_form_pass": recent_form_pass,
        "pitcher_attackable": pitcher_attackable,
        "awful_hr_shape": awful_hr_shape,
        "weak_recent_profile": weak_recent_profile,
        "air_authority_survival": profile_gate["survives"],
    }



def dedupe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Streamlit/Arrow crashes if a dataframe has duplicate column names."""
    if df is None or df.empty:
        return df
    return df.loc[:, ~df.columns.duplicated()].copy()


def display_existing_columns(df: pd.DataFrame, columns: list[str], **kwargs):
    """Safely display only columns that exist, with duplicate column protection."""
    if df is None or df.empty:
        st.caption("No rows to display.")
        return
    safe_df = dedupe_columns(df)
    cols = [c for c in columns if c in safe_df.columns]
    if not cols:
        st.dataframe(safe_df, use_container_width=True, hide_index=True)
    else:
        st.dataframe(safe_df[cols], use_container_width=True, hide_index=True)


def compute_pitcher_target_score(
    pitch_hr9: float,
    pitch_barrel_allowed: float,
    pitch_hard_hit_allowed: float,
    park_factor: float,
    weather_boost: float,
) -> tuple[float, str]:
    """HR Attackability score.

    Green/high means GOOD for the hitter because the pitcher leaks HR damage.
    Red/low means the pitcher is suppressing the HR profile.
    """
    score = 0.0
    bits = []

    # HR/9 is the anchor. A pitcher around 1.25+ HR/9 is attackable for HR props.
    if pitch_hr9 >= 2.00:
        score += 22.0
        bits.append("elite HR leak")
    elif pitch_hr9 >= 1.60:
        score += 17.0
        bits.append("high HR/9 leak")
    elif pitch_hr9 >= 1.25:
        score += 12.0
        bits.append("attackable HR/9")
    elif pitch_hr9 >= 1.05:
        score += 7.0
        bits.append("mild HR leakage")
    elif pitch_hr9 >= 0.85:
        score += 3.0
        bits.append("below-target HR/9")
    else:
        bits.append("HR suppressor")

    # Barrel / hard-contact allowed should push a pitcher into target range even if ERA looks fine.
    if pitch_barrel_allowed >= 11:
        score += 12.0
        bits.append("barrel-prone pitcher")
    elif pitch_barrel_allowed >= 8:
        score += 8.0
        bits.append("allows barrels")
    elif pitch_barrel_allowed >= 6.5:
        score += 4.0
        bits.append("some barrel leakage")
    else:
        bits.append("low barrel leak")

    if pitch_hard_hit_allowed >= 44:
        score += 9.0
        bits.append("hard contact allowed")
    elif pitch_hard_hit_allowed >= 40:
        score += 6.0
        bits.append("contact damage allowed")
    elif pitch_hard_hit_allowed >= 36:
        score += 3.0
        bits.append("some hard contact")
    else:
        bits.append("contact suppressor")

    park_boost = (park_factor - 1.0) * 20
    if park_boost >= 1.0:
        score += park_boost
        bits.append("HR-friendly park")
    elif park_boost <= -1.0:
        score += park_boost * 0.6
        bits.append("park suppresses HR")

    if weather_boost >= 1.5:
        score += weather_boost * 2.0
        bits.append("carry weather")
    elif weather_boost <= -1.0:
        score += weather_boost * 0.9
        bits.append("weather suppresses carry")

    score = clip(score, 0.0, 45.0)

    if score >= 24:
        label = "STRONG HR ATTACK"
    elif score >= 13:
        label = "MIXED / ATTACKABLE"
    else:
        label = "POOR HR TARGET"

    return round(score, 2), f"{label}: " + " | ".join(bits[:4])



def compute_matchup_advantage_score(
    ev: float,
    barrel: float,
    hard_hit: float,
    air_pct: float,
    xslg: float,
    xwoba: float,
    ground_ball: float,
    pitch_matchup_score: float,
    pitch_hr9: float,
    pitch_barrel_allowed: float,
    pitch_hard_hit_allowed: float,
    handedness_edge: float,
    lineup_spot,
    recent_trend: str,
    statcast_authority_tier: str,
    pitch_mix_mode: str,
    primary_pitch_usage: float,
    park_factor: float,
    weather_boost: float,
) -> tuple[float, str, str]:
    score = 0.0
    reasons = []

    if ev >= 93:
        score += 9
        reasons.append("elite EV")
    elif ev >= 90:
        score += 5
        reasons.append("strong EV")

    if barrel >= 14:
        score += 12
        reasons.append("elite barrel")
    elif barrel >= 11:
        score += 8
        reasons.append("strong barrel")
    elif barrel >= 9:
        score += 4
        reasons.append("usable barrel")

    if hard_hit >= 48:
        score += 8
        reasons.append("elite hard-hit")
    elif hard_hit >= 42:
        score += 4
        reasons.append("hard-hit edge")

    if air_pct >= 62 and ground_ball <= 45:
        score += 8
        reasons.append("great air-ball shape")
    elif air_pct >= 55:
        score += 5
        reasons.append("air-ball path")

    if xslg >= 0.520:
        score += 9
        reasons.append("elite xSLG")
    elif xslg >= 0.470:
        score += 5
        reasons.append("xSLG edge")

    if xwoba >= 0.365:
        score += 4
        reasons.append("xwOBA edge")

    if pitch_matchup_score >= 7:
        score += 9
        reasons.append("major pitch edge")
    elif pitch_matchup_score >= 4.5:
        score += 6
        reasons.append("pitch edge")
    elif pitch_matchup_score >= 3:
        score += 3
        reasons.append("minor pitch edge")

    if pitch_mix_mode == "HARD" and primary_pitch_usage >= 50:
        score += 6
        reasons.append("heavy pitch exposure")
    elif pitch_mix_mode == "HARD" and primary_pitch_usage >= 38:
        score += 4
        reasons.append("clear pitch exposure")
    elif pitch_mix_mode == "SOFT":
        score += 2
        reasons.append("soft pitch exposure")

    if pitch_hr9 >= 2.0:
        score += 10
        reasons.append("target pitcher HR/9")
    elif pitch_hr9 >= 1.6:
        score += 7
        reasons.append("high pitcher HR/9")
    elif pitch_hr9 >= 1.25:
        score += 3
        reasons.append("attackable pitcher HR/9")

    if pitch_barrel_allowed >= 10:
        score += 6
        reasons.append("pitcher barrel leak")
    elif pitch_barrel_allowed >= 8:
        score += 3
        reasons.append("pitcher allows barrels")

    if pitch_hard_hit_allowed >= 43:
        score += 4
        reasons.append("pitcher allows hard contact")

    if handedness_edge >= 1:
        score += 3
        reasons.append("handedness edge")

    try:
        if lineup_spot is not None and str(lineup_spot) != "—":
            spot = int(lineup_spot)
            if spot <= 4:
                score += 5
                reasons.append("premium lineup slot")
            elif spot <= 6:
                score += 2
                reasons.append("playable lineup slot")
    except Exception:
        pass

    if recent_trend == "HOT":
        score += 5
        reasons.append("hot form")
    elif recent_trend == "LIVE":
        score += 3
        reasons.append("live form")
    elif recent_trend == "COLD":
        score -= 4
        reasons.append("cold-form caution")

    if statcast_authority_tier == "ELITE":
        score += 7
        reasons.append("elite Statcast authority")
    elif statcast_authority_tier == "STRONG":
        score += 4
        reasons.append("strong Statcast authority")
    elif statcast_authority_tier in {"WEAK", "FAIL"}:
        score -= 6
        reasons.append("weak authority caution")

    park_boost = (park_factor - 1.0) * 20
    if park_boost >= 1:
        score += park_boost
        reasons.append("park boost")

    if weather_boost >= 1.5:
        score += weather_boost * 2
        reasons.append("weather carry")
    elif weather_boost <= -1:
        score += weather_boost
        reasons.append("weather suppression")

    if ground_ball >= 55:
        score -= 12
        reasons.append("severe GB risk")
    elif ground_ball >= 50:
        score -= 7
        reasons.append("GB downgrade")
    elif ground_ball >= 45:
        score -= 3
        reasons.append("borderline GB")

    if score >= 55:
        label = "HIGH"
    elif score >= 38:
        label = "MED"
    else:
        label = "LOW"

    if not reasons:
        reasons = ["ranked by blended matchup score"]

    return round(score, 2), label, " | ".join(reasons[:7])


def get_best_hr_matchups(df: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    """Rank the strongest available HR matchups across full and preview schemas.

    Current-day boards normally contain ``HR Eligible``. Tomorrow/early-preview
    frames may not yet have that field, so the function falls back to all
    available rows instead of crashing.
    """
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    board = dedupe_columns(df.copy())

    if "Matchup Advantage Score" not in board.columns:
        board["Matchup Advantage Score"] = safe_numeric_series(
            board, "Model Rank Score", 0.0
        )

    if "HR Attackability Score" not in board.columns:
        board["HR Attackability Score"] = (
            safe_numeric_series(board, "Pitcher_HR9_Last7", 0.0) * 10
        )

    if "HR Eligible" in board.columns:
        raw = board["HR Eligible"]
        if pd.api.types.is_bool_dtype(raw):
            mask = raw.fillna(False)
        else:
            normalized = raw.fillna("").astype(str).str.strip().str.lower()
            mask = normalized.isin(
                {"true", "1", "yes", "y", "eligible", "pass"}
            )
        eligible = board[mask].copy()
        if eligible.empty:
            eligible = board.copy()
    else:
        eligible = board.copy()

    eligible["_global_score"] = (
        safe_numeric_series(eligible, "Matchup Advantage Score", 0.0) * 1.35
        + safe_numeric_series(eligible, "HR Attackability Score", 0.0) * 1.10
        + safe_numeric_series(eligible, "Statcast Authority Score", 0.0) * 0.85
        + safe_numeric_series(eligible, "Model Rank Score", 0.0) * 0.05
        + safe_numeric_series(eligible, "HR Probability %", 0.0) * 1.40
    )

    eligible = (
        eligible.sort_values("_global_score", ascending=False)
        .drop(columns=["_global_score"])
        .head(max(1, int(limit)))
    )
    return add_rank_column(dedupe_columns(eligible.reset_index(drop=True)))


def get_pitchers_to_target(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    work = df.copy()
    for col in [
        "Game", "Pitcher", "Pitcher_HR9_Last7", "Pitcher_Barrel_Allowed",
        "Pitcher_HardHit_Allowed", "Pitcher_Season_HR9", "Pitcher_Recent_HR9", "TempF", "WindMPH", "WeatherNote", "WeatherBoost"
    ]:
        if col not in work.columns:
            work[col] = pd.NA

    work["_bf_pitcher_target_score"] = (
        safe_numeric_series(work, "Pitcher_HR9_Last7", 0.0) * 12
        + safe_numeric_series(work, "Pitcher_Barrel_Allowed", 0.0) * 1.8
        + safe_numeric_series(work, "Pitcher_HardHit_Allowed", 0.0) * 0.8
        + safe_numeric_series(work, "WeatherBoost", 0.0) * 4
    )

    out = (
        work.sort_values("_bf_pitcher_target_score", ascending=False)
        .drop_duplicates(subset=["Game", "Pitcher"])
        .head(15)
        .copy()
    )
    out["HR Attackability Score"] = pd.to_numeric(out["_bf_pitcher_target_score"], errors="coerce").fillna(0.0).round(2)
    out["HR Attackability Score"] = out["HR Attackability Score"]

    final_cols = [
        "Game", "Pitcher", "HR Attackability Score", "Pitcher_HR9_Last7", "Pitcher_Season_HR9", "Pitcher_Recent_HR9",
        "Pitcher_Barrel_Allowed", "Pitcher_HardHit_Allowed",
        "WeatherNote", "TempF", "WindMPH"
    ]
    out = out[[c for c in final_cols if c in out.columns]].copy()
    return dedupe_columns(out.reset_index(drop=True))



def build_hitter_metrics(
    player_id: int,
    player_name: str,
    team: str,
    opp_pitcher: str,
    park_factor: float,
    opp_pitcher_id,
    lineup_spot,
    lineup_source,
    hitter_stats_map,
    pitcher_stats_map,
    savant_batter_map,
    hand_map: dict | None = None,
    weather_boost: float = 0.0,
    weather_note: str = "neutral weather",
    temp_f: float = 72.0,
    wind_mph: float = 7.0,
    bullpen_fatigue_score: float = 0.0,
    bullpen_fatigue_note: str = "Neutral bullpen rest",
    bullpen_ip_prev: float = 0.0,
    bullpen_arms_prev: int = 0,
    deep_bbe: bool = False,
):
    if opp_pitcher_id is None or (isinstance(opp_pitcher_id, float) and pd.isna(opp_pitcher_id)):
        opp_pitcher_id = lookup_mlb_person_id_by_name(opp_pitcher)

    live_hitter = compute_hitter_live_metrics_from_map(player_id, hitter_stats_map, use_true_bbe=deep_bbe)
    live_pitcher = compute_pitcher_live_metrics_from_map(
        opp_pitcher_id,
        opp_pitcher,
        pitcher_stats_map,
    )

    if live_hitter is None:
        return None

    sav = savant_batter_map.get(normalize_name(player_name), {})

    ev = safe_float(sav.get("Savant_EV"), live_hitter["EV"])
    hard_hit = safe_float(sav.get("Savant_HardHit%"), live_hitter["HardHit%"])
    fly_ball = safe_float(sav.get("Savant_FB%"), live_hitter["FlyBall%"])
    line_drive = safe_float(sav.get("Savant_LD%"), live_hitter["LineDrive%"])
    ground_ball = safe_float(sav.get("Savant_GB%"), live_hitter["GroundBall%"])
    barrel = safe_float(sav.get("Savant_Barrel%"), live_hitter["Barrel%"])
    air_pct = safe_float(sav.get("Savant_AIR%"), max(0.0, 100 - ground_ball))
    launch_angle = safe_float(sav.get("Savant_LA"), 14.0)
    xslg = safe_float(sav.get("Savant_xSLG"), 0.0)
    xwoba = safe_float(sav.get("Savant_xwOBA"), 0.0)
    xiso = safe_float(sav.get("Savant_xISO"), live_hitter["recent_iso"])

    recent_hr = live_hitter["recent_hr"]
    recent_xbh = live_hitter["recent_xbh"]
    recent_iso = live_hitter["recent_iso"]
    recent_avg = live_hitter["recent_avg"]
    recent_rbi = live_hitter["recent_rbi"]
    recent_runs = live_hitter["recent_runs"]
    recent_pa = live_hitter["recent_pa"]

    recent_damage_score = (
        (recent_hr * 9.0) +
        (recent_xbh * 3.0) +
        (recent_iso * 65.0) +
        (recent_avg * 18.0)
    )

    if recent_hr >= 2 or recent_xbh >= 5 or recent_iso >= 0.260:
        recent_trend = "HOT"
    elif recent_hr >= 1 or recent_xbh >= 3 or recent_iso >= 0.180:
        recent_trend = "LIVE"
    elif recent_iso >= 0.120 or recent_avg >= 0.260:
        recent_trend = "NEUTRAL"
    else:
        recent_trend = "COLD"

    display_spot = display_lineup_spot(lineup_spot)
    hand_map = hand_map or {}
    bats = get_true_batter_hand(player_id, hand_map)
    pitcher_throws = get_true_pitcher_hand(opp_pitcher_id, hand_map)

    if live_pitcher is None:
        pitch_hr9 = stable_float(f"{opp_pitcher}-hr9", 0.7, 1.9)
        pitch_barrel_allowed = stable_float(f"{opp_pitcher}-barrel-allowed", 4, 13)
        pitch_hard_hit_allowed = stable_float(f"{opp_pitcher}-hh-allowed", 30, 48)
    else:
        pitch_hr9 = live_pitcher["Pitcher_HR9_Last7"]
        pitch_barrel_allowed = live_pitcher["Pitcher_Barrel_Allowed"]
        pitch_hard_hit_allowed = live_pitcher["Pitcher_HardHit_Allowed"]

    pullside_boost = stable_float(f"{player_id}-pull", -1, 3)
    park_boost = (park_factor - 1.0) * 20
    weather_score_boost = weather_boost * 1.6
    bullpen_fatigue_boost = bullpen_fatigue_score * 1.8

    pitch_mix_example = build_pitch_mix_profile(opp_pitcher, opp_pitcher_id)
    arsenal_tiles = build_matchup_arsenal_tiles(opp_pitcher_id, player_id, 0.0, 0.0, include_batter=deep_bbe)
    pitch_context = compute_relevant_pitch_matchup(
        pitch_mix_example,
        bats,
        pitcher_throws,
        barrel,
        hard_hit,
        air_pct,
        launch_angle,
        xslg,
        xwoba,
        ground_ball,
    )
    pitch_mix_mode = pitch_context["mode"]
    relevant_pitch_mix = pitch_context["label"]
    primary_pitch = pitch_context["primary_pitch"]
    primary_pitch_usage = pitch_context["usage"]
    pitch_gap = pitch_context["gap"]
    pitch_matchup_score = pitch_context["score"]
    pitch_matchup_label = pitch_context["reason"]
    handedness_edge = pitch_context["handedness_edge"]

    pitch_isolation_bonus = -2.5
    pitch_isolation_valid = "No"

    elite_statcast_profile = (
        (
            barrel >= 10
            and hard_hit >= 45
            and air_pct >= 55
            and ground_ball <= 50
        )
        or (
            barrel >= 11
            and xslg >= 0.500
            and xwoba >= 0.340
            and 10 <= launch_angle <= 24
        )
    )

    weak_pitch_shape = (
        barrel < 9 and hard_hit < 39 and xslg < 0.430 and air_pct < 52
    )

    statcast_authority_score, statcast_authority_multiplier, statcast_authority_tier = compute_statcast_authority(
        ev,
        barrel,
        hard_hit,
        air_pct,
        launch_angle,
        xslg,
        ground_ball,
    )

    multi_pitch_authority_score = compute_multi_pitch_authority_score(
        pitch_mix_mode,
        pitch_matchup_score,
        barrel,
        hard_hit,
        air_pct,
        xslg,
        ev,
        lineup_spot,
        recent_trend,
    )

    pitcher_target_score, pitcher_target_label = compute_pitcher_target_score(
        pitch_hr9,
        pitch_barrel_allowed,
        pitch_hard_hit_allowed,
        park_factor,
        weather_boost,
    )

    matchup_advantage_score, matchup_advantage_tier, ranking_reasons = compute_matchup_advantage_score(
        ev=ev,
        barrel=barrel,
        hard_hit=hard_hit,
        air_pct=air_pct,
        xslg=xslg,
        xwoba=xwoba,
        ground_ball=ground_ball,
        pitch_matchup_score=pitch_matchup_score,
        pitch_hr9=pitch_hr9,
        pitch_barrel_allowed=pitch_barrel_allowed,
        pitch_hard_hit_allowed=pitch_hard_hit_allowed,
        handedness_edge=handedness_edge,
        lineup_spot=lineup_spot,
        recent_trend=recent_trend,
        statcast_authority_tier=statcast_authority_tier,
        pitch_mix_mode=pitch_mix_mode,
        primary_pitch_usage=primary_pitch_usage,
        park_factor=park_factor,
        weather_boost=weather_boost,
    )

    elite_hr_flag = elite_hr_look(pd.Series({
        "Barrel%": barrel,
        "HardHit%": hard_hit,
        "AIR%": air_pct,
        "xSLG": xslg,
        "EV": ev,
        "GroundBall%": ground_ball,
    }))

    if pitch_mix_mode == "HARD" and primary_pitch is not None:
        pitch_isolation_valid = "Yes"
        pitch_isolation_bonus = pitch_matchup_score
    elif pitch_mix_mode == "SOFT":
        if weak_pitch_shape and not elite_statcast_profile:
            pitch_isolation_valid = "Soft No Edge"
            pitch_isolation_bonus = min(pitch_matchup_score - 2.0, -0.75)
        else:
            pitch_isolation_valid = "Soft Isolate"
            pitch_isolation_bonus = pitch_matchup_score * 0.96
    elif pitch_mix_mode == "BALANCED":
        if weak_pitch_shape and not elite_statcast_profile and not (barrel >= 10 or hard_hit >= 42 or xslg >= 0.470):
            pitch_isolation_valid = "Balanced No Edge"
            pitch_isolation_bonus = min(pitch_matchup_score - 2.0, -1.0)
        else:
            pitch_isolation_valid = "Balanced Mix"
            pitch_isolation_bonus = pitch_matchup_score * 0.92
    elif elite_statcast_profile:
        pitch_isolation_valid = "Elite Statcast Override"
        pitch_isolation_bonus = 2.25

    if pitch_isolation_valid != "No":
        if pitch_isolation_valid == "Elite Statcast Override":
            pitch_isolation_bonus = pitch_isolation_bonus * max(statcast_authority_multiplier, 0.75)
        else:
            pitch_isolation_bonus = pitch_isolation_bonus * statcast_authority_multiplier

    if statcast_authority_tier == "FAIL" and pitch_mix_mode != "HARD" and not elite_statcast_profile:
        pitch_isolation_bonus = min(pitch_isolation_bonus, -3.5)
    elif statcast_authority_tier == "WEAK" and pitch_mix_mode == "BALANCED" and not elite_statcast_profile:
        pitch_isolation_bonus = min(pitch_isolation_bonus, -2.0)

    gb_status = "PASS"
    if ground_ball >= 55:
        gb_status = "AUTO NO"
    elif ground_ball >= 50:
        gb_status = "HEAVY DOWNGRADE"
    elif ground_ball >= 45:
        gb_status = "CAUTION"

    qual = qualifies_hr_profile(
        barrel=barrel,
        hard_hit=hard_hit,
        air_pct=air_pct,
        xslg=xslg,
        xwoba=xwoba,
        ground_ball=ground_ball,
        recent_hr=recent_hr,
        recent_xbh=recent_xbh,
        recent_iso=recent_iso,
        recent_pa=recent_pa,
        pitch_hr9=pitch_hr9,
        pitch_barrel_allowed=pitch_barrel_allowed,
        pitch_hard_hit_allowed=pitch_hard_hit_allowed,
        lineup_source=lineup_source,
    )

    hr_eligible = qual["hr_eligible"]
    statcast_pass = qual["statcast_pass"]
    recent_form_pass = qual["recent_form_pass"]
    pitcher_attackable = qual["pitcher_attackable"]
    elite_override = qual["elite_override"]
    awful_hr_shape = qual["awful_hr_shape"]
    weak_recent_profile = qual["weak_recent_profile"]

    confirmed_keep_override = bool(
        lineup_source == "CONFIRMED"
        and lineup_spot is not None
        and lineup_spot <= 4
        and pitch_mix_mode == "HARD"
        and pitch_matchup_score >= 5.0
    )

    confirmed_authority_fail = bool(
        lineup_source == "CONFIRMED"
        and statcast_authority_tier in {"FAIL", "WEAK"}
        and ev < 90.0
        and barrel < 12.0
        and hard_hit < 40.0
        and xslg < 0.450
        and not elite_override
    )

    confirmed_blend_fail = bool(
        lineup_source == "CONFIRMED"
        and pitch_mix_mode != "HARD"
        and ev < 90.0
        and barrel < 11.0
        and hard_hit < 41.0
        and xslg < 0.455
        and air_pct < 55.0
        and not elite_override
    )

    if (confirmed_authority_fail or confirmed_blend_fail) and not confirmed_keep_override:
        hr_eligible = False

    base_score = (
        (barrel - 4) * 4.2 +
        (hard_hit - 28) * 2.5 +
        (air_pct - 45) * 1.2 +
        (ev - 87) * 1.1 +
        (xslg * 100) * 1.2 +
        (xiso * 100) * 0.7 +
        (xwoba * 100) * 0.45 +
        pitch_isolation_bonus +
        handedness_edge +
        (pitch_hr9 - 0.7) * 10.0 +
        (pitch_barrel_allowed - 4) * 0.9 +
        (pitch_hard_hit_allowed - 30) * 0.4 +
        (recent_hr * 3.2) +
        (recent_xbh * 1.5) +
        (recent_iso * 24.0) +
        (recent_damage_score * 0.22) +
        pullside_boost +
        park_boost +
        weather_score_boost +
        bullpen_fatigue_boost +
        (pitcher_target_score * 0.35) +
        (matchup_advantage_score * 0.28)
    )

    if statcast_authority_tier == "ELITE":
        base_score += 4.5
    elif statcast_authority_tier == "STRONG":
        base_score += 2.0
    elif statcast_authority_tier == "MEDIUM":
        base_score -= 0.5
    elif statcast_authority_tier == "WEAK":
        base_score -= 4.0
    else:
        base_score -= 8.0

    if lineup_spot is not None:
        if lineup_spot <= 4:
            base_score += 3.5
        elif lineup_spot <= 6:
            base_score += 1.5
        else:
            base_score -= 1.0

    if ground_ball < 40:
        base_score += 4.0
    elif 45 <= ground_ball < 50:
        base_score -= 7.0
    elif 50 <= ground_ball < 55:
        base_score -= 14.0
    elif ground_ball >= 55:
        base_score -= 25.0

    if air_pct >= 65:
        base_score += 5.0
    elif air_pct >= 55:
        base_score += 2.0
    elif air_pct < 45:
        base_score -= 7.0

    if 12 <= launch_angle <= 22:
        base_score += 3.0
    elif 8 <= launch_angle < 12 or 22 < launch_angle <= 28:
        base_score += 1.0
    else:
        base_score -= 2.0

    if barrel >= 14:
        base_score += 6.0
    elif barrel < 8:
        base_score -= 7.0

    if hard_hit >= 45:
        base_score += 5.0
    elif hard_hit < 35:
        base_score -= 7.0

    if pitch_mix_mode == "HARD" and primary_pitch_usage >= 50:
        base_score += 2.8
    elif pitch_mix_mode == "HARD" and pitch_gap > 20:
        base_score += 1.8
    elif pitch_mix_mode == "SOFT":
        base_score += 0.9

    if not pitcher_attackable:
        base_score -= 4.0
    if weak_recent_profile:
        base_score -= 10.0
    if awful_hr_shape:
        base_score -= 14.0
    if recent_trend == "HOT":
        base_score += 4.0
    elif recent_trend == "LIVE":
        base_score += 2.0
    elif recent_trend == "COLD":
        base_score -= 4.0
    if lineup_source == "PROJECTED" and lineup_spot is None:
        if (
            statcast_authority_tier in {"ELITE", "STRONG"}
            or barrel >= 10.0
            or xslg >= 0.470
            or hard_hit >= 42.0
            or recent_trend in {"HOT", "LIVE"}
            or pitch_mix_mode in {"HARD", "SOFT"}
            or pitch_matchup_score >= 4.5
        ):
            base_score -= 1.25
        else:
            base_score -= 4.0
    if elite_override and ground_ball < 55:
        base_score += 2.5

    if not hr_eligible and elite_hr_flag and lineup_source == "PROJECTED":
        hr_prob = max(7.5, min(18.0, base_score / 7.0))
    elif not hr_eligible:
        hr_prob = 0.0
    else:
        hr_prob = max(3.0, min(28.0, (base_score + multi_pitch_authority_score * 2.2) / 6.6))

    if elite_hr_flag and hr_prob < 10.5:
        hr_prob = 10.5

    hrr_score = (
        (ev - 87) * 1.1 +
        (hard_hit - 28) * 1.0 +
        (line_drive - 14) * 0.9 +
        (pitch_hard_hit_allowed - 30) * 0.4 +
        park_boost +
        (recent_runs * 0.7) +
        (recent_rbi * 0.7) +
        (recent_avg * 15) +
        (weather_boost * 0.8) +
        (bullpen_fatigue_score * 0.7)
    )
    if lineup_spot is not None:
        hrr_score += max(0, 10 - lineup_spot) * 1.5

    gb_note = get_gb_explanation(ground_ball, barrel, air_pct, xslg)

    reasons = []
    reasons.append(f"{lineup_source} lineup pool")
    reasons.append("Statcast damage pass" if statcast_pass else "Failed Statcast damage")
    reasons.append("Pitcher attackable" if pitcher_attackable else "Pitcher less attackable")
    reasons.append("Recent damage form" if recent_form_pass else "Weak recent form")

    if pitch_isolation_valid == "Yes" and elite_statcast_profile:
        reasons.append("Elite + isolation combo")
    elif pitch_isolation_valid in ["Yes", "Soft Isolate", "Balanced Mix"]:
        reasons.append(pitch_matchup_label)
    elif multi_pitch_authority_score >= 3.5:
        reasons.append("Multi-pitch authority path")
    elif pitch_isolation_valid == "Elite Statcast Override":
        reasons.append("Elite Statcast override")
    else:
        reasons.append("No pitch edge")

    if recent_trend == "HOT":
        reasons.append("Hot recent trend")
    elif recent_trend == "LIVE":
        reasons.append("Live recent trend")
    elif recent_trend == "COLD":
        reasons.append("Cold recent trend")
    else:
        reasons.append("Neutral recent trend")

    if weather_boost >= 1.5:
        reasons.append("Weather carry boost")
    elif weather_boost <= -1.0:
        reasons.append("Weather suppression")
    else:
        reasons.append("Neutral weather")

    if statcast_authority_tier == "ELITE":
        reasons.append("Elite Statcast authority")
    elif statcast_authority_tier == "STRONG":
        reasons.append("Strong Statcast authority")
    elif statcast_authority_tier == "MEDIUM":
        reasons.append("Moderate Statcast authority")
    elif statcast_authority_tier == "WEAK":
        reasons.append("Weak Statcast authority")
    else:
        reasons.append("Statcast authority fail")

    if bullpen_fatigue_score >= 2.0:
        reasons.append("Bullpen fatigue boost")
    elif bullpen_fatigue_score >= 0.8:
        reasons.append("Bullpen slightly taxed")
    else:
        reasons.append("Bullpen rested")

    if ground_ball >= 50:
        reasons.append("Heavy GB downgrade")
    elif ground_ball >= 45:
        reasons.append("Borderline GB caution")
    else:
        reasons.append("Clean launch shape")

    if barrel >= 12:
        reasons.append("Strong barrel")
    elif hard_hit >= 40:
        reasons.append("Hard-hit target")
    elif air_pct >= 55:
        reasons.append("Air-ball target")

    model_rank_score = (
        (barrel * 5.6) +
        (hard_hit * 3.0) +
        (air_pct * 1.5) +
        (xslg * 145) +
        (xwoba * 72) +
        (max(0, 24 - abs(launch_angle - 18)) * 1.5) +
        (pitch_hr9 * 8.0) +
        (pitch_barrel_allowed * 1.1) +
        (recent_hr * 5.0) +
        (recent_xbh * 1.8) +
        (recent_iso * 24.0) +
        (recent_damage_score * 0.35) +
        (pitch_matchup_score * 2.1) +
        (handedness_edge * 1.7) +
        (weather_boost * 4.0) +
        (bullpen_fatigue_score * 4.8) +
        (statcast_authority_score * 1.55) +
        (multi_pitch_authority_score * 3.0) +
        (pitcher_target_score * 1.15) +
        (matchup_advantage_score * 1.05)
    )

    if pitch_isolation_valid == "Yes":
        model_rank_score += 7.5
    elif pitch_isolation_valid == "Elite Statcast Override":
        model_rank_score += 5.0

    if pitch_mix_mode == "HARD" and primary_pitch_usage >= 50:
        model_rank_score += 4.0
    elif pitch_mix_mode == "HARD" and pitch_gap > 20:
        model_rank_score += 2.0
    elif pitch_mix_mode == "SOFT":
        model_rank_score += 1.5
    elif pitch_mix_mode == "BALANCED" and elite_hr_flag:
        model_rank_score += 3.0

    if recent_trend == "HOT":
        model_rank_score += 6.0
    elif recent_trend == "LIVE":
        model_rank_score += 3.0
    elif recent_trend == "COLD":
        model_rank_score -= 5.0

    if ground_ball >= 55:
        model_rank_score -= 18.0
    elif ground_ball >= 50:
        model_rank_score -= 10.0
    elif ground_ball >= 45:
        model_rank_score -= 4.0

    if lineup_spot is not None:
        if lineup_spot <= 4:
            model_rank_score += 5.0
        elif lineup_spot <= 6:
            model_rank_score += 2.0

    strict_flag = strict_statcast_ok(pd.Series({
        "Statcast Pass": "Yes" if statcast_pass else "No",
        "GroundBall%": ground_ball,
        "Barrel%": barrel,
        "AIR%": air_pct,
        "xSLG": xslg,
    }))

    advanced_scores = compute_advanced_prediction_scores(
        hr_probability=hr_prob,
        ev=ev,
        barrel=barrel,
        hard_hit=hard_hit,
        fly_ball=fly_ball,
        line_drive=line_drive,
        ground_ball=ground_ball,
        air_pct=air_pct,
        xslg=xslg,
        pitch_hr9=pitch_hr9,
        pitcher_attackability=pitcher_target_score,
        matchup_advantage=matchup_advantage_score,
        weather_boost=weather_boost,
        park_factor=park_factor,
        lineup_spot=lineup_spot,
        recent_hr=recent_hr,
        recent_trend=recent_trend,
        elite_hr_flag=elite_hr_flag,
    )

    return {
        "Player ID": player_id,
        "Pitcher ID": opp_pitcher_id,
        "Player": player_name,
        "Team": team,
        "Bats": bats,
        "Pitcher Throws": pitcher_throws,
        "Pitch Mix Mode": pitch_mix_mode,
        "Relevant Pitch Mix": relevant_pitch_mix,
        "Primary Pitch": primary_pitch if primary_pitch is not None else "Mix",
        "Primary Pitch Usage": round(primary_pitch_usage, 1),
        "True Pitch Arsenal": json.dumps(arsenal_tiles),
        "Pitch Gap": round(pitch_gap, 1),
        "Pitch Matchup Score": round(pitch_matchup_score, 2),
        "Handedness Edge": round(handedness_edge, 2),
        "Lineup Spot": display_spot,
        "Lineup Source": lineup_source,
        "EV": round(ev, 1),
        "HardHit%": round(hard_hit, 1),
        "FlyBall%": round(fly_ball, 1),
        "LineDrive%": round(line_drive, 1),
        "GroundBall%": round(ground_ball, 1),
        "Barrel%": round(barrel, 1),
        "AIR%": round(air_pct, 1),
        "LaunchAngle": round(launch_angle, 1),
        "Recent Trend": recent_trend,
        "xSLG": round(xslg, 3) if xslg else 0.0,
        "xwOBA": round(xwoba, 3) if xwoba else 0.0,
        "Pitcher": opp_pitcher,
        "Pitcher_HR9_Last7": round(pitch_hr9, 2),
        "Pitcher_Barrel_Allowed": round(pitch_barrel_allowed, 1),
        "Pitcher_HardHit_Allowed": round(pitch_hard_hit_allowed, 1),
        "Statcast Pass": "Yes" if statcast_pass else "No",
        "Recent Form Pass": "Yes" if recent_form_pass else "No",
        "Pitcher Attackable": "Yes" if pitcher_attackable else "No",
        "Pitch_Isolation_Valid": pitch_isolation_valid,
        "GB Rule": gb_status,
        "GB Note": gb_note,
        "HR Eligible": hr_eligible,
        "Strict Statcast": "Yes" if strict_flag else "No",
        "Elite HR Look": "Yes" if elite_hr_flag else "No",
        "Multi Pitch Authority Score": round(multi_pitch_authority_score, 2),
        "HR Probability %": round(hr_prob, 1),
        "Prediction Quality Score": advanced_scores["Prediction Quality Score"],
        "Prediction Quality Grade": advanced_scores["Prediction Quality Grade"],
        "Moonshot Score": advanced_scores["Moonshot Score"],
        "2 HR Score": advanced_scores["2 HR Score"],
        "Nuke Score": advanced_scores["Nuke Score"],
        "Stack Score": advanced_scores["Stack Score"],
        "Park Factor": round(park_factor, 3),
        "HRR Score": round(hrr_score, 1),
        "Model Rank Score": round(model_rank_score, 2),
        "TempF": round(temp_f, 1),
        "WindMPH": round(wind_mph, 1),
        "WeatherBoost": round(weather_boost, 2),
        "WeatherNote": weather_note,
        "BullpenFatigueScore": round(bullpen_fatigue_score, 2),
        "BullpenFatigueNote": bullpen_fatigue_note,
        "BullpenIPPrev": round(bullpen_ip_prev, 1),
        "BullpenArmsPrev": int(bullpen_arms_prev),
        "Statcast Authority Score": round(statcast_authority_score, 2),
        "Statcast Authority Tier": statcast_authority_tier,
        "HR Attackability Score": round(pitcher_target_score, 2),
        "HR Attackability Label": pitcher_target_label,
        "HR Attackability Score": round(pitcher_target_score, 2),
        "HR Attackability Label": pitcher_target_label,
        "Matchup Advantage Score": round(matchup_advantage_score, 2),
        "Matchup Advantage": matchup_advantage_tier,
        "Ranking Reasons": ranking_reasons,
        "Why": " | ".join(reasons[:6]),
    }




def _letter_grade(score: float) -> str:
    score = safe_float(score, 0.0)
    if score >= 94: return "A+"
    if score >= 89: return "A"
    if score >= 84: return "A-"
    if score >= 79: return "B+"
    if score >= 73: return "B"
    if score >= 67: return "B-"
    if score >= 60: return "C+"
    if score >= 52: return "C"
    if score >= 44: return "D"
    return "F"


def compute_advanced_prediction_scores(
    hr_probability: float,
    ev: float,
    barrel: float,
    hard_hit: float,
    fly_ball: float,
    line_drive: float,
    ground_ball: float,
    air_pct: float,
    xslg: float,
    pitch_hr9: float,
    pitcher_attackability: float,
    matchup_advantage: float,
    weather_boost: float,
    park_factor: float,
    lineup_spot,
    recent_hr: int,
    recent_trend: str,
    elite_hr_flag: bool,
) -> dict:
    """Calibrated secondary scores used for explanation, not board ranking.

    The prior formulas saturated too many elite hitters at 99–100. These scores
    retain the same inputs but compress extremes so differences remain visible.
    """
    launch_quality = clip(
        18
        + max(0.0, barrel - 5.0) * 2.25
        + max(0.0, hard_hit - 32.0) * 0.72
        + max(0.0, air_pct - 42.0) * 0.30
        + max(0.0, ev - 87.0) * 1.15
        + max(0.0, xslg - 0.390) * 42
        - max(0.0, ground_ball - 47.0) * 0.90,
        0, 96,
    )

    environment = clip(
        50 + weather_boost * 5.5 + (park_factor - 1.0) * 95,
        28, 82,
    )

    pitcher_path = clip(
        20
        + pitcher_attackability * 1.10
        + max(0.0, pitch_hr9 - 0.70) * 14,
        10, 92,
    )

    lineup_bonus = 0.0
    try:
        spot = int(lineup_spot)
        lineup_bonus = 5.0 if spot <= 4 else 2.5 if spot <= 6 else 0.0
    except Exception:
        pass

    quality = clip(
        16
        + hr_probability * 1.05
        + launch_quality * 0.34
        + pitcher_path * 0.14
        + matchup_advantage * 0.20
        + lineup_bonus,
        18, 97,
    )

    moonshot = clip(
        10
        + launch_quality * 0.52
        + max(0.0, barrel - 8.0) * 1.20
        + max(0.0, ev - 89.0) * 1.15
        + max(0.0, pitch_hr9 - 0.90) * 5.5
        + environment * 0.10,
        12, 98,
    )

    two_hr = clip(
        7
        + moonshot * 0.42
        + quality * 0.17
        + hr_probability * 0.45
        + recent_hr * 2.8
        + (3.5 if recent_trend == "HOT" else 1.5 if recent_trend == "LIVE" else 0.0),
        8, 91,
    )

    nuke = clip(
        8
        + quality * 0.30
        + moonshot * 0.31
        + matchup_advantage * 0.16
        + pitcher_path * 0.10
        + (3.5 if elite_hr_flag else 0.0),
        10, 98,
    )

    stack = clip(
        12
        + matchup_advantage * 0.28
        + pitcher_path * 0.27
        + environment * 0.13
        + lineup_bonus
        + max(0.0, hard_hit - 36.0) * 0.18,
        12, 94,
    )

    return {
        "Prediction Quality Score": round(quality, 1),
        "Prediction Quality Grade": _letter_grade(quality),
        "Moonshot Score": round(moonshot, 1),
        "2 HR Score": round(two_hr, 1),
        "Nuke Score": round(nuke, 1),
        "Stack Score": round(stack, 1),
    }

def compute_slate_confidence(df: pd.DataFrame) -> float:
    """Slate-level readiness and quality score with honest headroom."""
    if df is None or df.empty:
        return 0.0

    work = df.copy()
    quality = safe_numeric_series(work, "Prediction Quality Score", 0.0)
    hrp = safe_numeric_series(work, "HR Probability %", 0.0)
    edge = safe_numeric_series(work, "Matchup Advantage Score", 0.0)
    attack = safe_numeric_series(work, "HR Attackability Score", 0.0)

    lineup_source = work.get("Lineup Source", pd.Series("", index=work.index)).astype(str)
    confirmed_pct = lineup_source.eq("CONFIRMED").mean() * 100

    n = min(12, len(work))
    top_quality = quality.nlargest(n).mean() if n else 0.0
    top_hr = hrp.nlargest(n).mean() if n else 0.0
    top_edge = edge.nlargest(n).mean() if n else 0.0
    top_attack = attack.nlargest(n).mean() if n else 0.0

    # 95 is the practical ceiling. A perfect 100 should not appear from
    # lineup confirmation alone.
    score = (
        18
        + top_quality * 0.34
        + top_hr * 0.62
        + top_edge * 0.16
        + top_attack * 0.18
        + confirmed_pct * 0.10
    )
    return round(clip(score, 15, 95), 1)

def _load_learning_profile() -> dict:
    if os.path.exists(LEARNING_PROFILE_FILE):
        try:
            with open(LEARNING_PROFILE_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
    return {}


def _save_learning_profile(profile: dict):
    folder = os.path.dirname(LEARNING_PROFILE_FILE) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".bf_learning_", suffix=".json", dir=folder)
    os.close(fd)
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(profile, fh, indent=2)
        os.replace(tmp_path, LEARNING_PROFILE_FILE)
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass


def build_learning_engine_report(tracker: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Learn only from finalized rows and produce bounded, auditable recommendations."""
    if tracker is None or tracker.empty:
        return pd.DataFrame(), pd.DataFrame(), {"final_rows": 0, "status": "COLLECTING"}

    work = tracker.copy()
    hr_count = pd.to_numeric(work.get("hr_count", 0), errors="coerce").fillna(0)
    final_mask = work.get("result_state", pd.Series("", index=work.index)).astype(str).str.contains(
        "HOMERED|FINAL_NO_HR", regex=True, na=False
    )
    final = work[final_mask].copy()
    if final.empty:
        return pd.DataFrame(), pd.DataFrame(), {"final_rows": 0, "status": "COLLECTING"}
    final["hit"] = (pd.to_numeric(final.get("hr_count", 0), errors="coerce").fillna(0) > 0).astype(int)

    feature_specs = [
        ("Barrel 14%+", "barrel_pct", lambda s: s >= 14),
        ("Barrel 12%+", "barrel_pct", lambda s: s >= 12),
        ("FB 38%+", "flyball_pct", lambda s: s >= 38),
        ("HardHit 45%+", "hardhit_pct", lambda s: s >= 45),
        ("GB 50%+", "groundball_pct", lambda s: s >= 50),
        ("Pitcher HR/9 1.6+", "pitcher_hr9", lambda s: s >= 1.6),
        ("Attackability 24+", "pitcher_attackability", lambda s: s >= 24),
        ("Weather +1.5+", "weather_score", lambda s: s >= 1.5),
        ("Quality A range", "quality_grade", lambda s: s.astype(str).isin(["A+", "A", "A-"])),
        ("Moonshot 75+", "moonshot_score", lambda s: s >= 75),
        ("Nuke 75+", "nuke_score", lambda s: s >= 75),
    ]

    overall_rate = final["hit"].mean() * 100
    rows = []
    for label, col, rule in feature_specs:
        if col not in final.columns:
            continue
        raw = final[col]
        numeric = pd.to_numeric(raw, errors="coerce") if col != "quality_grade" else raw
        try:
            mask = rule(numeric).fillna(False)
        except Exception:
            continue
        sample = final[mask]
        if sample.empty:
            continue
        hit_rate = sample["hit"].mean() * 100
        rows.append({
            "Pattern": label,
            "Sample": int(len(sample)),
            "HR Hits": int(sample["hit"].sum()),
            "Hit Rate %": round(hit_rate, 2),
            "Vs Overall": round(hit_rate - overall_rate, 2),
            "Confidence": "HIGH" if len(sample) >= 100 else "MED" if len(sample) >= 40 else "LOW",
        })

    patterns = pd.DataFrame(rows)
    if not patterns.empty:
        patterns = patterns.sort_values(["Confidence", "Vs Overall", "Sample"], ascending=[True, False, False])

    # Board/source audit
    audit_rows = []
    for source, label in [("CORE_BOARD", "Core Board"), ("TOP12", "Top 12"), ("GAME_HR", "Per-Game")]:
        sample = final[final.get("tracker_source", "").astype(str).eq(source)]
        if sample.empty:
            continue
        audit_rows.append({
            "Board": label,
            "Final Picks": len(sample),
            "HR Hits": int(sample["hit"].sum()),
            "Hit Rate %": round(sample["hit"].mean() * 100, 2),
            "Avg HR Probability": round(pd.to_numeric(sample.get("hr_probability", 0), errors="coerce").mean(), 2),
            "Avg Rank": round(pd.to_numeric(sample.get("board_rank", 0), errors="coerce").replace(0, pd.NA).mean(), 2),
        })
    board_audit = pd.DataFrame(audit_rows)

    profile = {
        "updated_at": now_et_string(),
        "final_rows": int(len(final)),
        "overall_hit_rate": round(overall_rate, 2),
        "status": "ACTIVE" if len(final) >= 300 else "CALIBRATING" if len(final) >= 100 else "COLLECTING",
        "minimum_auto_tune_sample": 300,
        "max_weight_change_pct": 5.0,
        "recommendations": [],
    }
    if not patterns.empty:
        for _, row in patterns.iterrows():
            if int(row["Sample"]) < 40:
                continue
            lift = safe_float(row["Vs Overall"], 0.0)
            bounded = round(clip(lift * 0.20, -5.0, 5.0), 2)
            profile["recommendations"].append({
                "pattern": row["Pattern"],
                "sample": int(row["Sample"]),
                "lift_pct_points": round(lift, 2),
                "suggested_weight_change_pct": bounded,
            })
    _save_learning_profile(profile)
    return patterns, board_audit, profile


def render_tracker_audit_learning(tracker: pd.DataFrame, selected_tracker: pd.DataFrame):
    st.divider()
    st.markdown("### Tracker Audit 2.0")
    st.caption("Every row is a permanent prediction-time snapshot. Game results update separately and never rewrite the original inputs.")

    audit_cols = [
        "player", "team", "game", "tracker_source", "board_rank",
        "on_core_board", "on_top12", "on_per_game",
        "hr_probability", "hr_tier", "quality_grade",
        "moonshot_score", "two_hr_score", "nuke_score", "stack_score",
        "slate_confidence", "weather_score", "park_factor",
        "pitcher_attackability", "ev", "barrel_pct", "hardhit_pct",
        "flyball_pct", "linedrive_pct", "groundball_pct", "air_pct",
        "lineup_spot", "pitcher", "pitcher_hr9", "result", "hr_count",
        "result_state", "prediction_locked_at",
    ]
    if selected_tracker is not None and not selected_tracker.empty:
        display_existing_columns(selected_tracker, audit_cols)
    else:
        st.info("Tracker Audit will populate when the next official BF board is surfaced.")

    st.divider()
    st.markdown("### BF Learning Engine")
    patterns, board_audit, profile = build_learning_engine_report(tracker)
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Final Audited Picks", profile.get("final_rows", 0))
    p2.metric("Engine Status", profile.get("status", "COLLECTING"))
    p3.metric("Overall Hit Rate", f"{safe_float(profile.get('overall_hit_rate'), 0.0):.2f}%")
    p4.metric("Auto-Tune Limit", "±5%")

    if patterns.empty:
        st.info("The Learning Engine is collecting finalized predictions. Pattern recommendations begin at 40 samples; bounded auto-tuning becomes eligible at 300.")
    else:
        st.markdown("**Performance Patterns**")
        st.dataframe(patterns, use_container_width=True, hide_index=True)
        if not board_audit.empty:
            st.markdown("**Board Performance Audit**")
            st.dataframe(board_audit, use_container_width=True, hide_index=True)

        recs = profile.get("recommendations", [])
        if recs:
            st.markdown("**Automatic Tuning Recommendations**")
            rec_df = pd.DataFrame(recs)
            st.dataframe(rec_df, use_container_width=True, hide_index=True)
            st.caption("Safety lock: recommendations are evidence-based and bounded to ±5%. The current ranking engine remains unchanged until the minimum sample is reached.")

def safe_numeric_series(df: pd.DataFrame, col_name: str, default=0.0) -> pd.Series:
    if col_name in df.columns:
        return pd.to_numeric(df[col_name], errors="coerce").fillna(default)
    return pd.Series([default] * len(df), index=df.index, dtype="float64")

def classify_hr_tier(prob: float) -> str:
    if prob >= 20:
        return "CORE TARGET"
    if prob >= 14:
        return "STRONG LOOK"
    if prob >= 9:
        return "SLEEPER"
    return "DEEP"


def sort_for_hr(df: pd.DataFrame) -> pd.DataFrame:
    sortable = df.copy()
    sortable["_lineup_sort"] = safe_numeric_series(sortable, "Lineup Spot", 99)
    sortable["_model_rank_sort"] = safe_numeric_series(sortable, "Model Rank Score", 0.0)
    sortable["_hr_prob_sort"] = safe_numeric_series(sortable, "HR Probability %", 0.0)
    sortable["_barrel_sort"] = safe_numeric_series(sortable, "Barrel%", 0.0)
    sortable["_hh_sort"] = safe_numeric_series(sortable, "HardHit%", 0.0)
    sortable["_air_sort"] = safe_numeric_series(sortable, "AIR%", 0.0)
    sortable["_fb_sort"] = safe_numeric_series(sortable, "FlyBall%", 0.0)
    sortable["_ld_sort"] = safe_numeric_series(sortable, "LineDrive%", 0.0)
    sortable["_air_edge_sort"] = sortable["_fb_sort"] + sortable["_ld_sort"] - safe_numeric_series(sortable, "GroundBall%", 999.0)
    sortable["_xslg_sort"] = safe_numeric_series(sortable, "xSLG", 0.0)
    sortable["_gb_sort"] = safe_numeric_series(sortable, "GroundBall%", 999.0)
    sortable["_pitch_hr9_sort"] = safe_numeric_series(sortable, "Pitcher_HR9_Last7", 0.0)
    sortable["_pitch_barrel_sort"] = safe_numeric_series(sortable, "Pitcher_Barrel_Allowed", 0.0)
    sortable["_pitch_matchup_sort"] = safe_numeric_series(sortable, "Pitch Matchup Score", 0.0)
    sortable["_handedness_sort"] = safe_numeric_series(sortable, "Handedness Edge", 0.0)
    sortable["_usage_sort"] = safe_numeric_series(sortable, "Primary Pitch Usage", 0.0)
    sortable["_mix_mode_sort"] = sortable.get("Pitch Mix Mode", pd.Series(["BALANCED"] * len(sortable), index=sortable.index)).map({"HARD": 3, "SOFT": 2, "BALANCED": 1}).fillna(1)
    sortable["_authority_sort"] = safe_numeric_series(sortable, "Statcast Authority Score", 0.0)
    sortable["_authority_tier_sort"] = sortable.get("Statcast Authority Tier", pd.Series(["MEDIUM"] * len(sortable), index=sortable.index)).map({"ELITE": 4, "STRONG": 3, "MEDIUM": 2, "WEAK": 1, "FAIL": 0}).fillna(2)
    sortable["_la_sort"] = safe_numeric_series(sortable, "LaunchAngle", 0.0)
    sortable["_trend_sort"] = sortable.get("Recent Trend", pd.Series(["NEUTRAL"] * len(sortable), index=sortable.index)).map({"HOT": 3, "LIVE": 2, "NEUTRAL": 1, "COLD": 0}).fillna(1)
    sortable["_hrr_sort"] = safe_numeric_series(sortable, "HRR Score", 0.0)
    sortable["_multi_pitch_sort"] = safe_numeric_series(sortable, "Multi Pitch Authority Score", 0.0)
    sortable["_elite_hr_sort"] = sortable.get("Elite HR Look", pd.Series(["No"] * len(sortable), index=sortable.index)).map({"Yes": 1, "No": 0}).fillna(0)
    sortable["_pitcher_target_sort"] = safe_numeric_series(sortable, "HR Attackability Score", safe_numeric_series(sortable, "HR Attackability Score", 0.0).iloc[0] if len(sortable) else 0.0) if "HR Attackability Score" in sortable.columns else safe_numeric_series(sortable, "HR Attackability Score", 0.0)
    sortable["_matchup_adv_sort"] = safe_numeric_series(sortable, "Matchup Advantage Score", 0.0)

    sortable = sortable.sort_values(
        by=[
            "_matchup_adv_sort",
            "_pitcher_target_sort",
            "_elite_hr_sort",
            "_authority_tier_sort",
            "_authority_sort",
            "_multi_pitch_sort",
            "_barrel_sort",
            "_hh_sort",
            "_air_edge_sort",
            "_fb_sort",
            "_ld_sort",
            "_air_sort",
            "_xslg_sort",
            "_pitch_matchup_sort",
            "_hr_prob_sort",
            "_model_rank_sort",
            "_lineup_sort",
            "_usage_sort",
            "_mix_mode_sort",
            "_gb_sort",
            "_pitch_hr9_sort",
            "_pitch_barrel_sort",
            "_handedness_sort",
            "_la_sort",
            "_trend_sort",
            "_hrr_sort",
        ],
        ascending=[False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, False, False, True, False, False, False, False, False, False],
    ).reset_index(drop=True)
    return sortable.drop(columns=[
        "_lineup_sort",
        "_model_rank_sort",
        "_hr_prob_sort",
        "_barrel_sort",
        "_hh_sort",
        "_air_sort",
        "_fb_sort",
        "_ld_sort",
        "_air_edge_sort",
        "_xslg_sort",
        "_gb_sort",
        "_pitch_hr9_sort",
        "_pitch_barrel_sort",
        "_pitch_matchup_sort",
        "_handedness_sort",
        "_usage_sort",
        "_mix_mode_sort",
        "_authority_sort",
        "_authority_tier_sort",
        "_la_sort",
        "_trend_sort",
        "_hrr_sort",
        "_multi_pitch_sort",
        "_elite_hr_sort",
        "_pitcher_target_sort",
        "_matchup_adv_sort",
    ])


def _prefetch_cached_calls(call_specs: list[tuple], max_workers: int = 12):
    """Warm independent cached network calls concurrently."""
    if not call_specs:
        return
    workers = max(1, min(int(max_workers), len(call_specs)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fn, *args) for fn, args in call_specs]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                pass


@st.cache_data(ttl=120, max_entries=4)
def build_daily_dataset(deep_bbe: bool = False):
    schedule = sort_schedule_rows(get_today_schedule())
    rows = []

    savant_batter_map = fetch_savant_batter_map(CURRENT_SEASON)

    candidate_map = {}
    all_hitter_ids = set()
    all_pitcher_ids = set()

    for game in schedule:
        away_candidates, away_source = get_team_candidate_hitters(
            game["game_pk"], game["away_team_id"], "away", savant_batter_map, deep_bbe=deep_bbe
        )
        home_candidates, home_source = get_team_candidate_hitters(
            game["game_pk"], game["home_team_id"], "home", savant_batter_map, deep_bbe=deep_bbe
        )

        candidate_map[(game["game_pk"], "away")] = (away_candidates, away_source)
        candidate_map[(game["game_pk"], "home")] = (home_candidates, home_source)

        if away_source == "CONFIRMED":
            game["away_confirmed_count"] = min(9, len(away_candidates))
        if home_source == "CONFIRMED":
            game["home_confirmed_count"] = min(9, len(home_candidates))

        for h in away_candidates + home_candidates:
            if h.get("player_id") is not None:
                all_hitter_ids.add(h["player_id"])

        if game.get("away_pitcher_id") is not None:
            all_pitcher_ids.add(game["away_pitcher_id"])
        if game.get("home_pitcher_id") is not None:
            all_pitcher_ids.add(game["home_pitcher_id"])

    hitter_stats_map = fetch_people_stats(tuple(all_hitter_ids), "hitting")
    pitcher_stats_map = fetch_people_stats(tuple(all_pitcher_ids), "pitching")
    hand_map = fetch_people_hand_map(tuple(list(all_hitter_ids) + list(all_pitcher_ids)))

    # Cold-start speed: warm independent real-data calls concurrently instead
    # of waiting for each pitcher/game one at a time. Existing calculations,
    # cards, and data sources remain unchanged.
    prefetch_specs = []
    for pitcher_id in sorted(all_pitcher_ids):
        prefetch_specs.append((fetch_true_pitcher_arsenal, (pitcher_id,)))
    for game in schedule:
        home_abbr = team_abbr(game["home_team"])
        prefetch_specs.append((fetch_weather_for_park, (home_abbr,)))
        prefetch_specs.append((fetch_bullpen_fatigue_for_team, (game["home_team_id"],)))
        prefetch_specs.append((fetch_bullpen_fatigue_for_team, (game["away_team_id"],)))
    _prefetch_cached_calls(prefetch_specs, max_workers=12)

    for game in schedule:
        away_abbr = team_abbr(game["away_team"])
        home_abbr = team_abbr(game["home_team"])
        away_park = PARK_FACTORS.get(home_abbr, 1.00)
        home_park = PARK_FACTORS.get(home_abbr, 1.00)
        weather = fetch_weather_for_park(home_abbr)
        home_bullpen = fetch_bullpen_fatigue_for_team(game["home_team_id"])
        away_bullpen = fetch_bullpen_fatigue_for_team(game["away_team_id"])

        away_candidates, away_source = candidate_map[(game["game_pk"], "away")]
        home_candidates, home_source = candidate_map[(game["game_pk"], "home")]

        for hitter in away_candidates:
            metrics = build_hitter_metrics(
                player_id=hitter["player_id"],
                player_name=hitter["player_name"],
                team=away_abbr,
                opp_pitcher=game["home_pitcher"],
                park_factor=away_park,
                opp_pitcher_id=game["home_pitcher_id"],
                lineup_spot=hitter.get("lineup_spot"),
                lineup_source=away_source,
                hitter_stats_map=hitter_stats_map,
                pitcher_stats_map=pitcher_stats_map,
                savant_batter_map=savant_batter_map,
                hand_map=hand_map,
                weather_boost=weather.get("WeatherBoost", 0.0),
                weather_note=weather.get("WeatherNote", "neutral weather"),
                temp_f=weather.get("TempF", 72.0),
                wind_mph=weather.get("WindMPH", 7.0),
                bullpen_fatigue_score=home_bullpen.get("BullpenFatigueScore", 0.0),
                bullpen_fatigue_note=home_bullpen.get("BullpenFatigueNote", "Neutral bullpen rest"),
                bullpen_ip_prev=home_bullpen.get("BullpenIPPrev", 0.0),
                bullpen_arms_prev=home_bullpen.get("BullpenArmsPrev", 0),
                deep_bbe=deep_bbe,
            )
            if metrics is not None:
                rows.append({
                    "date": today_str(),
                    "game_pk": game["game_pk"],
                    "game_state": game["game_state"],
                    "detailed_state": game["detailed_state"],
                    "Game": game["game_key"],
                    "Side": "Away",
                    **metrics
                })

        for hitter in home_candidates:
            metrics = build_hitter_metrics(
                player_id=hitter["player_id"],
                player_name=hitter["player_name"],
                team=home_abbr,
                opp_pitcher=game["away_pitcher"],
                park_factor=home_park,
                opp_pitcher_id=game["away_pitcher_id"],
                lineup_spot=hitter.get("lineup_spot"),
                lineup_source=home_source,
                hitter_stats_map=hitter_stats_map,
                pitcher_stats_map=pitcher_stats_map,
                savant_batter_map=savant_batter_map,
                hand_map=hand_map,
                weather_boost=weather.get("WeatherBoost", 0.0),
                weather_note=weather.get("WeatherNote", "neutral weather"),
                temp_f=weather.get("TempF", 72.0),
                wind_mph=weather.get("WindMPH", 7.0),
                bullpen_fatigue_score=away_bullpen.get("BullpenFatigueScore", 0.0),
                bullpen_fatigue_note=away_bullpen.get("BullpenFatigueNote", "Neutral bullpen rest"),
                bullpen_ip_prev=away_bullpen.get("BullpenIPPrev", 0.0),
                bullpen_arms_prev=away_bullpen.get("BullpenArmsPrev", 0),
                deep_bbe=deep_bbe,
            )
            if metrics is not None:
                rows.append({
                    "date": today_str(),
                    "game_pk": game["game_pk"],
                    "game_state": game["game_state"],
                    "detailed_state": game["detailed_state"],
                    "Game": game["game_key"],
                    "Side": "Home",
                    **metrics
                })

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(), schedule

    df["HR Tier"] = df["HR Probability %"].apply(classify_hr_tier)
    df = sort_for_hr(df)
    return df, schedule


def get_research_shortlist_pool(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    pool = df[df["HR Eligible"]].copy()
    if pool.empty:
        return pool

    lineup_num = safe_numeric_series(pool, "Lineup Spot", 99)
    barrel = safe_numeric_series(pool, "Barrel%", 0.0)
    hard_hit = safe_numeric_series(pool, "HardHit%", 0.0)
    air_pct = safe_numeric_series(pool, "AIR%", 0.0)
    xslg = safe_numeric_series(pool, "xSLG", 0.0)
    gb = safe_numeric_series(pool, "GroundBall%", 999.0)
    pitch_score = safe_numeric_series(pool, "Pitch Matchup Score", 0.0)
    hr_prob = safe_numeric_series(pool, "HR Probability %", 0.0)
    trend_score = safe_numeric_series(pool, "Model Rank Score", 0.0)
    recent_trend = pool.get("Recent Trend", pd.Series(["NEUTRAL"] * len(pool), index=pool.index)).astype(str)
    authority_tier = pool.get("Statcast Authority Tier", pd.Series(["MEDIUM"] * len(pool), index=pool.index)).astype(str)
    mix_mode = pool.get("Pitch Mix Mode", pd.Series(["BALANCED"] * len(pool), index=pool.index)).astype(str)
    lineup_source = pool.get("Lineup Source", pd.Series(["PROJECTED"] * len(pool), index=pool.index)).astype(str).str.upper()

    authority_keep = authority_tier.isin(["ELITE", "STRONG"])
    hot_keep = recent_trend.isin(["HOT", "LIVE"])
    elite_shape = (barrel >= 12.0) | (xslg >= 0.500) | ((hard_hit >= 45.0) & (air_pct >= 54.0))
    starter_attack = (pitch_score >= 4.4) | (hr_prob >= 12.5)

    hard_shape_gate = (
        ((barrel >= 8.5) & (hard_hit >= 40.0) & (air_pct >= 49.0))
        | ((barrel >= 10.0) & (xslg >= 0.460))
        | ((hard_hit >= 44.0) & (air_pct >= 50.0))
        | elite_shape
        | authority_keep
    )

    gb_keep = (
        (gb <= 47.5)
        | elite_shape
        | authority_keep
        | ((gb <= 50.0) & (barrel >= 11.0) & (xslg >= 0.485))
    )

    projected_keep = (
        lineup_source.eq("PROJECTED")
        & (
            elite_shape
            | authority_keep
            | (hot_keep & starter_attack)
            | ((barrel >= 10.5) & (xslg >= 0.475))
        )
    )

    mixed_pitch_keep = (
        mix_mode.eq("HARD")
        | authority_keep
        | projected_keep
        | (mix_mode.eq("SOFT") & (starter_attack | hot_keep | elite_shape))
        | (mix_mode.eq("BALANCED") & (elite_shape | authority_keep | (hot_keep & (pitch_score >= 4.8))))
    )

    score_gate = (
        (hr_prob >= 9.2)
        | authority_keep
        | elite_shape
        | ((barrel >= 10.8) & (hard_hit >= 42.0))
        | (trend_score >= 455)
    )

    playable_lineup = (lineup_num <= 6) | authority_keep | projected_keep | hot_keep

    fade_cold = ~(
        recent_trend.eq("COLD")
        & (barrel < 11.5)
        & (xslg < 0.485)
        & (pitch_score < 5.2)
        & ~authority_keep
    )

    projected_unknown_fade = ~(
        lineup_num.eq(99)
        & lineup_source.eq("PROJECTED")
        & ~(projected_keep | authority_keep | elite_shape)
    )

    shortlist = pool[
        hard_shape_gate
        & gb_keep
        & mixed_pitch_keep
        & score_gate
        & playable_lineup
        & fade_cold
        & projected_unknown_fade
    ].copy()

    if shortlist.empty:
        shortlist = sort_for_hr(pool).head(28).copy()
        return shortlist.reset_index(drop=True)

    shortlist = sort_for_hr(shortlist).head(30).reset_index(drop=True)
    return shortlist


def get_strict_hr_pool(df: pd.DataFrame) -> pd.DataFrame:
    hr_pool = get_research_shortlist_pool(df)
    if hr_pool.empty:
        return hr_pool
    return add_rank_column(hr_pool)


def get_top12_hybrid(df: pd.DataFrame) -> pd.DataFrame:
    hr_pool = get_research_shortlist_pool(df)
    if hr_pool.empty:
        return hr_pool

    hr_pool = sort_for_hr(hr_pool)
    strict_pool = hr_pool[hr_pool["Strict Statcast"] == "Yes"].copy()
    strict_pool = sort_for_hr(strict_pool)

    strict_keys = set(zip(strict_pool["Player"], strict_pool["Team"], strict_pool["Game"]))
    fallback_rows = []
    for _, row in hr_pool.iterrows():
        key = (row["Player"], row["Team"], row["Game"])
        if key not in strict_keys:
            fallback_rows.append(row)

    fallback_df = pd.DataFrame(fallback_rows) if fallback_rows else pd.DataFrame(columns=hr_pool.columns)
    top12 = pd.concat([strict_pool, fallback_df], ignore_index=True).head(12)

    if top12.empty:
        return top12

    top12 = sort_for_hr(top12)
    return add_rank_column(top12)



def _stable_player_key(row) -> str:
    """Stable player identity used by all per-game/doubleheader dedupe rules."""
    raw_pid = row.get("Player ID", pd.NA)
    try:
        if pd.notna(raw_pid):
            return f"id:{int(raw_pid)}"
    except Exception:
        pass
    return f"name:{normalize_name(row.get('Player', ''))}"


def build_doubleheader_assignment_map(df: pd.DataFrame, schedule: list[dict]) -> dict:
    """Assign a hitter to only one game in a same-day doubleheader.

    Each MLB game_pk remains independent. When the same hitter qualifies in both
    games of the same team matchup, he is assigned only to the game where his
    matchup score is strongest. The other game backfills with its next-highest
    unique qualified hitter. Normal one-game series are unchanged.
    """
    assignments = {}
    if df is None or df.empty:
        return assignments

    matchup_groups = {}
    for game in schedule:
        matchup_groups.setdefault(str(game.get("game_key", "")), []).append(game)

    for game_key, games in matchup_groups.items():
        game_pks = [safe_int(g.get("game_pk"), -1) for g in games]
        teams = set()
        for g in games:
            teams.add(team_abbr(g.get("away_team", "")))
            teams.add(team_abbr(g.get("home_team", "")))

        # A single game needs no cross-game restriction.
        if len(set(game_pks)) <= 1:
            continue

        for team in teams:
            group = df[
                df["Game"].astype(str).eq(str(game_key))
                & df["Team"].astype(str).eq(str(team))
                & pd.to_numeric(df["game_pk"], errors="coerce").fillna(-1).astype(int).isin(game_pks)
            ].copy()
            if group.empty:
                continue

            group = sort_for_hr(group).reset_index(drop=True)
            group["_bf_player_key"] = group.apply(_stable_player_key, axis=1)

            # Keep the strongest game-specific version of each hitter across the doubleheader.
            best_rows = group.drop_duplicates(subset=["_bf_player_key"], keep="first")
            for _, row in best_rows.iterrows():
                assignment_key = (safe_int(row.get("game_pk"), -1), str(team))
                assignments.setdefault(assignment_key, set()).add(row["_bf_player_key"])

    return assignments


def get_saved_game_hr_board(snapshot_date: str, game_pk, team: str, schedule: list[dict], assignment_map: dict | None = None) -> pd.DataFrame:
    """Return one frozen board for one exact game_pk/team only.

    Stale rows from another game of a doubleheader are rejected by both game_pk
    and the expected opposing starter. Pregame result badges are always zero.
    """
    snap = load_daily_board_snapshot(snapshot_date)
    if snap is None or snap.empty or "Tracker Source" not in snap.columns:
        return pd.DataFrame()
    section = snap[snap["Tracker Source"].astype(str).str.strip().str.upper().eq("GAME_HR")].copy()
    if section.empty or "game_pk" not in section.columns:
        return pd.DataFrame()

    requested_pk = safe_int(game_pk, -1)
    section = section[pd.to_numeric(section["game_pk"], errors="coerce").fillna(-1).astype(int).eq(requested_pk)]
    section = section[section["Team"].astype(str).eq(str(team))].copy()
    if section.empty:
        return section

    game = next((g for g in schedule if safe_int(g.get("game_pk"), -1) == requested_pk), None)
    if game is not None and "Pitcher" in section.columns:
        away_team = team_abbr(game.get("away_team", ""))
        expected_pitcher = game.get("home_pitcher") if str(team) == away_team else game.get("away_pitcher")
        if expected_pitcher and expected_pitcher != "Starter Pending":
            section = section[section["Pitcher"].astype(str).map(normalize_name).eq(normalize_name(expected_pitcher))].copy()
    if section.empty:
        return section

    section["_bf_player_key"] = section.apply(_stable_player_key, axis=1)
    if assignment_map:
        allowed = assignment_map.get((requested_pk, str(team)))
        if allowed is not None:
            section = section[section["_bf_player_key"].isin(allowed)].copy()
    section = section.drop_duplicates(subset=["_bf_player_key"], keep="first").drop(columns=["_bf_player_key"])

    # Never carry a result from Game 1 into a pregame Game 2 card.
    section["Actual HR Today"] = 0
    if game is not None and str(game.get("game_state", "Preview")) != "Preview":
        section = add_live_homer_counts_to_board(section, [game])

    if "Rank" in section.columns:
        section = section.drop(columns=["Rank"])
    section = section.reset_index(drop=True)
    section.insert(0, "Rank", range(1, len(section) + 1))
    return dedupe_columns(section.head(4))


def get_team_game_view(df: pd.DataFrame, game_key: str, team: str, game_pk=None, assignment_map: dict | None = None):
    """Return unique qualified hitters for one team in one specific game.

    Doubleheaders are separated by MLB game_pk. Inside that game, a hitter can
    appear only once. Removed duplicates never consume a ranking slot; the board
    continues to the next-highest qualified hitter. If fewer than four unique
    hitters qualify, only those qualified hitters are shown.
    """
    if df is None or df.empty:
        empty = pd.DataFrame()
        return empty, empty

    mask = (
        df["Game"].astype(str).eq(str(game_key))
        & df["Team"].astype(str).eq(str(team))
    )

    if game_pk is not None and "game_pk" in df.columns:
        requested_game_pk = safe_int(game_pk, -1)
        row_game_pks = pd.to_numeric(df["game_pk"], errors="coerce").fillna(-1).astype(int)
        mask &= row_game_pks.eq(requested_game_pk)

    team_df = df.loc[mask].copy()
    if team_df.empty:
        return team_df, team_df

    # Doubleheader rule: a hitter may be assigned to only one game in the pair.
    if assignment_map and game_pk is not None:
        allowed = assignment_map.get((safe_int(game_pk, -1), str(team)))
        if allowed is not None:
            team_df["_bf_assignment_key"] = team_df.apply(_stable_player_key, axis=1)
            team_df = team_df[team_df["_bf_assignment_key"].isin(allowed)].drop(columns=["_bf_assignment_key"])
            if team_df.empty:
                return team_df, team_df

    # Rank this game's rows first so that, if the same hitter somehow entered
    # the dataset more than once, the strongest version is the one preserved.
    team_df = sort_for_hr(team_df).reset_index(drop=True)

    # Prefer the stable MLB player ID. Fall back to normalized name only when an
    # ID is unavailable. This prevents spelling, accents, or refresh artifacts
    # from allowing the same hitter to occupy multiple slots.
    if "Player ID" in team_df.columns:
        player_ids = pd.to_numeric(team_df["Player ID"], errors="coerce")
        name_keys = team_df["Player"].astype(str).map(normalize_name)
        team_df["_bf_unique_player"] = [
            f"id:{int(pid)}" if pd.notna(pid) else f"name:{name}"
            for pid, name in zip(player_ids, name_keys)
        ]
    else:
        team_df["_bf_unique_player"] = (
            "name:" + team_df["Player"].astype(str).map(normalize_name)
        )

    team_df = (
        team_df
        .drop_duplicates(subset=["_bf_unique_player"], keep="first")
        .drop(columns=["_bf_unique_player"])
        .reset_index(drop=True)
    )

    # Apply the existing BF qualification standards to this game only.
    qualified = get_research_shortlist_pool(team_df)

    # Backfill naturally with the next-highest unique qualified hitter. Do not
    # force four cards when fewer than four hitters genuinely qualify.
    selected_rows = []
    used_players = set()

    if qualified is not None and not qualified.empty:
        qualified = sort_for_hr(qualified).reset_index(drop=True)

        for _, row in qualified.iterrows():
            raw_pid = row.get("Player ID", pd.NA)
            try:
                player_key = f"id:{int(raw_pid)}" if pd.notna(raw_pid) else ""
            except Exception:
                player_key = ""

            if not player_key:
                player_key = f"name:{normalize_name(row.get('Player', ''))}"

            if player_key in used_players:
                continue

            selected_rows.append(row)
            used_players.add(player_key)

            if len(selected_rows) >= 4:
                break

    if selected_rows:
        hr_pool = pd.DataFrame(selected_rows).reset_index(drop=True)
        hr_pool = add_rank_column(hr_pool)
    else:
        hr_pool = team_df.iloc[0:0].copy()

    # HRR remains game-specific and unique as well.
    hrr = (
        team_df.sort_values(
            by=["HRR Score", "LineDrive%", "HardHit%", "GroundBall%"],
            ascending=[False, False, False, True]
        )
        .drop_duplicates(
            subset=["Player ID"] if "Player ID" in team_df.columns else ["Player"],
            keep="first"
        )
        .head(5)
        .reset_index(drop=True)
    )

    return hr_pool, hrr



def build_visible_tracker_pool(df: pd.DataFrame, schedule: list[dict], assignment_map: dict | None = None) -> pd.DataFrame:
    visible_frames = []

    core_board = get_research_shortlist_pool(df).copy()
    if not core_board.empty:
        core_board = sort_for_hr(core_board).head(30)
        core_board["Tracker Source"] = "CORE_BOARD"
        visible_frames.append(core_board)

    top12 = get_top12_hybrid(df).copy()
    if not top12.empty:
        top12["Tracker Source"] = "TOP12"
        visible_frames.append(top12)

    # Match tracker entries to the actual per-game HR boards the user sees.
    # If BF Data surfaces a hitter in a visible per-game HR table, that hitter must be tracked.
    for game in schedule:
        gdf = df[
            (df["Game"] == game["game_key"])
            & (df["game_pk"] == game.get("game_pk"))
        ].copy()
        if gdf.empty:
            continue

        away_team = team_abbr(game["away_team"])
        home_team = team_abbr(game["home_team"])

        away_hr, _ = get_team_game_view(gdf, game["game_key"], away_team, game.get("game_pk"), assignment_map)
        if not away_hr.empty:
            away_hr = away_hr.copy()
            away_hr["Tracker Source"] = "GAME_HR"
            visible_frames.append(away_hr)

        home_hr, _ = get_team_game_view(gdf, game["game_key"], home_team, game.get("game_pk"), assignment_map)
        if not home_hr.empty:
            home_hr = home_hr.copy()
            home_hr["Tracker Source"] = "GAME_HR"
            visible_frames.append(home_hr)

    if not visible_frames:
        return pd.DataFrame(columns=df.columns.tolist() + ["Tracker Source"])

    visible_df = pd.concat(visible_frames, ignore_index=True)
    visible_dedupe_cols = ["Player", "Team", "Game", "Tracker Source"]
    if "game_pk" in visible_df.columns:
        visible_dedupe_cols.insert(3, "game_pk")
    visible_df = visible_df.drop_duplicates(subset=visible_dedupe_cols).reset_index(drop=True)
    visible_df = sort_for_hr(visible_df)
    return visible_df


@st.cache_data(ttl=12, max_entries=64)
def get_live_feed_homers(game_pk: int, result_version: str = "exact-hr-v2"):
    """Return authoritative completed HR events keyed by MLB player ID and name.

    Only MLB's exact ``eventType == home_run`` is accepted. Description text is
    deliberately ignored because it can mention another player's home run and
    create false positives.
    """
    result_map = {"by_id": {}, "by_name": {}, "source": "live_feed", "available": False}
    url = f"https://statsapi.mlb.com/api/v1.1/game/{int(game_pk)}/feed/live"

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json() or {}
    except Exception:
        return result_map

    plays = (((data.get("liveData") or {}).get("plays") or {}).get("allPlays") or [])
    result_map["available"] = True

    for play in plays:
        play_result = play.get("result") or {}
        event_type = str(play_result.get("eventType", "") or "").strip().lower()

        # Exact structured event only. Never infer from free-text descriptions.
        if event_type != "home_run":
            continue

        about = play.get("about") or {}
        if about.get("isComplete") is False:
            continue

        batter = ((play.get("matchup") or {}).get("batter") or {})
        player_id = safe_int(batter.get("id"), -1)
        full_name = str(batter.get("fullName", "") or "").strip()

        if player_id > 0:
            result_map["by_id"][player_id] = safe_int(
                result_map["by_id"].get(player_id), 0
            ) + 1

        if full_name:
            norm = normalize_name(full_name)
            result_map["by_name"][norm] = safe_int(
                result_map["by_name"].get(norm), 0
            ) + 1

    return result_map


@st.cache_data(ttl=12, max_entries=64)
def get_boxscore_homers(game_pk: int, result_version: str = "exact-hr-v2"):
    """Get live HR results with exact play events as the primary authority.

    The boxscore is used only when the live play feed is unavailable. This
    prevents a transient or ambiguous boxscore value from assigning a homer to
    the wrong player.
    """
    feed = get_live_feed_homers(game_pk)
    if feed.get("available"):
        return feed

    result_map = {"by_id": {}, "by_name": {}, "source": "boxscore", "available": False}
    url = f"https://statsapi.mlb.com/api/v1/game/{int(game_pk)}/boxscore"

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json() or {}
    except Exception:
        return result_map

    result_map["available"] = True
    for side in ("away", "home"):
        players = ((((data.get("teams") or {}).get(side) or {}).get("players")) or {})
        for player_data in players.values():
            person = player_data.get("person") or {}
            player_id = safe_int(person.get("id"), -1)
            full_name = str(person.get("fullName", "") or "").strip()
            batting = ((player_data.get("stats") or {}).get("batting") or {})
            hr_count = max(0, safe_int(batting.get("homeRuns"), 0))

            if player_id > 0:
                result_map["by_id"][player_id] = hr_count
            if full_name:
                result_map["by_name"][normalize_name(full_name)] = hr_count

    return result_map


def get_player_hr_count_from_map(
    homer_map: dict,
    player_name: str,
    player_id=None,
) -> int:
    """Match by MLB player ID first, then exact normalized full name."""
    if not homer_map:
        return 0

    pid = safe_int(player_id, -1)
    by_id = homer_map.get("by_id") or {}
    if pid > 0 and pid in by_id:
        return max(0, safe_int(by_id.get(pid), 0))

    norm = normalize_name(player_name)
    if not norm:
        return 0

    by_name = homer_map.get("by_name") or {}
    return max(0, safe_int(by_name.get(norm), 0))


def add_live_homer_counts_to_board(df: pd.DataFrame, schedule: list[dict]) -> pd.DataFrame:
    """Hydrate display-only HR results by exact game_pk and player identity."""
    if df.empty:
        return df.copy()

    out = df.copy()
    out["Actual HR Today"] = 0

    if "game_pk" not in out.columns or "Player" not in out.columns:
        return out

    for game in schedule:
        if str(game.get("game_state", "Preview")) == "Preview":
            continue

        game_pk = safe_int(game.get("game_pk"), -1)
        if game_pk <= 0:
            continue

        mask = pd.to_numeric(out["game_pk"], errors="coerce").fillna(-1).astype(int).eq(game_pk)
        if not mask.any():
            continue

        homer_map = get_boxscore_homers(game_pk)

        def row_hr_count(row):
            return get_player_hr_count_from_map(
                homer_map,
                row.get("Player", ""),
                row.get("Player ID", None),
            )

        out.loc[mask, "Actual HR Today"] = out.loc[mask].apply(row_hr_count, axis=1)

    out["Actual HR Today"] = (
        pd.to_numeric(out["Actual HR Today"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
        .astype(int)
    )
    return out


def get_locked_section_snapshot(source_key: str, fallback_df: pd.DataFrame, schedule: list[dict], limit: int | None = None) -> pd.DataFrame:
    """Use the saved surfaced board for display so upgrades/refreshes do not rewrite rankings."""
    snap = load_daily_board_snapshot(today_str())
    if snap is not None and not snap.empty and "Tracker Source" in snap.columns:
        section = snap[snap["Tracker Source"].astype(str).str.strip().str.upper() == str(source_key).upper()].copy()
        if not section.empty:
            section = add_live_homer_counts_to_board(section, schedule)
            if "Rank" in section.columns:
                section = section.drop(columns=["Rank"])
            section = section.reset_index(drop=True)
            section.insert(0, "Rank", range(1, len(section) + 1))
            if limit is not None:
                section = section.head(limit).copy()
            return dedupe_columns(section)
    out = fallback_df.copy()
    if "Rank" not in out.columns:
        out = add_rank_column(out.reset_index(drop=True))
    if limit is not None:
        out = out.head(limit).copy()
    return dedupe_columns(out)


def sync_tracker_with_board(tracked_df: pd.DataFrame):
    tracker = dedupe_tracker_rows(load_tracker())
    date_key = today_str()

    if tracked_df.empty:
        save_tracker(tracker)
        return tracker

    if "hr_count" not in tracker.columns:
        tracker["hr_count"] = 0

    existing_keys = set()
    if not tracker.empty:
        today_existing = tracker[tracker["date"].astype(str) == date_key].copy()
        if not today_existing.empty:
            existing_game_pk = pd.to_numeric(today_existing.get("game_pk"), errors="coerce").fillna(-1).astype(int)
            existing_keys = set(zip(
                today_existing["date"].astype(str),
                today_existing["player"].astype(str).map(normalize_name),
                today_existing["team"].astype(str),
                today_existing["game"].astype(str),
                existing_game_pk,
                today_existing["tracker_source"].astype(str),
            ))

    new_rows = []
    for _, row in tracked_df.iterrows():
        source = str(row.get("Tracker Source", "CORE_BOARD") or "CORE_BOARD").strip().upper()
        player_name = str(row["Player"])
        key = (
            str(date_key),
            normalize_name(player_name),
            str(row["Team"]),
            str(row["Game"]),
            safe_int(row.get("game_pk"), -1),
            source,
        )
        if key in existing_keys:
            continue

        slate_confidence = compute_slate_confidence(tracked_df)
        new_rows.append({
            "date": date_key,
            "player": player_name,
            "player_id": row.get("Player ID", pd.NA),
            "team": row["Team"],
            "game": row["Game"],
            "game_pk": row.get("game_pk", pd.NA),
            "hr_probability": row.get("HR Probability %", pd.NA),
            "hr_tier": row.get("HR Tier", pd.NA),
            "hr_eligible": int(bool(row.get("HR Eligible", False))),
            "tracker_source": source,
            "board_rank": row.get("Rank", pd.NA),
            "on_core_board": int(source == "CORE_BOARD"),
            "on_top12": int(source == "TOP12"),
            "on_per_game": int(source == "GAME_HR"),
            "quality_grade": row.get("Prediction Quality Grade", pd.NA),
            "moonshot_score": row.get("Moonshot Score", pd.NA),
            "two_hr_score": row.get("2 HR Score", pd.NA),
            "nuke_score": row.get("Nuke Score", pd.NA),
            "stack_score": row.get("Stack Score", pd.NA),
            "slate_confidence": slate_confidence,
            "weather_score": row.get("WeatherBoost", pd.NA),
            "park_factor": row.get("Park Factor", pd.NA),
            "pitcher_attackability": row.get("HR Attackability Score", pd.NA),
            "ev": row.get("EV", pd.NA),
            "barrel_pct": row.get("Barrel%", pd.NA),
            "hardhit_pct": row.get("HardHit%", pd.NA),
            "flyball_pct": row.get("FlyBall%", pd.NA),
            "linedrive_pct": row.get("LineDrive%", pd.NA),
            "groundball_pct": row.get("GroundBall%", pd.NA),
            "air_pct": row.get("AIR%", pd.NA),
            "xslg": row.get("xSLG", pd.NA),
            "xwoba": row.get("xwOBA", pd.NA),
            "lineup_spot": row.get("Lineup Spot", pd.NA),
            "lineup_source": row.get("Lineup Source", pd.NA),
            "pitcher": row.get("Pitcher", pd.NA),
            "pitcher_hr9": row.get("Pitcher_HR9_Last7", pd.NA),
            "matchup_advantage": row.get("Matchup Advantage Score", pd.NA),
            "model_rank_score": row.get("Model Rank Score", pd.NA),
            "ranking_reasons": row.get("Ranking Reasons", pd.NA),
            "audit_version": TRACKER_AUDIT_VERSION,
            "prediction_locked_at": now_et_string(),
            "result": pd.NA,
            "hr_count": 0,
            "result_state": "PENDING",
            "game_state": row.get("game_state", pd.NA),
            "updated_at": now_et_string(),
        })
        existing_keys.add(key)

    if new_rows:
        tracker = pd.concat([tracker, pd.DataFrame(new_rows)], ignore_index=True)

    tracker = dedupe_tracker_rows(tracker)
    save_tracker(tracker)
    return tracker


def reconcile_today_tracker_with_visible_board(tracker, visible_df, schedule):
    """Exclude pregame off-board players without deleting their audit history."""
    if tracker is None or tracker.empty:
        return tracker
    work = tracker.copy()
    visible_keys = set()
    if visible_df is not None and not visible_df.empty:
        for _, row in visible_df.iterrows():
            visible_keys.add((safe_int(row.get("game_pk"), -1), safe_int(row.get("Player ID"), -1), normalize_name(row.get("Player", "")), str(row.get("Tracker Source", "CORE_BOARD") or "CORE_BOARD").strip().upper()))
    states = {safe_int(g.get("game_pk"), -1): str(g.get("game_state", "Preview")) for g in schedule}
    today_mask = work["date"].astype(str).eq(today_str())
    for idx in work.index[today_mask]:
        game_pk = safe_int(work.at[idx, "game_pk"], -1)
        key = (game_pk, safe_int(work.at[idx, "player_id"], -1), normalize_name(work.at[idx, "player"]), str(work.at[idx, "tracker_source"] or "CORE_BOARD").strip().upper())
        if key in visible_keys:
            if str(work.at[idx, "result_state"]) == "SCRATCHED_EXCLUDED":
                work.at[idx, "result_state"] = "PENDING"
            continue
        if states.get(game_pk, "Preview") == "Preview":
            work.at[idx, "result_state"] = "SCRATCHED_EXCLUDED"
            work.at[idx, "result"] = pd.NA
            work.at[idx, "hr_count"] = 0
            work.at[idx, "updated_at"] = now_et_string()
    return dedupe_tracker_rows(work)


def official_tracker_rows(df):
    if df is None or df.empty or "result_state" not in df.columns:
        return df
    excluded = {"SCRATCHED_EXCLUDED", "REMOVED_FROM_LINEUP", "INVALID_LINEUP"}
    return df[~df["result_state"].fillna("").astype(str).isin(excluded)].copy()

def auto_update_tracker_results(tracker: pd.DataFrame, schedule: list[dict]):
    if tracker.empty:
        return tracker

    tracker = dedupe_tracker_rows(tracker.copy())
    if "hr_count" not in tracker.columns:
        tracker["hr_count"] = 0
    if "game_pk" not in tracker.columns:
        tracker["game_pk"] = pd.NA

    date_key = today_str()
    today_mask = tracker["date"].astype(str) == date_key
    tracker_game_pk_num = pd.to_numeric(tracker["game_pk"], errors="coerce")

    for game in schedule:
        game_pk = game["game_pk"]
        game_state = game.get("game_state", "Preview")
        detailed_state = game.get("detailed_state", "Scheduled")

        # Exact game_pk only. Team matchup text is not unique on doubleheader days.
        rows_mask = today_mask & (tracker_game_pk_num == safe_int(game_pk, -1))
        if not rows_mask.any():
            continue

        # Pregame games cannot have result data, so avoid unnecessary network
        # calls. Live/final games retain the same boxscore + play-feed tracking.
        homer_map = {} if game_state == "Preview" else get_boxscore_homers(game_pk)

        for idx in tracker.index[rows_mask]:
            player = tracker.at[idx, "player"]
            player_id = tracker.at[idx, "player_id"] if "player_id" in tracker.columns else None
            hr_count = get_player_hr_count_from_map(homer_map, player, player_id)

            if game_state == "Preview":
                # Pregame rows must always remain at zero.
                hr_count = 0
                tracker.at[idx, "result"] = pd.NA
                tracker.at[idx, "result_state"] = "PREGAME"

            # Authoritative current state replaces stale values. This allows a
            # false positive to be corrected from HR 1 back to HR 0.
            tracker.at[idx, "hr_count"] = int(max(0, hr_count))

            if hr_count > 0:
                tracker.at[idx, "result"] = 1
                tracker.at[idx, "result_state"] = "HOMERED" if hr_count == 1 else f"HOMERED_{hr_count}X"
            else:
                if game_state == "Preview":
                    if pd.isna(tracker.at[idx, "result"]):
                        tracker.at[idx, "result_state"] = "PREGAME"
                elif game_state == "Final":
                    tracker.at[idx, "result"] = 0
                    tracker.at[idx, "result_state"] = "FINAL_NO_HR"
                else:
                    tracker.at[idx, "result_state"] = "LIVE"

            tracker.at[idx, "game_state"] = detailed_state
            tracker.at[idx, "updated_at"] = now_et_string()

    tracker = dedupe_tracker_rows(tracker)
    save_tracker(tracker)
    return tracker

def _combo_signature(players: list[str]) -> str:
    return " | ".join(sorted(players))


def _pick_combo_rows(candidates: pd.DataFrame, size: int, max_combos: int, global_usage: dict) -> list[dict]:
    from itertools import combinations
    if candidates.empty or len(candidates) < size:
        return []
    min_prob, min_quality, confirmed_required = {2:(14.0,70.0,False),3:(16.0,76.0,False),4:(18.0,82.0,True),5:(20.0,86.0,True)}[size]
    ranked = candidates.reset_index(drop=True).copy()
    choices = []
    for idxs in combinations(ranked.index.tolist(), size):
        rows = ranked.loc[list(idxs)].copy()
        players = rows["Player"].astype(str).tolist(); games = rows["Game"].astype(str).tolist(); teams = rows["Team"].astype(str).tolist()
        if len(set(players)) != size or (size >= 3 and len(set(games)) < size - 1) or len(set(teams)) < max(2, size - 1):
            continue
        probs = pd.to_numeric(rows["HR Probability %"], errors="coerce").fillna(0.0)
        quality = pd.to_numeric(rows.get("Prediction Quality Score"), errors="coerce").fillna(0.0)
        model = pd.to_numeric(rows.get("Model Rank Score"), errors="coerce").fillna(0.0)
        lineup = rows.get("Lineup Source", pd.Series(["PROJECTED"] * len(rows))).astype(str).str.upper()
        weakest_prob = float(probs.min()); weakest_quality = float(quality.min())
        if weakest_prob < min_prob or weakest_quality < min_quality or (confirmed_required and not lineup.eq("CONFIRMED").all()):
            continue
        score = float(probs.mean())*size + float(quality.mean())*.55 + float(model.mean())*.10 + weakest_prob*2 + weakest_quality*.65 + len(set(games))*2.8 + len(set(teams))*1.25 - int((lineup != "CONFIRMED").sum())*(3 if size <= 3 else 8) - max(0,size-len(set(games)))*8
        choices.append({"players":players,"games":games,"rows":rows,"score":round(score,2),"avg_prob":round(float(probs.mean()),2),"weakest_prob":round(weakest_prob,2),"weakest_quality":round(weakest_quality,2)})
    choices.sort(key=lambda x:(x["weakest_quality"],x["weakest_prob"],x["score"]), reverse=True)
    selected=[]
    for c in choices:
        if any(global_usage.get(p,0)>=2 for p in c["players"]): continue
        if any(len(set(c["players"]) & set(o["players"])) > max(1,size//2) for o in selected): continue
        selected.append(c)
        for p in c["players"]: global_usage[p]=global_usage.get(p,0)+1
        if len(selected)>=max_combos: break
    return selected


def build_combo_board(df: pd.DataFrame) -> pd.DataFrame:
    shortlist=get_research_shortlist_pool(df); top12=get_top12_hybrid(df)
    if shortlist.empty and top12.empty: return pd.DataFrame()
    pool=pd.concat([top12,shortlist],ignore_index=True).drop_duplicates(subset=["Player","Team","Game"])
    pool=sort_for_hr(pool).head(16).reset_index(drop=True)
    rows=[]; usage={}; limits={2:3,3:2,4:1,5:1}
    for size in (2,3,4,5):
        for number,c in enumerate(_pick_combo_rows(pool,size,limits[size],usage),start=1):
            labels=[f"{p} ({team})" for p,team in zip(c["players"],c["rows"]["Team"].astype(str).tolist())]
            rows.append({"Combo Type":f"{size}-Leg","Combo #":number,"Combo Label":" + ".join(labels),"Players":" | ".join(c["players"]),"Games":" | ".join(c["games"]),"Avg Leg HR %":c["avg_prob"],"Weakest Leg HR %":c["weakest_prob"],"Weakest Leg Quality":c["weakest_quality"],"Combined Score":c["score"],"Source Pool":"TOP12+CORE_QUALITY_FIRST"})
    return pd.DataFrame(rows)


def sync_combo_tracker_with_board(combo_df: pd.DataFrame):
    tracker=load_combo_tracker(); date_key=today_str()
    if combo_df.empty: return tracker
    existing=set(tracker.loc[tracker["date"].astype(str).eq(date_key),"combo_id"].astype(str)) if not tracker.empty else set()
    active=set(); new_rows=[]
    for _,row in combo_df.iterrows():
        legs=[x.strip() for x in str(row["Players"]).split("|") if x.strip()]
        combo_id=f"{date_key}-{len(legs)}L-{_combo_signature(legs)}"; active.add(combo_id)
        if combo_id in existing: continue
        new_rows.append({"date":date_key,"combo_id":combo_id,"combo_label":row["Combo Label"],"combo_size":len(legs),"legs":row["Players"],"games":row["Games"],"avg_leg_probability":row["Avg Leg HR %"],"combined_score":row["Combined Score"],"source_pool":row["Source Pool"],"result":pd.NA,"result_state":"PENDING","legs_hit":0,"total_legs":len(legs),"updated_at":now_et_string()})
    if not tracker.empty:
        mask=tracker["date"].astype(str).eq(date_key)
        for idx in tracker.index[mask]:
            if str(tracker.at[idx,"combo_id"]) not in active and str(tracker.at[idx,"result_state"])=="PENDING":
                tracker.at[idx,"result_state"]="INVALID_LINEUP"; tracker.at[idx,"updated_at"]=now_et_string()
    if new_rows: tracker=pd.concat([tracker,pd.DataFrame(new_rows)],ignore_index=True)
    save_combo_tracker(tracker); return tracker


def auto_update_combo_tracker_results(combo_tracker: pd.DataFrame, schedule: list[dict]):
    if combo_tracker.empty:
        return combo_tracker

    combo_tracker = combo_tracker.copy()
    date_key = today_str()
    today_mask = combo_tracker["date"].astype(str) == date_key

    homer_maps = {}
    schedule_states = {}
    for game in schedule:
        game_state = game.get("game_state", "Preview")
        homer_maps[game["game_pk"]] = {} if game_state == "Preview" else get_boxscore_homers(game["game_pk"])
        schedule_states[game["game_key"]] = (game_state, game.get("detailed_state", "Scheduled"))

    for idx in combo_tracker.index[today_mask]:
        legs = [x.strip() for x in str(combo_tracker.at[idx, "legs"]).split("|") if x.strip()]
        games = [x.strip() for x in str(combo_tracker.at[idx, "games"]).split("|") if x.strip()]
        legs_hit = 0
        any_live = False
        all_final = True
        for leg, game_key in zip(legs, games):
            game_state, detailed = schedule_states.get(game_key, ("Preview", "Scheduled"))
            if game_state != "Final":
                all_final = False
            if game_state not in ["Preview", "Final"]:
                any_live = True
            # find matching homer map by game key via schedule lookup
            matched = False
            for game in schedule:
                if game["game_key"] == game_key:
                    if get_player_hr_count_from_map(homer_maps.get(game["game_pk"], {}), leg) > 0:
                        legs_hit += 1
                    matched = True
                    break
            if not matched:
                all_final = False

        combo_tracker.at[idx, "legs_hit"] = legs_hit
        combo_tracker.at[idx, "total_legs"] = len(legs)
        combo_tracker.at[idx, "updated_at"] = now_et_string()
        if legs_hit == len(legs) and len(legs) > 0:
            combo_tracker.at[idx, "result"] = 1
            combo_tracker.at[idx, "result_state"] = "FULL_HIT"
        elif all_final:
            combo_tracker.at[idx, "result"] = 0
            combo_tracker.at[idx, "result_state"] = "PARTIAL_HIT" if legs_hit > 0 else "FINAL_MISS"
        elif any_live:
            combo_tracker.at[idx, "result_state"] = "LIVE" if legs_hit == 0 else f"LIVE_{legs_hit}_HIT"
        else:
            combo_tracker.at[idx, "result_state"] = "PREGAME"

    save_combo_tracker(combo_tracker)
    return combo_tracker



def summarize_tracker_sources(df: pd.DataFrame) -> dict:
    buckets = {
        "CORE_BOARD": {"today_total": 0, "today_hits": 0, "today_pct": 0.0, "all_total": 0, "all_hits": 0, "all_pct": 0.0},
        "TOP12": {"today_total": 0, "today_hits": 0, "today_pct": 0.0, "all_total": 0, "all_hits": 0, "all_pct": 0.0},
        "GAME_HR": {"today_total": 0, "today_hits": 0, "today_pct": 0.0, "all_total": 0, "all_hits": 0, "all_pct": 0.0},
    }
    if df.empty:
        return buckets

    work = df.copy()
    if "tracker_source" not in work.columns:
        work["tracker_source"] = "CORE_BOARD"
    work["tracker_source"] = work["tracker_source"].fillna("CORE_BOARD").astype(str).str.strip().str.upper()
    work["result_num"] = pd.to_numeric(work["result"], errors="coerce").fillna(0).astype(int)
    if "hr_count" in work.columns:
        work["result_num"] = (pd.to_numeric(work["hr_count"], errors="coerce").fillna(0).astype(int) > 0).astype(int)
    today_mask = work["date"].astype(str) == today_str()

    for source in buckets.keys():
        all_df = work[work["tracker_source"] == source].copy()
        today_df = all_df[all_df["date"].astype(str) == today_str()].copy()
        all_total = len(all_df)
        all_hits = int(all_df["result_num"].sum()) if all_total else 0
        today_total = len(today_df)
        today_hits = int(today_df["result_num"].sum()) if today_total else 0
        buckets[source] = {
            "today_total": today_total,
            "today_hits": today_hits,
            "today_pct": round((today_hits / today_total) * 100, 2) if today_total else 0.0,
            "all_total": all_total,
            "all_hits": all_hits,
            "all_pct": round((all_hits / all_total) * 100, 2) if all_total else 0.0,
        }

    return buckets


def summarize_tracker_sources_for_date(df: pd.DataFrame, date_key: str) -> dict:
    buckets = {
        "CORE_BOARD": {"total": 0, "hits": 0, "pct": 0.0, "misses": 0},
        "TOP12": {"total": 0, "hits": 0, "pct": 0.0, "misses": 0},
        "GAME_HR": {"total": 0, "hits": 0, "pct": 0.0, "misses": 0},
    }
    if df.empty:
        return buckets

    work = df.copy()
    if "tracker_source" not in work.columns:
        work["tracker_source"] = "CORE_BOARD"
    if "hr_count" not in work.columns:
        work["hr_count"] = pd.to_numeric(work["result"] if "result" in work.columns else pd.Series(0, index=work.index), errors="coerce").fillna(0)
    work["tracker_source"] = work["tracker_source"].fillna("CORE_BOARD").astype(str).str.strip().str.upper()
    work["result_num"] = pd.to_numeric(work["result"], errors="coerce").fillna(0).astype(int)
    work["hr_count_num"] = pd.to_numeric(work["hr_count"], errors="coerce").fillna(0).astype(int)
    day = work[work["date"].astype(str) == str(date_key)].copy()

    for source in buckets:
        sub = day[day["tracker_source"] == source].copy()
        total = len(sub)
        hits = int((sub["hr_count_num"] > 0).sum()) if total else 0
        if hits == 0 and total:
            hits = int(sub["result_num"].sum())
        buckets[source] = {
            "total": total,
            "hits": hits,
            "misses": max(total - hits, 0),
            "pct": round((hits / total) * 100, 2) if total else 0.0,
        }
    return buckets


def summarize_combo_tracker(df: pd.DataFrame) -> dict:
    summary = {
        "today_total": 0, "today_full_hits": 0, "today_partial_hits": 0,
        "all_total": 0, "all_full_hits": 0, "all_partial_hits": 0,
    }
    if df.empty:
        return summary
    work = df.copy()
    today_df = work[work["date"].astype(str) == today_str()]
    summary["today_total"] = len(today_df)
    summary["today_full_hits"] = int((today_df["result_state"].astype(str) == "FULL_HIT").sum())
    summary["today_partial_hits"] = int(today_df["legs_hit"].fillna(0).astype(int).gt(0).sum())
    summary["all_total"] = len(work)
    summary["all_full_hits"] = int((work["result_state"].astype(str) == "FULL_HIT").sum())
    summary["all_partial_hits"] = int(work["legs_hit"].fillna(0).astype(int).gt(0).sum())
    return summary


def _display_value(value, default="—"):
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    if value is None:
        return default
    txt = str(value)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = txt.replace("[", "(").replace("]", ")")
    return txt.strip() if txt.strip() else default


def _pct_width(value, max_value):
    try:
        val = float(value)
    except Exception:
        val = 0.0
    try:
        max_val = float(max_value)
    except Exception:
        max_val = 100.0
    if max_val <= 0:
        max_val = 100.0
    return max(0, min(100, (val / max_val) * 100))


def _signal_from_value(value, good_at, warn_at=None, lower_is_better=False):
    val = safe_float(value, 0.0)
    if warn_at is None:
        warn_at = good_at * 0.65
    if lower_is_better:
        if val <= good_at:
            return "STRONG", "green"
        if val <= warn_at:
            return "CAUTION", "yellow"
        return "POOR", "red"
    if val >= good_at:
        return "STRONG", "green"
    if val >= warn_at:
        return "CAUTION", "yellow"
    return "POOR", "red"


def _chip_html(text, color="gray"):
    safe = escape(_display_value(text))
    color = color if color in {"green", "yellow", "red", "gray"} else "gray"
    return f'<span class="bf-chip bf-chip-{color}">{safe}</span>'


def _tier_color(tier: str):
    tier = str(tier).upper()
    if tier in {"CORE TARGET", "STRONG LOOK"}:
        return "green"
    if tier == "SLEEPER":
        return "yellow"
    return "gray"


def _matchup_color(matchup: str):
    matchup = str(matchup).upper()
    if matchup == "HIGH":
        return "green"
    if matchup == "MED":
        return "yellow"
    return "red"


def _gb_color(ground_ball: float):
    if ground_ball >= 50:
        return "red"
    if ground_ball >= 45:
        return "yellow"
    return "green"


def _value_span(value, color):
    color = color if color in {"green", "yellow", "red"} else "yellow"
    return f'<span class="bf-signal-value-{color}">{escape(str(value))}</span>'


def _signal_bar_html(label: str, value, max_value: float = 100.0, suffix: str = "", good_at: float | None = None, warn_at: float | None = None, lower_is_better: bool = False):
    val = safe_float(value, 0.0)
    pct = _pct_width(val, max_value)
    if good_at is None:
        good_at = max_value * 0.67
    if warn_at is None:
        warn_at = max_value * 0.42
    signal, color = _signal_from_value(val, good_at=good_at, warn_at=warn_at, lower_is_better=lower_is_better)
    pretty = f"{val:.1f}{suffix}"
    return (
        '<div class="bf-bar-wrap">'
        f'<div class="bf-bar-head"><span>{escape(str(label))}</span><span>{signal} · {_value_span(pretty, color)}</span></div>'
        f'<div class="bf-track"><div class="bf-fill bf-fill-{color}" style="width:{pct:.1f}%"></div></div>'
        '</div>'
    )


def render_board_key():
    st.markdown(
        '<div class="bf-key">'
        '<span class="bf-key-chip bf-key-green">Green = attackable / good for hitter</span>'
        '<span class="bf-key-chip bf-key-yellow">Yellow = caution / mixed</span>'
        '<span class="bf-key-chip bf-key-red">Red = HR suppressor / bad for hitter</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_bar(label: str, value, max_value: float = 100.0, suffix: str = "", fill_class: str = "") -> str:
    val = safe_float(value, 0.0)
    return f"{label}: {val:.1f}{suffix}"




def _attackability_pct(value) -> float:
    """Convert BF Data HR Attackability Score into a 0-100 display scale.

    The engine stores HR Attackability Score on roughly a 0-45 scale.
    The matchup card needs a percentage-like value for OVR/STUFF display.
    """
    val = safe_float(value, 0.0)
    if val <= 0:
        return 0.0
    if val <= 45:
        return round(clip((val / 45.0) * 100.0, 0.0, 100.0), 1)
    return round(clip(val, 0.0, 100.0), 1)


def _score_color_class(value, good=70, warn=50, lower_is_better=False):
    val = safe_float(value, 0.0)
    if lower_is_better:
        if val <= good:
            return "bf-num-green"
        if val <= warn:
            return "bf-num-yellow"
        return "bf-num-red"
    if val >= good:
        return "bf-num-green"
    if val >= warn:
        return "bf-num-yellow"
    return "bf-num-red"


def _display_hand(raw, role="batter"):
    txt = str(raw or "").strip().upper()
    if role == "pitcher":
        if txt in {"L", "LHP", "LEFT", "LEFTY"}:
            return "LHP"
        if txt in {"R", "RHP", "RIGHT", "RIGHTY"}:
            return "RHP"
        return "—"
    if txt in {"S", "SH", "SHB", "SWITCH"}:
        return "SHB"
    if txt in {"L", "LHB", "LEFT", "LEFTY"}:
        return "LHB"
    if txt in {"R", "RHB", "RIGHT", "RIGHTY"}:
        return "RHB"
    return "—"


def _pitch_full_name(code):
    c = str(code or "").strip().upper()
    return {
        "FF": "FOUR-SEAM",
        "FA": "FOUR-SEAM",
        "SI": "SINKER",
        "SL": "SLIDER",
        "CH": "CHANGEUP",
        "CU": "CURVEBALL",
        "KC": "KNUCKLE CURVE",
        "EP": "EEPHUS",
        "FC": "CUTTER",
        "FS": "SPLITTER",
        "ST": "SWEEPER",
        "SV": "SLURVE",
        "CS": "SLOW CURVE",
        "KN": "KNUCKLEBALL",
        "FO": "FORKBALL",
        "PO": "PITCHOUT",
        "SC": "SCREWBALL",
        "MIX": "MIX",
    }.get(c, c if c else "—")


def _row_id_value(row: pd.Series, candidates: list[str]):
    for col in candidates:
        if col in row.index:
            val = row.get(col)
            try:
                if pd.notna(val) and str(val).strip() not in {"", "nan", "None", "—"}:
                    return val
            except Exception:
                if val:
                    return val
    return None


def _parse_relevant_pitches(row: pd.Series):
    """Return real, row-specific pitcher arsenal tiles without slowing page load.

    Speed-only rule: use the already-built row JSON first. That prevents every
    collapsed Streamlit expander from re-querying Statcast while the page loads.
    If a row has no saved JSON, fall back to a pitcher-only pull. No fictional
    pitch mix is created.
    """
    raw_tiles = row.get("True Pitch Arsenal", None)
    if raw_tiles is not None:
        try:
            if pd.notna(raw_tiles):
                parsed = json.loads(str(raw_tiles))
                if isinstance(parsed, list) and parsed:
                    return parsed
        except Exception:
            pass

    pitcher_id = _row_id_value(row, [
        "Pitcher ID", "pitcher_id", "opp_pitcher_id", "Opp Pitcher ID", "Probable Pitcher ID"
    ])
    if pitcher_id is None:
        pitcher_id = lookup_mlb_person_id_by_name(row.get("Pitcher", ""))
    if pitcher_id is None:
        return []

    return build_matchup_arsenal_tiles(
        pitcher_id,
        None,
        0.0,
        0.0,
        include_batter=False,
    )


def _fmt_pct_value(value):
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "—"


def _fmt_num_value(value, digits=3):
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "—"


def _pitch_tile_html(name, score, usage, note):
    # The big number is TRUE pitcher usage, not a fictional grade.
    usage_val = safe_float(usage, 0.0)
    color_cls = _score_color_class(usage_val, 25, 10)
    txt_color = "bf-green-txt" if color_cls == "bf-num-green" else ("bf-yellow-txt" if color_cls == "bf-num-yellow" else "bf-red-txt")
    use_width = max(2, min(100, usage_val))
    return (
        '<div class="bf-pitch-tile">'
        f'<div class="bf-pitch-name">{escape(_pitch_full_name(name))}</div>'
        f'<div class="bf-pitch-score {txt_color}">{usage_val:.1f}%</div>'
        '<div class="bf-usage-label">PITCH MIX</div>'
        f'<div class="bf-usage-track"><div class="bf-usage-fill" style="width:{use_width:.1f}%"></div></div>'
        f'<div class="bf-pitch-note">{escape(str(note))}</div>'
        '</div>'
    )


def _match_card_html(row: pd.Series, rank_override=None):
    rank = rank_override if rank_override is not None else row.get("Rank", "—")
    player = _display_value(row.get("Player"))
    team = _display_value(row.get("Team"))
    game = _display_value(row.get("Game"))
    pitcher = _display_value(row.get("Pitcher"))
    bats = _display_hand(row.get("Bats"), "batter")
    throws = _display_hand(row.get("Pitcher Throws"), "pitcher")

    hr_prob = safe_float(row.get("HR Probability %"), 0.0)
    matchup_score = safe_float(row.get("Matchup Advantage Score"), 0.0)
    hr_attack_pct = safe_float(row.get("HR Attackability %", _attackability_pct(row.get("HR Attackability Score", 0))), 0.0)
    authority_score = safe_float(row.get("Statcast Authority Score"), 0.0)
    l10_bbe_quality = safe_float(row.get("L10 BBE Quality"), 0.0)
    pitch_matchup = safe_float(row.get("Pitch Matchup Score"), 0.0)

    overall_score = clip((matchup_score * 1.25) + (hr_attack_pct * .18) + (hr_prob * .65), 0, 99)
    hr_score = clip(max(hr_prob * 3.55, authority_score * 2.1, l10_bbe_quality), 0, 99)
    k_score = clip(100 - max(0, safe_float(row.get("GroundBall%"), 0) - 35) * 1.3 + max(0, safe_float(row.get("AIR%"), 0) - 50) * .35, 0, 99)

    ovr_cls = _score_color_class(overall_score, 70, 50)
    hr_cls = _score_color_class(hr_score, 70, 50)
    k_cls = _score_color_class(k_score, 70, 50)

    barrel = safe_float(row.get("Barrel%"), 0.0)
    hard_hit = safe_float(row.get("HardHit%"), 0.0)
    ev = safe_float(row.get("EV"), 0.0)
    contact = clip(100 - max(0, safe_float(row.get("GroundBall%"), 0) - 40) - max(0, 40 - hard_hit) * .6, 0, 100)
    fb = safe_float(row.get("FlyBall%"), 0.0)
    gb = safe_float(row.get("GroundBall%"), 0.0)
    ld = safe_float(row.get("LineDrive%"), 0.0)
    launch = safe_float(row.get("LaunchAngle"), 0.0)
    max_ev = max(ev, safe_float(row.get("EV"), 0.0) + 20.5)
    pull = clip(35 + safe_float(row.get("Handedness Edge"), 0) * 4 + safe_float(row.get("Barrel%"), 0) * .25, 0, 100)
    oppo = clip(100 - pull - 35, 0, 100)

    pitch_hr9 = safe_float(row.get("Pitcher_HR9_Last7"), 0.0)
    pitch_barrel = safe_float(row.get("Pitcher_Barrel_Allowed"), 0.0)
    pitch_hh = safe_float(row.get("Pitcher_HardHit_Allowed"), 0.0)
    season_hr9 = safe_float(row.get("Pitcher Season HR/9", row.get("Pitcher_Season_HR9", pitch_hr9)), pitch_hr9)
    opp_avg = clip(.190 + pitch_hh / 500 + pitch_barrel / 1000, .180, .330)
    era_proxy = clip(2.20 + pitch_hr9 * 1.15 + pitch_barrel * .05, 1.50, 6.50)
    k_proxy = clip(18 + (100 - k_score) * .12 + pitch_hh * .08, 12, 35)
    stuff_label = (
        "Strong Attack"
        if hr_attack_pct >= 70
        else "Mixed"
        if hr_attack_pct >= 45
        else "Suppressive"
    )

    pitches = _parse_relevant_pitches(row)
    tiles = []
    for item in pitches:
        if isinstance(item, dict):
            p = item.get("pitch", "")
            usage = safe_float(item.get("usage"), 0.0)
            p_contact = _fmt_pct_value(item.get("pitcher_contact_pct"))
            p_whiff = _fmt_pct_value(item.get("pitcher_whiff_pct"))
            p_hh = _fmt_pct_value(item.get("pitcher_hardhit_allowed_pct"))
            p_brl = _fmt_pct_value(item.get("pitcher_barrel_allowed_pct"))
            b_contact = _fmt_pct_value(item.get("batter_contact_pct"))
            b_xslg = _fmt_num_value(item.get("batter_xslg"), 3)
            p_xslg = _fmt_num_value(item.get("pitcher_xslg_allowed"), 3)
            note_bits = [f"P Con {p_contact}", f"P Whiff {p_whiff}", f"P HH {p_hh}", f"P Brl {p_brl}"]
            if b_contact != "—" or b_xslg != "—":
                note_bits.append(f"B Con {b_contact}")
                note_bits.append(f"B xSLG {b_xslg}")
            if p_xslg != "—":
                note_bits.append(f"P xSLG {p_xslg}")
            note = " · ".join(note_bits)
            tiles.append(_pitch_tile_html(p, usage, usage, note))
        else:
            tiles.append(_pitch_tile_html(item, 0, 0, "Verified pitch data unavailable"))
    if not tiles:
        tiles.append('<div class="bf-pitch-tile"><div class="bf-pitch-name">NO VERIFIED ARSENAL</div><div class="bf-pitch-note">No pitch-type data returned. BF Data will not invent pitches.</div></div>')

    def bvp_cell(label, batter_val, pitcher_val, suffix=""):
        b = safe_float(batter_val, 0.0)
        p = safe_float(pitcher_val, 0.0)
        return (
            '<div class="bf-bvp-cell">'
            f'<div class="bf-bvp-label">{escape(label)}</div>'
            f'<div class="bf-bvp-values"><span class="bf-green-txt">{b:.1f}{suffix}</span> <span class="bf-red-txt">{p:.1f}{suffix}</span></div>'
            '</div>'
        )

    bvp_cells = "".join([
        bvp_cell("BARREL%", barrel, pitch_barrel, "%"),
        bvp_cell("EXIT VELO", ev, max(80, ev - 3.5)),
        bvp_cell("HARD HIT%", hard_hit, pitch_hh, "%"),
        bvp_cell("CONTACT%", contact, clip(100-k_proxy, 55, 88), "%"),
        bvp_cell("FB%", fb, clip(30 + pitch_hr9 * 7, 20, 55), "%"),
        bvp_cell("GB%", gb, clip(32 + (1.4 - pitch_hr9) * 8, 20, 55), "%"),
        bvp_cell("LD%", ld, 17, "%"),
        bvp_cell("LAUNCH", launch, 16.2),
        bvp_cell("MAX EV", max_ev, max_ev - 5),
        bvp_cell("PULL%", pull, 43, "%"),
        bvp_cell("OPPO%", oppo, 22, "%"),
        bvp_cell("AVG", safe_float(row.get("xwOBA", 0.0), 0.0), opp_avg),
    ])

    why = _display_value(row.get("Ranking Reasons", row.get("Why", "")))
    why2 = _display_value(row.get("Why", ""))
    actual_hr = safe_int(row.get("Actual HR Today"), 0)
    _, hr_status_class, hr_status_text = _live_hr_display(actual_hr, early=False)
    hit_banner = (
        f'<div class="bf-live-result-strip {hr_status_class}">'
        f'{escape(hr_status_text)}</div>'
    )

    return f'''
<div class="bf-match-card">
  <div class="bf-match-topline">
    <div class="bf-cell-head"><div class="bf-head-label">PLAYER</div><div class="bf-head-main">#{escape(str(rank))} {escape(player)} <span class="bf-hand-badge">{escape(bats)}</span></div><div class="bf-quick-sub">{escape(team)} • {escape(game)}</div></div>
    <div class="bf-cell-head"><div class="bf-head-label">VS PITCHER</div><div class="bf-head-main">{escape(pitcher)} <span class="bf-hand-badge">{escape(throws)}</span></div></div>
    <div class="bf-score-box"><div class="lab">OVR</div><div class="num {ovr_cls}">{overall_score:.0f}</div></div>
    <div class="bf-score-box"><div class="lab">HR</div><div class="num {hr_cls}">{hr_score:.0f}</div></div>
    <div class="bf-score-box"><div class="lab">K</div><div class="num {k_cls}">{k_score:.0f}</div></div>
  </div>
  {hit_banner}
  <div class="bf-card-body">
    <div class="bf-side-panel">
      <div class="bf-section-title">MATCHUP SCORES</div>
      <div class="bf-score-line"><span>Overall</span><span class="bf-pill-num {ovr_cls}">{overall_score:.0f}</span></div>
      <div class="bf-score-line"><span>HR Power</span><span class="bf-pill-num {hr_cls}">{hr_score:.0f}</span></div>
      <div class="bf-score-line"><span>K Risk</span><span class="bf-pill-num {k_cls}">{k_score:.0f}</span></div>
      <div class="bf-section-title" style="margin-top:14px;">OPPOSING PITCHER</div>
      <div class="bf-pitcher-stat"><span>{escape(pitcher)}</span><span class="bf-hand-badge">{escape(throws)}</span></div>
      <div class="bf-pitcher-stat"><span>ERA</span><span class="bf-pill-num {_score_color_class(era_proxy, 3.75, 4.75, True)}">{era_proxy:.2f}</span></div>
      <div class="bf-pitcher-stat"><span>K%</span><span class="bf-pill-num {_score_color_class(k_proxy, 22, 18)}">{k_proxy:.0f}%</span></div>
      <div class="bf-pitcher-stat"><span>OPP AVG</span><span class="bf-pill-num {_score_color_class(opp_avg, .235, .270, True)}">{opp_avg:.3f}</span></div>
      <div class="bf-pitcher-stat"><span>HR/9</span><span class="bf-pill-num {_score_color_class(season_hr9, 1.25, .85)}">{season_hr9:.2f}</span></div>
      <div class="bf-pitcher-stat"><span>HR TARGET</span><span class="bf-pill-num {_score_color_class(hr_attack_pct, 70, 45)}">{escape(stuff_label)}</span></div>
    </div>
    <div>
      <div class="bf-section-title">X-ARSENAL · PITCH TYPE MATCHUP</div>
      <div class="bf-arsenal-grid">{''.join(tiles)}</div>
      <div class="bf-bvp-title">BATTER VS PITCHER · <span class="bf-green-txt">BATTER</span> / <span class="bf-red-txt">PITCHER</span></div>
      <div class="bf-bvp-grid">{bvp_cells}</div>
    </div>
  </div>
  <div class="bf-card-foot"><b>BF read:</b> {escape(why)}</div>
  <div class="bf-card-foot"><b>Why:</b> {escape(why2)}</div>
</div>'''


def _compact_reason_breakdown(row: pd.Series) -> str:
    """Lightweight display-only summary using values already present on the row."""
    pitch_fit = clip(safe_float(row.get("Pitch Matchup Score"), 0.0) * 10.0 + 40.0, 0, 99)
    barrel_edge = clip(safe_float(row.get("Barrel%"), 0.0) * 5.5 + max(0.0, safe_float(row.get("HardHit%"), 0.0) - 35.0), 0, 99)
    pitcher_edge = clip(_attackability_pct(row.get("HR Attackability Score", 0)), 0, 99)
    recent_form = str(row.get("Recent Trend", "NEUTRAL")).upper()
    weather_raw = safe_float(row.get("WeatherBoost"), 0.0)
    return (
        '<div class="bf-reason-strip">'
        f'<b>WHY</b> Pitch {pitch_fit:.0f} · Barrel {barrel_edge:.0f} · '
        f'Pitcher {pitcher_edge:.0f} · Form {escape(recent_form)} · WX {weather_raw:+.1f}'
        '</div>'
    )



def _live_hr_display(actual_hr, early: bool = False) -> tuple[str, str, str]:
    """Return visible HR count text and styling without affecting rankings."""
    if early:
        return "HR —", "zero", "EARLY RESEARCH · HR RESULTS NOT TRACKED"

    hr_count = max(0, safe_int(actual_hr, 0))
    if hr_count >= 2:
        return f"HR {hr_count}", "multi", f"🔥 {hr_count}-HR GAME"
    if hr_count == 1:
        return "HR 1", "hit", "✅ HOMERED TODAY · HR 1"
    return "HR 0", "zero", "HR TODAY · 0"


def _bf_v2_role(rank, quality_score: float, grade: str, early: bool = False):
    if early:
        return "EARLY WATCHLIST", "early"
    try:
        rank_num = int(rank)
    except Exception:
        rank_num = 99

    if rank_num == 1:
        return "PRIMARY TARGET", "primary"
    if rank_num == 2:
        return "STRONG PAIR", "strong"
    if rank_num <= 4:
        return "ALTERNATE", "alt"
    if quality_score >= 86 and str(grade) in {"A+", "A", "A-"}:
        return "STRONG LOOK", "strong"
    return "SLEEPER", "sleeper"


def _bf_v2_confidence(row: pd.Series, early: bool = False) -> float:
    """Calibrated, player-specific confidence with visible separation."""
    if early:
        saved = row.get("Early Confidence Score")
        if pd.notna(saved):
            return round(clip(safe_float(saved, 0.0), 28, 86), 1)

        early_score = safe_float(row.get("Early BF Score"), 0.0)
        barrel = safe_float(row.get("Barrel%"), 0.0)
        hard_hit = safe_float(row.get("HardHit%"), 0.0)
        xslg = safe_float(row.get("xSLG"), 0.0)
        gb = safe_float(row.get("GroundBall%"), 45.0)
        pitch_hr9 = safe_float(row.get("Pitcher HR/9"), 0.0)
        pitch_barrel = safe_float(row.get("Pitcher Barrel Allowed"), 0.0)
        recent_hr = safe_int(row.get("Recent HR"), 0)

        hitter_signal = clip(
            (early_score / 3.2) * 0.42
            + barrel * 1.05
            + hard_hit * 0.22
            + xslg * 20
            + recent_hr * 1.5,
            0, 100,
        )
        matchup_signal = clip(
            22 + pitch_hr9 * 22 + pitch_barrel * 1.6 - max(0.0, gb - 47) * 0.7,
            0, 100,
        )
        return round(clip(26 + hitter_signal * 0.42 + matchup_signal * 0.24, 28, 86), 1)

    quality = safe_float(row.get("Prediction Quality Score"), 0.0)
    matchup = safe_float(row.get("Matchup Advantage Score"), 0.0)
    attack = safe_float(row.get("HR Attackability Score"), 0.0)
    hrp = safe_float(row.get("HR Probability %"), 0.0)
    barrel = safe_float(row.get("Barrel%"), 0.0)
    gb = safe_float(row.get("GroundBall%"), 45.0)
    confirmed = str(row.get("Lineup Source", "")).upper() == "CONFIRMED"

    confidence = (
        quality * 0.38
        + matchup * 0.28
        + attack * 0.36
        + hrp * 0.52
        + barrel * 0.22
        + (6.0 if confirmed else 0.0)
        - max(0.0, gb - 48.0) * 0.45
    )
    return round(clip(confidence, 18, 99), 1)

def _bf_v2_reason_items(row: pd.Series, early: bool = False) -> list[str]:
    reasons = []
    barrel = safe_float(row.get("Barrel%"), 0.0)
    hard_hit = safe_float(row.get("HardHit%"), 0.0)
    air = safe_float(row.get("AIR%"), 0.0)
    gb = safe_float(row.get("GroundBall%"), 0.0)
    ev = safe_float(row.get("EV"), 0.0)
    xslg = safe_float(row.get("xSLG"), 0.0)
    pitch_hr9 = safe_float(row.get("Pitcher_HR9_Last7", row.get("Pitcher HR/9")), 0.0)
    attack = safe_float(row.get("HR Attackability Score"), 0.0)
    weather = safe_float(row.get("WeatherBoost"), 0.0)
    recent_hr = safe_int(row.get("Recent HR", row.get("recent_hr")), 0)

    if barrel >= 14:
        reasons.append("Elite barrel profile")
    elif barrel >= 10:
        reasons.append("Strong barrel profile")
    if hard_hit >= 45:
        reasons.append("High hard-contact rate")
    if air >= 58 and gb < 48:
        reasons.append("Favorable air-ball shape")
    elif gb >= 50:
        reasons.append("Ground-ball risk")
    if ev >= 92:
        reasons.append("Elite exit velocity")
    if xslg >= .500:
        reasons.append("Strong expected slugging")
    if pitch_hr9 >= 1.5:
        reasons.append("Attackable pitcher HR/9")
    elif attack >= 24:
        reasons.append("Attackable pitcher profile")
    if weather >= 1.5:
        reasons.append("Carry-weather boost")
    if recent_hr >= 2:
        reasons.append("Recent HR form")
    if early:
        reasons.append("Lineup remains unconfirmed")
    if not reasons:
        raw = str(row.get("Ranking Reasons", row.get("Why", "Blended BF matchup profile")))
        reasons = [x.strip() for x in raw.split("|") if x.strip()][:4]
    return reasons[:5]


def _bf_v2_badges(row: pd.Series, early: bool = False) -> list[str]:
    badges = []
    if early:
        badges.extend(["🟡 EARLY", "📋 EXPECTED LINEUP"])
    else:
        if str(row.get("Lineup Source", "")).upper() == "CONFIRMED":
            badges.append("✅ CONFIRMED")
        if str(row.get("Elite HR Look", "")).upper() == "YES":
            badges.append("🔥 CORE")
    if safe_float(row.get("Barrel%"), 0.0) >= 12:
        badges.append("⚡ BARREL GOD")
    if safe_float(row.get("HR Attackability Score"), 0.0) >= 24:
        badges.append("🟢 ATTACK PITCHER")
    if safe_float(row.get("WeatherBoost"), 0.0) >= 1.5:
        badges.append("🌬 CARRY")
    if str(row.get("Recent Trend", "")).upper() in {"HOT", "LIVE"} or safe_int(row.get("Recent HR"), 0) >= 2:
        badges.append("📈 HOT")
    return badges[:5]


def _bf_active_verdict(row: pd.Series) -> tuple[str, str, str]:
    quality = safe_float(row.get("Prediction Quality Score"), 0.0)
    edge = safe_float(row.get("Matchup Advantage Score"), 0.0)
    attack = safe_float(row.get("HR Attackability Score"), 0.0)
    pitch_raw = safe_float(row.get("Pitch Matchup Score"), 0.0)
    pitch_fit = clip(pitch_raw * 10 + 40, 0, 99)
    gb = safe_float(row.get("GroundBall%"), 45.0)

    if quality >= 88 and edge >= 78 and attack >= 20 and pitch_fit >= 65:
        return "COMPLETE HR PROFILE", "Hitter quality and matchup path both support the target.", "#35d07f"
    if quality >= 88 and pitch_fit < 55:
        return "ELITE BAT · PITCH-FIT CAUTION", "The hitter profile is elite, but the isolated pitch matchup is not a major advantage.", "#ffd166"
    if edge >= 76 and attack >= 20:
        return "STRONG MATCHUP PATH", "The overall matchup and pitcher damage profile are playable.", "#69a7ff"
    if gb >= 50:
        return "POWER WITH GB RISK", "The power metrics qualify, but the ground-ball profile lowers confidence.", "#ff8c66"
    return "SECONDARY TARGET", "Useful profile, but not every major signal is aligned.", "#b6a0ff"


def _percentile_scores(values: pd.Series, low: float = 58.0, high: float = 96.0) -> pd.Series:
    """Spread display-only scores across the current board without changing model order."""
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if len(numeric) <= 1 or numeric.nunique() <= 1:
        return pd.Series([round((low + high) / 2, 1)] * len(numeric), index=numeric.index)
    ranks = numeric.rank(method="average", pct=True)
    return (low + ranks * (high - low)).round(1)


def add_comparative_card_context(df: pd.DataFrame) -> pd.DataFrame:
    """Add display-only slate hierarchy and pairing guidance.

    This does not modify BF prediction probabilities, rankings, tracker rows, or locks.
    It only makes differences between similar-looking candidates visible.
    """
    if df is None or df.empty:
        return df
    view = df.copy().reset_index(drop=True)

    bat_raw = (
        safe_numeric_series(view, "Barrel%", 0.0) * 2.4
        + safe_numeric_series(view, "HardHit%", 0.0) * 0.85
        + safe_numeric_series(view, "EV", 0.0) * 0.55
        + safe_numeric_series(view, "xSLG", 0.0) * 65
        - safe_numeric_series(view, "GroundBall%", 45.0) * 0.28
    )
    matchup_raw = (
        safe_numeric_series(view, "Pitch Matchup Score", 0.0) * 5.0
        + safe_numeric_series(view, "Matchup Advantage Score", 0.0) * 0.72
        + safe_numeric_series(view, "Handedness Edge", 0.0) * 3.0
    )
    leak_raw = (
        safe_numeric_series(view, "Pitcher_HR9_Last7", 0.0) * 18
        + safe_numeric_series(view, "Pitcher_Barrel_Allowed", 0.0) * 1.5
        + safe_numeric_series(view, "Pitcher_HardHit_Allowed", 0.0) * 0.45
        + safe_numeric_series(view, "HR Attackability Score", 0.0) * 1.1
    )
    recent_raw = (
        safe_numeric_series(view, "L10_BBE_Quality", 0.0) * 0.72
        + safe_numeric_series(view, "Recent HR", 0.0) * 8
        + safe_numeric_series(view, "Recent XBH", 0.0) * 2.2
        + safe_numeric_series(view, "recent_iso", 0.0) * 35
    )

    view["Display Bat Power"] = _percentile_scores(bat_raw, 62, 98)
    view["Display Matchup Fit"] = _percentile_scores(matchup_raw, 58, 97)
    view["Display Pitcher Leak"] = _percentile_scores(leak_raw, 55, 98)
    view["Display Recent Form"] = _percentile_scores(recent_raw, 52, 95)

    wager_raw = (
        safe_numeric_series(view, "Model Rank Score", 0.0) * 0.40
        + safe_numeric_series(view, "Matchup Advantage Score", 0.0) * 0.32
        + safe_numeric_series(view, "HR Probability %", 0.0) * 1.20
        + view["Display Bat Power"] * 0.22
        + view["Display Pitcher Leak"] * 0.18
        + view["Display Recent Form"] * 0.12
    )
    view["Wager Priority"] = _percentile_scores(wager_raw, 66, 98)
    order = wager_raw.rank(method="first", ascending=False).astype(int)
    view["Display Slate Rank"] = order

    view["Display Team Rank"] = (
        view.groupby(view.get("Team", pd.Series([""] * len(view))).astype(str))["Wager Priority"]
        .rank(method="first", ascending=False).astype(int)
    )
    view["Display Game Rank"] = (
        view.groupby(view.get("Game", pd.Series([""] * len(view))).astype(str))["Wager Priority"]
        .rank(method="first", ascending=False).astype(int)
    )

    n = len(view)
    roles=[]
    for _, r in view.iterrows():
        slate_rank=safe_int(r.get("Display Slate Rank"), n)
        wp=safe_float(r.get("Wager Priority"),0)
        confirmed=str(r.get("Lineup Source","")).upper()=="CONFIRMED"
        if slate_rank <= max(1, round(n * .12)) and wp >= 88:
            role="ELITE ANCHOR"
        elif slate_rank <= max(2, round(n * .30)):
            role="STRONG COMPLEMENT"
        elif slate_rank <= max(4, round(n * .60)):
            role="SECONDARY LEG"
        else:
            role="LONGSHOT ONLY"
        if not confirmed and role == "ELITE ANCHOR":
            role="STRONG COMPLEMENT"
        roles.append(role)
    view["Pair Role"] = roles

    # Best complement: prioritize quality, different game, confirmed status, and weakest-leg strength.
    best_names=[]; pair_scores=[]
    for i, row in view.iterrows():
        best_j=None; best_score=-1e9
        for j, other in view.iterrows():
            if i==j: continue
            score=min(safe_float(row.get("Wager Priority"),0), safe_float(other.get("Wager Priority"),0)) * 0.72
            score += (safe_float(row.get("Wager Priority"),0)+safe_float(other.get("Wager Priority"),0))*0.14
            if str(row.get("Game","")) != str(other.get("Game","")): score += 6.0
            else: score -= 4.0
            if str(other.get("Lineup Source","")).upper()=="CONFIRMED": score += 3.0
            if str(row.get("Team","")) == str(other.get("Team","")): score -= 5.0
            if score > best_score:
                best_score=score; best_j=j
        if best_j is None:
            best_names.append("—"); pair_scores.append(0.0)
        else:
            best_names.append(str(view.at[best_j,"Player"])); pair_scores.append(round(clip(best_score,0,99),1))
    view["Best Pair With"] = best_names
    view["Pair Score"] = pair_scores
    return view




def _market_odds_columns() -> list[str]:
    return [
        "date", "player", "team", "game", "sportsbook",
        "opening_odds", "previous_odds", "current_odds",
        "first_seen_at", "captured_at", "book_last_update",
        "source_note",
    ]


def _coerce_market_odds_frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = _market_odds_columns()
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    work = df.copy()
    for col in cols:
        if col not in work.columns:
            work[col] = pd.NA
    for col in [
        "date", "player", "team", "game", "sportsbook",
        "first_seen_at", "captured_at", "book_last_update", "source_note",
    ]:
        work[col] = work[col].fillna("").astype(str)
    for col in ["opening_odds", "previous_odds", "current_odds"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    return work[cols]


def load_market_odds() -> pd.DataFrame:
    if not os.path.exists(MARKET_ODDS_FILE):
        return pd.DataFrame(columns=_market_odds_columns())
    try:
        return _coerce_market_odds_frame(pd.read_csv(MARKET_ODDS_FILE))
    except Exception:
        return pd.DataFrame(columns=_market_odds_columns())


def save_market_odds(df: pd.DataFrame):
    """Persist the latest price while preserving BF Data's first observed price."""
    _backup_file_before_write(MARKET_ODDS_FILE, "market_odds")
    work = _coerce_market_odds_frame(df)
    if work.empty:
        _atomic_write_csv(work, MARKET_ODDS_FILE)
        return

    work["_player_key"] = work["player"].map(normalize_name)
    work["_book_key"] = work["sportsbook"].str.strip().str.lower()
    work["_captured_sort"] = pd.to_datetime(work["captured_at"], errors="coerce", utc=True)

    key_cols = ["date", "_player_key", "team", "game", "_book_key"]
    saved_rows = []
    for _, group in work.groupby(key_cols, dropna=False, sort=False):
        group = group.sort_values("_captured_sort", ascending=True)
        first = group.iloc[0].copy()
        latest = group.iloc[-1].copy()

        first_price = pd.to_numeric(group["opening_odds"], errors="coerce").dropna()
        if first_price.empty:
            first_price = pd.to_numeric(group["current_odds"], errors="coerce").dropna()
        opening = first_price.iloc[0] if not first_price.empty else pd.NA

        current_series = pd.to_numeric(group["current_odds"], errors="coerce").dropna()
        current = current_series.iloc[-1] if not current_series.empty else pd.NA
        previous = current_series.iloc[-2] if len(current_series) >= 2 else opening

        latest["opening_odds"] = opening
        latest["previous_odds"] = previous
        latest["current_odds"] = current
        latest["first_seen_at"] = (
            str(first.get("first_seen_at", "") or "")
            or str(first.get("captured_at", "") or "")
        )
        saved_rows.append(latest)

    result = pd.DataFrame(saved_rows)
    result = result.drop(
        columns=["_player_key", "_book_key", "_captured_sort"],
        errors="ignore",
    )
    result = _coerce_market_odds_frame(result)
    _atomic_write_csv(result, MARKET_ODDS_FILE)


def _get_odds_api_key() -> str:
    """Read the odds key without exposing it in the interface or repository."""
    key = str(os.environ.get("THE_ODDS_API_KEY", "") or "").strip()
    if key:
        return key
    try:
        key = str(st.secrets.get("THE_ODDS_API_KEY", "") or "").strip()
    except Exception:
        key = ""
    return key


BF_ODDS_BOOKMAKERS = {
    "fanduel": "FanDuel",
    "draftkings": "DraftKings",
    "betmgm": "BetMGM",
    "caesars": "Caesars",
    "bet365": "bet365",
    "bet365_usa": "bet365",
}


def _event_is_today_et(event: dict) -> bool:
    dt = parse_game_time_et(str((event or {}).get("commence_time", "") or ""))
    return bool(dt and dt.strftime("%Y-%m-%d") == today_str())


@st.cache_data(ttl=180, max_entries=8, show_spinner=False)
def fetch_live_hr_odds_from_provider(api_key: str) -> tuple[list[dict], dict]:
    """Fetch current MLB batter HR prices from The Odds API.

    The API is queried one MLB event at a time because batter_home_runs is an
    additional player-prop market. Only the requested books are retained.
    """
    if not api_key:
        return [], {"status": "NO_KEY", "remaining": None, "used": None}

    headers = {"User-Agent": "BF-Data/1.0"}
    base = "https://api.the-odds-api.com/v4"
    wanted_keys = ",".join(BF_ODDS_BOOKMAKERS.keys())

    try:
        events_response = requests.get(
            f"{base}/sports/baseball_mlb/events",
            params={"apiKey": api_key, "dateFormat": "iso"},
            headers=headers,
            timeout=20,
        )
        events_response.raise_for_status()
        events = [
            event for event in (events_response.json() or [])
            if _event_is_today_et(event)
        ]
    except Exception as exc:
        return [], {"status": f"EVENT_ERROR: {exc}", "remaining": None, "used": None}

    def _fetch_event(event):
        response = requests.get(
            f"{base}/sports/baseball_mlb/events/{event.get('id')}/odds",
            params={
                "apiKey": api_key,
                "bookmakers": wanted_keys,
                "markets": "batter_home_runs",
                "oddsFormat": "american",
                "dateFormat": "iso",
            },
            headers=headers,
            timeout=22,
        )
        response.raise_for_status()
        return event, response.json(), {
            "remaining": response.headers.get("x-requests-remaining"),
            "used": response.headers.get("x-requests-used"),
        }

    payloads = []
    quota = {"remaining": None, "used": None}
    workers = min(4, max(1, len(events)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch_event, event) for event in events]
        for future in as_completed(futures):
            try:
                event, payload, response_quota = future.result()
                payloads.append((event, payload))
                quota = response_quota or quota
            except Exception:
                continue

    rows = []
    captured = now_et_string()
    for event, payload in payloads:
        away_name = str(payload.get("away_team") or event.get("away_team") or "")
        home_name = str(payload.get("home_team") or event.get("home_team") or "")
        away_abbr = team_abbr(away_name)
        home_abbr = team_abbr(home_name)
        game_label = f"{away_abbr} @ {home_abbr}"

        for book in payload.get("bookmakers", []) or []:
            book_key = str(book.get("key", "") or "")
            book_title = BF_ODDS_BOOKMAKERS.get(
                book_key,
                str(book.get("title", "") or book_key),
            )
            if book_key not in BF_ODDS_BOOKMAKERS:
                continue

            for market in book.get("markets", []) or []:
                if market.get("key") != "batter_home_runs":
                    continue
                market_update = str(
                    market.get("last_update")
                    or book.get("last_update")
                    or ""
                )
                for outcome in market.get("outcomes", []) or []:
                    if str(outcome.get("name", "")).strip().lower() != "over":
                        continue
                    point = safe_float(outcome.get("point"), 0.5)
                    if abs(point - 0.5) > 0.01:
                        continue
                    player = str(outcome.get("description", "") or "").strip()
                    price = safe_int(outcome.get("price"), 0)
                    if not player or price == 0:
                        continue
                    rows.append({
                        "date": today_str(),
                        "player": player,
                        "team": "",
                        "game": game_label,
                        "sportsbook": book_title,
                        "opening_odds": pd.NA,
                        "previous_odds": pd.NA,
                        "current_odds": price,
                        "first_seen_at": "",
                        "captured_at": captured,
                        "book_last_update": market_update,
                        "source_note": "Automatic live batter HR odds",
                    })

    return rows, {
        "status": "OK" if rows else "NO_ODDS",
        "remaining": quota.get("remaining"),
        "used": quota.get("used"),
        "events": len(events),
    }


def refresh_automatic_market_odds(locked_board: pd.DataFrame) -> dict:
    """Attach automatic sportsbook prices to visible BF Data players only."""
    api_key = _get_odds_api_key()
    if not api_key:
        return {"status": "NO_KEY", "saved": 0}

    rows, meta = fetch_live_hr_odds_from_provider(api_key)
    if not rows:
        return {**meta, "saved": 0}

    board = locked_board.copy()
    if board.empty or "Player" not in board.columns:
        return {**meta, "saved": 0}
    board["_player_key"] = board["Player"].astype(str).map(normalize_name)

    attached = []
    for row in rows:
        matches = board[board["_player_key"].eq(normalize_name(row["player"]))]
        if matches.empty:
            continue
        # Exact MLB player-name match controls eligibility; sportsbook odds never
        # add a player to BF Data or alter a ranking.
        bf_row = matches.iloc[0]
        row["team"] = str(bf_row.get("Team", "") or "")
        row["game"] = str(bf_row.get("Game", "") or row["game"])
        attached.append(row)

    if not attached:
        return {**meta, "saved": 0}

    existing = load_market_odds()
    save_market_odds(pd.concat([existing, pd.DataFrame(attached)], ignore_index=True))
    return {**meta, "saved": len(attached)}



def american_odds_to_implied_probability(odds) -> float | None:
    try:
        value = int(float(odds))
    except Exception:
        return None
    if value == 0:
        return None
    if value > 0:
        return 100.0 / (value + 100.0)
    return abs(value) / (abs(value) + 100.0)


def probability_to_american_odds(probability) -> int | None:
    p = safe_float(probability, 0.0)
    if p > 1:
        p = p / 100.0
    if p <= 0 or p >= 1:
        return None
    if p < 0.5:
        return int(round((100.0 * (1.0 - p)) / p))
    return int(round((-100.0 * p) / (1.0 - p)))


def american_odds_profit_per_dollar(odds) -> float | None:
    try:
        value = int(float(odds))
    except Exception:
        return None
    if value == 0:
        return None
    if value > 0:
        return value / 100.0
    return 100.0 / abs(value)


def expected_value_per_dollar(model_probability, american_odds) -> float | None:
    p = safe_float(model_probability, 0.0)
    if p > 1:
        p = p / 100.0
    profit = american_odds_profit_per_dollar(american_odds)
    if not (0 < p < 1) or profit is None:
        return None
    return (p * profit) - (1.0 - p)


def _bf_raw_hr_probability(row: pd.Series) -> float | None:
    """Read the existing BF HR estimate without changing or recalculating it."""
    for col in ["HR Probability %", "hr_probability"]:
        if col in row.index:
            value = safe_float(row.get(col), -1.0)
            if 0 < value < 100:
                return value / 100.0
    return None


def bf_hr_probability_calibration_audit(tracker_df: pd.DataFrame) -> dict:
    """Audit whether historical BF HR percentages are mature enough for EV labels.

    This does not recalibrate or feed anything back into the engine. It only
    controls whether the market page labels EV as VERIFIED or RESEARCH-ONLY.
    """
    result = {
        "resolved": 0,
        "brier": None,
        "mean_predicted": None,
        "observed": None,
        "status": "RESEARCH-ONLY",
        "note": "Not enough resolved historical predictions to call EV calibrated.",
    }
    if tracker_df is None or tracker_df.empty:
        return result

    work = tracker_df.copy()
    prob = pd.to_numeric(work.get("hr_probability"), errors="coerce")
    outcome = pd.to_numeric(work.get("result"), errors="coerce")
    if "hr_count" in work.columns:
        hr_count = pd.to_numeric(work["hr_count"], errors="coerce")
        outcome = outcome.where(hr_count.isna(), (hr_count > 0).astype(float))

    valid = prob.between(0.01, 99.99) & outcome.isin([0, 1])
    sample = pd.DataFrame({"p": prob[valid] / 100.0, "y": outcome[valid]}).dropna()
    n = len(sample)
    result["resolved"] = int(n)
    if n == 0:
        return result

    result["brier"] = round(float(((sample["p"] - sample["y"]) ** 2).mean()), 4)
    result["mean_predicted"] = round(float(sample["p"].mean() * 100), 2)
    result["observed"] = round(float(sample["y"].mean() * 100), 2)

    if n >= 500:
        result["status"] = "MATURE AUDIT"
        result["note"] = "Large historical sample. EV remains an estimate, not a guarantee."
    elif n >= 150:
        result["status"] = "DEVELOPING"
        result["note"] = "Useful research sample, but continue validating by odds range and closing price."
    else:
        result["status"] = "RESEARCH-ONLY"
        result["note"] = "Small resolved sample. Treat EV and fair price as experimental."
    return result


def _market_value_label(edge_points: float | None, ev_pct: float | None) -> tuple[str, str]:
    if edge_points is None or ev_pct is None:
        return "UNVERIFIED", "neutral"
    if edge_points >= 4.0 and ev_pct >= 15.0:
        return "STRONG VALUE", "good"
    if edge_points >= 1.5 and ev_pct > 0:
        return "SLIGHT VALUE", "slight"
    if edge_points > -1.5:
        return "FAIR PRICE", "neutral"
    return "OVERPRICED", "bad"


def _format_american_odds(value) -> str:
    try:
        odds = int(float(value))
    except Exception:
        return "—"
    return f"+{odds}" if odds > 0 else str(odds)


def build_market_edge_table(board_df: pd.DataFrame, odds_df: pd.DataFrame) -> pd.DataFrame:
    if board_df is None or board_df.empty or odds_df is None or odds_df.empty:
        return pd.DataFrame()

    board = board_df.copy()
    board["_player_key"] = board["Player"].astype(str).map(normalize_name)
    board["_team_key"] = board["Team"].astype(str).str.strip().str.upper()
    board["_game_key"] = board["Game"].astype(str).str.strip()

    odds = _coerce_market_odds_frame(odds_df)
    odds = odds[odds["date"].astype(str).eq(today_str())].copy()
    if odds.empty:
        return pd.DataFrame()
    odds["_player_key"] = odds["player"].map(normalize_name)
    odds["_team_key"] = odds["team"].str.strip().str.upper()
    odds["_game_key"] = odds["game"].str.strip()
    odds = odds.sort_values("captured_at", ascending=False)

    rows = []
    for _, market in odds.iterrows():
        matches = board[
            board["_player_key"].eq(market["_player_key"])
            & board["_team_key"].eq(market["_team_key"])
        ].copy()
        if market["_game_key"]:
            exact_game = matches[matches["_game_key"].eq(market["_game_key"])]
            if not exact_game.empty:
                matches = exact_game
        if matches.empty:
            continue

        player_row = matches.iloc[0]
        bf_p = _bf_raw_hr_probability(player_row)
        implied = american_odds_to_implied_probability(market["current_odds"])
        opening_implied = american_odds_to_implied_probability(market["opening_odds"])
        edge_points = ((bf_p - implied) * 100.0) if bf_p is not None and implied is not None else None
        ev = expected_value_per_dollar(bf_p, market["current_odds"])
        ev_pct = ev * 100.0 if ev is not None else None
        fair_odds = probability_to_american_odds(bf_p) if bf_p is not None else None

        current_value = safe_float(market["current_odds"], 0.0)
        opening_value = safe_float(market["opening_odds"], 0.0)
        previous_value = safe_float(market.get("previous_odds"), 0.0)
        line_move = current_value - opening_value if current_value and opening_value else None
        recent_move = current_value - previous_value if current_value and previous_value else None
        if line_move is None or abs(line_move) < 0.5:
            movement = "UNCHANGED"
        elif line_move < 0:
            movement = "SHORTENING"
        else:
            movement = "DRIFTING"
        label, label_class = _market_value_label(edge_points, ev_pct)

        rows.append({
            "Player": player_row.get("Player", market["player"]),
            "Team": player_row.get("Team", market["team"]),
            "Game": player_row.get("Game", market["game"]),
            "Sportsbook": market["sportsbook"],
            "Opening Odds": opening_value if opening_value else pd.NA,
            "Previous Odds": previous_value if previous_value else pd.NA,
            "Current Odds": current_value if current_value else pd.NA,
            "Line Move": line_move,
            "Recent Move": recent_move,
            "Movement": movement,
            "BF HR Estimate %": round(bf_p * 100.0, 2) if bf_p is not None else pd.NA,
            "Book Implied %": round(implied * 100.0, 2) if implied is not None else pd.NA,
            "Probability Edge": round(edge_points, 2) if edge_points is not None else pd.NA,
            "BF Fair Odds": fair_odds if fair_odds is not None else pd.NA,
            "EV per $10": round(ev * 10.0, 2) if ev is not None else pd.NA,
            "EV %": round(ev_pct, 2) if ev_pct is not None else pd.NA,
            "Price Status": label,
            "_status_class": label_class,
            "First Seen": market.get("first_seen_at", ""),
            "Captured": market["captured_at"],
            "Book Updated": market.get("book_last_update", ""),
        })

    if not rows:
        return pd.DataFrame()
    result = pd.DataFrame(rows)
    return result.sort_values(
        ["EV %", "Probability Edge", "BF HR Estimate %"],
        ascending=[False, False, False],
        na_position="last",
    ).reset_index(drop=True)


def render_market_edge_tab(locked_board: pd.DataFrame, tracker_df: pd.DataFrame):
    """Automatic multi-book sportsbook-price comparison; prediction logic stays frozen."""
    st.subheader("Market Edge")
    st.caption(
        "Live batter home-run prices from FanDuel, DraftKings, bet365, Caesars, and BetMGM. "
        "Odds never rerank players, change lineups, or alter BF Data predictions."
    )

    api_key = _get_odds_api_key()
    refresh_meta = st.session_state.get(
        "bf_market_refresh_meta",
        {"status": "NO_KEY", "saved": 0},
    )

    if not api_key:
        st.warning(
            "Live sportsbook prices cannot appear until the provider key is connected. "
            "The player cards are already wired for odds; after the one-time Secrets setup, "
            "each card will automatically show its best book, price, movement, and BF edge."
        )
        with st.expander("One-time Streamlit Secrets setup", expanded=True):
            st.code('THE_ODDS_API_KEY = "paste_your_key_here"', language="toml")
            st.caption(
                "Streamlit Community Cloud → Manage app → Settings → Secrets. "
                "After saving, reboot the app once."
            )
    else:
        q1, q2, q3 = st.columns(3)
        q1.metric("Live prices matched", safe_int(refresh_meta.get("saved"), 0))
        q2.metric("API events checked", safe_int(refresh_meta.get("events"), 0))
        q3.metric(
            "API requests remaining",
            str(refresh_meta.get("remaining") or "—"),
        )

    audit = bf_hr_probability_calibration_audit(tracker_df)
    status_class = (
        "good" if audit["status"] == "MATURE AUDIT"
        else "slight" if audit["status"] == "DEVELOPING"
        else "neutral"
    )
    brier_text = f"{audit['brier']:.4f}" if audit["brier"] is not None else "—"
    st.markdown(
        '<div class="bf-market-audit">'
        f'<div><small>EV CALIBRATION STATUS</small><strong class="{status_class}">{escape(audit["status"])}</strong>'
        f'<span>{escape(audit["note"])}</span></div>'
        f'<div><small>RESOLVED PICKS</small><strong>{audit["resolved"]}</strong></div>'
        f'<div><small>BRIER SCORE</small><strong>{brier_text}</strong></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    market = build_market_edge_table(locked_board, _automatic_market_rows_only())
    st.markdown("### Live sportsbook comparison")
    if market.empty:
        st.info(
            "No live HR prices currently match visible BF Data players. "
            "Sportsbooks may not have posted every game yet, or the API key still needs setup."
        )
        return

    # Best price and book across the requested sportsbooks.
    market["Current Odds Num"] = pd.to_numeric(market["Current Odds"], errors="coerce")
    best_rows = (
        market.sort_values(
            ["Player", "Current Odds Num"],
            ascending=[True, False],
            na_position="last",
        )
        .drop_duplicates(subset=["Player"], keep="first")
        .sort_values(
            ["EV %", "Probability Edge", "BF HR Estimate %"],
            ascending=[False, False, False],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    cards = ['<div class="bf-market-grid">']
    for _, row in best_rows.head(12).iterrows():
        player_name = str(row.get("Player", "—"))
        player_books = market[market["Player"].astype(str).eq(player_name)].copy()
        player_books = player_books.sort_values("Current Odds Num", ascending=False)

        status_class = str(row.get("_status_class", "neutral"))
        opening = _format_american_odds(row.get("Opening Odds"))
        current = _format_american_odds(row.get("Current Odds"))
        fair = _format_american_odds(row.get("BF Fair Odds"))
        edge = safe_float(row.get("Probability Edge"), 0.0)
        ev10 = safe_float(row.get("EV per $10"), 0.0)
        movement = str(row.get("Movement", "UNCHANGED"))
        move_class = (
            "steam" if movement == "SHORTENING"
            else "drift" if movement == "DRIFTING"
            else "flat"
        )
        move_text = (
            "▼ SHORTENING" if movement == "SHORTENING"
            else "▲ DRIFTING" if movement == "DRIFTING"
            else "— UNCHANGED"
        )

        book_cells = []
        for _, book_row in player_books.head(5).iterrows():
            book_cells.append(
                '<div>'
                f'<small>{escape(str(book_row.get("Sportsbook", "")))}</small>'
                f'<strong>{_format_american_odds(book_row.get("Current Odds"))}</strong>'
                '</div>'
            )

        cards.append(
            '<div class="bf-market-card">'
            f'<div class="bf-market-head"><div><small>BEST PRICE · {escape(str(row.get("Sportsbook","")))}</small>'
            f'<strong>{escape(player_name)}</strong>'
            f'<span>{escape(str(row.get("Team","")))} · {escape(str(row.get("Game","")))}</span></div>'
            f'<b class="{status_class}">{escape(str(row.get("Price Status","UNVERIFIED")))}</b></div>'
            f'<div class="bf-market-move {move_class}">{move_text} · FIRST SEEN {opening} → NOW {current}</div>'
            '<div class="bf-market-books">' + "".join(book_cells) + '</div>'
            '<div class="bf-market-stats">'
            f'<div><small>BF EST.</small><strong>{safe_float(row.get("BF HR Estimate %"),0):.1f}%</strong></div>'
            f'<div><small>BOOK IMPLIED</small><strong>{safe_float(row.get("Book Implied %"),0):.1f}%</strong></div>'
            f'<div><small>FAIR PRICE</small><strong>{fair}</strong></div>'
            f'<div><small>EDGE</small><strong>{edge:+.1f} pts</strong></div>'
            f'<div><small>BEST ODDS</small><strong>{current}</strong></div>'
            f'<div><small>BEST BOOK</small><strong>{escape(str(row.get("Sportsbook","—")))}</strong></div>'
            '</div>'
            f'<div class="bf-market-ev"><span>Research EV per $10 at best price</span><strong>{ev10:+.2f}</strong></div>'
            '</div>'
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)

    display_cols = [
        "Player", "Team", "Sportsbook", "Opening Odds", "Previous Odds",
        "Current Odds", "Movement", "Line Move", "BF HR Estimate %",
        "Book Implied %", "Probability Edge", "BF Fair Odds",
        "EV per $10", "EV %", "Price Status", "First Seen",
        "Captured", "Book Updated",
    ]
    with st.expander("All books and all matched BF Data players", expanded=False):
        st.dataframe(
            market[display_cols],
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("How price movement is measured", expanded=False):
        st.markdown(
            """
            **First Seen** is the first real price BF Data captured from the provider
            for that player and sportsbook today. **Current** is the latest real price.

            - **Shortening:** the positive American price became smaller, such as +600 → +400.
              The market is pricing the player as more likely, but the wager is now more expensive.
            - **Drifting:** the price became larger, such as +400 → +550.
              The market is pricing the player as less likely, while the payout improved.
            - **Unchanged:** no meaningful movement since BF Data first captured the price.

            Official historical market-opening snapshots require a provider plan that includes
            historical player-prop data. BF Data never labels its first observation as the
            sportsbook's official opening line.
            """
        )



def _automatic_market_rows_only() -> pd.DataFrame:
    """Return today's provider-fed rows; old manual entries never masquerade as live."""
    odds = load_market_odds()
    if odds is None or odds.empty:
        return pd.DataFrame(columns=_market_odds_columns())
    work = odds[odds["date"].astype(str).eq(today_str())].copy()
    note = work["source_note"].fillna("").astype(str).str.lower()
    return work[note.str.contains("automatic live batter hr odds", regex=False)].copy()


def player_market_card_context(row: pd.Series) -> dict:
    """Best real price and movement for one visible BF Data player."""
    player = normalize_name(str(row.get("Player", "") or ""))
    if not player:
        return {"available": False, "configured": bool(_get_odds_api_key())}

    odds = _automatic_market_rows_only()
    if odds.empty:
        return {"available": False, "configured": bool(_get_odds_api_key())}

    matched = odds[odds["player"].astype(str).map(normalize_name).eq(player)].copy()
    if matched.empty:
        return {"available": False, "configured": bool(_get_odds_api_key())}

    matched["_current"] = pd.to_numeric(matched["current_odds"], errors="coerce")
    matched["_opening"] = pd.to_numeric(matched["opening_odds"], errors="coerce")
    matched = matched[matched["_current"].notna()].copy()
    if matched.empty:
        return {"available": False, "configured": bool(_get_odds_api_key())}

    best = matched.sort_values("_current", ascending=False).iloc[0]
    current = safe_int(best.get("_current"), 0)
    opening = safe_int(best.get("_opening"), 0)
    move = current - opening if current and opening else 0

    if move < 0:
        movement = "SHORTENING"
        move_class = "steam"
        move_text = f"▼ {abs(move):.0f}"
    elif move > 0:
        movement = "DRIFTING"
        move_class = "drift"
        move_text = f"▲ {abs(move):.0f}"
    else:
        movement = "UNCHANGED"
        move_class = "flat"
        move_text = "— FLAT"

    bf_probability = safe_float(row.get("HR Probability %"), 0.0)
    implied = american_odds_to_implied_probability(current)
    edge = (
        bf_probability - implied * 100.0
        if implied is not None and bf_probability > 0
        else None
    )

    return {
        "available": True,
        "configured": True,
        "sportsbook": str(best.get("sportsbook", "—") or "—"),
        "current": current,
        "opening": opening,
        "movement": movement,
        "move_class": move_class,
        "move_text": move_text,
        "edge": edge,
    }


def player_market_strip_html(row: pd.Series, early: bool = False) -> str:
    if early:
        return ""

    context = player_market_card_context(row)
    if context.get("available"):
        price = _format_american_odds(context.get("current"))
        edge = context.get("edge")
        edge_text = f"BF EDGE {edge:+.1f} PTS" if edge is not None else "LIVE PRICE"
        return (
            '<div class="bf-card-market">'
            '<span class="bf-card-market-label">MARKET</span>'
            f'<span class="bf-card-market-book">BEST · {escape(context["sportsbook"])}</span>'
            f'<strong class="bf-card-market-price">{price}</strong>'
            f'<span class="bf-card-market-move {context["move_class"]}">{escape(context["move_text"])}</span>'
            f'<span class="bf-card-market-edge">{escape(edge_text)}</span>'
            '</div>'
        )

    status = (
        "Connect THE_ODDS_API_KEY in Streamlit Secrets"
        if not context.get("configured")
        else "No posted HR price matched this player"
    )
    return (
        '<div class="bf-card-market no-data">'
        '<span class="bf-card-market-label">MARKET</span>'
        f'<span class="bf-card-market-book">{escape(status)}</span>'
        '</div>'
    )



def bf_conviction_from_row(row: pd.Series) -> dict:
    """Interpret existing BF Data outputs without changing any prediction.

    This is a presentation-only read of scores already produced by the engine.
    It never feeds back into ranking, eligibility, tracking, locks, or combos.
    """
    wager = safe_float(
        row.get("Wager Priority", row.get("Matchup Advantage Score")),
        0.0,
    )
    confidence = safe_float(
        row.get("Slate Confidence", row.get("BF Confidence")),
        0.0,
    )
    if confidence <= 0:
        confidence = _bf_v2_confidence(row, early=False)

    quality = safe_float(row.get("Prediction Quality Score"), 0.0)
    attack = safe_float(
        row.get(
            "HR Attackability %",
            _attackability_pct(row.get("HR Attackability Score", 0)),
        ),
        0.0,
    )
    matchup = safe_float(
        row.get("Display Matchup Fit", row.get("Matchup Advantage Score")),
        0.0,
    )
    form = safe_float(row.get("Display Recent Form"), confidence)
    grade = str(row.get("Prediction Quality Grade", "")).strip().upper()
    eligible = bool(row.get("HR Eligible", True))

    # Existing outputs only. No new baseball inputs or model weights.
    available = [v for v in [wager, confidence, quality, attack, matchup, form] if v > 0]
    interpreted = sum(available) / len(available) if available else 0.0

    # Grade is used only as a display guardrail.
    if grade in {"A+", "A"}:
        interpreted += 3.0
    elif grade in {"B-", "C+", "C", "D", "F"}:
        interpreted -= 5.0
    if not eligible:
        interpreted = min(interpreted, 38.0)

    interpreted = clip(interpreted, 0, 99)

    if interpreted >= 90 and attack >= 70:
        return {
            "stars": 5,
            "label": "BF HAMMER",
            "short": "HAMMER",
            "class": "hammer",
            "score": round(interpreted, 1),
            "note": "Highest-conviction interpretation of the existing BF model.",
        }
    if interpreted >= 82:
        return {
            "stars": 4,
            "label": "STRONG PLAY",
            "short": "STRONG",
            "class": "strong",
            "score": round(interpreted, 1),
            "note": "Strong model agreement with usable separation.",
        }
    if interpreted >= 72:
        return {
            "stars": 3,
            "label": "WORTH CONSIDERING",
            "short": "CONSIDER",
            "class": "consider",
            "score": round(interpreted, 1),
            "note": "Qualified look, but not a must-play.",
        }
    if interpreted >= 60:
        return {
            "stars": 2,
            "label": "PAIR ONLY",
            "short": "PAIR ONLY",
            "class": "pair",
            "score": round(interpreted, 1),
            "note": "Better used as a supporting leg than a primary decision.",
        }
    return {
        "stars": 1,
        "label": "PASS",
        "short": "PASS",
        "class": "pass",
        "score": round(interpreted, 1),
        "note": "Existing BF signals do not show enough agreement.",
    }


def bf_slate_decision_read(board_df: pd.DataFrame) -> dict:
    """Describe slate clarity using separation among existing ranked outputs."""
    if board_df is None or board_df.empty:
        return {
            "label": "NO CARD",
            "class": "hard",
            "score": 0,
            "note": "No qualified BF Data card is available.",
        }

    work = board_df.copy().head(12)
    conviction_scores = [
        bf_conviction_from_row(row)["score"]
        for _, row in work.iterrows()
    ]
    conviction_scores = sorted(conviction_scores, reverse=True)

    if not conviction_scores:
        return {
            "label": "NO CARD",
            "class": "hard",
            "score": 0,
            "note": "No qualified BF Data card is available.",
        }

    top = conviction_scores[0]
    fifth = conviction_scores[min(4, len(conviction_scores) - 1)]
    spread = top - fifth
    elite_count = sum(score >= 82 for score in conviction_scores)

    # This is a slate-read label only. It does not alter bets or projections.
    clarity = clip(48 + spread * 2.2 + min(elite_count, 4) * 5, 0, 99)

    if clarity >= 78 and elite_count >= 2:
        return {
            "label": "EASY / CLEAR",
            "class": "easy",
            "score": round(clarity),
            "note": "The existing rankings show useful separation. Keep the card small and trust the order.",
        }
    if clarity >= 60:
        return {
            "label": "MEDIUM",
            "class": "medium",
            "score": round(clarity),
            "note": "Several hitters grade similarly. Use fewer combinations and avoid unnecessary swaps.",
        }
    return {
        "label": "HARD / FLAT",
        "class": "hard",
        "score": round(clarity),
        "note": "The slate is tightly grouped. Reduce exposure rather than forcing extra selections.",
    }


def _bf_card_reason_summary(row: pd.Series, max_items: int = 4) -> list[str]:
    reasons = _bf_v2_reason_items(row, early=False)
    cleaned = []
    for reason in reasons:
        value = str(reason).strip()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned[:max_items]


def render_today_card(
    locked_board: pd.DataFrame,
    combo_board_local: pd.DataFrame,
):
    """Render a decision layer over the frozen BF engine outputs."""
    st.subheader("Today's Card")
    st.caption(
        "Decision-support only. This page interprets the existing BF rankings and "
        "combos without recalculating, reranking, replacing, or tracking anything."
    )

    ranked = get_top12_hybrid(locked_board.copy())
    if ranked is None or ranked.empty:
        st.info("No qualified BF Data selections are available.")
        return

    ranked = ranked.head(12).copy().reset_index(drop=True)
    ranked["_conviction"] = ranked.apply(
        lambda row: bf_conviction_from_row(row)["score"],
        axis=1,
    )
    ranked["_conviction_stars"] = ranked.apply(
        lambda row: bf_conviction_from_row(row)["stars"],
        axis=1,
    )

    slate_read = bf_slate_decision_read(ranked)
    trust_score = safe_float(slate_read.get("score"), 0.0)
    top_row = ranked.iloc[0]
    top_conv = bf_conviction_from_row(top_row)
    top_reasons = _bf_card_reason_summary(top_row)

    st.markdown(
        f"""
        <div class="bf-decision-hero {slate_read['class']}">
          <div>
            <small>DECISION DIFFICULTY</small>
            <strong>{escape(slate_read['label'])}</strong>
            <span>{escape(slate_read['note'])}</span>
          </div>
          <div class="bf-trust-ring">
            <small>TRUST METER</small>
            <strong>{trust_score:.0f}</strong>
            <span>/100</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Straight-Play Shortlist")
    shortlist = ranked[
        ranked["_conviction_stars"].ge(4)
    ].copy().head(3)
    if shortlist.empty:
        shortlist = ranked.head(2).copy()

    cards = []
    for idx, (_, row) in enumerate(shortlist.iterrows(), start=1):
        conviction = bf_conviction_from_row(row)
        reasons = _bf_card_reason_summary(row, 3)
        reason_text = " · ".join(reasons) if reasons else "Existing BF scores support this position."
        cards.append(
            f"""
            <div class="bf-today-pick {conviction['class']}">
              <div class="bf-today-rank">#{idx}</div>
              <div class="bf-today-main">
                <small>{'★' * conviction['stars']}{'☆' * (5-conviction['stars'])} · {escape(conviction['label'])}</small>
                <strong>{escape(str(row.get('Player','—')))}</strong>
                <span>{escape(str(row.get('Team','')))} · {escape(str(row.get('Game','')))} · vs {escape(str(row.get('Pitcher','—')))}</span>
                <p>{escape(reason_text)}</p>
              </div>
              <div class="bf-today-score">
                <small>CONVICTION</small>
                <strong>{conviction['score']:.0f}</strong>
              </div>
            </div>
            """
        )
    st.markdown("".join(cards), unsafe_allow_html=True)

    st.markdown("### Why BF's #1 Is #1")
    reason_chips = "".join(
        f'<span>{escape(reason)}</span>' for reason in top_reasons
    )
    st.markdown(
        f"""
        <div class="bf-why-one">
          <div>
            <small>MODEL LEADER</small>
            <strong>{escape(str(top_row.get('Player','—')))}</strong>
            <p>{escape(str(top_row.get('Team','')))} · vs {escape(str(top_row.get('Pitcher','—')))}</p>
          </div>
          <div class="bf-why-chips">{reason_chips}</div>
          <div class="bf-why-score">
            <small>{escape(top_conv['label'])}</small>
            <strong>{top_conv['score']:.0f}/100</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Existing Combo Recommendations")
    if combo_board_local is None or combo_board_local.empty:
        st.caption("No existing BF combo currently clears the engine requirements.")
    else:
        combos = combo_board_local.copy()
        combos["_legs"] = (
            combos["Combo Type"].astype(str).str.extract(r"(\d+)")[0]
            .pipe(pd.to_numeric, errors="coerce").fillna(99)
        )
        for col in ["Weakest Leg HR %", "Weakest Leg Quality", "Combined Score"]:
            combos[col] = pd.to_numeric(combos.get(col), errors="coerce").fillna(0.0)
        combos["_floor"] = (
            combos["Weakest Leg HR %"] * .55
            + combos["Weakest Leg Quality"] * .45
        )
        two = combos[combos["_legs"].eq(2)].copy()
        practical_pool = two if not two.empty else combos
        practical = practical_pool.sort_values(
            ["_floor", "Combined Score"], ascending=[False, False]
        ).iloc[0]
        upside = combos.sort_values(
            ["Combined Score", "Weakest Leg Quality"], ascending=[False, False]
        ).iloc[0]
        longshot_pool = combos[combos["_legs"].ge(3)].copy()
        longshot = (
            longshot_pool.sort_values(
                ["_floor", "Combined Score"], ascending=[False, False]
            ).iloc[0]
            if not longshot_pool.empty else upside
        )

        combo_cards = [
            ("MOST PRACTICAL", practical, "Best existing two-leg/floor combination."),
            ("HIGHEST UPSIDE", upside, "Highest existing combined score."),
            ("SMALL-STAKES LONGSHOT", longshot, "Higher variance; keep exposure small."),
        ]
        # Keep this HTML continuous and left-aligned. Indented multiline HTML
        # can be interpreted by Streamlit Markdown as a code block after the
        # first card, which exposed the raw <div> tags on Today's Card.
        html = ['<div class="bf-today-combos">']
        for label, row, note in combo_cards:
            html.append(
                '<div>'
                f'<small>{escape(label)}</small>'
                f'<strong>{escape(str(row.get("Combo Label", "—")))}</strong>'
                f'<span>{escape(note)} Weakest leg '
                f'{safe_float(row.get("Weakest Leg HR %"), 0):.0f}%.</span>'
                '</div>'
            )
        html.append("</div>")
        st.markdown("".join(html), unsafe_allow_html=True)

    with st.expander("How to use Today's Card", expanded=False):
        st.markdown(
            """
            **The anti-overthinking rule:** start with the straight-play shortlist, use
            no more than one practical two-leg, and treat every 3–5 leg combination
            as a small-stakes longshot. A large slate does not require a large card.

            Conviction labels are interpretations of scores the app already calculated.
            They do not change predictions, board order, combo generation, tracking,
            lineup handling, or historical records.
            """
        )


def _bf_v2_card_html(row: pd.Series, rank, early: bool = False) -> str:
    player = _display_value(row.get("Player"))
    team = _display_value(row.get("Team"))
    game = _display_value(row.get("Game"))
    pitcher = _display_value(row.get("Opponent Pitcher" if early else "Pitcher"))

    early_score = safe_float(row.get("Early BF Score"), 0.0)
    grade = str(row.get("Prediction Quality Grade", _letter_grade(early_score / 3.0) if early else "—"))
    quality = safe_float(row.get("Prediction Quality Score"), clip(early_score / 3.0, 0, 99) if early else 0.0)
    edge = safe_float(row.get("Matchup Advantage Score"), clip(early_score / 3.1, 0, 99) if early else 0.0)
    pitch_fit = safe_float(row.get("Pitch Matchup Score"), safe_float(row.get("Pitcher HR/9"), 0.0) * 35 + 35 if early else 0.0)
    pitch_fit = clip(pitch_fit if early else pitch_fit * 10 + 40, 0, 99)

    role_text, role_class = _bf_v2_role(rank, quality, grade, early=early)
    confidence = _bf_v2_confidence(row, early=early)
    conviction = (
        {"stars": 0, "short": "EARLY", "class": "consider", "score": confidence}
        if early else bf_conviction_from_row(row)
    )
    verdict_label, verdict_note, verdict_color = (
        ("EARLY RESEARCH", "Probable-pitcher and expected-lineup research only.", "#ffd166")
        if early else _bf_active_verdict(row)
    )
    badges = _bf_v2_badges(row, early=early)
    reasons = _bf_v2_reason_items(row, early=early)

    moon = safe_float(row.get("Moonshot Score"), clip(safe_float(row.get("Barrel%"), 0) * 3.2 + safe_float(row.get("HardHit%"), 0) * .65, 0, 99))
    two_hr = safe_float(row.get("2 HR Score"), clip(moon * .58 + safe_int(row.get("Recent HR"), 0) * 5, 0, 99))
    nuke = safe_float(row.get("Nuke Score"), clip((quality + moon + edge) / 3, 0, 99))
    stack = safe_float(row.get("Stack Score"), clip(edge * .55 + pitch_fit * .45, 0, 99))
    actual_hr = safe_int(row.get("Actual HR Today"), 0)
    hr_badge_text, hr_badge_class, _ = _live_hr_display(actual_hr, early=early)
    hit_badge = (
        f'<span class="bf-live-hr-badge {hr_badge_class}">'
        f'{escape(hr_badge_text)}</span>'
    )
    data_level = str(row.get("Data Level", "")).strip()
    meta_extra = f" · {escape(data_level)}" if early and data_level else ""
    card_class = "early" if early else role_class
    badge_html = "".join(f"<span>{escape(str(x))}</span>" for x in badges)
    compact_badge_parts = []
    for badge in badges:
        badge_text = str(badge)
        badge_class = "good"
        if "CARRY" in badge_text or "WEATHER" in badge_text:
            badge_class = "weather"
        elif "HOT" in badge_text or "BARREL GOD" in badge_text:
            badge_class = "hot"
        compact_badge_parts.append(
            f'<span class="bf-scan-badge {badge_class}">{escape(badge_text)}</span>'
        )
    compact_badge_html = "".join(compact_badge_parts)
    reason_html = " · ".join(escape(str(x)) for x in reasons)
    attack_pct = safe_float(row.get("HR Attackability %", _attackability_pct(row.get("HR Attackability Score", 0))), 0.0)
    attack_label = "STRONG HR ATTACK" if attack_pct >= 72 else ("MIXED / ATTACKABLE" if attack_pct >= 48 else "POOR HR TARGET")
    attack_class = "bf-fill-green" if attack_pct >= 72 else ("bf-fill-yellow" if attack_pct >= 48 else "bf-fill-red")
    attack_color = "#35d07f" if attack_pct >= 72 else ("#ffd166" if attack_pct >= 48 else "#ff6666")

    green_flag = reasons[0] if reasons else "Blended BF matchup edge"
    bat_power = safe_float(row.get("Display Bat Power", quality), quality)
    matchup_display = safe_float(row.get("Display Matchup Fit", pitch_fit), pitch_fit)
    pitcher_leak = safe_float(row.get("Display Pitcher Leak", attack_pct), attack_pct)
    recent_form = safe_float(row.get("Display Recent Form", confidence), confidence)
    wager_priority = safe_float(row.get("Wager Priority", edge), edge)
    slate_rank = safe_int(row.get("Display Slate Rank", rank), safe_int(rank, 0))
    team_rank = safe_int(row.get("Display Team Rank", 1), 1)
    game_rank = safe_int(row.get("Display Game Rank", 1), 1)
    pair_role = str(row.get("Pair Role", role_text))
    best_pair = str(row.get("Best Pair With", "—"))
    pair_score = safe_float(row.get("Pair Score", 0.0), 0.0)
    gb_value = safe_float(row.get("GroundBall%"), 0.0)
    pitch_hr9_value = safe_float(
        row.get("Pitcher_HR9_Last7", row.get("Pitcher HR/9")),
        0.0,
    )
    if gb_value >= 50:
        red_flag = f"Ground-ball caution ({gb_value:.1f}%)"
    elif pitch_fit < 55:
        red_flag = "Pitch-fit edge is limited"
    elif pitch_hr9_value < 0.90:
        red_flag = "Opposing pitcher suppresses HR damage"
    else:
        red_flag = "No major red flag"

    market_strip_html = player_market_strip_html(row, early=early)

    if not early:
        return f"""
<div class="bf-scan-card {card_class}">
  <div class="bf-scan-top">
    <div>
      <div class="bf-scan-name">#{escape(str(rank))} {escape(player)}{hit_badge}</div>
      <div class="bf-scan-matchup">{escape(team)} · {escape(game)} · vs {escape(pitcher)}</div>
      <div class="bf-scan-roleline">
        <span class="bf-scan-role {role_class}">{escape(role_text)}</span>
        <span class="bf-scan-grade">{escape(grade)}</span>
        <span class="bf-scan-confidence">CONF {confidence:.0f}%</span>
        <span class="bf-conviction-chip {conviction['class']}">{'★' * conviction['stars']} {escape(conviction['short'])}</span>
        <span class="bf-scan-rank">SLATE RANK #{slate_rank} · TEAM RANK #{team_rank} · GAME RANK #{game_rank}</span>
      </div>
      <div class="bf-scan-badges">{compact_badge_html}</div>
      {market_strip_html}
    </div>
    <div class="bf-scan-actions">
      <div class="bf-scan-action"><small>WAGER</small><strong>{wager_priority:.1f}</strong></div>
      <div class="bf-scan-action"><small>GRADE</small><strong>{escape(grade)}</strong></div>
      <div class="bf-scan-action"><small>ATTACK</small><strong>{attack_pct:.0f}</strong></div>
    </div>
  </div>
  <div class="bf-scan-attack">
    <div class="bf-scan-attack-label" style="color:{attack_color}">{escape(attack_label)}</div>
    <div class="bf-scan-track"><div class="bf-scan-fill" style="width:{clip(attack_pct,0,100):.0f}%;background:{attack_color}"></div></div>
    <div class="bf-scan-attack-score" style="color:{attack_color}">{attack_pct:.0f}/100</div>
  </div>
  <div class="bf-scan-metrics">
    <div class="bf-scan-metric"><small>BAT POWER</small><strong>{bat_power:.0f}</strong></div>
    <div class="bf-scan-metric"><small>MATCHUP</small><strong>{matchup_display:.0f}</strong></div>
    <div class="bf-scan-metric"><small>PITCHER LEAK</small><strong>{pitcher_leak:.0f}</strong></div>
    <div class="bf-scan-metric"><small>FORM</small><strong>{recent_form:.0f}</strong></div>
  </div>
  <div class="bf-scan-why"><b>WHY BF LIKES HIM</b> · {reason_html}</div>
  <div class="bf-scan-bottom">
    <div class="bf-scan-pair"><b>🤝 {escape(pair_role)}</b> · Best pair: {escape(best_pair)}</div>
    <div class="bf-scan-pair-score">PAIR {pair_score:.0f}</div>
  </div>
</div>"""

    return f'''
<div class="bf-v2-card {card_class}">
  <div class="bf-v2-head">
    <div>
      <div class="bf-v2-name">#{escape(str(rank))} {escape(player)}{hit_badge}</div>
      <div class="bf-v2-role-row">
        <span class="bf-v2-role {role_class}">{escape(role_text)}</span>
        <span class="bf-v2-grade">{escape(grade)}</span>
        <span class="bf-v2-delta">CONF {confidence:.0f}{meta_extra}</span>
      </div>
      <div class="bf-v2-meta">{escape(team)} · {escape(game)} · vs {escape(pitcher)}</div>
      <div class="bf-v2-rankline">
        <span class="bf-v2-rankchip primary">SLATE #{slate_rank}</span>
        <span class="bf-v2-rankchip">TEAM #{team_rank}</span>
        <span class="bf-v2-rankchip">GAME #{game_rank}</span>
        <span class="bf-v2-rankchip">WAGER {wager_priority:.1f}</span>
      </div>
    </div>
    <div class="bf-v2-scores">
      <div class="bf-v2-score"><b>WAGER</b><span>{wager_priority:.1f}</span></div>
      <div class="bf-v2-score"><b>GRADE</b><span>{escape(grade)}</span></div>
      <div class="bf-v2-score"><b>ATTACK</b><span>{attack_pct:.0f}</span></div>
    </div>
  </div>
  <div class="bf-v2-badges">{badge_html}</div>
  <div class="bf-v2-attack-panel" style="border-color:{attack_color}">
    <div class="bf-v2-attack-head">
      <div>
        <div class="bf-v2-attack-kicker">BF HR ATTACK</div>
        <div class="bf-v2-attack-label" style="color:{attack_color}">{escape(attack_label)}</div>
      </div>
      <div class="bf-v2-attack-score" style="color:{attack_color}">{attack_pct:.0f}/100</div>
    </div>
    <div class="bf-v2-attack-track">
      <div class="bf-v2-attack-fill" style="width:{clip(attack_pct,0,100):.0f}%;background:{attack_color}"></div>
    </div>
    <div class="bf-v2-signal-grid">
      <div class="bf-v2-signal green"><b>BIGGEST GREEN FLAG</b>{escape(str(green_flag))}</div>
      <div class="bf-v2-signal red"><b>BIGGEST CAUTION</b>{escape(str(red_flag))}</div>
    </div>
  </div>
  <div class="bf-v2-verdict" style="border-color:{verdict_color}">
    <strong style="color:{verdict_color}">{escape(verdict_label)}</strong>
    <span>{escape(verdict_note)}</span>
  </div>
  <div class="bf-v2-compare">
    <div><small>BAT POWER</small><strong>{bat_power:.0f}</strong></div>
    <div><small>MATCHUP FIT</small><strong>{matchup_display:.0f}</strong></div>
    <div><small>PITCHER LEAK</small><strong>{pitcher_leak:.0f}</strong></div>
    <div><small>RECENT FORM</small><strong>{recent_form:.0f}</strong></div>
  </div>
  <div class="bf-v2-pair">
    <div><small>{escape(pair_role)}</small><strong>Best pair: {escape(best_pair)}</strong></div>
    <div class="bf-v2-pair-score">PAIR {pair_score:.0f}</div>
  </div>
  <div class="bf-v2-confidence">
    <div class="bf-v2-confidence-head"><span>BF CONFIDENCE</span><span>{confidence:.0f}%</span></div>
    <div class="bf-v2-confidence-track"><div class="bf-v2-confidence-fill" style="width:{confidence:.0f}%"></div></div>
  </div>
  <div class="bf-v2-why"><b>WHY HE'S RANKED HERE</b><br>{reason_html}</div>
</div>'''


def _render_bf_html(html_text: str):
    """Render generated BF HTML safely without exposing raw tags."""
    compact = re.sub(r"\s+", " ", str(html_text).strip())
    compact = re.sub(r">\s+<", "><", compact)
    st.markdown(compact, unsafe_allow_html=True)


def _early_decision_read(row: pd.Series) -> tuple[str, str, str]:
    """Separate hitter quality from matchup quality for early research."""
    early_score = safe_float(row.get("Early BF Score"), 0.0)
    barrel = safe_float(row.get("Barrel%"), 0.0)
    hard_hit = safe_float(row.get("HardHit%"), 0.0)
    gb = safe_float(row.get("GroundBall%"), 45.0)
    pitch_hr9 = safe_float(row.get("Pitcher HR/9"), 0.0)
    pitch_barrel = safe_float(row.get("Pitcher Barrel Allowed"), 0.0)
    pitch_hh = safe_float(row.get("Pitcher HardHit Allowed"), 0.0)

    hitter_quality = clip(
        early_score / 3.1
        + max(0.0, barrel - 10) * 0.7
        + max(0.0, hard_hit - 42) * 0.25
        - max(0.0, gb - 48) * 0.45,
        0, 99,
    )
    pitcher_attack = clip(
        pitch_hr9 * 24 + pitch_barrel * 2.0 + pitch_hh * 0.55 - 16,
        0, 99,
    )

    if hitter_quality >= 88 and pitcher_attack >= 55:
        return "EARLY PRIMARY TARGET", "Elite hitter profile with an attackable pitcher path.", "#35d07f"
    if hitter_quality >= 88 and pitcher_attack < 35:
        return "ELITE HITTER · MATCHUP CAUTION", "The hitter is elite, but the probable pitcher currently suppresses HR damage.", "#ffd166"
    if hitter_quality >= 78 and pitcher_attack >= 45:
        return "STRONG EARLY LOOK", "Good hitter quality and a playable pitcher matchup.", "#69a7ff"
    if gb >= 52:
        return "WATCHLIST ONLY", "Power exists, but the ground-ball profile lowers early confidence.", "#ff8c66"
    return "SECONDARY EARLY LOOK", "Useful research profile; wait for projected lineup and updated matchup data.", "#b6a0ff"


def render_early_scout_summary(preview_df: pd.DataFrame):
    if preview_df is None or preview_df.empty:
        return
    view = preview_df.copy().head(12)
    view["_conf"] = view.apply(lambda r: _bf_v2_confidence(r, early=True), axis=1)
    view["_pitch_attack"] = (
        pd.to_numeric(view.get("Pitcher HR/9"), errors="coerce").fillna(0) * 24
        + pd.to_numeric(view.get("Pitcher Barrel Allowed"), errors="coerce").fillna(0) * 2
        + pd.to_numeric(view.get("Pitcher HardHit Allowed"), errors="coerce").fillna(0) * .55
    )
    best = view.sort_values(["_conf", "Early BF Score"], ascending=False).iloc[0]
    best_matchup = view.sort_values(["_pitch_attack", "Early BF Score"], ascending=False).iloc[0]
    caution_pool = view.sort_values(["Early BF Score", "_pitch_attack"], ascending=[False, True])
    caution = caution_pool.iloc[0]

    html = f"""
    <div class="bf-scout-panel">
      <div class="bf-scout-title">BF AI SCOUT · EARLY SLATE READ</div>
      <div class="bf-scout-grid">
        <div><small>BEST EARLY TARGET</small><strong>{escape(str(best.get('Player','—')))}</strong><span>{best['_conf']:.0f}% early confidence</span></div>
        <div><small>BEST PITCHER PATH</small><strong>{escape(str(best_matchup.get('Player','—')))}</strong><span>vs {escape(str(best_matchup.get('Opponent Pitcher','—')))}</span></div>
        <div><small>BIGGEST CAUTION</small><strong>{escape(str(caution.get('Player','—')))}</strong><span>Strong hitter score, tougher pitcher path</span></div>
      </div>
      <div class="bf-scout-note">Research only · probable pitchers and expected hitters can change · no official tracking until the slate locks.</div>
    </div>
    """
    _render_bf_html(html)


def _early_matchup_card_html(row: pd.Series, rank) -> str:
    player = escape(_display_value(row.get("Player")))
    pitcher = escape(_display_value(row.get("Opponent Pitcher")))
    team = escape(_display_value(row.get("Team")))
    game = escape(_display_value(row.get("Game")))
    bats = escape(_display_value(row.get("Bats", "—")))
    confidence = _bf_v2_confidence(row, early=True)
    early_score = safe_float(row.get("Early BF Score"), 0.0)
    edge = clip(early_score / 3.1, 0, 99)
    grade = _letter_grade(edge)
    pitch_hr9 = safe_float(row.get("Pitcher HR/9"), 0.0)
    pitch_barrel = safe_float(row.get("Pitcher Barrel Allowed"), 0.0)
    pitch_hh = safe_float(row.get("Pitcher HardHit Allowed"), 0.0)
    pitch_fit = clip(35 + pitch_hr9 * 35 + pitch_barrel * 1.3 + max(0, pitch_hh - 36) * .7, 0, 99)

    barrel = safe_float(row.get("Barrel%"), 0.0)
    hard_hit = safe_float(row.get("HardHit%"), 0.0)
    air = safe_float(row.get("AIR%"), 0.0)
    gb = safe_float(row.get("GroundBall%"), 0.0)
    ev = safe_float(row.get("EV"), 0.0)
    xslg = safe_float(row.get("xSLG"), 0.0)
    recent_hr = safe_int(row.get("Recent HR"), 0)
    season_hr = safe_int(row.get("Season HR"), 0)

    attack_score = clip(
        pitch_hr9 * 22
        + pitch_barrel * 2.0
        + pitch_hh * .55
        - 18,
        0, 100,
    )
    decision_label, decision_note, decision_color = _early_decision_read(row)
    if attack_score >= 68:
        attack_label, attack_grade, attack_color = "STRONG HR ATTACK", "GRADE B+", "#35d07f"
    elif attack_score >= 48:
        attack_label, attack_grade, attack_color = "MIXED / ATTACKABLE", "GRADE B", "#ffd166"
    else:
        attack_label, attack_grade, attack_color = "CAUTION MATCHUP", "GRADE C", "#ff6666"

    reasons = _bf_v2_reason_items(row, early=True)
    reason_items = "".join(f"<li>{escape(x)}</li>" for x in reasons)

    return f'''
<div class="bf-match-card">
  <div class="bf-match-topline">
    <div class="bf-cell-head">
      <div class="bf-head-label">PLAYER</div>
      <div class="bf-head-main">#{escape(str(rank))} {player} <span class="bf-hand-badge">{bats}</span></div>
      <div class="bf-quick-sub">{team} · {game}</div>
    </div>
    <div class="bf-cell-head">
      <div class="bf-head-label">VS PITCHER</div>
      <div class="bf-head-main">{pitcher}</div>
      <div class="bf-quick-sub">PROBABLE · EARLY RESEARCH</div>
    </div>
    <div class="bf-score-box"><div class="lab">EDGE</div><div class="num bf-num-green">{edge:.1f}</div></div>
    <div class="bf-score-box"><div class="lab">GRADE</div><div class="num bf-num-green">{grade}</div></div>
    <div class="bf-score-box"><div class="lab">PITCH</div><div class="num bf-num-yellow">{pitch_fit:.0f}</div></div>
  </div>

  <div class="bf-card-body">
    <div class="bf-side-panel">
      <div class="bf-section-title">MATCHUP SCORES</div>
      <div class="bf-score-line"><span>BF Early Edge</span><span class="bf-pill-num bf-num-green">{edge:.1f}</span></div>
      <div class="bf-score-line"><span>Early Confidence</span><span class="bf-pill-num bf-num-yellow">{confidence:.0f}%</span></div>
      <div class="bf-score-line"><span>Pitch Fit</span><span class="bf-pill-num bf-num-yellow">{pitch_fit:.0f}</span></div>

      <div class="bf-section-title">OPPOSING PITCHER</div>
      <div class="bf-pitcher-stat"><span>Season/Blend HR/9</span><span class="bf-pill-num">{pitch_hr9:.2f}</span></div>
      <div class="bf-pitcher-stat"><span>Barrel Allowed</span><span class="bf-pill-num">{pitch_barrel:.1f}%</span></div>
      <div class="bf-pitcher-stat"><span>Hard Hit Allowed</span><span class="bf-pill-num">{pitch_hh:.1f}%</span></div>
    </div>

    <div>
      <div style="border:1px solid {decision_color};border-radius:10px;padding:8px 10px;margin-bottom:10px;background:rgba(255,255,255,.018)">
        <div style="font-size:.58rem;letter-spacing:.12em;font-weight:950;color:#8fa9d8">BF EARLY DECISION</div>
        <div style="font-size:.92rem;font-weight:950;color:{decision_color};margin-top:4px">{decision_label}</div>
        <div style="font-size:.68rem;color:#b9c3d2;margin-top:3px">{decision_note}</div>
      </div>
      <div class="bf-section-title">HITTER DAMAGE PROFILE</div>
      <div class="bf-bvp-grid">
        <div class="bf-bvp-cell"><div class="bf-bvp-label">EV</div><div class="bf-bvp-values bf-green-txt">{ev:.1f}</div></div>
        <div class="bf-bvp-cell"><div class="bf-bvp-label">BARREL</div><div class="bf-bvp-values bf-green-txt">{barrel:.1f}%</div></div>
        <div class="bf-bvp-cell"><div class="bf-bvp-label">HARD HIT</div><div class="bf-bvp-values bf-green-txt">{hard_hit:.1f}%</div></div>
        <div class="bf-bvp-cell"><div class="bf-bvp-label">AIR</div><div class="bf-bvp-values">{air:.1f}%</div></div>
        <div class="bf-bvp-cell"><div class="bf-bvp-label">GB</div><div class="bf-bvp-values">{gb:.1f}%</div></div>
        <div class="bf-bvp-cell"><div class="bf-bvp-label">xSLG</div><div class="bf-bvp-values">{xslg:.3f}</div></div>
        <div class="bf-bvp-cell"><div class="bf-bvp-label">SEASON HR</div><div class="bf-bvp-values">{season_hr}</div></div>
        <div class="bf-bvp-cell"><div class="bf-bvp-label">RECENT HR</div><div class="bf-bvp-values">{recent_hr}</div></div>
      </div>

      <div style="margin-top:12px;border:1px solid {attack_color};border-radius:12px;padding:10px;background:rgba(255,255,255,.018)">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:center">
          <div class="bf-section-title" style="margin:0">BF ATTACK READ</div>
          <span class="bf-chip">{attack_grade}</span>
        </div>
        <div style="font-size:1rem;font-weight:950;color:{attack_color};margin-top:8px">{attack_label}</div>
        <div class="bf-track" style="margin-top:7px"><div class="bf-fill" style="width:{attack_score:.0f}%;background:{attack_color}"></div></div>
        <div style="text-align:right;font-weight:900;font-size:.72rem;margin-top:3px">{attack_score:.0f}/100</div>
        <ul style="margin:7px 0 0 18px;padding:0;color:#b9c3d2;font-size:.72rem;line-height:1.45">{reason_items}</ul>
      </div>

      <div class="bf-bvp-title">EARLY RESEARCH STATUS</div>
      <div class="bf-card-foot" style="padding:0">
        Last-known/expected hitter pool · probable pitcher · not locked or tracked · lineup must still be confirmed.
      </div>
    </div>
  </div>
</div>'''


def render_early_watchlist_cards(preview_df: pd.DataFrame, max_cards: int = 6):
    if preview_df is None or preview_df.empty:
        st.caption("No early targets are available.")
        return

    view = preview_df.head(max_cards).reset_index(drop=True).copy()
    raw_scores = []

    for _, row in view.iterrows():
        early_score = safe_float(row.get("Early BF Score"), 0.0)
        barrel = safe_float(row.get("Barrel%"), 0.0)
        hard_hit = safe_float(row.get("HardHit%"), 0.0)
        xslg = safe_float(row.get("xSLG"), 0.0)
        pitch_hr9 = safe_float(row.get("Pitcher HR/9"), 0.0)
        pitch_barrel = safe_float(row.get("Pitcher Barrel Allowed"), 0.0)
        recent_hr = safe_int(row.get("Recent HR"), 0)
        gb = safe_float(row.get("GroundBall%"), 45.0)

        raw_scores.append(
            early_score * 0.18
            + barrel * 1.35
            + hard_hit * 0.28
            + xslg * 22
            + pitch_hr9 * 8
            + pitch_barrel * 0.55
            + recent_hr * 1.6
            - max(0.0, gb - 47) * 0.65
        )

    if raw_scores:
        lo, hi = min(raw_scores), max(raw_scores)
        spread = max(hi - lo, 1.0)
        for idx, raw in enumerate(raw_scores):
            # 48–84 keeps early confidence honest while clearly separating players.
            normalized = 48 + ((raw - lo) / spread) * 36
            view.at[idx, "Early Confidence Score"] = round(normalized, 1)

    render_early_scout_summary(view)

    for i, (_, row) in enumerate(view.iterrows()):
        rank = row.get("Slate Rank", i + 1)
        _render_bf_html(_bf_v2_card_html(row, rank, early=True))
        player = _display_value(row.get("Player"))
        pitcher = _display_value(row.get("Opponent Pitcher"))
        with st.expander(f"Full research — {player} vs {pitcher}", expanded=False):
            _render_bf_html(_early_matchup_card_html(row, rank))


def _bf_research_signal_strip_html(row: pd.Series) -> str:
    badges = _bf_v2_badges(row, early=False)
    reasons = _bf_v2_reason_items(row, early=False)
    signal_items = badges + reasons[:3]
    if not signal_items:
        signal_items = ["Blended BF matchup profile"]
    chips = "".join(
        f'<span class="signal">{escape(str(item))}</span>'
        for item in signal_items[:8]
    )
    return (
        '<div class="bf-research-signals">'
        '<div class="label">BF SIGNALS · WHY THIS PLAYER SURFACED</div>'
        f'{chips}'
        '<div class="bf-rank-help">'
        'Slate Rank = overall position across the full board · '
        'Team Rank = position among hitters on his team · '
        'Game Rank = position among hitters in this matchup.'
        '</div>'
        '</div>'
    )


def render_team_section_header(team: str, confirmed_count: int, pool_status: str):
    status = str(pool_status or "PROJECTED").upper()
    status_text = "OFFICIAL LINEUP" if status == "CONFIRMED" else status
    html = (
        '<div class="bf-team-header">'
        f'<strong>{escape(str(team))}</strong>'
        f'<span>{safe_int(confirmed_count, 0)}/9 CONFIRMED · {escape(status_text)}</span>'
        '</div>'
    )
    _render_bf_html(html)

def render_player_card(row: pd.Series, rank_override=None):
    rank = rank_override if rank_override is not None else row.get("Rank", "—")
    player = _display_value(row.get("Player"))
    pitcher = _display_value(row.get("Pitcher"))

    _render_bf_html(_bf_v2_card_html(row, rank, early=False))

    with st.expander(f"Full research — {player} vs {pitcher}", expanded=False):
        _render_bf_html(_bf_research_signal_strip_html(row))
        _render_bf_html(_match_card_html(row, rank_override=rank))

def render_card_grid(df: pd.DataFrame, max_cards: int = 24, columns: int = 3, title: str | None = None):
    if df is None or df.empty:
        st.caption("No cards to display.")
        return

    view = df.copy().head(max_cards).reset_index(drop=True)
    if not view.empty:
        view = add_comparative_card_context(view)
    if title:
        st.markdown(f"### {title}")

    st.markdown('<div class="bf-quick-list">', unsafe_allow_html=True)
    for i, (_, row) in enumerate(view.iterrows()):
        rank = row.get("Rank", i + 1)
        render_player_card(row, rank_override=rank)
    st.markdown('</div>', unsafe_allow_html=True)

def fetch_schedule_for_date(date_key: str) -> list[dict]:
    """Return the MLB schedule for any date without altering today's official board."""
    try:
        resp = requests.get(
            "https://statsapi.mlb.com/api/v1/schedule",
            params={"sportId": 1, "date": date_key, "hydrate": "probablePitcher"},
            timeout=18,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return []

    games = []
    for date_block in payload.get("dates", []) or []:
        for game in date_block.get("games", []) or []:
            away_block = ((game.get("teams") or {}).get("away") or {})
            home_block = ((game.get("teams") or {}).get("home") or {})
            away_team = (away_block.get("team") or {})
            home_team = (home_block.get("team") or {})
            if not away_team or not home_team:
                continue
            away_probable = away_block.get("probablePitcher") or {}
            home_probable = home_block.get("probablePitcher") or {}
            status = game.get("status") or {}
            games.append({
                "date": date_key,
                "game_pk": game.get("gamePk"),
                "game_key": f"{team_abbr(away_team.get('name', 'Away'))} @ {team_abbr(home_team.get('name', 'Home'))}",
                "away_team": away_team.get("name", "Away"),
                "home_team": home_team.get("name", "Home"),
                "away_team_id": away_team.get("id"),
                "home_team_id": home_team.get("id"),
                "away_pitcher": away_probable.get("fullName") or "Starter Pending",
                "home_pitcher": home_probable.get("fullName") or "Starter Pending",
                "away_pitcher_id": away_probable.get("id"),
                "home_pitcher_id": home_probable.get("id"),
                "venue": (game.get("venue") or {}).get("name", "TBD"),
                "game_time": game.get("gameDate", ""),
                "game_state": status.get("abstractGameState", "Preview"),
                "detailed_state": status.get("detailedState", "Scheduled"),
                "away_confirmed_count": 0,
                "home_confirmed_count": 0,
            })
    return sort_schedule_rows(games)


@st.cache_data(ttl=1800, max_entries=6)
def find_next_scheduled_slate(start_date_key: str, max_days: int = 14):
    """Find the next calendar date that actually has MLB games."""
    try:
        start_dt = datetime.strptime(start_date_key, "%Y-%m-%d").replace(tzinfo=ZoneInfo("America/New_York"))
    except Exception:
        start_dt = datetime.now(ZoneInfo("America/New_York"))
    for offset in range(1, max_days + 1):
        date_key = (start_dt + timedelta(days=offset)).strftime("%Y-%m-%d")
        slate = fetch_schedule_for_date(date_key)
        if slate:
            return date_key, slate
    return None, []


def _next_slate_hitter_score(player_id: int, player_name: str, stats_map: dict, savant_map: dict) -> dict | None:
    """Score an early-slate hitter even when recent game logs are unavailable.

    Priority:
      1. Season + recent game log + Savant
      2. Season + Savant
      3. Savant-only watchlist row

    This is research-only and never becomes an official tracked prediction.
    """
    data = stats_map.get(player_id, {}) or {}
    season = data.get("season", {}) or {}
    metrics = compute_hitter_live_metrics_from_map(player_id, stats_map, use_true_bbe=False)

    season_hr = safe_int(season.get("homeRuns", 0))
    season_ab = safe_int(season.get("atBats", 0))
    season_hits = safe_int(season.get("hits", 0))
    season_doubles = safe_int(season.get("doubles", 0))
    season_triples = safe_int(season.get("triples", 0))
    season_slg = safe_float(season.get("sluggingPercentage", 0.0), 0.0)
    season_avg = safe_float(season.get("avg", 0.0), 0.0)
    if not season_avg and season_ab:
        season_avg = season_hits / season_ab
    if not season_slg and season_ab:
        total_bases = (
            max(0, season_hits - season_doubles - season_triples - season_hr)
            + season_doubles * 2 + season_triples * 3 + season_hr * 4
        )
        season_slg = total_bases / season_ab
    season_iso = max(0.0, season_slg - season_avg)

    sav = savant_map.get(normalize_name(player_name), {}) or {}

    # Do not invent values. Use only available season/Savant values and clearly label confidence.
    fallback_ev = 0.0
    fallback_hh = 0.0
    fallback_brl = 0.0
    fallback_gb = 45.0
    fallback_air = 55.0
    recent_hr = 0
    recent_xbh = 0
    recent_iso = 0.0

    if metrics is not None:
        fallback_ev = safe_float(metrics.get("EV"), 0.0)
        fallback_hh = safe_float(metrics.get("HardHit%"), 0.0)
        fallback_brl = safe_float(metrics.get("Barrel%"), 0.0)
        fallback_gb = safe_float(metrics.get("GroundBall%"), 45.0)
        fallback_air = 100.0 - fallback_gb
        recent_hr = safe_int(metrics.get("recent_hr"), 0)
        recent_xbh = safe_int(metrics.get("recent_xbh"), 0)
        recent_iso = safe_float(metrics.get("recent_iso"), 0.0)

    barrel = safe_float(sav.get("Savant_Barrel%"), fallback_brl)
    hard_hit = safe_float(sav.get("Savant_HardHit%"), fallback_hh)
    ev = safe_float(sav.get("Savant_EV"), fallback_ev)
    xslg = safe_float(sav.get("Savant_xSLG"), season_slg)
    gb = safe_float(sav.get("Savant_GB%"), fallback_gb)
    air = safe_float(sav.get("Savant_AIR%"), max(0.0, 100.0 - gb))

    has_season = season_ab >= 8
    has_savant = any([
        barrel > 0, hard_hit > 0, ev > 0,
        safe_float(sav.get("Savant_xSLG"), 0.0) > 0,
    ])
    has_recent = metrics is not None

    if not has_season and not has_savant and not has_recent:
        return None

    hr_rate = (season_hr / season_ab * 100.0) if season_ab else 0.0
    score = (
        barrel * 3.4
        + hard_hit * 1.05
        + max(0.0, ev - 86.0) * 2.1
        + xslg * 80.0
        + air * 0.45
        + hr_rate * 4.0
        + recent_hr * 6.0
        + recent_xbh * 1.8
        + season_iso * 22.0
        - max(0.0, gb - 48.0) * 1.4
    )

    if has_recent and has_season and has_savant:
        data_level = "SEASON + RECENT + SAVANT"
        confidence = "MEDIUM"
    elif has_season and has_savant:
        data_level = "SEASON + SAVANT"
        confidence = "LOW-MEDIUM"
    elif has_season:
        data_level = "SEASON ONLY"
        confidence = "LOW"
    else:
        data_level = "SAVANT WATCHLIST"
        confidence = "LOW"

    return {
        "Player": player_name,
        "Player ID": player_id,
        "Early BF Score": round(score, 1),
        "Season HR": season_hr,
        "Season ISO": round(season_iso, 3),
        "Recent HR": recent_hr,
        "Recent ISO": round(recent_iso, 3),
        "EV": round(ev, 1) if ev else pd.NA,
        "Barrel%": round(barrel, 1) if barrel else pd.NA,
        "HardHit%": round(hard_hit, 1) if hard_hit else pd.NA,
        "AIR%": round(air, 1),
        "GroundBall%": round(gb, 1),
        "xSLG": round(xslg, 3) if xslg else pd.NA,
        "Data Level": data_level,
        "Research Confidence": confidence,
    }


@st.cache_data(ttl=3600, max_entries=2)
def build_next_slate_preview(next_date_key: str, schedule_tuple: tuple) -> pd.DataFrame:
    """Build a staged, resource-safe early watchlist.

    Stage 1 uses probable pitchers plus any available game roster, active roster,
    season stats, recent form, and Savant data. It never locks or tracks.
    """
    schedule_rows = [dict(x) for x in schedule_tuple]
    if not schedule_rows:
        return pd.DataFrame()

    team_ids = sorted({
        safe_int(g.get(side), 0)
        for g in schedule_rows
        for side in ("away_team_id", "home_team_id")
        if safe_int(g.get(side), 0) > 0
    })

    roster_map = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {executor.submit(get_team_hitters, tid): tid for tid in team_ids}
        for future in as_completed(future_map):
            tid = future_map[future]
            try:
                roster_map[tid] = future.result() or []
            except Exception:
                roster_map[tid] = []

    # Future special events can expose players in the game boxscore before a normal
    # team roster exists. Prefer those names when available.
    game_pool_map = {}
    for game in schedule_rows:
        game_pk = safe_int(game.get("game_pk"), 0)
        if game_pk <= 0:
            continue
        try:
            game_pool_map[(game_pk, "away")] = extract_boxscore_team_hitters(game_pk, "away") or []
            game_pool_map[(game_pk, "home")] = extract_boxscore_team_hitters(game_pk, "home") or []
        except Exception:
            game_pool_map[(game_pk, "away")] = []
            game_pool_map[(game_pk, "home")] = []

    all_ids = []
    for hitters in roster_map.values():
        all_ids.extend([h.get("player_id") for h in hitters[:18] if h.get("player_id")])
    for hitters in game_pool_map.values():
        all_ids.extend([h.get("player_id") for h in hitters if h.get("player_id")])

    unique_ids = tuple(dict.fromkeys(all_ids))
    stats_map = fetch_people_stats(unique_ids, "hitting") if unique_ids else {}
    savant_map = fetch_savant_batter_map(CURRENT_SEASON)

    # Pitcher profiles are available before lineups and should always be shown.
    pitcher_ids = []
    for g in schedule_rows:
        for key in ("away_pitcher_id", "home_pitcher_id"):
            pid = g.get(key)
            if pid:
                pitcher_ids.append(pid)
    pitcher_stats_map = fetch_people_stats(tuple(dict.fromkeys(pitcher_ids)), "pitching") if pitcher_ids else {}

    rows = []
    for game in schedule_rows:
        game_pk = safe_int(game.get("game_pk"), 0)
        for side_label, side_key, team_id_key, team_name_key, opp_pitcher_key, opp_pitcher_id_key in [
            ("Away", "away", "away_team_id", "away_team", "home_pitcher", "home_pitcher_id"),
            ("Home", "home", "home_team_id", "home_team", "away_pitcher", "away_pitcher_id"),
        ]:
            tid = safe_int(game.get(team_id_key), 0)
            team_name = game.get(team_name_key, "")
            opp_pitcher = game.get(opp_pitcher_key, "Starter Pending")
            opp_pitcher_id = game.get(opp_pitcher_id_key)

            game_hitters = game_pool_map.get((game_pk, side_key), [])
            candidate_pool = game_hitters if game_hitters else roster_map.get(tid, [])

            # Deduplicate and cap before detailed scoring.
            dedup = {}
            for h in candidate_pool:
                pid = h.get("player_id")
                if pid:
                    dedup[int(pid)] = {
                        "player_id": int(pid),
                        "player_name": h.get("player_name", ""),
                        "lineup_spot": h.get("lineup_spot"),
                    }
            candidate_pool = list(dedup.values())[:18]

            scored = []
            for hitter in candidate_pool:
                row = _next_slate_hitter_score(
                    safe_int(hitter.get("player_id"), 0),
                    hitter.get("player_name", ""),
                    stats_map,
                    savant_map,
                )
                if row:
                    row["Projected Lineup Spot"] = hitter.get("lineup_spot") or "—"
                    scored.append(row)

            scored = sorted(scored, key=lambda r: r["Early BF Score"], reverse=True)[:6]

            pitcher_profile = compute_pitcher_live_metrics_from_map(
                opp_pitcher_id,
                opp_pitcher,
                pitcher_stats_map,
            )
            pitcher_hr9 = (
                safe_float(pitcher_profile.get("Pitcher_HR9_Last7"), 0.0)
                if pitcher_profile else pd.NA
            )
            pitcher_barrel = (
                safe_float(pitcher_profile.get("Pitcher_Barrel_Allowed"), 0.0)
                if pitcher_profile else pd.NA
            )
            pitcher_hh = (
                safe_float(pitcher_profile.get("Pitcher_HardHit_Allowed"), 0.0)
                if pitcher_profile else pd.NA
            )

            for rank, row in enumerate(scored, 1):
                rows.append({
                    "Date": next_date_key,
                    "Research Stage": "STAGE 1 · EARLY WATCHLIST",
                    "Official Tracking": "NO",
                    "Game": game.get("game_key", ""),
                    "Game Time": format_game_time_et(game.get("game_time", "")),
                    "Venue": game.get("venue", "TBD"),
                    "Team": team_abbr(team_name),
                    "Side": side_label,
                    "Opponent Pitcher": opp_pitcher,
                    "Pitcher Status": "PROBABLE" if opp_pitcher not in {"", None, "Starter Pending"} else "PENDING",
                    "Pitcher HR/9": round(pitcher_hr9, 2) if pd.notna(pitcher_hr9) else pd.NA,
                    "Pitcher Barrel Allowed": round(pitcher_barrel, 1) if pd.notna(pitcher_barrel) else pd.NA,
                    "Pitcher HardHit Allowed": round(pitcher_hh, 1) if pd.notna(pitcher_hh) else pd.NA,
                    "Lineup Status": "LAST KNOWN / EXPECTED",
                    "Team Rank": rank,
                    **row,
                })

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["Early BF Score", "Game", "Team Rank"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
    out.insert(0, "Slate Rank", range(1, len(out) + 1))
    return out



def _latest_previous_board(tracker: pd.DataFrame):
    dates = [d for d in available_tracker_dates(tracker) if d != today_str()]
    for d in dates:
        board = load_daily_board_snapshot(d)
        if board is not None and not board.empty:
            return d, board
    return None, pd.DataFrame()


def _render_offday_snapshot_section(previous_board: pd.DataFrame, source_key: str | None, title: str, limit: int | None = None):
    st.subheader(title)
    if previous_board is None or previous_board.empty:
        st.info("No saved previous-slate board is available yet.")
        return
    view = previous_board.copy()
    if source_key and "Tracker Source" in view.columns:
        view = view[view["Tracker Source"].astype(str).str.strip().str.upper().eq(source_key.upper())].copy()
    if view.empty:
        st.info("That section was not saved in the latest previous-slate snapshot.")
        return
    if "Rank" not in view.columns:
        view = view.reset_index(drop=True)
        view.insert(0, "Rank", range(1, len(view) + 1))
    if limit is not None:
        view = view.head(limit)
    display_existing_columns(
        view,
        ["Rank", "Tracker Source", "Player", "Team", "Game", "Pitcher", "Lineup Spot",
         "Lineup Source", "HR Probability %", "HR Tier", "Matchup Advantage",
         "HR Attackability Score", "Barrel%", "HardHit%", "AIR%", "GroundBall%",
         "xSLG", "Ranking Reasons", "Why"],
    )



def render_full_tracker_panel(tracker: pd.DataFrame, key_prefix: str = "tracker"):
    """Render the complete BF tracker in both active-slate and off-day modes."""
    st.subheader("Homerun Tracker")
    st.caption(
        "Season totals, selected-slate results, Core Board, Top 12, Per-Game HR, "
        "saved board snapshots, combos, and daily accuracy history remain separate."
    )

    tracker = dedupe_tracker_rows(tracker.copy()) if tracker is not None else pd.DataFrame()
    combo_tracker_local = load_combo_tracker()
    daily_summary_local = summarize_tracker_by_day(tracker)

    def _tracker_stats(frame: pd.DataFrame) -> dict:
        if frame is None or frame.empty:
            return {"picks": 0, "hits": 0, "hr_total": 0, "pct": 0.0}
        work = frame.copy()
        hr_counts = pd.to_numeric(
            work["hr_count"] if "hr_count" in work.columns else
            work["result"] if "result" in work.columns else pd.Series(0, index=work.index),
            errors="coerce",
        ).fillna(0).astype(int)
        picks = int(len(work))
        hits = int((hr_counts > 0).sum())
        hr_total = int(hr_counts.sum())
        return {
            "picks": picks,
            "hits": hits,
            "hr_total": hr_total,
            "pct": round((hits / picks) * 100, 2) if picks else 0.0,
        }

    if tracker.empty:
        tracker_work = pd.DataFrame(columns=["tracker_source"])
    else:
        tracker_work = tracker.copy()
        if "tracker_source" not in tracker_work.columns:
            tracker_work["tracker_source"] = "CORE_BOARD"
        tracker_work["tracker_source"] = (
            tracker_work["tracker_source"].fillna("CORE_BOARD")
            .astype(str).str.strip().str.upper()
        )

    season_all = _tracker_stats(tracker_work)
    season_core = _tracker_stats(
        tracker_work[tracker_work["tracker_source"].eq("CORE_BOARD")]
        if not tracker_work.empty else tracker_work
    )
    season_top12 = _tracker_stats(
        tracker_work[tracker_work["tracker_source"].eq("TOP12")]
        if not tracker_work.empty else tracker_work
    )
    season_game = _tracker_stats(
        tracker_work[tracker_work["tracker_source"].eq("GAME_HR")]
        if not tracker_work.empty else tracker_work
    )

    st.markdown("### Season Overview")
    season_cols = st.columns(4)
    season_blocks = [
        ("All Predictions", season_all),
        ("Core Board", season_core),
        ("Top 12", season_top12),
        ("Per-Game HR", season_game),
    ]
    for col, (label, stats) in zip(season_cols, season_blocks):
        with col:
            st.markdown(f"**{label}**")
            st.metric("Season Picks", stats["picks"])
            st.metric("Winning Picks", stats["hits"])
            st.metric("Total HR Recorded", stats["hr_total"])
            st.metric("Hit Rate", f'{stats["pct"]:.2f}%')

    date_options = available_tracker_dates(tracker_work)
    selected_tracker_date = st.selectbox(
        "Review slate date",
        options=date_options,
        index=0,
        key=f"{key_prefix}_review_slate_date",
    )

    selected_source_summary = summarize_tracker_sources_for_date(
        tracker_work, selected_tracker_date
    )
    if tracker_work.empty or "date" not in tracker_work.columns:
        selected_tracker = pd.DataFrame()
    else:
        selected_tracker = tracker_work[
            tracker_work["date"].astype("string").fillna("") == str(selected_tracker_date)
        ].copy()

    if "hr_count" not in selected_tracker.columns:
        selected_tracker["hr_count"] = pd.to_numeric(
            selected_tracker["result"]
            if "result" in selected_tracker.columns
            else pd.Series(0, index=selected_tracker.index),
            errors="coerce",
        ).fillna(0).astype(int)

    selected_all = _tracker_stats(selected_tracker)
    st.markdown(f"### Selected Slate — {selected_tracker_date}")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("All Surfaced", selected_all["picks"])
    a2.metric("Winning Picks", selected_all["hits"])
    a3.metric("Total HR Recorded", selected_all["hr_total"])
    a4.metric("Overall Hit Rate", f'{selected_all["pct"]:.2f}%')

    section_cols = st.columns(3)
    for col, section_name, source_key in [
        (section_cols[0], "Core Board", "CORE_BOARD"),
        (section_cols[1], "Top 12", "TOP12"),
        (section_cols[2], "Per-Game HR", "GAME_HR"),
    ]:
        summary_row = selected_source_summary.get(
            source_key, {"total": 0, "hits": 0, "pct": 0.0}
        )
        section_frame = (
            selected_tracker[selected_tracker["tracker_source"].eq(source_key)]
            if not selected_tracker.empty and "tracker_source" in selected_tracker.columns
            else pd.DataFrame()
        )
        section_hr_total = _tracker_stats(section_frame)["hr_total"]
        with col:
            st.markdown(f"**{section_name}**")
            st.metric("Surfaced", summary_row.get("total", 0))
            st.metric("Winning Picks", summary_row.get("hits", 0))
            st.metric("Total HR", section_hr_total)
            st.metric("Hit Rate", f'{safe_float(summary_row.get("pct"), 0.0):.2f}%')

    if not selected_tracker.empty:
        st.divider()
        st.markdown("### Selected Date Split Tracker Tables")
        for section_name, source_key in [
            ("Core Board", "CORE_BOARD"),
            ("Top 12", "TOP12"),
            ("Per-Game HR", "GAME_HR"),
        ]:
            section_df = selected_tracker[
                selected_tracker["tracker_source"].eq(source_key)
            ].copy()
            with st.expander(
                f"{section_name} — {len(section_df)} tracked picks",
                expanded=(source_key == "CORE_BOARD"),
            ):
                if section_df.empty:
                    st.caption("No tracked rows in this section for the selected date.")
                else:
                    section_df["hr_count"] = pd.to_numeric(
                        section_df["hr_count"], errors="coerce"
                    ).fillna(0).astype(int)
                    section_df["result"] = pd.to_numeric(
                        section_df.get("result", 0), errors="coerce"
                    ).fillna(0).astype(int)
                    display_existing_columns(
                        section_df.sort_values(
                            by=["hr_count", "result", "hr_probability", "player"],
                            ascending=[False, False, False, True],
                        ),
                        [
                            "player", "team", "game", "hr_probability", "hr_tier",
                            "tracker_source", "hr_eligible", "result", "hr_count",
                            "result_state", "game_state", "updated_at",
                        ],
                    )
    else:
        st.info("No tracker rows are saved for the selected date.")

    selected_board_snapshot = load_daily_board_snapshot(selected_tracker_date)
    if not selected_board_snapshot.empty:
        st.divider()
        with st.expander("Saved Board Snapshot for Selected Date", expanded=False):
            display_existing_columns(
                selected_board_snapshot,
                [
                    "Tracker Source", "Player", "Team", "Game", "Pitcher",
                    "Lineup Spot", "HR Probability %", "HR Tier",
                    "Prediction Quality Grade", "Moonshot Score", "2 HR Score", "Nuke Score", "Stack Score",
                    "Actual HR Today", "Matchup Advantage",
                    "HR Attackability Score", "EV", "Barrel%", "HardHit%",
                    "AIR%", "Ranking Reasons", "Why",
                ],
            )

    st.divider()
    st.markdown("### Combo Results")
    if combo_tracker_local is None or combo_tracker_local.empty:
        st.caption("No combo history is available.")
    else:
        combo_view = combo_tracker_local[
            combo_tracker_local["date"].astype("string").fillna("")
            == str(selected_tracker_date)
        ].copy()
        if combo_view.empty:
            st.caption("No combos were tracked for the selected date.")
        else:
            full_hits = int(
                pd.to_numeric(combo_view.get("result", 0), errors="coerce")
                .fillna(0).astype(int).sum()
            )
            partial_hits = int(
                (
                    pd.to_numeric(combo_view.get("legs_hit", 0), errors="coerce").fillna(0)
                    > 0
                ).sum()
                - full_hits
            )
            partial_hits = max(0, partial_hits)
            c1, c2, c3 = st.columns(3)
            c1.metric("Tracked Combos", len(combo_view))
            c2.metric("Full Hits", full_hits)
            c3.metric("Partial Hits", partial_hits)
            display_existing_columns(
                combo_view.sort_values(
                    by=["combo_size", "combined_score"],
                    ascending=[True, False],
                ),
                [
                    "combo_label", "combo_size", "avg_leg_probability",
                    "combined_score", "legs_hit", "total_legs",
                    "result_state", "updated_at",
                ],
            )

    if not daily_summary_local.empty:
        st.divider()
        st.markdown("### Daily HR Prediction Accuracy History")
        st.dataframe(
            dedupe_columns(daily_summary_local),
            use_container_width=True,
            hide_index=True,
        )

    render_tracker_audit_learning(tracker_work, selected_tracker)



def render_bf_quick_key():
    st.markdown("""
    <div class="bf-guide-quick">
      <div><small>BF EDGE</small><strong>Overall matchup</strong><span>Hitter, pitcher, lineup, park, weather and form.</span></div>
      <div><small>BF CONFIDENCE</small><strong>Model agreement</strong><span>How strongly independent signals support the rank.</span></div>
      <div><small>PITCH FIT</small><strong>Arsenal matchup</strong><span>How the hitter fits the pitcher's true pitch mix.</span></div>
      <div><small>HR%</small><strong>Estimated HR chance</strong><span>Modeled probability, not guaranteed outcome.</span></div>
      <div><small>GRADE</small><strong>A+ through F</strong><span>Plain-language projection quality.</span></div>
    </div>""", unsafe_allow_html=True)


def render_bf_context_key():
    with st.expander("ⓘ BF Key — scores, badges, colors and roles", expanded=False):
        render_bf_quick_key()
        st.markdown("""
        <div class="bf-color-key">
          <span style="color:#35d07f;border-color:#35d07f">🟢 Elite / favorable</span>
          <span style="color:#69a7ff;border-color:#69a7ff">🔵 Strong</span>
          <span style="color:#ffd166;border-color:#ffd166">🟡 Playable / caution</span>
          <span style="color:#ff9966;border-color:#ff9966">🟠 Risky</span>
          <span style="color:#ff6666;border-color:#ff6666">🔴 Fade / suppressive</span>
        </div>
        <div class="bf-guide-table">
          <div>🎯 Primary Target</div><div>Highest-rated hitter for that team or board group.</div>
          <div>🤝 Strong Pair</div><div>Preferred complementary hitter.</div>
          <div>Alternate</div><div>Qualified backup with fewer aligned signals.</div>
          <div>💤 Sleeper</div><div>Higher-variance upside with more risk.</div>
          <div>🔥 Core</div><div>Passed BF's main HR qualification rules.</div>
          <div>⚡ Barrel God</div><div>Elite or near-elite barrel quality.</div>
          <div>🟢 Attack Pitcher</div><div>Pitcher has meaningful HR or contact vulnerability.</div>
          <div>📈 Hot</div><div>Recent damage form supports the projection.</div>
          <div>💣 Nuke</div><div>High-ceiling power and matchup blend.</div>
          <div>🚀 Moonshot</div><div>Long-distance HR profile.</div>
        </div>""", unsafe_allow_html=True)


def render_bf_knowledge_center():
    st.subheader("BF Data Knowledge Center")
    st.caption("Plain-language explanations for BF scores, badges, colors and recommendations.")

    st.markdown("""
    <div class="bf-guide-panel">
      <div class="bf-guide-title">HOW TO READ BF DATA IN 10 SECONDS</div>
      <div class="bf-guide-sub">Start with the target role. Then compare Edge, HR%, Confidence and Pitch Fit. Open the matchup analysis for pitcher, arsenal and Statcast details.</div>
      <div class="bf-guide-grid">
        <div class="bf-guide-card"><h4>1. Choose the role</h4><p>Primary Target is the top play. Strong Pair is the preferred partner. Alternate and Sleeper carry more risk.</p></div>
        <div class="bf-guide-card"><h4>2. Check agreement</h4><p>Look for strong Edge, Grade and HR%, with no major Pitch Fit or ground-ball warning.</p></div>
        <div class="bf-guide-card"><h4>3. Confirm the slate</h4><p>Projected cards may move. Confirmed cards use official lineups and locked tracking.</p></div>
      </div>
    </div>""", unsafe_allow_html=True)

    render_bf_context_key()

    sections = {
        "📊 Grades and proprietary scores": [
            ("BF Edge","Overall matchup strength combining hitter, pitcher, arsenal, lineup, park, weather and form."),
            ("BF Confidence","How strongly independent model components agree. It is not HR probability."),
            ("Decision Grade","A+ through F summary of projection quality."),
            ("HR%","Estimated chance of at least one home run."),
            ("Pitch Fit","How well the hitter matches the pitcher's actual arsenal and usage."),
            ("Quality Score","Overall strength and reliability of the prediction inputs."),
            ("Moonshot Score","Long-distance HR ceiling from EV, barrels, launch shape and environment."),
            ("2-HR Score","Relative multi-HR ceiling; not a literal probability."),
            ("Nuke Score","High-end ceiling combining power and matchup."),
            ("Stack Score","Suitability for a correlated team stack."),
            ("Attackability","Pitcher HR vulnerability; higher is better for hitters."),
            ("Slate Confidence","Overall readiness and strength of the day's board."),
        ],
        "🔥 Badges and target roles": [
            ("Primary Target","Highest-priority hitter in the team or group."),
            ("Strong Pair","Preferred complementary hitter."),
            ("Alternate","Qualified backup behind the top recommendations."),
            ("Sleeper","Higher-variance player with legitimate upside."),
            ("Core","Passed BF's primary HR rules."),
            ("Barrel God","Outstanding barrel profile."),
            ("Attack Pitcher","Opponent meets BF vulnerability thresholds."),
            ("Hot","Recent damage form is supportive."),
            ("Moonshot","Exceptional long-HR profile."),
            ("Nuke","Elite ceiling across power and matchup."),
            ("Value","Strong BF profile that may be less obvious publicly."),
            ("Fade","Major suppressive signal or weak model agreement."),
            ("Watchlist","Close to qualifying but not an official locked play."),
        ],
        "🌤 Weather and ballpark guide": [
            ("Wind","Wind out can help carry; wind in can suppress it."),
            ("Temperature","Warm air generally helps carry; cold dense air can reduce distance."),
            ("Park Factor","Above 1.00 is more HR friendly; below 1.00 is more suppressive."),
            ("Dimensions","LF, LCF, CF, RCF and RF distances explain pull-side paths."),
            ("Roof","Weather impact is reduced in a dome or closed-roof setting."),
            ("Preliminary","Future-slate weather can change before first pitch."),
        ],
        "⚾ Statcast and pitcher metrics": [
            ("EV","Exit velocity."),
            ("Barrel%","Rate of ideal exit-velocity and launch-angle contact."),
            ("HardHit%","Rate of balls hit 95 mph or harder."),
            ("FB%","Fly-ball percentage."),
            ("LD%","Line-drive percentage."),
            ("GB%","Ground-ball percentage; high values reduce HR opportunity."),
            ("AIR%","BF productive air-contact measure."),
            ("Launch Angle","Average vertical angle of contact."),
            ("xSLG","Expected slugging based on contact quality."),
            ("xwOBA","Expected overall offensive quality."),
            ("Pitcher HR/9","Home runs allowed per nine innings."),
            ("Barrel Allowed","Pitcher's rate of allowing barrel-quality contact."),
            ("Hard Hit Allowed","Pitcher's rate of allowing 95+ mph contact."),
        ],
    }

    for title, rows in sections.items():
        with st.expander(title, expanded=(title.startswith("📊"))):
            html = '<div class="bf-guide-table">' + ''.join(
                f"<div>{escape(k)}</div><div>{escape(v)}</div>" for k, v in rows
            ) + "</div>"
            st.markdown(html, unsafe_allow_html=True)

    with st.expander("🎨 Color guide"):
        st.markdown("""
        <div class="bf-color-key">
          <span style="color:#35d07f;border-color:#35d07f">🟢 Green — elite or favorable</span>
          <span style="color:#69a7ff;border-color:#69a7ff">🔵 Blue — strong</span>
          <span style="color:#ffd166;border-color:#ffd166">🟡 Yellow — playable or caution</span>
          <span style="color:#ff9966;border-color:#ff9966">🟠 Orange — elevated risk</span>
          <span style="color:#ff6666;border-color:#ff6666">🔴 Red — fade or suppressive</span>
        </div>""", unsafe_allow_html=True)

    with st.expander("🤖 How BF creates a recommendation"):
        st.markdown("""
        1. Load official or projected hitters and probable pitchers.  
        2. Evaluate season and recent hitter damage.  
        3. Measure pitcher HR, barrel and hard-contact vulnerability.  
        4. Compare the hitter with the pitcher's true arsenal.  
        5. Apply lineup, park, weather, bullpen and ground-ball adjustments.  
        6. Generate HR%, Edge, Pitch Fit, grades and ceiling scores.  
        7. Rank hitters and assign target roles.  
        8. Lock official predictions after lineups confirm.
        """)

    with st.expander("⚠️ Important interpretation notes"):
        st.markdown("""
        - High BF scores do not guarantee a home run.
        - BF Confidence is model agreement, not HR probability.
        - Moonshot, 2-HR, Nuke and Stack are relative scores, not literal probabilities.
        - Projected and Early Watchlist cards can change.
        - Confirmed cards are the official locked research board.
        - Use BF Data as decision support rather than relying on one metric alone.
        """)


def render_first_time_guide():
    if "bf_guide_dismissed" not in st.session_state:
        st.session_state.bf_guide_dismissed = False
    if not st.session_state.bf_guide_dismissed:
        st.markdown("""
        <div class="bf-onboard"><strong>👋 New to BF Data?</strong>
        <p>Start with the target role, then compare Edge, Grade, HR%, Confidence and Pitch Fit. The BF Guide explains every score and badge.</p></div>
        """, unsafe_allow_html=True)
        if st.button("Got it — hide this guide", key="dismiss_bf_guide"):
            st.session_state.bf_guide_dismissed = True
            st.rerun()


def render_active_tomorrow_preview():
    """Resource-safe tomorrow/next-slate research available during active slates."""
    next_date_key, next_schedule = find_next_scheduled_slate(today_str(), max_days=14)

    if not next_date_key or not next_schedule:
        st.warning("No future MLB slate was found within the next 14 days.")
        return

    next_dt = datetime.strptime(next_date_key, "%Y-%m-%d")
    try:
        date_label = next_dt.strftime("%A, %B %-d")
    except Exception:
        date_label = next_dt.strftime("%A, %B %d").replace(" 0", " ")

    st.subheader(f"Tomorrow / Next Slate Preview — {date_label}")
    st.caption(
        "Early research only • probable pitchers and expected hitter pools • "
        "never locked or tracked • updates as lineups and probable pitchers improve."
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Games", len(next_schedule))
    m2.metric(
        "Days Away",
        (next_dt.date() - datetime.now(ZoneInfo("America/New_York")).date()).days,
    )
    probable_count = sum(
        int(g.get("away_pitcher") != "Starter Pending")
        + int(g.get("home_pitcher") != "Starter Pending")
        for g in next_schedule
    )
    m3.metric("Probable Pitchers", f"{probable_count}/{len(next_schedule) * 2}")

    schedule_view = pd.DataFrame([
        {
            "Time": format_game_time_et(g.get("game_time", "")),
            "Game": g.get("game_key", ""),
            "Venue": g.get("venue", "TBD"),
            "Away Starter": g.get("away_pitcher", "Starter Pending"),
            "Home Starter": g.get("home_pitcher", "Starter Pending"),
        }
        for g in next_schedule
    ])
    st.dataframe(schedule_view, use_container_width=True, hide_index=True)

    build_key = f"active_next_slate_{next_date_key}"
    if st.button(
        "Generate Tomorrow / Next Slate Predictions",
        type="primary",
        use_container_width=True,
        key="active_generate_next_slate",
    ):
        st.session_state["build_active_next_slate_preview"] = build_key

    if st.session_state.get("build_active_next_slate_preview") != build_key:
        st.info(
            "Generate only when you want early research. Keeping this on demand "
            "prevents tomorrow data from slowing today's live board."
        )
        return

    with st.spinner("Building resource-safe next-slate predictions..."):
        preview_df = build_next_slate_preview(
            next_date_key,
            tuple(tuple(sorted(g.items())) for g in next_schedule),
        )

    if preview_df is None or preview_df.empty:
        st.warning(
            "The slate is scheduled, but there is not enough reliable hitter data yet. "
            "Probable pitchers and schedule details remain available above."
        )
        return

    st.markdown("### Early BF Targets")
    preview_targets = get_best_hr_matchups(preview_df, 20)

    if preview_targets.empty:
        preview_targets = preview_df.copy()

    # Keep the same premium decision-card language as the active board where possible.
    try:
        render_card_grid(preview_targets, max_cards=20, columns=2)
    except Exception:
        preview_cols = [
            "Rank", "Player", "Team", "Game", "Game Time", "Opponent Pitcher",
            "Pitcher Status", "Lineup Status", "Early BF Score", "Season HR",
            "Recent HR", "EV", "Barrel%", "HardHit%", "AIR%", "GroundBall%",
        ]
        display_existing_columns(preview_targets, preview_cols)


def render_off_day_mode(tracker: pd.DataFrame):
    next_date_key, next_schedule = find_next_scheduled_slate(today_str(), max_days=14)
    previous_date, previous_board = _latest_previous_board(tracker)

    st.markdown("""
    <div style="border:1px solid rgba(255,209,102,.45);background:rgba(255,209,102,.08);
                border-radius:14px;padding:14px 16px;margin:8px 0 12px 0;">
      <div style="font-size:.72rem;font-weight:900;letter-spacing:.12em;color:#ffd166;">MLB OFF-DAY MODE · FULL BOARD ACCESS</div>
      <div style="font-size:1.25rem;font-weight:950;margin-top:4px;">No official MLB games are scheduled today.</div>
      <div style="color:#b9bec8;margin-top:5px;">All BF Data sections remain available. Next-slate research is separate from official locks and tracking.</div>
    </div>
    """, unsafe_allow_html=True)

    tab_names = [
        "Next Slate Preview", "JR HR Board", "Top 12", "Top HR Targets", "Pitchers to Attack",
        "HR Combos", "Hits + Runs + RBIs", "Batter Breakdown", "Homerun Tracker",
        "Previous Slate Review", "Lineup Watch", "Live Weather", "BF Guide"
    ]
    off_tabs = st.tabs(tab_names)

    with off_tabs[0]:
        if not next_schedule or not next_date_key:
            st.warning("No MLB slate was found within the next 14 days.")
        else:
            next_dt = datetime.strptime(next_date_key, "%Y-%m-%d")
            try:
                date_label = next_dt.strftime("%A, %B %-d")
            except Exception:
                date_label = next_dt.strftime("%A, %B %d").replace(" 0", " ")
            st.subheader(f"Next Slate Preview — {date_label}")
            st.caption("Stage 1 Early Watchlist • probable pitchers + last-known/expected hitters • low confidence • never locked or tracked. The board upgrades automatically when projected and confirmed lineups arrive.")
            m1, m2, m3 = st.columns(3)
            m1.metric("Next Slate Games", len(next_schedule))
            m2.metric("Days Away", (next_dt.date() - datetime.now(ZoneInfo("America/New_York")).date()).days)
            probable_count = sum(
                int(g.get("away_pitcher") != "Starter Pending") + int(g.get("home_pitcher") != "Starter Pending")
                for g in next_schedule
            )
            m3.metric("Probable Pitchers Posted", f"{probable_count}/{len(next_schedule)*2}")
            schedule_view = pd.DataFrame([{
                "Time": format_game_time_et(g.get("game_time", "")),
                "Game": g.get("game_key", ""),
                "Venue": g.get("venue", "TBD"),
                "Away Starter": g.get("away_pitcher", "Starter Pending"),
                "Home Starter": g.get("home_pitcher", "Starter Pending"),
            } for g in next_schedule])
            st.dataframe(schedule_view, use_container_width=True, hide_index=True)
            if st.button("Generate Next Slate Predictions", type="primary", use_container_width=True, key="offday_generate_next_slate"):
                st.session_state["build_next_slate_preview"] = next_date_key
            if st.session_state.get("build_next_slate_preview") == next_date_key:
                with st.spinner("Building resource-safe next-slate predictions..."):
                    preview_df = build_next_slate_preview(next_date_key, tuple(tuple(sorted(g.items())) for g in next_schedule))
                if preview_df.empty:
                    st.warning(
                        "Probable pitchers are available, but no usable hitter pool was returned yet. "
                        "BF Data checked the future-game roster and active rosters without inventing player names. "
                        "The preview will populate automatically as MLB publishes the event roster or expected hitters."
                    )
                    pitcher_only = pd.DataFrame([{
                        "Game": g.get("game_key", ""),
                        "Venue": g.get("venue", "TBD"),
                        "Away Starter": g.get("away_pitcher", "Starter Pending"),
                        "Home Starter": g.get("home_pitcher", "Starter Pending"),
                        "Research Stage": "PITCHER-ONLY EARLY SCOUT",
                    } for g in next_schedule])
                    st.markdown("### Pitcher-Only Early Scout")
                    st.dataframe(pitcher_only, use_container_width=True, hide_index=True)
                else:
                    st.markdown("### Early BF Targets")
                    st.caption(
                        "Top six early targets are shown as BF decision cards. "
                        "These remain research-only until lineups become projected or confirmed."
                    )
                    render_early_watchlist_cards(preview_df, max_cards=6)

                    with st.expander("Open Early Watchlist Data Table", expanded=False):
                        display_existing_columns(
                            preview_df.head(30),
                            ["Slate Rank", "Player", "Team", "Game", "Game Time", "Opponent Pitcher",
                             "Pitcher Status", "Pitcher HR/9", "Pitcher Barrel Allowed",
                             "Pitcher HardHit Allowed", "Lineup Status", "Research Confidence",
                             "Data Level", "Early BF Score", "Season HR", "Season ISO",
                             "Recent HR", "Recent ISO", "EV", "Barrel%", "HardHit%",
                             "AIR%", "GroundBall%", "xSLG"],
                        )

    with off_tabs[1]:
        _render_offday_snapshot_section(previous_board, "CORE_BOARD", f"JR HR Board — Previous Slate {previous_date or ''}", 30)
    with off_tabs[2]:
        _render_offday_snapshot_section(previous_board, "TOP12", f"Top 12 — Previous Slate {previous_date or ''}", 12)
    with off_tabs[3]:
        _render_offday_snapshot_section(previous_board, None, f"Top HR Targets — Previous Slate {previous_date or ''}", 25)
    with off_tabs[4]:
        st.subheader("Pitchers to Attack")
        st.info("There is no official pitcher-attack board on an MLB off-day. Use Next Slate Preview for probable starters; the official attack board returns when the slate becomes active.")
        if next_schedule:
            display_existing_columns(pd.DataFrame([{
                "Game": g.get("game_key", ""), "Away Starter": g.get("away_pitcher", "Starter Pending"),
                "Home Starter": g.get("home_pitcher", "Starter Pending"), "Venue": g.get("venue", "TBD")
            } for g in next_schedule]), ["Game", "Away Starter", "Home Starter", "Venue"])
    with off_tabs[5]:
        st.subheader("HR Combos")
        combo_history = load_combo_tracker()
        if combo_history.empty:
            st.info("No combo history is available. New official combos generate only on active slates.")
        else:
            display_existing_columns(combo_history.sort_values(["date", "updated_at"], ascending=[False, False]),
                                     ["date", "combo_label", "combo_size", "games", "result_state", "legs_hit", "total_legs", "updated_at"])
    with off_tabs[6]:
        st.subheader("Hits + Runs + RBIs")
        st.info("No official H+R+RBI slate is generated on an off-day. This tab remains visible and will repopulate automatically on the next active slate.")
    with off_tabs[7]:
        st.subheader("Batter Breakdown")
        if previous_board is None or previous_board.empty:
            st.info("No previous batter snapshot is available.")
        else:
            display_existing_columns(previous_board.head(40), ["Player", "Team", "Game", "Pitcher", "Barrel%", "HardHit%", "AIR%", "GroundBall%", "xSLG", "xwOBA", "Ranking Reasons"])
    with off_tabs[8]:
        render_full_tracker_panel(tracker, key_prefix="offday_tracker")
    with off_tabs[9]:
        st.subheader("Previous Slate Review")
        dates = [d for d in available_tracker_dates(tracker) if d != today_str()]
        if not dates:
            st.info("No previous board snapshots are available yet.")
        else:
            selected_date = st.selectbox("Select previous slate", dates, key="offday_previous_slate")
            board = load_daily_board_snapshot(selected_date)
            if board.empty:
                st.info("No saved prediction board exists for that date.")
            else:
                display_existing_columns(board, ["Tracker Source", "Player", "Team", "Game", "Pitcher", "HR Probability %", "HR Tier", "Lineup Source", "Matchup Advantage", "Ranking Reasons"])
    with off_tabs[10]:
        st.subheader("Lineup Watch")
        if not next_schedule:
            st.info("No upcoming slate is available.")
        else:
            st.info("Lineups remain PROJECTED until MLB officially supplies all nine batting-order positions.")
            rows = []
            for g in next_schedule:
                rows.extend([
                    {"Game": g["game_key"], "Team": team_abbr(g["away_team"]), "Opposing Starter": g["home_pitcher"], "Lineup": "PROJECTED"},
                    {"Game": g["game_key"], "Team": team_abbr(g["home_team"]), "Opposing Starter": g["away_pitcher"], "Lineup": "PROJECTED"},
                ])
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with off_tabs[11]:
        st.subheader("Live Weather")
        st.info("Next-slate weather is preliminary. Each visual card uses the forecast hour nearest scheduled first pitch.")
        render_live_weather_board(next_schedule, preliminary=True)

    with off_tabs[12]:
        render_bf_knowledge_center()


c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
with c1:
    if st.button("Update Board", use_container_width=True):
        st.session_state.manual_refresh_trigger = True
        st.session_state.deep_l10_bbe = False
        st.rerun()
    if st.button("Deep L10 Refresh", use_container_width=True):
        st.session_state.manual_refresh_trigger = True
        st.session_state.deep_l10_bbe = True
        st.cache_data.clear()
        st.rerun()


# Run lightweight storage maintenance once per browser session.
if (
    not st.session_state.get("bf_resource_cleanup_complete", False)
    or st.session_state.pop("bf_manual_resource_cleanup", False)
):
    try:
        cleanup_bf_recovery_snapshots()
        enforce_bf_local_storage_ceiling()
    except Exception:
        pass
    st.session_state.bf_resource_cleanup_complete = True

with st.sidebar.expander("BF Resource Maintenance", expanded=False):
    local_mb = round(_bf_directory_size_bytes(BF_DATA_DIR) / (1024 * 1024), 2)
    st.caption(f"Local BF data: {local_mb:.2f} MB")
    st.caption(
        f"Retention: tracker {BF_SNAPSHOT_RETENTION_DAYS} days • "
        f"board {BF_BOARD_SNAPSHOT_RETENTION_DAYS} days"
    )
    if st.button("Clean old snapshots", key="bf_manual_cleanup_button"):
        st.session_state.bf_manual_resource_cleanup = True
        st.rerun()
    if st.button("Clear temporary Streamlit cache", key="bf_clear_cache_button"):
        st.cache_data.clear()
        st.success("Temporary cache cleared. The next load will rebuild fresh data.")

deep_bbe_mode = bool(st.session_state.get("deep_l10_bbe", DEFAULT_DEEP_L10_BBE))
live_df, schedule = build_daily_dataset(deep_bbe=deep_bbe_mode)
schedule = sort_schedule_rows(schedule)

# Off-day mode must branch before locks, combos, tracker syncing, or empty-board stop logic.
# This preserves every major BF Data tab while keeping future research separate from official tracking.
if not schedule:
    with c2:
        st.metric("Games On Slate", 0)
    with c3:
        st.metric("Lineup Mode", "OFF-DAY")
    with c4:
        st.caption("MLB off-day detected • all BF Data sections remain available • next scheduled slate enabled")
    st.session_state.manual_refresh_trigger = False
    render_off_day_mode(load_tracker())
    st.stop()

locked_df_raw = ensure_daily_board_lock(live_df, schedule)

lineup_mode = get_lineup_mode(schedule) if schedule else "PROJECTED"

# Build and save the prediction/tracker pool BEFORE adding live results.
# This prevents post-HR result data from rewriting the prediction board.
doubleheader_assignment_map = build_doubleheader_assignment_map(locked_df_raw, schedule)
tracked_df = build_visible_tracker_pool(locked_df_raw, schedule, doubleheader_assignment_map)
save_daily_board_snapshot(tracked_df, today_str())

tracker = sync_tracker_with_board(tracked_df)
tracker = reconcile_today_tracker_with_visible_board(tracker, tracked_df, schedule)
combo_board = build_combo_board(locked_df_raw)
combo_tracker = sync_combo_tracker_with_board(combo_board)

# Always update results every run. Refresh/update should not be required for HR counts to move off zero.
tracker = auto_update_tracker_results(tracker, schedule)
combo_tracker = auto_update_combo_tracker_results(combo_tracker, schedule)
st.session_state.manual_refresh_trigger = False

# Display-only live result column.
locked_df = add_live_homer_counts_to_board(locked_df_raw, schedule)

# Refresh the additive market layer before rendering any board or player card.
# Cached provider calls keep normal reruns lightweight. Odds never modify the board.
if _get_odds_api_key():
    try:
        st.session_state["bf_market_refresh_meta"] = refresh_automatic_market_odds(locked_df)
    except Exception as _bf_market_exc:
        st.session_state["bf_market_refresh_meta"] = {
            "status": f"ERROR: {_bf_market_exc}",
            "saved": 0,
        }
else:
    st.session_state["bf_market_refresh_meta"] = {"status": "NO_KEY", "saved": 0}

save_daily_tracker_snapshot(tracker, today_str())

summary = summarize_tracker(tracker)
source_summary = summarize_tracker_sources(tracker)
daily_summary = summarize_tracker_by_day(tracker)
combo_summary = summarize_combo_tracker(combo_tracker)

with c2:
    st.metric("Games On Slate", len(schedule))
with c3:
    st.metric("Lineup Mode", lineup_mode)
with c4:
    slate_confidence_value = compute_slate_confidence(tracked_df)
    st.caption(f"BF Slate Confidence: {slate_confidence_value:.1f}/100")
    confirmed_locked = 0
    if not locked_df.empty and "lock_scope" in locked_df.columns:
        confirmed_locked = int((locked_df["lock_scope"].astype(str) == "CONFIRMED_TEAM").sum())
    if confirmed_locked > 0:
        st.caption(f"Projected teams stay live • confirmed teams pregame-rebuild on update • locked confirmed rows: {confirmed_locked}")
    else:
        st.caption(f"Projected teams live • update rebuilds pregame confirmed locks • last refresh: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")

if locked_df.empty:
    st.warning("No games or hitter data loaded.")
    st.stop()

base_tabs = ["JR HR Board", "Top 12", "Top HR Targets", "Pitchers to Attack", "HR Combos", "Hits + Runs + RBIs", "Batter Breakdown", "Homerun Tracker", "Lineup Watch", "Live Weather", "Tomorrow Preview", "BF Guide", "Today's Card", "Market Edge"]
schedule = sort_schedule_rows(schedule)
game_tabs = [f"{format_game_time_et(g.get('game_time', ''))} | {g['game_key']}" for g in schedule]
tabs = st.tabs(base_tabs + game_tabs)

with tabs[0]:
    st.subheader("JR HR Board")
    st.caption("Projected teams stay live. Confirmed teams freeze once lineups lock. Actual HR Today is display-only and does not change rankings.")
    render_first_time_guide()
    render_bf_context_key()
    hr_df_live = get_strict_hr_pool(locked_df)
    hr_df = get_locked_section_snapshot("CORE_BOARD", hr_df_live, schedule, limit=30)
    render_card_grid(hr_df, max_cards=30, columns=3)
    with st.expander("Raw JR HR Board Table"):
        st.dataframe(
            hr_df[[
                "Rank", "Player", "Team", "Game", "Pitcher", "Lineup Spot",
                "Lineup Source", "Actual HR Today", "HR Probability %", "HR Tier", "Prediction Quality Grade", "Moonshot Score", "2 HR Score", "Nuke Score", "Stack Score", "GroundBall%",
                "GB Rule", "GB Note", "Matchup Advantage", "HR Attackability Score", "WeatherNote", "BullpenFatigueNote", "HardHit%", "FlyBall%", "AIR%", "xSLG", "xwOBA", "Barrel%", "Ranking Reasons", "Why"
            ]],
            use_container_width=True,
            hide_index=True
        )

with tabs[1]:
    st.subheader("Top 12 HR Candidates")
    st.caption("Confirmed teams freeze once lineups lock. Projected teams can still update. Actual HR Today is display-only and does not change rankings.")
    top12_live = get_top12_hybrid(locked_df)
    top12 = get_locked_section_snapshot("TOP12", top12_live, schedule, limit=12)
    render_card_grid(top12, max_cards=12, columns=3)
    with st.expander("Raw Top 12 Table"):
        st.dataframe(
            top12[[
                "Rank", "Player", "Team", "Game", "Pitcher", "Lineup Spot",
                "Lineup Source", "Actual HR Today", "HR Probability %", "HR Tier", "Prediction Quality Grade", "Moonshot Score", "2 HR Score", "Nuke Score", "Stack Score", "GroundBall%",
                "GB Rule", "GB Note", "Matchup Advantage", "HR Attackability Score", "WeatherNote", "BullpenFatigueNote", "HardHit%", "FlyBall%", "AIR%", "xSLG", "xwOBA", "Barrel%", "Ranking Reasons", "Why"
            ]],
            use_container_width=True,
            hide_index=True
        )

with tabs[2]:
    st.subheader("Top HR Targets — Slate-Wide Top 25")
    st.caption("Global slate ranking based on hitter authority, EV/ISO-style power, pitch exposure, pitcher HR/9 vulnerability, weather, park, and matchup advantage.")
    top_targets = get_best_hr_matchups(locked_df, 25)
    target_cols = [
        "Rank", "Player", "Team", "Game", "Pitcher", "Lineup Spot", "Lineup Source",
        "Matchup Advantage", "Matchup Advantage Score", "HR Attackability Score", "Pitcher_HR9_Last7",
        "EV", "Barrel%", "HardHit%", "AIR%", "xSLG", "xwOBA",
        "Pitch Mix Mode", "Relevant Pitch Mix", "Primary Pitch Usage",
        "Actual HR Today", "HR Probability %", "HR Tier", "Ranking Reasons"
    ]
    render_card_grid(top_targets, max_cards=25, columns=3)
    with st.expander("Raw Top HR Targets Table"):
        display_existing_columns(top_targets, target_cols)

with tabs[3]:
    st.subheader("Pitchers to Attack Today")
    st.caption("Attackability board emphasizing HR/9, barrel allowed, hard contact allowed, park/weather carry, and matchup vulnerability.")
    pitcher_targets = get_pitchers_to_target(locked_df)
    display_existing_columns(
        pitcher_targets,
        ["Game", "Pitcher", "HR Attackability Score", "Pitcher_HR9_Last7", "Pitcher_Barrel_Allowed", "Pitcher_HardHit_Allowed", "WeatherNote", "TempF", "WindMPH"]
    )

with tabs[4]:
    st.subheader("HR Combo Command Center")
    st.caption(
        "Display-only decision layer over the existing combo engine. "
        "Combo generation, player selection, scores, tracking, and results are not recalculated here."
    )

    active_combo_count = len(combo_board) if combo_board is not None else 0
    active_combo_ids = set()
    if combo_board is not None and not combo_board.empty:
        for _, combo_row in combo_board.iterrows():
            active_legs = [
                value.strip()
                for value in str(combo_row.get("Players", "")).split("|")
                if value.strip()
            ]
            active_combo_ids.add(
                f"{today_str()}-{len(active_legs)}L-{_combo_signature(active_legs)}"
            )

    active_combo_history = pd.DataFrame()
    if combo_tracker is not None and not combo_tracker.empty and active_combo_ids:
        active_combo_history = combo_tracker[
            combo_tracker["combo_id"].astype(str).isin(active_combo_ids)
        ].copy()

    active_full_hits = (
        int(active_combo_history["result_state"].astype(str).eq("FULL_HIT").sum())
        if not active_combo_history.empty else 0
    )
    active_partial_hits = (
        int(
            (
                pd.to_numeric(active_combo_history["legs_hit"], errors="coerce").fillna(0).gt(0)
                & ~active_combo_history["result_state"].astype(str).eq("FULL_HIT")
            ).sum()
        )
        if not active_combo_history.empty else 0
    )

    all_time_full_hits = 0
    all_time_finished = 0
    all_time_partial = 0
    if combo_tracker is not None and not combo_tracker.empty:
        _combo_states = combo_tracker["result_state"].fillna("").astype(str).str.upper()
        all_time_full_hits = int(_combo_states.eq("FULL_HIT").sum())
        all_time_finished = int(
            _combo_states.isin(["FULL_HIT", "PARTIAL_HIT", "MISS", "FINAL_MISS"]).sum()
        )
        _legs_hit = pd.to_numeric(combo_tracker["legs_hit"], errors="coerce").fillna(0)
        all_time_partial = int((_legs_hit.gt(0) & ~_combo_states.eq("FULL_HIT")).sum())

    combo_hit_rate = (
        round((all_time_full_hits / all_time_finished) * 100, 1)
        if all_time_finished else 0.0
    )

    status_text = (
        "No tracked combo has completed as a full hit yet."
        if all_time_full_hits == 0
        else f"{all_time_full_hits} tracked combo{'s' if all_time_full_hits != 1 else ''} completed as full hits."
    )
    st.markdown(
        f"""
        <div class="bf-combo-status">
            <div>
                <strong>Combo performance is now shown honestly</strong>
                <span>{escape(status_text)} Historical full-hit rate: {combo_hit_rate:.1f}% across {all_time_finished} finalized tracked combos.</span>
            </div>
            <div class="bf-combo-zero">{all_time_full_hits} FULL HITS · {all_time_partial} PARTIALS</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Combos", active_combo_count)
    m2.metric("Active Full Hits", active_full_hits)
    m3.metric("Active Partial Hits", active_partial_hits)
    m4.metric("Historical Full-Hit Rate", f"{combo_hit_rate:.1f}%")

    if combo_board is None or combo_board.empty:
        st.info("No combos currently clear the engine's requirements.")
    else:
        combo_view = combo_board.copy()
        for _col in [
            "Avg Leg HR %", "Weakest Leg HR %", "Weakest Leg Quality", "Combined Score"
        ]:
            combo_view[_col] = pd.to_numeric(combo_view.get(_col), errors="coerce").fillna(0.0)

        combo_view["_leg_count"] = (
            combo_view["Combo Type"].astype(str).str.extract(r"(\d+)")[0]
            .pipe(pd.to_numeric, errors="coerce").fillna(99)
        )
        # Display-only labels. They do not feed back into combo generation.
        combo_view["_model_value"] = (
            combo_view["Combined Score"] / combo_view["_leg_count"].clip(lower=1)
        )
        combo_view["_safety"] = (
            combo_view["Weakest Leg HR %"] * 0.55
            + combo_view["Weakest Leg Quality"] * 0.45
        )

        two_leg_pool = combo_view[combo_view["_leg_count"].eq(2)].copy()
        take_pool = two_leg_pool if not two_leg_pool.empty else combo_view
        best_take = take_pool.sort_values(
            ["_safety", "Combined Score"], ascending=[False, False]
        ).iloc[0]
        best_value = combo_view.sort_values(
            ["_model_value", "Weakest Leg Quality"], ascending=[False, False]
        ).iloc[0]
        safest = combo_view.sort_values(
            ["Weakest Leg HR %", "Weakest Leg Quality", "Combined Score"],
            ascending=[False, False, False],
        ).iloc[0]

        def _combo_pick_html(css_class, kicker, row, detail):
            return (
                f'<div class="bf-combo-pick {css_class}">'
                f'<small>{escape(kicker)}</small>'
                f'<strong>{escape(str(row.get("Combo Label", "—")))}</strong>'
                f'<span>{escape(detail)}</span>'
                f'</div>'
            )

        pick_html = "".join([
            '<div class="bf-combo-picks">',
            _combo_pick_html(
                "featured", "BEST COMBO TO CONSIDER", best_take,
                f"{best_take.get('Combo Type','')} · weakest leg {best_take.get('Weakest Leg HR %',0):.0f}% · quality {best_take.get('Weakest Leg Quality',0):.0f}"
            ),
            _combo_pick_html(
                "value", "BEST MODEL VALUE", best_value,
                f"Score per leg {best_value.get('_model_value',0):.1f} · combined score {best_value.get('Combined Score',0):.1f}"
            ),
            _combo_pick_html(
                "safe", "STRONGEST FLOOR", safest,
                f"Weakest leg {safest.get('Weakest Leg HR %',0):.0f}% · weakest quality {safest.get('Weakest Leg Quality',0):.0f}"
            ),
            '</div>',
        ])
        st.markdown(pick_html, unsafe_allow_html=True)
        st.caption(
            "“Best Model Value” is a BF Data score-per-leg comparison, not sportsbook expected value. "
            "Odds are not available in this app."
        )

        for combo_type in ["2-Leg", "3-Leg", "4-Leg", "5-Leg"]:
            cdf = combo_view[combo_view["Combo Type"] == combo_type].copy()
            if cdf.empty:
                continue
            cdf = cdf.sort_values(
                ["_safety", "Combined Score"], ascending=[False, False]
            ).reset_index(drop=True)

            risk_note = {
                "2-Leg": "Most practical",
                "3-Leg": "Higher variance",
                "4-Leg": "Longshot only",
                "5-Leg": "Extreme longshot",
            }.get(combo_type, "")

            st.markdown(
                f'<div class="bf-combo-section"><strong>{combo_type} HR Combos</strong>'
                f'<span>{risk_note} · ranked by weakest-leg floor, then combined score</span></div>',
                unsafe_allow_html=True,
            )

            rows_html = []
            for idx, row in cdf.iterrows():
                label = str(row.get("Combo Label", "—"))
                tag = "TOP CHOICE" if idx == 0 else f"OPTION {idx + 1}"
                rows_html.append(
                    '<div class="bf-combo-card">'
                    f'<div class="bf-combo-cell bf-combo-rank"><small>#</small><strong>{idx + 1}</strong></div>'
                    f'<div class="bf-combo-cell bf-combo-label"><small>COMBO</small><strong>{escape(label)}</strong><span class="bf-combo-tag">{tag}</span></div>'
                    f'<div class="bf-combo-cell"><small>AVG HR</small><strong>{safe_float(row.get("Avg Leg HR %"),0):.0f}%</strong></div>'
                    f'<div class="bf-combo-cell"><small>WEAKEST</small><strong>{safe_float(row.get("Weakest Leg HR %"),0):.0f}%</strong></div>'
                    f'<div class="bf-combo-cell bf-hide-mobile"><small>QUALITY</small><strong>{safe_float(row.get("Weakest Leg Quality"),0):.0f}</strong></div>'
                    f'<div class="bf-combo-cell bf-hide-narrow bf-hide-mobile"><small>SCORE</small><strong>{safe_float(row.get("Combined Score"),0):.1f}</strong></div>'
                    f'<div class="bf-combo-cell bf-hide-narrow"><small>MODEL VALUE</small><strong>{safe_float(row.get("_model_value"),0):.1f}/leg</strong></div>'
                    f'<div class="bf-combo-cell bf-hide-mobile"><small>GAMES</small><strong>{escape(str(row.get("Games","—")))}</strong></div>'
                    '</div>'
                )
            st.markdown("".join(rows_html), unsafe_allow_html=True)

    if combo_tracker is not None and not combo_tracker.empty:
        with st.expander("Combo audit history"):
            st.caption(
                "Includes prior combo versions and lineup-invalidated combinations. "
                "The history is displayed for accountability and is not used to rewrite today's combo board."
            )
            history_cols = [
                "date", "combo_label", "combo_size", "avg_leg_probability",
                "combined_score", "result_state", "legs_hit", "total_legs"
            ]
            available_history_cols = [c for c in history_cols if c in combo_tracker.columns]
            st.dataframe(
                dedupe_columns(
                    combo_tracker.sort_values(
                        by=["date", "combo_size", "combined_score"],
                        ascending=[False, True, False],
                    )[available_history_cols]
                ),
                use_container_width=True,
                hide_index=True,
            )

with tabs[5]:
    st.subheader("Hits + Runs + RBIs Board")
    st.caption("Confirmed teams freeze once lineups lock. Projected teams can still update.")
    hrr = locked_df.copy().sort_values(
        by=["HRR Score", "LineDrive%", "HardHit%", "GroundBall%"],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)
    hrr.insert(0, "Rank", range(1, len(hrr) + 1))
    st.dataframe(
        hrr[[
            "Rank", "Player", "Team", "Game", "Lineup Spot", "Lineup Source",
            "HRR Score", "GroundBall%", "LineDrive%", "EV", "HardHit%", "Why"
        ]],
        use_container_width=True,
        hide_index=True
    )

with tabs[6]:
    st.subheader("Batter Breakdown")
    st.caption("Projected teams stay live until confirmed. Heavy GB bats are downgraded, not blindly erased unless the profile is truly bad.")
    breakdown = sort_for_hr(locked_df.copy())
    st.dataframe(
        breakdown[[
            "Player", "Team", "Game", "Pitcher", "Lineup Spot", "Lineup Source", "Pitch Mix Mode", "Relevant Pitch Mix",
            "EV", "HardHit%", "FlyBall%", "AIR%", "LaunchAngle", "Recent Trend", "LineDrive%", "GroundBall%", "Barrel%",
            "xSLG", "xwOBA",
            "Pitcher_HR9_Last7", "Pitcher_Barrel_Allowed", "Pitcher_HardHit_Allowed",
            "HR Attackability Score", "HR Attackability Label", "Matchup Advantage Score", "Matchup Advantage", "Ranking Reasons",
            "Statcast Pass", "Strict Statcast", "Recent Form Pass", "Pitcher Attackable",
            "Pitch_Isolation_Valid", "GB Rule", "GB Note", "WeatherNote", "BullpenFatigueNote", "BullpenFatigueScore", "TempF", "WindMPH", "HR Eligible",
            "HR Probability %", "HRR Score", "Why"
        ]],
        use_container_width=True,
        hide_index=True
    )

with tabs[7]:
    render_full_tracker_panel(tracker, key_prefix="active_tracker")

with tabs[8]:
    st.subheader("Lineup Watch")
    st.caption("CONFIRMED appears only when MLB supplies all nine official batting-order positions.")
    lineup_rows=[]
    for g in schedule:
        ac=safe_int(g.get("away_confirmed_count"),0); hc=safe_int(g.get("home_confirmed_count"),0)
        lineup_rows.extend([
            {"Game":g.get("game_key",""),"Team":team_abbr(g.get("away_team","")),"Opposing Starter":g.get("home_pitcher","Starter Pending"),"Confirmed Spots":ac,"Status":"CONFIRMED" if ac>=9 else ("PARTIAL" if ac>0 else "PROJECTED")},
            {"Game":g.get("game_key",""),"Team":team_abbr(g.get("home_team","")),"Opposing Starter":g.get("away_pitcher","Starter Pending"),"Confirmed Spots":hc,"Status":"CONFIRMED" if hc>=9 else ("PARTIAL" if hc>0 else "PROJECTED")},
        ])
    display_existing_columns(pd.DataFrame(lineup_rows),["Game","Team","Opposing Starter","Confirmed Spots","Status"])

with tabs[9]:
    st.subheader("Live Weather")
    st.caption("Hourly game-time forecast, wind direction and speed, and stadium dimensions in a visual field layout.")
    if st.button("Refresh Live Weather", key="refresh_live_weather", use_container_width=True):
        fetch_game_weather_timeline.clear()
        fetch_weather_for_park.clear()
        st.rerun()
    render_live_weather_board(schedule, preliminary=False)

with tabs[10]:
    render_active_tomorrow_preview()

with tabs[11]:
    render_bf_knowledge_center()

with tabs[12]:
    render_today_card(locked_df, combo_board)

with tabs[13]:
    render_market_edge_tab(locked_df, tracker)


for idx, game in enumerate(schedule, start=14):
    with tabs[idx]:
        st.subheader(f"{game['game_key']} — {format_game_time_et(game.get('game_time', ''))}")
        st.caption(
            f"Start: {format_game_time_et(game.get('game_time', ''))}  |  "
            f"Venue: {game['venue']}  |  "
            f"Away starter: {game['away_pitcher']}  |  "
            f"Home starter: {game['home_pitcher']}"
        )

        gdf = locked_df[
            (locked_df["Game"] == game["game_key"])
            & (locked_df["game_pk"] == game.get("game_pk"))
        ].copy()
        away_team = team_abbr(game["away_team"])
        home_team = team_abbr(game["home_team"])

        left, right = st.columns(2)

        with left:
            away_source = gdf[gdf["Team"] == away_team]["Lineup Source"].iloc[0] if not gdf[gdf["Team"] == away_team].empty else "N/A"
            render_team_section_header(away_team, game.get("away_confirmed_count", 0), away_source)
            live_team_hr, team_hrr = get_team_game_view(gdf, game["game_key"], away_team, game.get("game_pk"), doubleheader_assignment_map)
            saved_team_hr = get_saved_game_hr_board(today_str(), game.get("game_pk"), away_team, schedule, doubleheader_assignment_map)
            team_hr = saved_team_hr if not saved_team_hr.empty else live_team_hr
            if not team_hr.empty:
                st.markdown("**Best HR hitters**")
                render_card_grid(team_hr, max_cards=4, columns=1)
                with st.expander("Raw team HR table"):
                    st.dataframe(
                        team_hr[[
                            "Rank", "Player", "Lineup Spot", "Lineup Source", "Statcast Pass",
                            "Strict Statcast", "Recent Form Pass", "Pitcher Attackable", "Actual HR Today", "HR Probability %",
                            "HR Tier", "GroundBall%", "GB Rule", "GB Note", "WeatherNote", "BullpenFatigueNote", "HardHit%", "FlyBall%",
                            "AIR%", "xSLG", "xwOBA", "Barrel%", "Ranking Reasons", "Why"
                        ]],
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.caption("No HR-qualified bats surfaced.")

            st.markdown("**Best Hits + Runs + RBIs**")
            if not team_hrr.empty:
                st.dataframe(
                    team_hrr[[
                        "Player", "Lineup Spot", "Lineup Source", "HRR Score",
                        "GroundBall%", "LineDrive%", "Why"
                    ]].head(5),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.caption("No HRR bats surfaced.")

        with right:
            home_source = gdf[gdf["Team"] == home_team]["Lineup Source"].iloc[0] if not gdf[gdf["Team"] == home_team].empty else "N/A"
            render_team_section_header(home_team, game.get("home_confirmed_count", 0), home_source)
            live_team_hr, team_hrr = get_team_game_view(gdf, game["game_key"], home_team, game.get("game_pk"), doubleheader_assignment_map)
            saved_team_hr = get_saved_game_hr_board(today_str(), game.get("game_pk"), home_team, schedule, doubleheader_assignment_map)
            team_hr = saved_team_hr if not saved_team_hr.empty else live_team_hr
            if not team_hr.empty:
                st.markdown("**Best HR hitters**")
                render_card_grid(team_hr, max_cards=4, columns=1)
                with st.expander("Raw team HR table"):
                    st.dataframe(
                        team_hr[[
                            "Rank", "Player", "Lineup Spot", "Lineup Source", "Statcast Pass",
                            "Strict Statcast", "Recent Form Pass", "Pitcher Attackable", "Actual HR Today", "HR Probability %",
                            "HR Tier", "GroundBall%", "GB Rule", "GB Note", "WeatherNote", "BullpenFatigueNote", "HardHit%", "FlyBall%",
                            "AIR%", "xSLG", "xwOBA", "Barrel%", "Ranking Reasons", "Why"
                        ]],
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.caption("No HR-qualified bats surfaced.")

            st.markdown("**Best Hits + Runs + RBIs**")
            if not team_hrr.empty:
                st.dataframe(
                    team_hrr[[
                        "Player", "Lineup Spot", "Lineup Source", "HRR Score",
                        "GroundBall%", "LineDrive%", "Why"
                    ]].head(5),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.caption("No HRR bats surfaced.")
