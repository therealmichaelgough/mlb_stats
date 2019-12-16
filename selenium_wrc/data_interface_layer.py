from selenium_wrc.wrc_scraper import WRCScraper
from sqlitedict import SqliteDict
import datetime
import csv
from graph_server.utilities import daterange
from graph_server.utilities import TEAM_NAMES
from graph_server.utilities import retrieve_team_gameday
from graph_server.config import OPENING_DAY

class ScrapeDriver:
    """something to orchestrate scraping
    """

    def launch_crawler(start_date, end_date):

        spider = WRCScraper(start_date=start_date,
                            end_date=end_date)

        print "starting crawl"

        spider.scrape_wrc_all()
        # display.stop()
        # time.sleep(1)
        # spider.rename_download()

    def scrape_date(start_date, end_date=None):
        start_as_string = start_date.date().strftime(DATE_FORMAT)
        if end_date is not None:
            end_as_string = end_date.date().strftime(DATE_FORMAT)
        else:
            end_as_string = start_as_string

        csv_name = WRCScraper.get_csv_name(start_as_string, end_as_string)

        if not os.path.exists(csv_name):
            launch_crawler(start_as_string, end_as_string)
        update_sqlite_from_csv(db_name=DB_NAME, csv_name=csv_name)


class MLBStatsOneDayOneTeam:
    """represents all relevant statistics for a single team on a single date
    {"game_day": datetime, "1_wRC": float, "game_outcome": {game report},
        # "7_wRC": float ..., }
    """
    def __init__(self, team, date, **kwargs):
        self.game_day = date
        self.team_name = team
        for stat_name in kwargs:
            self.stat_name = kwargs[stat_name]

    @staticmethod
    def read_stat_from_db(db_date, team_name, stat_name, db, date):
        """retrieve a team stat for a single team for the given date. if the team or stat isn't there, store it as empty
        :param db_date: a list of team stat dicts for one date
        :param date: datetime object (key for db team stats)
        :return : {"game_day" <datetime>, "1_wRC": <float>, "7_wRC": <float>, "game_outcome": {<game_outcome>>}}
        """
        ret = MLBStatsOneDayOneTeam(team_name, date)
        try:
            team_stats = db_date[team_name]
            for k, v in team_stats.iteritems():
                if stat_name in k:
                    ret[k] = team_stats[k]
        except KeyError:
            print "no team {} for date {}".format(team_name, date)
            pass
        return ret

    def __setitem__(self, key, value):
        self.key = value

    def __getitem__(self, item):
        return self.__dict__[item]

class DataAdapter:
    """
    instances of this class serve as an interface between the web scraper, persistent storage, and presentation layer
    consumers
    """
    """
    schema:
    {'LAA': {'name': 'LAA', '1_wRC': {datetime.datetime(2018, 4, 7, 0, 0): '103.15789505901412'}}, '15_wRC': {...}}
    """

    # def update_sqlite_from_csv(db_name, csv_name):
    #     earliest_day = datetime.datetime.strptime(csv_name[-25:-4].split("_")[0], DATE_FORMAT)
    #     """
    #     #TODO: more robust date exraction
    #     try:
    #
    #         latest_day = datetime.datetime.strptime(csv_name[-25:-4].split("_")[1], DATE_FORMAT)
    #         interval = (latest_day - earliest_day).days
    #     except:
    #         interval = 1
    #     #update_wrc(update_key, db_name, earliest_day)
    #     """
    #
    #     with SqliteDict(db_name) as db:
    #         with open(csv_name, 'r') as csv_file:
    #             reader = csv.DictReader(csv_file)
    #             for row in reader:
    #                 team_name = row["Tm"]
    #                 for stat_name in ENABLED_STATS:
    #                     update_key = "{}_{}".format(1, stat_name)
    #                     # ugly hack
    #                     if stat_name == "wRC":
    #                         new_stat = row[stat_name + "+"]
    #                     else:
    #                         new_stat = row[stat_name]
    #
    #                     if team_name not in db or db[team_name] is None:
    #                         team_data = {"name": team_name, update_key: {earliest_day: new_stat}}
    #                     else:  # team name in db and not None
    #                         team_data = db[team_name]
    #                         if update_key not in team_data:
    #                             team_data[update_key] = {earliest_day: new_stat}
    #                         else:  # update key in team data
    #                             team_data[update_key][earliest_day] = new_stat
    #                     db[team_name] = team_data
    #             db.commit()
    #         db.commit()

    ENABLED_STATS = ["wRC", "wOBA", "wOBA_home", "wOBA_away"]

    TEAM_NAMES = {"OAK": "Athletics", "NYY": "Yankees", "SEA": "Mariners", "BOS": "Red Sox", "ATL": "Braves",
                  "TBR": "Rays",
                  "HOU": "Astros", "TOR": "Blue Jays", "CHW": "White Sox", "PIT": "Pirates", "LAA": "Angels",
                  "NYM": "Mets",
                  "CHC": "Cubs", "LAD": "Dodgers", "ARI": "D-backs", "WSN": "Nationals", "STL": "Cardinals",
                  "MIN": "Twins",
                  "DET": "Tigers", "PHI": "Phillies", "KCR": "Royals", "CIN": "Reds", "SFG": "Giants", "SDP": "Padres",
                  "CLE": "Indians", "MIL": "Brewers", "TEX": "Rangers", "BAL": "Orioles", "MIA": "Marlins",
                  "COL": "Rockies"}

    REVERSE_TEAM_NAMES = {v: k for k, v in TEAM_NAMES.iteritems()}

    GAME_OUTCOMES_KEY = "daily_game_outcomes"
    DATES_INDEX_KEY = "dates_available"

    def __init__(self, sqlite_file):
        self.sqlite_file_name = sqlite_file

    def read_date(self, date, team_name=None, stat_name=None, read_only=False):
        """
        :param date: datetime obj
        :param team_name: 3-letter team abbr
        :param stat_name: key for stat to store. e.g. 1_wRC, 1_wOBA,
        :return: an MLBStatDay object
        """
        ret = {"game_day": date}
        if date < OPENING_DAY or date >= datetime.datetime.today():
            return ret
        with SqliteDict(self.sqlite_file_name) as db:
            try:
                stored_date = db[date]
            except KeyError:
                print "no games stored in DB from {}".format(date)
                if (not read_only) and date < datetime.datetime.today() and \
                        retrieve_team_gameday(team_name, date)['outcome'] is not None:
                    print "fetching valid day {} from fangraphs".format(date)
                    stored_date = self.fetch_and_store(date, db)
                else:
                    print "no scrape - day not valid: {} (ro: {})".format(date, read_only)
                    stored_date = {"game_day": date}
            if team_name is None:
                return stored_date
            try:
                ret.update(stored_date[team_name])
                ret.update({"team_name": team_name})
            except KeyError:
                print "team {} not found in db from day {}".format(team_name, date)
        return ret

    def fetch_and_store(self, date, db):
        # {team_name: {stat_name: stat}}
        csv_list = {}
        while not all(["home" in csv_list, "away" in csv_list, "all" in csv_list]):
            scraper = WRCScraper(start_date=date)
            csv_list = scraper.scrape_all()
            if not csv_list and datetime.datetime.today().date() == date.date():
                break
        all_teams_all_stats_for_day = self.transform_scraped(csv_list)  # type: dict
        for team in all_teams_all_stats_for_day:
            self.update_date(date, team, all_teams_all_stats_for_day[team], db)
        return all_teams_all_stats_for_day

    def update_date(self, date, team, stat_dict, db=None):
        """stores the date object in the database. will not overwrite existing fields unless new values are specified
        :param date: datetime obj
        :param stat_dict: dict of stat names to stat values for one day
        :return:
        """
        close = False
        if db is None:
            db = SqliteDict(self.sqlite_file_name)
            close = True

        #game_day = date["game_day"]
        object_to_update = {"team_name": team, "game_day": date}
        object_to_update.update(stat_dict)
        try:
            existing_date = db[date]
        except KeyError:
            existing_date = {t: {} for t in TEAM_NAMES}
            existing_date.update({"game_day": date})

        team_data = existing_date[team]
        team_data.update(object_to_update)
        #team_data = {team: object_to_update}
        existing_date.update({team: team_data})
        db[date] = existing_date
        db.commit()
        if close:
            db.close()

    def write_date(self, object_to_store, db):
        """stores the date object in the database. will not overwrite existing fields unless new values are specified
        :param date: an MLBStatDay object
        :return:
        """
        pass

    def read_all_dates_in_year(self, year, end_date, team_name, stat_name):
        """
        :param year: yyyy
        :param team_name: 3-letter abbr
        :param stat_name: one of [wRC, wOBA]
        :return: [{"game_day": date, "stat_name": stat_value, ...}, ...]
        """
        year_to_date_days = daterange(OPENING_DAY, end_date)
        return self.get_stat_date_range(year_to_date_days, team_name, stat_name)

    def get_stat_date_range(self, iterable_of_datetime, team_name=None, stat_name=None):
        """
        :param iterable_of_datetime:
        :param team_name:
        :param stat_name:
        :return: list of MLBStatDay
        """
        dates = {}
        print "getting stats on date range"
        for date in iterable_of_datetime:
            print "\t{}".format(date)
            date_read = self.read_date(date, team_name, stat_name, read_only=True)
            dates[date_read['game_day']] = date_read
        return dates

    def write_ytd(self, datetime_obj, team_name, stat_name):
        """
        :param datetime_obj:
        :param team_name:
        :param stat_name:
        :return:
        """

    def transform_scraped(self, csv_list):
        """
        :param csv_list: a dict of lists, one per split, each containing dicts, one per team,
         from the WRCScraper for a single date
        :return: a dict of {team: {stat_name: stat}}
        """
        def find_scraped_team_data(team_name, split_name, stats_list):
            for scraped_team_split in stats_list:
                if scraped_team_split["team_name"] == team_name:
                    return {"1_{}_{}".format(k, split_name): float(v) for k, v in scraped_team_split.iteritems() if k != "team_name"}
            return {}

        scraped = {}
        # if nothing scraped, then there were no games on that day
        for team_name in TEAM_NAMES:
            for split_name, split_stats_list in csv_list.iteritems():
                team_stats = scraped.setdefault(team_name, {})
                team_stats.update(find_scraped_team_data(team_name, split_name, split_stats_list))

        return scraped
