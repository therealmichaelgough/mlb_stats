import falcon
from waitress import serve
import time
from selenium_wrc.wrc_scraper import WRCScraper
from falcon.http_status import HTTPStatus
import gviz_api
import os
import jinja2
from sqlitedict import SqliteDict
import datetime
from pyvirtualdisplay import Display
import csv
import mlbgame
#from profilehooks import profile
#from numpy import cumsum, insert
#from multiprocessing.pool import ThreadPool
#from subprocess import Popen, PIPE
#import pdb
#import logging

#PORT = 80

ADDRESS = "app.datasleuth.agency/mlb_graphs"
#ADDRESS = "localhost/mlb_graphs"
INTERVALS = [1, 7, 15, 30, 60, 120]

CHART_VAXIS = {
    "wRC": {"MAX": 275, "MIN": -30},
    "wOBA": {"MAX": 1, "MIN": -1}
}

DATE_FORMAT = "%Y-%m-%d"

DEBUG_CLEAR_WL = False

ENABLED_STATS = ["wRC", "wOBA"]

TEAM_NAMES = {"OAK": "Athletics", "NYY": "Yankees", "SEA": "Mariners", "BOS": "Red Sox", "ATL": "Braves", "TBR": "Rays",
              "HOU": "Astros", "TOR": "Blue Jays", "CHW": "White Sox", "PIT": "Pirates", "LAA": "Angels", "NYM": "Mets",
              "CHC": "Cubs", "LAD": "Dodgers", "ARI": "D-backs", "WSN": "Nationals", "STL": "Cardinals", "MIN": "Twins",
              "DET": "Tigers", "PHI": "Phillies", "KCR": "Royals", "CIN": "Reds", "SFG": "Giants", "SDP": "Padres",
              "CLE": "Indians", "MIL": "Brewers", "TEX": "Rangers", "BAL": "Orioles", "MIA": "Marlins", "COL": "Rockies"}

REVERSE_TEAM_NAMES = {v: k for k, v in TEAM_NAMES.iteritems()}

GAME_OUTCOMES_KEY = "daily_game_outcomes"
#GAME_OUTCOMES_TOOLTIP_KEY = "daily_game_outcome_tooltip_string"

DB_NAME = "data/wRC.sqlite"

display = Display(visible=0, size=(800, 600))
display.start()

#logging.basicConfig(filename="/waitress.log")
#logger = logging.getLogger('waitress')
#logger.setLevel(logging.DEBUG)

def load_template(name):
    path = os.path.abspath('graph_server/templates')
    with open(os.path.join(os.getcwd(), path, name), 'r') as fp:
        return jinja2.Template(fp.read())


def launch_crawler(start_date, end_date):

    spider = WRCScraper(start_date=start_date,
                        end_date=end_date)

    print "starting crawl"
    spider.scrape_wrc_all()
        #display.stop()
    #time.sleep(1)
    #spider.rename_download()


def daterange(start_date, end_date, interval):
    start_date = datetime.datetime.strptime(start_date, DATE_FORMAT)
    end_date = datetime.datetime.strptime(end_date, DATE_FORMAT)
    for n in range(0, int((end_date - start_date).days) + 1, interval):
        yield start_date + datetime.timedelta(n)


# generate a list of json which each define a graph in a table row in the web page for one team on all intervals
def populate_gviz_data(start_date, end_date):
    """
    :param start_date:
    :param end_date:
    :param intervals: a list of intervals for which to return data
    :return: a list of dict containing name and chart data for each team

    table_description: {('a', 'number'): {'b': 'number', 'c': 'string'}}
    AppendData( data: {1: {'b': 2, 'c': 'z'}, 3: {'b': 4, 'c': 'w'}}
    Table:
    a  b  c
    1  2  z
    3  4  w

    """
    GRAPH_FORMAT = {
        "wRC" : gviz_api.DataTable(table_description={("game_day", "date", "Game Day"): {
            "1_wRC":  ("number", "Daily wRC+"),
            "7_wRC": ("number", "Weekly wRC+"),
            "15_wRC": ("number", "15-Day"),
            "30_wRC": ("number", "30-Day"),
            "60_wRC": ("number", "60-Day"),
            "120_wRC": ("number", "120-Day"),
            GAME_OUTCOMES_KEY: ('string', GAME_OUTCOMES_KEY, {'role': 'tooltip', 'isHtml': True})}}),
        "wOBA": gviz_api.DataTable(table_description={("game_day", "date", "Game Day"): {
            "1_wOBA":  ("number", "Daily wOBA"),
            "7_wOBA": ("number", "Weekly wOBA"),
            "15_wOBA": ("number", "15-Day"),
            "30_wOBA": ("number", "30-Day"),
            "60_wOBA": ("number", "60-Day"),
            "120_wOBA": ("number", "120-Day")}})

    }


    list_of_team_data = []
    for stat_name in ENABLED_STATS:
        for team in TEAM_NAMES:
            dict_for_page_rendering = {}
            stat_team_data = fetch_stat_by_team(start_date, end_date, team, stat_name)
            stat_ytd = stat_team_data["ytd_{}".format(stat_name)]
            del stat_team_data["ytd_{}".format(stat_name)]
            GRAPH_FORMAT[stat_name].LoadData(stat_team_data)
            stat_json = GRAPH_FORMAT[stat_name].ToJSon()
            #stat_json = GRAPH_FORMAT[stat_name].ToJSCode("table_name")

            dict_for_page_rendering["stat_data"] = stat_json
            dict_for_page_rendering["team_name"] = team
            dict_for_page_rendering["stat_ytd"] = stat_ytd
            dict_for_page_rendering["stat_name"] = stat_name

            list_of_team_data.append(
                dict_for_page_rendering
            )

    return list_of_team_data

CACHED_GAMEDAY_REPORTS = {}
#TODO CHECK THIS
# getting reports for all teams for a day takes just as long as getting a report for a single team
def retrieve_cached_gameday_report(date, long_team_name):
    if date in CACHED_GAMEDAY_REPORTS:
        return CACHED_GAMEDAY_REPORTS[date][long_team_name]
    else:
        CACHED_GAMEDAY_REPORTS[date] = {}
        fetched_reports_all_teams_day = mlbgame.games(date.year, date.month, date.day)[0]
        for game_report in fetched_reports_all_teams_day:
            CACHED_GAMEDAY_REPORTS[date].update({game_report.home_team: game_report})
            CACHED_GAMEDAY_REPORTS[date].update({game_report.away_team: game_report})
        return CACHED_GAMEDAY_REPORTS[date][long_team_name]


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
        print "no games for {} on {}".format(long_team_name, date)

    return {date: compiled_gameday_report}


"""db schema:
{'LAA': {
GAME_OUTCOMES_KEY:{datetime.datetime(): {"opponent": "str", "team_score": int, "opponent_score": int, "outcome": "W"|"L"}},
 'name': 'LAA', 
 '1_wRC': {datetime.datetime(2018, 4, 7, 0, 0): '103.15789505901412'}}, '15_wRC': {...}}"""


def get_wl_string(date, team_name, db):
    try:
        if DEBUG_CLEAR_WL:
            raise KeyError
        gameday_report = db[team_name][GAME_OUTCOMES_KEY][date]
        print "found stored w/l for {} for date {}".format(team_name, date)
    except KeyError:
        print "db miss for team {team_name} on date {date}".format(team_name=team_name, date=date)
        to_update = db[team_name]
        # {date: game_report}

        to_update.update({GAME_OUTCOMES_KEY: retrieve_team_gameday(team_name, date)})
        db[team_name] = to_update
        db.commit()
        gameday_report = db[team_name][GAME_OUTCOMES_KEY][date]

        """{"opponent": opponent_short, "outcome": outcome,
         "team_score": team_score, "opponent_score": opponent_score}"""
    return "{outcome} vs {opponent} \n({team_score}-{opponent_score})".format(**gameday_report)


def add_moving_averages_to_date_object(date, daily_stat, stat_name):
    '''
    for ma in INTERVALS[1:] + ["ytd"]:
        if ma == "ytd":
            days_back = len(daily_wrc)
        else:
            days_back = ma
        if '{}_wrc'.format(ma) in date:
            continue
            '''
    for ma in INTERVALS[1:]:
        start_date = date["game_day"] - datetime.timedelta(days=ma)
        #start_date = date["game_day"] - datetime.timedelta(days=days_back)
        lead_up_date_range = (d for d in (start_date + datetime.timedelta(days=n) for n in range((date["game_day"]-start_date).days +1)))
        wrc_over_lead_up = [float(daily_stat[d]) for d in lead_up_date_range if d in daily_stat]
        average = sum(wrc_over_lead_up) / float(len(wrc_over_lead_up))
        date['{}_{}'.format(ma, stat_name)] = round(average,2)

def get_team_ytd_stat(start_date, daily_stat_dict):
    year = start_date.year
    lead_up_date_range = (d for d in daily_stat_dict if d.year == year)
    wrc_over_lead_up = [float(daily_stat_dict[d]) for d in lead_up_date_range if d in daily_stat_dict]
    average = sum(wrc_over_lead_up) / (float(len(wrc_over_lead_up)) + 1*pow(10, -10))
    return round(average, 3)


#TODO: had this been a real project, we'd need to re-map the data interface layer
def fetch_stat_by_team(start_date, end_date, team_name, stat_name):
    '''[ {("game_day", "date", "Game Day"): {
        "1_wRC":  ("number", "Daily wRC+"),
        "15_wRC": ("number", "15-Day wRC+ M.A."),
        "30_wRC": ("number", "15-Day wRC+ M.A."),
        "60_wRC": ("number", "15-Day wRC+ M.A."),
        "120_wRC": ("number", "15-Day wRC+ M.A.")}} ]

        possible stat names: ['wRC', 'wOBA']
        '''

    with SqliteDict(DB_NAME) as db:
        if team_name not in db:
            fetched_team_data = {'name': team_name}
        else:
            fetched_team_data = db[team_name]
        index_by_date = {}
        stat_key = '1_{}'.format(stat_name)

        daily_stat = fetched_team_data[stat_key]

        ytd = get_team_ytd_stat(start_date, daily_stat)
        index_by_date["ytd_{}".format(stat_name)] = ytd

        for date in daily_stat:
            if date > end_date or date < start_date:
                continue
            else:
                index_by_date[date] = {"game_day": date,
                                       '1_{}'.format(stat_name): float(fetched_team_data['1_{}'.format(stat_name)][date]),
                                       }

                # {"opponent": "str", "team_score": int, "opponent_score": int, "outcome": "W"|"L"}}
                daily_wl = get_wl_string(date, team_name, db)
                index_by_date[date][GAME_OUTCOMES_KEY] = daily_wl
                add_moving_averages_to_date_object(index_by_date[date], daily_stat, stat_name)

                #save_the_date(team_name, date, index_by_date)
        return index_by_date


def save_the_date(team_name, date, date_index):
    with SqliteDict(DB_NAME) as db:
        if team_name in db:
            for interval in date_index:
                db[team_name][interval] = date_index[interval]
        db.commit()

"""
schema:
{'LAA': {'name': 'LAA', '1_wRC': {datetime.datetime(2018, 4, 7, 0, 0): '103.15789505901412'}}, '15_wRC': {...}}
"""
def update_sqlite_from_csv(db_name, csv_name):
    #TODO: more robust date exraction
    earliest_day = datetime.datetime.strptime(csv_name[-25:-4].split("_")[0], DATE_FORMAT)
    latest_day = datetime.datetime.strptime(csv_name[-25:-4].split("_")[1], DATE_FORMAT)
    interval = (latest_day - earliest_day).days
    #update_wrc(update_key, db_name, earliest_day)

    with SqliteDict(db_name) as db:
        with open(csv_name, 'r') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                team_name = row["Tm"]
                for stat_name in ENABLED_STATS:
                    update_key = "{}_{}".format(interval, stat_name)
                    # ugly hack
                    if stat_name == "wRC":
                        new_stat = row[stat_name + "+"]
                    else:
                        new_stat = row[stat_name]

                    if team_name not in db or db[team_name] is None:
                        team_data = {"name": team_name, update_key: {earliest_day: new_stat}}
                    else: #team name in db and not None
                        team_data = db[team_name]
                        if update_key not in team_data:
                            team_data[update_key] = {earliest_day: new_stat}
                        else: # update key in team data
                            team_data[update_key][earliest_day] = new_stat
                    db[team_name] = team_data
            db.commit()
        db.commit()


def scrape_date(start_date, end_date):
    start_as_string = start_date.date().strftime(DATE_FORMAT)
    end_as_string = end_date.date().strftime(DATE_FORMAT)
    csv_name = WRCScraper.get_csv_name(start_as_string, end_as_string)

    if not os.path.exists(csv_name):
        launch_crawler(start_as_string, end_as_string)
    update_sqlite_from_csv(db_name=DB_NAME, csv_name=csv_name)


class ServeLandingPage:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = 'text/html'
        template = load_template('get_wrc_graphs.html')
        today = datetime.date.today()
        today_string = today.strftime(DATE_FORMAT)
        yesterday = today - datetime.timedelta(days=1)
        yesterday_sting = yesterday.strftime(DATE_FORMAT)
        resp.body = template.render(today=today_string, yesterday=yesterday_sting, port=PORT, address=ADDRESS)


# endpoint for downloading and saving CSVs
# first download all csv's. then we draw graphs with the saved data
class ServeMLBMA(object):
    def on_get(self, req, resp):
        """Handles GET requests"""
        #print "{}".format(req)
        #pdb.set_trace()
        start_date_param = req._params.get("start_date")
        end_date_param = req._params.get("end_date")
        end_date = datetime.datetime.strptime(end_date_param, DATE_FORMAT)
        #intervals = INTERVALS
        #for interval_length_in_days in intervals:
        #    # for start_day to end_day, get list of [(start_day - interval, start_day), (start_day+1 - interval, start+day+1), ...]
        start_dates = list(daterange(start_date_param, end_date_param, 1))
        #ranges = [
        #    (date - datetime.timedelta(interval_length_in_days), date) for date in start_dates
        #    if date-datetime.timedelta(interval_length_in_days)>=start_dates[0]
        #]
        for date in start_dates:
            scrape_date(start_date=date, end_date=date+datetime.timedelta(days=1))

        resp.status = falcon.HTTP_200  # This is the default status
        resp.content_type = 'text/html'
        page_template = load_template("graphs.html")
        teams_json = populate_gviz_data(datetime.datetime.strptime(start_date_param, DATE_FORMAT), end_date)
        teams_json.sort(key=lambda x: x['team_name'])
        #teams_json = teams_json[:2]

        interval_length_in_days = (end_date - datetime.datetime.strptime(start_date_param, DATE_FORMAT)).days
        # teams_json: a list of dict containing name and chart data for each team
        resp.body = page_template.render(teams=teams_json, start_date=start_date_param, end_date=end_date_param, port=PORT,
                                         address=ADDRESS, CHART_VAXIS=CHART_VAXIS, interval_length_in_days=interval_length_in_days)


class HandleCORS(object):
    def process_request(self, req, resp):
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', '*')
        resp.set_header('Access-Control-Allow-Headers', '*')
        resp.set_header('Access-Control-Max-Age', 1728000)  # 20 days
        if req.method == 'OPTIONS':
            raise HTTPStatus(falcon.HTTP_200, body='\n')


app = falcon.API(middleware=[HandleCORS()])
graph_server = ServeMLBMA()

app.add_route('/mlb_graphs/graph'.format(ADDRESS), ServeMLBMA())
app.add_route('/mlb_graphs'.format(ADDRESS), ServeLandingPage())

if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--port", required=False, default=None)
    args = parser.parse_args()
    if args.port is not None:
        PORT = args.port
    else:
        PORT = 80
    try:
        serve(app, listen='*:{}'.format(PORT), expose_tracebacks=True)
    except Exception as e:
        #print "{}".format()
        raise


    #httpd = simple_server.make_server('127.0.0.1', 8080, app)
    #httpd.serve_forever()