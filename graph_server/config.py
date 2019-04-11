import datetime

ADDRESS = "app.datasleuth.agency/mlb_graphs"
#ADDRESS = "localhost/mlb_graphs"
INTERVALS = [1, 7, 15, 30, 60, 120]

WL_COLOR = {"W": "green", "L": "red"}

CHART_VAXIS = {
    "wRC": {"MAX": 275, "MIN": -30},
    "wOBA": {"MAX": 1, "MIN": -1}
}

DEBUG_CLEAR_WL = False


GAME_OUTCOMES_KEY = "daily_game_outcomes"
DATES_INDEX_KEY = "dates_available"
#GAME_OUTCOMES_TOOLTIP_KEY = "daily_game_outcome_tooltip_string"

DB_NAME = "data/wRC.sqlite"

OPENING_DAY = datetime.datetime(2019, 3, 28)

ENABLED_STATS = ["wRC", "wOBA", "wOBA_home", "wOBA_away"]