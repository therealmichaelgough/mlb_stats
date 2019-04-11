import datetime
import mlbgame
from datetime import timedelta

DATE_FORMAT = "%Y-%m-%d"

# these must match the tab names in HTML
ENABLED_STATS = ["wRC_all", "wOBA_all", "wOBA_home", "wOBA_away"]

TEAM_NAMES = {"OAK": "Athletics", "NYY": "Yankees", "SEA": "Mariners", "BOS": "Red Sox", "ATL": "Braves", "TBR": "Rays",
              "HOU": "Astros", "TOR": "Blue Jays", "CHW": "White Sox", "PIT": "Pirates", "LAA": "Angels", "NYM": "Mets",
              "CHC": "Cubs", "LAD": "Dodgers", "ARI": "D-backs", "WSN": "Nationals", "STL": "Cardinals", "MIN": "Twins",
              "DET": "Tigers", "PHI": "Phillies", "KCR": "Royals", "CIN": "Reds", "SFG": "Giants", "SDP": "Padres",
              "CLE": "Indians", "MIL": "Brewers", "TEX": "Rangers", "BAL": "Orioles", "MIA": "Marlins", "COL": "Rockies"}

REVERSE_TEAM_NAMES = {v: k for k, v in TEAM_NAMES.iteritems()}

FANGRAPHS_USERNAME = "Laghezza12"
FANGRAPHS_PW = "mlbmovingaverages"
FANGRAPHS_COOKIES = {"wordpress_logged_in_0cae6f5cb929d209043cb97f8c2eee44":
                         "Laghezza12%7C1586564128%7Ch57nweQ5FehtDIfSD5xli0Dj0zDwJQHLY7AIkiYuBXM%7C927a623ef537b35bd74c3cb5cc9ee7f1187457f86f30fcc851ff4d3567f4d0ee"}

def daterange(start_date, end_date, interval=1):
    """yield an iterator of datetime objects from start date to end date, inclusive, counting by interval, default 1
    :param start_date: datetime object or string
    :param end_date: datetime object or string
    :param interval: integer count by, optional
    :return: a generator of datetime
    """
    try:
        start_date = datetime.datetime.strptime(start_date, DATE_FORMAT)
        end_date = datetime.datetime.strptime(end_date, DATE_FORMAT)
    except TypeError:
        pass

    for n in range(0, int((end_date - start_date).days) + 1, interval):
        yield start_date + datetime.timedelta(n)


def retrieve_team_gameday(team_name, date):
    long_team_name = TEAM_NAMES[team_name]
    compiled_gameday_report = {"opponent": None, "outcome": None, "team_score": None, "opponent_score": None}

    try:
        fetched_gameday_report = retrieve_cached_gameday_report(date, long_team_name)

        if fetched_gameday_report.home_team == long_team_name:
            we_are_home = True
        else:
            we_are_home = False

        outcome = {True: "W", False: "L"}[long_team_name == fetched_gameday_report.w_team]

        opponent_short = REVERSE_TEAM_NAMES[{True: fetched_gameday_report.away_team,
                                             False: fetched_gameday_report.home_team}[we_are_home]]

        team_score = {False: fetched_gameday_report.away_team_runs, True: fetched_gameday_report.home_team_runs}[we_are_home]
        opponent_score = {True: fetched_gameday_report.away_team_runs, False: fetched_gameday_report.home_team_runs}[we_are_home]

        compiled_gameday_report.update({"opponent": opponent_short, "outcome": outcome,
                                        "team_score": team_score, "opponent_score": opponent_score})
    except (IndexError, AttributeError, KeyError):
        print "no gameday report for {} on {}".format(long_team_name, date)

    return compiled_gameday_report


CACHED_GAMEDAY_REPORTS = {}
#TODO CHECK THIS
# getting reports for all teams for a day takes just as long as getting a report for a single team
def retrieve_cached_gameday_report(date, long_team_name=None):
    try:
        all_teams_report = CACHED_GAMEDAY_REPORTS[date]
    except KeyError:
        CACHED_GAMEDAY_REPORTS[date] = {}
        fetched_reports_all_teams_day = mlbgame.games(date.year, date.month, date.day)[0]
        for game_report in fetched_reports_all_teams_day:
            CACHED_GAMEDAY_REPORTS[date].update({game_report.home_team: game_report})
            CACHED_GAMEDAY_REPORTS[date].update({game_report.away_team: game_report})
        all_teams_report = CACHED_GAMEDAY_REPORTS[date]

    if long_team_name is not None:
        try:
            team_report = all_teams_report[long_team_name]
            if team_report.game_status != 'FINAL':
                return None
            return team_report
        except KeyError:
            return None
    else:
        return CACHED_GAMEDAY_REPORTS[date]


