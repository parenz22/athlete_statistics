"""
Athlete Stat Tracker — Streamlit App
Supports: NBA, WNBA, NFL
Shows last 10 games for a player with a stat threshold analysis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from nba_api.stats.endpoints import playergamelog, commonallplayers
from nba_api.stats.static import players as nba_players_static
import time

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Athlete Stat Tracker",
    page_icon="🏀",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0d0d0f;
    color: #f0f0f0;
}

h1, h2, h3 {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 2px;
}

.stApp {
    background: linear-gradient(135deg, #0d0d0f 0%, #12141a 100%);
}

.metric-card {
    background: linear-gradient(135deg, #1a1d27, #22263a);
    border: 1px solid #2e3450;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}

.metric-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #888;
    margin-bottom: 6px;
}

.metric-value {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 42px;
    line-height: 1;
    color: #fff;
}

.metric-sub {
    font-size: 13px;
    color: #aaa;
    margin-top: 4px;
}

.hit { color: #4ade80; }
.miss { color: #f87171; }

.sport-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.badge-nba { background: #1d4ed8; color: #fff; }
.badge-wnba { background: #f97316; color: #fff; }
.badge-nfl { background: #16a34a; color: #fff; }

div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stNumberInput"] label {
    color: #aaa;
    font-size: 12px;
    letter-spacing: 1px;
    text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)


# ── Auto-detect current season ─────────────────────────────────────────────────
def current_nba_season() -> str:
    """Returns the current NBA season string e.g. '2025-26'.
    NBA seasons start in October, so Oct-Dec belong to the new season year."""
    from datetime import date
    today = date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"

def current_wnba_season() -> str:
    """Returns the current WNBA season year string e.g. '2026'.
    WNBA seasons start in May."""
    from datetime import date
    today = date.today()
    return str(today.year if today.month >= 5 else today.year - 1)

def current_nfl_season() -> str:
    """Returns the current NFL season year string e.g. '2025'.
    NFL seasons start in September."""
    from datetime import date
    today = date.today()
    return str(today.year if today.month >= 9 else today.year - 1)

# ── Stat Options ────────────────────────────────────────────────────────────────
NBA_WNBA_STATS = {
    "Points": "PTS",
    "Rebounds": "REB",
    "Assists": "AST",
    "Steals": "STL",
    "Blocks": "BLK",
    "Turnovers": "TOV",
    "3-Pointers Made": "FG3M",
    "Field Goals Made": "FGM",
    "Free Throws Made": "FTM",
    "Minutes Played": "MIN",
    "Plus/Minus": "PLUS_MINUS",
    "Fantasy Points (PTS+REB+AST)": "FANTASY",
}

NFL_STATS_BY_POSITION = {
    "Passing Yards": "pass_yds",
    "Passing TDs": "pass_td",
    "Interceptions": "pass_int",
    "Rushing Yards": "rush_yds",
    "Rushing TDs": "rush_td",
    "Receiving Yards": "rec_yds",
    "Receptions": "rec",
    "Receiving TDs": "rec_td",
}

# ── Helper: NBA/WNBA via nba_api ───────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=86400)  # player IDs don't change, 24hr cache is fine
def get_nba_player_id(name: str, is_wnba: bool = False):
    """Find NBA/WNBA player ID by name (fuzzy)."""
    all_players = nba_players_static.get_players()
    name_lower = name.lower().strip()
    # Exact match first
    for p in all_players:
        if p["full_name"].lower() == name_lower:
            return p["id"], p["full_name"]
    # Partial match
    matches = [p for p in all_players if name_lower in p["full_name"].lower()]
    if matches:
        return matches[0]["id"], matches[0]["full_name"]
    return None, None


def get_nba_last10(player_id: int, stat_col: str, season: str = ""):
    """
    Fetch last 10 games across Regular Season + Play-In + Playoffs.
    Cache key includes the current hour so stale regular-season-only
    results never block playoff data from appearing.
    """
    # Build an hourly cache key — forces re-fetch every hour automatically
    from datetime import datetime
    cache_key = f"{player_id}_{stat_col}_{season}_{datetime.now().strftime('%Y%m%d%H')}"
    return _get_nba_last10_cached(player_id, stat_col, season, cache_key)


@st.cache_data(show_spinner=False, ttl=3600)
def _get_nba_last10_cached(player_id: int, stat_col: str, season: str, _cache_key: str):
    """Internal cached implementation — called with an hourly cache key."""
    season_types = ["Regular Season", "PlayIn", "Playoffs"]
    all_frames = []
    errors = []

    for stype in season_types:
        try:
            time.sleep(0.8)
            log = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season,
                season_type_all_star=stype,
                timeout=30,
                # No custom headers — nba_api ships correct Chrome 145 headers
            )
            frame = log.get_data_frames()[0]
            if not frame.empty:
                frame = frame.copy()
                frame["SEASON_TYPE"] = stype
                all_frames.append(frame)
        except Exception as e:
            errors.append(f"{stype}: {type(e).__name__}: {e}")
            continue

    if not all_frames:
        err_detail = " | ".join(errors) if errors else "Unknown error"
        raise RuntimeError(
            f"No game log data returned for any season type. "
            f"Details: {err_detail}"
        )

    df = pd.concat(all_frames, ignore_index=True)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])

    # Most recent 10 across all types, then oldest→newest for the chart
    df = df.sort_values("GAME_DATE", ascending=False).head(10)
    df = df.sort_values("GAME_DATE", ascending=True).reset_index(drop=True)

    if stat_col == "FANTASY":
        df["FANTASY"] = df["PTS"] + df["REB"] + df["AST"]

    df["LABEL"] = df["MATCHUP"].str.replace(r".*? (vs\.|@) ", r"\1 ", regex=True)
    df["LABEL"] = df.apply(
        lambda r: f"{r['LABEL']}\n{r['GAME_DATE'].strftime('%b %d')}", axis=1
    )
    df[stat_col] = pd.to_numeric(df[stat_col], errors="coerce")
    return df[["GAME_DATE", "LABEL", "MATCHUP", "SEASON_TYPE", stat_col]].dropna()


# ── Helper: NFL via Pro-Football-Reference (sportsreference) ───────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def get_nfl_last10(player_name: str, stat_col: str):
    """
    Fetch NFL game log from Pro-Football-Reference via sportsreference package.
    Falls back to ESPN API if sportsreference is unavailable.
    """
    try:
        from sportsreference.nfl.roster import Player
        from sportsreference.nfl.schedule import Schedule

        # sportsreference needs a player ID — try searching
        # This is a simplified lookup; in production you'd build a name→ID map
        st.warning(
            "NFL data via sportsreference requires the player's PFR ID. "
            "Trying ESPN API fallback..."
        )
    except ImportError:
        pass

    # ── ESPN API fallback (public, no key needed) ──────────────────────────────
    try:
        search_url = (
            f"https://site.api.espn.com/apis/common/v3/search"
            f"?query={requests.utils.quote(player_name)}&sport=football&limit=5"
        )
        r = requests.get(search_url, timeout=10)
        r.raise_for_status()
        results = r.json().get("items", [])
        athlete = next(
            (x for x in results if x.get("type") == "athlete"), None
        )
        if not athlete:
            return None, "Player not found in ESPN search."

        athlete_id = athlete["id"]

        # Game log
        log_url = (
            f"https://site.web.api.espn.com/apis/common/v3/sports/football/nfl"
            f"/athletes/{athlete_id}/gamelog?season={current_nfl_season()}"
        )
        r2 = requests.get(log_url, timeout=10)
        r2.raise_for_status()
        data = r2.json()

        # Parse the table
        labels = data.get("seasonTypes", [])
        events = data.get("events", {})
        categories = data.get("categories", [])

        stat_map = {c["name"]: c["totals"] for c in categories}
        event_list = list(events.values())

        # Find the stat index we need
        espn_stat_map = {
            "pass_yds": "passingYards",
            "pass_td": "passingTouchdowns",
            "pass_int": "interceptions",
            "rush_yds": "rushingYards",
            "rush_td": "rushingTouchdowns",
            "rec_yds": "receivingYards",
            "rec": "receptions",
            "rec_td": "receivingTouchdowns",
        }
        espn_key = espn_stat_map.get(stat_col)

        rows = []
        for ev in event_list[-10:]:
            game_date = ev.get("gameDate", "")[:10]
            opp = ev.get("opponent", {}).get("displayName", "?")
            stats = ev.get("stats", {})
            val = stats.get(espn_key, None)
            if val is not None:
                rows.append({
                    "GAME_DATE": pd.to_datetime(game_date),
                    "LABEL": f"vs {opp}\n{pd.to_datetime(game_date).strftime('%b %d')}",
                    stat_col: float(val),
                })

        if not rows:
            return None, f"No '{espn_key}' data found for this player."

        df = pd.DataFrame(rows).sort_values("GAME_DATE")
        return df, None

    except Exception as e:
        return None, str(e)


# ── Main UI ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:52px; margin-bottom:0'>ATHLETE STAT TRACKER</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#888; margin-top:0; margin-bottom:32px; font-size:14px'>"
    "Last 10 games · Threshold analysis · NBA · WNBA · NFL</p>",
    unsafe_allow_html=True,
)

# ── Sidebar inputs ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Search")

    sport = st.selectbox("Sport", ["NBA", "WNBA", "NFL"])

    player_name = st.text_input("Player Name", placeholder="e.g. LeBron James")

    if sport in ["NBA", "WNBA"]:
        stat_options = list(NBA_WNBA_STATS.keys()) + ["Custom..."]
        stat_choice = st.selectbox("Statistic", stat_options)
        if stat_choice == "Custom...":
            custom_stat = st.text_input(
                "Custom stat column (exact NBA API name)",
                placeholder="e.g. FG3A",
            )
            stat_label = custom_stat
            stat_col = custom_stat.upper()
        else:
            stat_label = stat_choice
            stat_col = NBA_WNBA_STATS[stat_choice]
    else:
        stat_options = list(NFL_STATS_BY_POSITION.keys()) + ["Custom..."]
        stat_choice = st.selectbox("Statistic", stat_options)
        if stat_choice == "Custom...":
            custom_stat = st.text_input("Custom stat key", placeholder="e.g. rec_yds")
            stat_label = custom_stat
            stat_col = custom_stat
        else:
            stat_label = stat_choice
            stat_col = NFL_STATS_BY_POSITION[stat_choice]

    threshold = st.number_input(
        "Threshold (over this value = ✅)",
        min_value=0.0,
        value=20.0,
        step=0.5,
        format="%.1f",
    )

    go_btn = st.button("🔎 Analyze", use_container_width=True, type="primary")

    st.markdown("---")
    if st.button("🔄 Clear Cache & Refresh", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared — search again for live data.")

# ── Analysis ───────────────────────────────────────────────────────────────────
if go_btn:
    if not player_name.strip():
        st.error("Please enter a player name.")
        st.stop()

    with st.spinner(f"Fetching last 10 games for **{player_name}**..."):

        df = None
        error_msg = None
        resolved_name = player_name

        if sport in ["NBA", "WNBA"]:
            player_id, resolved_name = get_nba_player_id(player_name)
            if not player_id:
                error_msg = f"Could not find '{player_name}' in the NBA/WNBA player database."
            else:
                season = current_nba_season() if sport == "NBA" else current_wnba_season()
                try:
                    df = get_nba_last10(player_id, stat_col, season=season)
                    if df is None or df.empty:
                        error_msg = (
                            f"No game log data found for **{resolved_name}** "
                            f"with stat '{stat_col}'. Try a different stat."
                        )
                except RuntimeError as e:
                    error_msg = str(e)
        else:
            df, error_msg = get_nfl_last10(player_name, stat_col)

    if error_msg:
        st.error(error_msg)
        st.stop()

    # ── Compute metrics ────────────────────────────────────────────────────────
    df = df.tail(10).copy()
    stat_values = df[stat_col].tolist()
    games_over = sum(v > threshold for v in stat_values)
    total = len(stat_values)
    pct = games_over / total * 100 if total else 0
    avg_val = sum(stat_values) / total if total else 0
    colors = ["#4ade80" if v > threshold else "#3b4a6b" for v in stat_values]

    # ── Sport badge ────────────────────────────────────────────────────────────
    badge_class = f"badge-{sport.lower()}"
    st.markdown(
        f"<span class='sport-badge {badge_class}'>{sport}</span> &nbsp;"
        f"<span style='color:#aaa; font-size:13px'>{resolved_name}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<h2 style='margin-top:4px'>{stat_label} — Last {total} Games</h2>",
                unsafe_allow_html=True)

    # ── Summary cards ──────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)

    hit_color = "#4ade80" if games_over > total / 2 else "#f87171"

    with c1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Games Over {threshold:g}</div>
            <div class='metric-value' style='color:{hit_color}'>{games_over}/{total}</div>
            <div class='metric-sub'>out of last {total} games</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Hit Rate</div>
            <div class='metric-value' style='color:{hit_color}'>{pct:.0f}%</div>
            <div class='metric-sub'>threshold exceeded</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Avg {stat_label}</div>
            <div class='metric-value'>{avg_val:.1f}</div>
            <div class='metric-sub'>over last {total} games</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Bar chart ──────────────────────────────────────────────────────────────
    labels = df["LABEL"].tolist()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=stat_values,
        marker_color=colors,
        marker_line_color=["#86efac" if v > threshold else "#4a5578" for v in stat_values],
        marker_line_width=1.5,
        text=[f"<b>{v:.0f}</b>" for v in stat_values],
        textposition="outside",
        textfont=dict(color="#fff", size=13, family="DM Sans"),
        hovertemplate="<b>%{x}</b><br>" + stat_label + ": %{y}<extra></extra>",
    ))

    # Threshold line
    fig.add_hline(
        y=threshold,
        line_dash="dot",
        line_color="#facc15",
        line_width=2,
        annotation_text=f"  Threshold: {threshold:g}",
        annotation_font_color="#facc15",
        annotation_font_size=12,
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#ccc"),
        margin=dict(t=40, b=20, l=10, r=10),
        xaxis=dict(
            tickfont=dict(size=11, color="#aaa"),
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=11, color="#aaa"),
            gridcolor="#1e2235",
            zeroline=False,
            title=stat_label,
            title_font=dict(color="#888", size=12),
        ),
        bargap=0.25,
        hoverlabel=dict(
            bgcolor="#1a1d27",
            bordercolor="#3b4a6b",
            font=dict(color="#fff"),
        ),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── Game-by-game table ─────────────────────────────────────────────────────
    with st.expander("📋 Game-by-game breakdown"):
        display_df = df.copy()
        display_df["Date"] = display_df["GAME_DATE"].dt.strftime("%b %d, %Y")
        display_df["Stat"] = display_df[stat_col]
        display_df["Over Threshold?"] = display_df[stat_col].apply(
            lambda v: "✅ Yes" if v > threshold else "❌ No"
        )
        matchup_col = "MATCHUP" if "MATCHUP" in display_df.columns else "LABEL"
        show_cols = ["Date", matchup_col, "Stat", "Over Threshold?"]
        rename_map = {matchup_col: "Matchup", "Stat": stat_label}
        if "SEASON_TYPE" in display_df.columns:
            show_cols.insert(2, "SEASON_TYPE")
            rename_map["SEASON_TYPE"] = "Game Type"
        st.dataframe(
            display_df[show_cols].rename(columns=rename_map),
            use_container_width=True,
            hide_index=True,
        )

else:
    # Landing state
    st.markdown("""
    <div style="
        margin-top: 60px;
        text-align: center;
        color: #444;
        font-size: 15px;
        line-height: 2;
    ">
        <div style="font-size: 56px; margin-bottom: 16px">🏀🏈</div>
        <div style="font-family: 'Bebas Neue', sans-serif; font-size: 28px; color: #555; letter-spacing: 3px">
            ENTER A PLAYER & STAT TO BEGIN
        </div>
        <div style="color: #333; margin-top: 8px">
            NBA · WNBA · NFL &nbsp;|&nbsp; Last 10 games &nbsp;|&nbsp; Threshold analysis
        </div>
    </div>
    """, unsafe_allow_html=True)
