import datetime

DATE_FORMAT = "%Y-%m-%d"

# these must match the tab names in HTML
ENABLED_STATS = ["wRC_all", "wOBA_all", "wOBA_home", "wOBA_away"]

TEAM_NAMES = {"OAK": "Athletics", "NYY": "Yankees", "SEA": "Mariners", "BOS": "Red Sox", "ATL": "Braves", "TBR": "Rays",
              "HOU": "Astros", "TOR": "Blue Jays", "CHW": "White Sox", "PIT": "Pirates", "LAA": "Angels", "NYM": "Mets",
              "CHC": "Cubs", "LAD": "Dodgers", "ARI": "D-backs", "WSN": "Nationals", "STL": "Cardinals", "MIN": "Twins",
              "DET": "Tigers", "PHI": "Phillies", "KCR": "Royals", "CIN": "Reds", "SFG": "Giants", "SDP": "Padres",
              "CLE": "Indians", "MIL": "Brewers", "TEX": "Rangers", "BAL": "Orioles", "MIA": "Marlins", "COL": "Rockies"}

REVERSE_TEAM_NAMES = {v: k for k, v in TEAM_NAMES.iteritems()}

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