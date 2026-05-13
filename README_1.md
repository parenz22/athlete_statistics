# 🏀🏈 Athlete Stat Tracker

A Streamlit app that lets you look up any NBA, WNBA, or NFL player and analyze how they performed against a custom stat threshold across their last 10 games.

---

## Features

- **Multi-sport support** — NBA, WNBA, and NFL
- **Flexible stats** — choose from a dropdown of common stats or type a custom one
- **Threshold analysis** — set any number and instantly see how many of the last 10 games the player exceeded it
- **Visual bar chart** — green bars = over threshold, dark bars = under, with a dotted threshold line
- **Summary cards** — games over threshold (e.g. 7/10), hit rate (70%), and average stat value
- **Game-by-game table** — expandable breakdown with ✅/❌ for each game

---

## Requirements

- Python 3.9+
- See `requirements.txt` for all dependencies

---

## Installation

**1. Clone or download this project**

```bash
git clone https://github.com/yourname/athlete-stat-tracker.git
cd athlete-stat-tracker
```

**2. (Recommended) Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Running the App

```bash
streamlit run athlete_stat_tracker.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

## How to Use

1. **Select a sport** — NBA, WNBA, or NFL from the sidebar dropdown
2. **Type a player name** — e.g. `LeBron James`, `Caitlin Clark`, `Josh Allen`
3. **Choose a stat** — pick from the dropdown or select `Custom...` to type your own
4. **Set a threshold** — e.g. `20` to see games where the player scored over 20 points
5. **Click Analyze** — the chart and summary cards will populate with the last 10 games

---

## Supported Stats

### NBA / WNBA
| Label | API Column |
|---|---|
| Points | PTS |
| Rebounds | REB |
| Assists | AST |
| Steals | STL |
| Blocks | BLK |
| Turnovers | TOV |
| 3-Pointers Made | FG3M |
| Field Goals Made | FGM |
| Free Throws Made | FTM |
| Minutes Played | MIN |
| Plus/Minus | PLUS_MINUS |
| Fantasy Points (PTS+REB+AST) | FANTASY |

### NFL
| Label | Key |
|---|---|
| Passing Yards | pass_yds |
| Passing TDs | pass_td |
| Interceptions | pass_int |
| Rushing Yards | rush_yds |
| Rushing TDs | rush_td |
| Receiving Yards | rec_yds |
| Receptions | rec |
| Receiving TDs | rec_td |

---

## Data Sources

| Sport | Source | API Key Required? |
|---|---|---|
| NBA | [nba_api](https://github.com/swar/nba_api) (official NBA stats) | ❌ No |
| WNBA | [nba_api](https://github.com/swar/nba_api) | ❌ No |
| NFL | ESPN Public API | ❌ No |

> **Note on NFL data:** ESPN's public API works for most active players but coverage can vary for less prominent players or older games. For guaranteed NFL reliability, consider integrating a [SportsRadar](https://developer.sportradar.com/) or [SportsData.io](https://sportsdata.io/) API key.

---

## Custom Stats (Advanced)

Select `Custom...` from the stat dropdown to enter any raw column name from the NBA API or ESPN's response. For NBA, valid column names include anything returned by the `PlayerGameLog` endpoint such as `FG3A`, `OREB`, `DREB`, `PF`, etc.

---

## Project Structure

```
athlete-stat-tracker/
├── athlete_stat_tracker.py   # Main Streamlit app
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## Troubleshooting

**Player not found**
- Double-check spelling — the NBA API requires reasonably close name matches
- For WNBA players, make sure the WNBA option is selected (some players share names with NBA players)

**No data returned for a stat**
- Confirm the stat column name is correct (especially for custom stats)
- Some stats (e.g. blocks for a point guard) may return zeros rather than errors

**NFL player not showing up**
- ESPN search works best with full names — try `Patrick Mahomes` rather than `Mahomes`
- Rookie players or practice squad players may not be indexed

**Rate limiting (NBA API)**
- The app includes a small delay between requests to avoid hitting NBA API rate limits; if you see timeout errors, wait 30 seconds and try again

---

## License

MIT — free to use, modify, and distribute.
