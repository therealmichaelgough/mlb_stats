import falcon
from waitress import serve
import time
from selenium_wrc.data_interface_layer import DataAdapter
from graph_server.utilities import daterange
from graph_server.utilities import DATE_FORMAT
from graph_server.utilities import TEAM_NAMES
from graph_server.utilities import REVERSE_TEAM_NAMES
from graph_server.utilities import ENABLED_STATS
from falcon.http_status import HTTPStatus
import gviz_api
import os
import jinja2
import datetime
from pyvirtualdisplay import Display
import json
from graph_server.utilities import retrieve_team_gameday
from graph_server.config import INTERVALS
from graph_server.config import GAME_OUTCOMES_KEY
from graph_server.config import WL_COLOR
from graph_server.config import DB_NAME
from graph_server.config import CHART_VAXIS
from graph_server.config import ADDRESS
from graph_server.config import OPENING_DAY


#from profilehooks import profile
#from numpy import cumsum, insert
#from multiprocessing.pool import ThreadPool
#from subprocess import Popen, PIPE
#import pdb
#import logging

#PORT = 80


display = Display(visible=0, size=(1024, 1200))
display.start()

#logging.basicConfig(filename="/waitress.log")
#logger = logging.getLogger('waitress')
#logger.setLevel(logging.DEBUG)

def load_template(name):
    path = os.path.abspath('graph_server/templates')
    with open(os.path.join(os.getcwd(), path, name), 'r') as fp:
        return jinja2.Template(fp.read())


"""embarrassing to make another helper but also I'm too lazy to re-factor"""
def build_google_charts_json_data_table(fetched_team_json):
    """
    :param fetched_team_json: from fetch_stat_by_team
    :return: https://developers.google.com/chart/interactive/docs/reference#dataparam

            {
      cols: [{id: 'A', label: 'NEW A', type: 'string'},
             {id: 'B', label: 'B-label', type: 'number'},
             {id: 'C', label: 'C-label', type: 'date'}
      ],
      rows: [{c:[{v: 'a'},
                 {v: 1.0, f: 'One'},
                 {v: new Date(2008, 1, 28, 0, 31, 26), f: '2/28/08 12:31 AM'}
            ]},
             {c:[{v: 'b'},
                 {v: 2.0, f: 'Two'},
                 {v: new Date(2008, 2, 30, 0, 31, 26), f: '3/30/08 12:31 AM'}
            ]},
             {c:[{v: 'c'},
                 {v: 3.0, f: 'Three'},
                 {v: new Date(2008, 3, 30, 0, 31, 26), f: '4/30/08 12:31 AM'}
            ]}
      ],
      p: {foo: 'hello', bar: 'world!'}
    }

    also eg
    var data = google.visualization.arrayToDataTable
                ([['X', 'Y', {'type': 'string', 'role': 'style'}],
                  [1, 3, null],
                  [2, 2.5, null],
                  [3, 3, null],
                  [4, 4, null],
                  [5, 4, null],
                  [6, 3, 'point { size: 18; shape-type: star; fill-color: #a52714; }'],
                  [7, 2.5, null],
                  [8, 3, null]
            ]);

            fetched_team_json: for date in dates:
            index_by_date["dates"] = [{"game_day": date,
                                    '1_{}'.format(stat_name): float(fetched_team_data['1_{}'.format(stat_name)][date]),
                                }]

                # {"opponent": "str", "team_score": int, "opponent_score": int, "outcome": "W"|"L"}}
                daily_wl = cached_daily_wl.setdefault(date, get_wl_string(date, team_name, db))
                #daily_wl = get_wl_string(date, team_name, db)
                index_by_date[date][GAME_OUTCOMES_KEY] = daily_wl
                add_moving_averages_to_date_object(index_by_date[date], daily_stat, stat_name)


            """
    interval_name_map = {1: "Daily", 7: "Weekly", 15: "15-Day", 30: "30-Day", 60: "60-Day", 120: "120-Day"}

    ret = []
    # "p": {}}
    stat_key = fetched_team_json["stat_name"]
    stat_name = "_".join(stat_key.split("_")[1:])
    header = [{"type": "date", "label": "gameday"}]

    for interval in INTERVALS:
        column_def = {}
        # the series label
        column_def["label"] = "{} {}".format(interval_name_map[interval], stat_name.split("_")[0])
        column_def["id"] = "{}_{}".format(stat_name, interval)
        column_def["type"] = "number"
        header.append(column_def)
        if interval == 1:
            header.append({"type": "string", "role": "style"})
            header.append({"type": "string", "role": "tooltip", 'p': {"html": True}})

    #header.append(json.dumps({"type": "string", "role": "style"}))
    #header.append(json.dumps({"type": "string", "role": "tooltip", "isHtml": True}))

    ret.append(header)

    #ret["cols"].append({"type": "string", "role": "style"})
    #ret["cols"].append({"type": "string", "role": "tooltip", "isHtml": True})

    for date in fetched_team_json["dates"]:
        """
        date_object = {"game_day": date}
        date_object["1_{}".format(stat_name)] = float(fetched_team_data['1_{}'.format(stat_name)][date])
        date_object[GAME_OUTCOMES_KEY] = cached_daily_wl.setdefault(date, get_wl_string(date, team_name, db))
        add_moving_averages_to_date_object(date_object, daily_stat, stat_name)
        """
        row = []
        json_date = "Date({year}, {month}, {day})".format(
            year=date["game_day"].year,
            month=date["game_day"].month - 1,  # to match JS,
            day=date["game_day"].day)
        row.append(json_date)
        for cell_name in ["{}_{}".format(interval, stat_name) for interval in INTERVALS]:
            # float
            try:
                row.append("{}".format(date[cell_name]))  #, 'f': json_date})
            except:
                continue

            # after all columns added for each row, tack on style column attributes
            # {"opponent": "str", "team_score": int, "opponent_score": int, "outcome": "W"|"L"}}
            if cell_name.split("_")[0] == "1":

                game_outcome = date[GAME_OUTCOMES_KEY]
                if game_outcome["outcome"] is not None:

                    outcome_color = WL_COLOR[game_outcome["outcome"]]
                    # 'point { size: 18; shape-type: star; fill-color: #a52714; }'
                    point_style = {"size": 8, "fill-color": outcome_color}
                    row.append("point {{size:{}; fill-color: {};}}".format(8, outcome_color))

                    outcome_tooltip = """
                    <strong>{date}</strong><br>
                    {stat_interval_name} {stat_name}: {stat}<br><br>
                    <strong>Game Outcome</strong>:<br> 
                    <strong>{outcome}</strong> ({our_score}) vs {away_team} ({their_score})
                    """.format(
                        date=date["game_day"].strftime("%m %d %Y"),
                        stat_interval_name=interval_name_map[int(cell_name.split("_")[0])],
                        stat_name=cell_name.split("_")[1],
                        stat=date[cell_name],
                        outcome=game_outcome["outcome"],
                        our_score=game_outcome["team_score"],
                        away_team=game_outcome["opponent"],
                        their_score=game_outcome["opponent_score"]
                    )

                else:
                    row.append("null")
                    outcome_tooltip = """
                    <strong>{date}</strong><br>
                    {stat_interval_name} {stat_name}: {stat}<br><br>
                    <strong>No Game</strong>:<br> 
                    """.format(
                        date=date["game_day"].strftime("%m %d %Y"),
                        stat_interval_name=interval_name_map[int(cell_name.split("_")[0])],
                        stat_name=cell_name.split("_")[1],
                        stat=date[cell_name]
                    )

                row.append(outcome_tooltip)
        ret.append(row)

    return json.dumps(ret)



# generate a list of json which each define a graph in a table row in the web page for one team on all intervals
def populate_gviz_data(start_date, end_date, db):
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

    # a list of dict, each a series belonging to some chart or
    list_of_team_data = []

    print "fulfilling request for dates {} - {}".format(start_date, end_date)
    for stat_name in ENABLED_STATS:
        for team in TEAM_NAMES:
            dict_for_page_rendering = {}
            # all the moving averages for one stat, for one team, over an interval of dates
            stat_team_data = fetch_stat_by_team(start_date, end_date, team, stat_name, db)
            stat_ytd = stat_team_data["ytd_{}".format(stat_name)]
            del stat_team_data["ytd_{}".format(stat_name)]

            #GRAPH_FORMAT[stat_name] = #.LoadData(stat_team_data)
            stat_json = build_google_charts_json_data_table(stat_team_data)
            # comes out as a json string literal for input to google visualization
            #stat_json = GRAPH_FORMAT[stat_name].ToJSon()
            #stat_json = GRAPH_FORMAT[stat_name].ToJSCode("table_name")

            dict_for_page_rendering["stat_data"] = stat_json
            dict_for_page_rendering["team_name"] = team
            dict_for_page_rendering["stat_ytd"] = stat_ytd
            dict_for_page_rendering["stat_name"] = stat_name

            list_of_team_data.append(
                dict_for_page_rendering
            )

    return list_of_team_data


"""db schema:
{'LAA': {
GAME_OUTCOMES_KEY:{datetime.datetime(): {"opponent": "str", "team_score": int, "opponent_score": int, "outcome": "W"|"L"}},
 'name': 'LAA', 
 '1_wRC': {datetime.datetime(2018, 4, 7, 0, 0): '103.15789505901412'}}, '15_wRC': {...}}"""

"""
def get_wl_string(date, team_name, db):
    try:
        if DEBUG_CLEAR_WL:
            raise KeyError
        gameday_report = db[team_name][GAME_OUTCOMES_KEY][date]
        #print "found stored w/l for {} for date {}".format(team_name, date)
    except KeyError:
        print "db miss for team {team_name} on date {date}".format(team_name=team_name, date=date)
        to_update = db[team_name]
        game_outcomes = to_update.setdefault(GAME_OUTCOMES_KEY, {})
        gameday_report = game_outcomes.setdefault(date, retrieve_team_gameday(team_name, date))

        # {date: game_report}
        #to_update = to_update[GAME_OUTCOMES_KEY]

        #to_update.update(retrieve_team_gameday(team_name, date))
        db[team_name] = to_update
        db.commit()
        #gameday_report = db[team_name][GAME_OUTCOMES_KEY][date]

        #{"opponent": opponent_short, "outcome": outcome,
        # "team_score": team_score, "opponent_score": opponent_score}
    return "{outcome} vs {opponent} \n({team_score}-{opponent_score})".format(**gameday_report)
"""

def add_moving_averages_to_date_object(date, stat_name, team_name, run_up_stats):
    '''
    date: e.g. {"game_day" <datetime>, "1_wRC": <float>, "7_wRC": <float>, "game_outcome": {<game_outcome>>}}
    '''
    print "adding {} moving averages for {}...".format(stat_name, team_name)
    stat_key = "1_{}".format(stat_name)
    for interval in INTERVALS[1:]:
        print "interval: {} days".format(interval)
        start_date = date["game_day"] - datetime.timedelta(days=interval)
        lead_up_date_range = (d for d in (start_date + datetime.timedelta(days=n) for n in range((date["game_day"]-start_date).days +1)))
        valid_values_only = []
        for day in lead_up_date_range:
            try:
                valid_values_only.append(run_up_stats[day][team_name][stat_key])
            except KeyError:
                continue
        if valid_values_only:
            average = sum(valid_values_only) / (float(len(valid_values_only)) + 1*pow(10, -10))
            ma_key = '{}_{}'.format(interval, stat_name)
            ma_value = round(average, 2)
            date[ma_key] = ma_value
        #db.update_date(date['game_day'], team_name, {ma_key: ma_value}, )


def get_team_ytd_stat(team_name, dates_this_year, stat_name):
    """get a final average of a stat for a team over all available dates for the current year
    :param end_date: the final date in the averaging period
    :param team_name: 3-letter abbr
    :param stat_name: one of AVAILABLE_STATS
    :param db: data access layer object
    :return: float
    """
    stat_to_date = []
    for date in dates_this_year:
        try:
            stat_to_date.append(float(dates_this_year[date][team_name][stat_name]))
        except KeyError:
            pass
    ytd = sum(stat_to_date) / (float(len(stat_to_date)) + 1*pow(10, -10))
    return round(ytd, 3)


def add_game_outcome_to_date_object(date_object, team_name, db):
    print "fetching outcome for game: {}".format(date_object)
    date = date_object["game_day"]
    game_outcome = retrieve_team_gameday(team_name, date)
    date_object[GAME_OUTCOMES_KEY] = game_outcome
        #db.update_date(date, team_name, {GAME_OUTCOMES_KEY: game_outcome})
    return date_object


def fetch_stat_by_team(start_date, end_date, team_name, stat_name, db):
    '''
    :returns: all the moving averages for one stat, for one team, over an interval of dates
    [ {("game_day", "date", "Game Day"): {
        "1_wRC":  ("number", "Daily wRC+"),
        "15_wRC": ("number", "15-Day wRC+ M.A."),
        "30_wRC": ("number", "15-Day wRC+ M.A."),
        "60_wRC": ("number", "15-Day wRC+ M.A."),
        "120_wRC": ("number", "15-Day wRC+ M.A.")}} ]

        possible stat names: ['wRC_all', 'wOBA_all', 'wOBA_home', 'wOBA_away']

        data storage schema
        db[team_name] -> {stat_key: {date: {}}}
        '''
    index_by_date = {}
    date_list = index_by_date.setdefault("dates", [])
    stat_key = '1_{}'.format(stat_name)
    print "populating {} for {}".format(stat_name, team_name)

    for date in list(daterange(start_date, end_date, 1)):
        if date >= OPENING_DAY and date < datetime.datetime.today():
            print "populating date: {}".format(date)
            # a single date, for a single team. multiple stats: e.g. {"game_day" <datetime>, "1_wRC": <float>, "7_wRC": <float>, "game_outcome": {<game_outcome>>}}
            date_object = db.read_date(date, team_name, stat_name)
            if "1_{}".format(stat_name) not in date_object:
                continue
            date_object = add_game_outcome_to_date_object(date_object, team_name, db)
            date_list.append(date_object)

    stats_run_up = db.get_stat_date_range(daterange(OPENING_DAY, end_date))

    for date_object in date_list:
        add_moving_averages_to_date_object(date_object, stat_name, team_name, stats_run_up)

    ytd = get_team_ytd_stat(team_name, stats_run_up, "1_" + stat_name)
    index_by_date["ytd_{}".format(stat_name)] = ytd
    index_by_date["stat_name"] = stat_key
    return index_by_date


class ServeLandingPage:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = 'text/html'
        template = load_template('get_wrc_graphs.html')
        today = datetime.date.today() - datetime.timedelta(days=1)
        today_string = today.strftime(DATE_FORMAT)
        #yesterday = today - datetime.timedelta(days=1)
        yesterday = OPENING_DAY
        yesterday_sting = yesterday.strftime(DATE_FORMAT)
        resp.body = template.render(today=today_string, yesterday=yesterday_sting, port=PORT, address=ADDRESS)


# endpoint for downloading and saving CSVs
# first download all csv's. then we draw graphs with the saved data
class ServeMLBMA(object):
    super_awesome_cache = {}
    """TODO: from flask import Flask
from flask_caching import Cache

app = Flask(__name__)
# Check Configuring Flask-Caching section for more details
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
...
class Person(db.Model):
    @cache.memoize(50)
    def has_membership(self, role_id):
        return Group.query.filter_by(user=self, role_id=role_id).count() >= 1
    """

    @staticmethod
    def build_ma_page(start_date_param, end_date_param,):
        data_access_object = DataAdapter(sqlite_file=DB_NAME)
        end_date = datetime.datetime.strptime(end_date_param, DATE_FORMAT)
        start_date = datetime.datetime.strptime(start_date_param, DATE_FORMAT)
        # intervals = INTERVALS
        # for interval_length_in_days in intervals:
        #    # for start_day to end_day, get list of [(start_day - interval, start_day), (start_day+1 - interval, start+day+1), ...]
        start_dates = list(daterange(start_date_param, end_date_param, 1))
        # ranges = [
        #    (date - datetime.timedelta(interval_length_in_days), date) for date in start_dates
        #    if date-datetime.timedelta(interval_length_in_days)>=start_dates[0]
        # ]
        #for date in start_dates:
        #    scrape_date(start_date=date)#, end_date=date + datetime.timedelta(days=1))

        page_template = load_template("graphs.html")
        # a list of dictionaries, each of which is {"team_name": "", "stat_name": "", "stat_data": <StatData>}
        # StatData needs to be a json literal of the form
        """
        {
      cols: [{id: 'A', label: 'NEW A', type: 'string'},
             {id: 'B', label: 'B-label', type: 'number'},
             {id: 'C', label: 'C-label', type: 'date'}
      ],
      rows: [{c:[{v: 'a'},
                 {v: 1.0, f: 'One'},
                 {v: new Date(2008, 1, 28, 0, 31, 26), f: '2/28/08 12:31 AM'}
            ]},
             {c:[{v: 'b'},
                 {v: 2.0, f: 'Two'},
                 {v: new Date(2008, 2, 30, 0, 31, 26), f: '3/30/08 12:31 AM'}
            ]},
             {c:[{v: 'c'},
                 {v: 3.0, f: 'Three'},
                 {v: new Date(2008, 3, 30, 0, 31, 26), f: '4/30/08 12:31 AM'}
            ]}
      ],
      p: {foo: 'hello', bar: 'world!'}
    }
        """
        teams_json = populate_gviz_data(start_date, end_date, data_access_object)

        teams_json.sort(key=lambda x: x['team_name'])
        # teams_json = teams_json[:2]

        interval_length_in_days = (end_date - datetime.datetime.strptime(start_date_param, DATE_FORMAT)).days
        # teams_json: a list of dict containing name and chart data for each team

        return page_template.render(teams=teams_json, start_date=start_date_param, end_date=end_date_param, port=PORT,
                                    address=ADDRESS, CHART_VAXIS=CHART_VAXIS,
                                    interval_length_in_days=interval_length_in_days)

    def on_get(self, req, resp):
        """Handles GET requests"""
        #print "{}".format(req)
        #pdb.set_trace()
        start_date_param = req._params.get("start_date")
        end_date_param = req._params.get("end_date")
        resp.status = falcon.HTTP_200  # This is the default status
        resp.content_type = 'text/html'
        #TODO: figure out the correct way to cahce like this
        #resp.body = ServeMLBMA.super_awesome_cache.setdefault("{}->{}".format(start_date_param, end_date_param),
        #                                                      ServeMLBMA.build_ma_page(start_date_param, end_date_param))
        resp.body = ServeMLBMA.build_ma_page(start_date_param, end_date_param)


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