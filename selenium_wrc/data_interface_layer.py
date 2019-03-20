from selenium_wrc.wrc_scraper import WRCScraper
from sqlitedict import SqliteDict
import datetime
import csv

ENABLED_STATS = ["wRC", "wOBA", "wOBA_home", "wOBA_away"]

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


class MLBStatDay:
    """represents all relevant statistics for a single team on a single date
    {"game_day": datetime, "1_wRC": float, "game_outcome": {game report},
        # "7_wRC": float ..., }
    """

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

    def write_date(self, date, team_name, stat_name, stat_value):
        """stores the date object and replaces existing
        :param date: an MLBStatDay object
        :return:
        """
        pass

    def read_date(self, date, team_name, stat_name):
        """
        :param date: datetime obj
        :param team_name: 3-letter team abbr
        :param stat_name: key for stat to store. e.g. 1_wRC, 1_wOBA,
        :return: an MLBStatDay object
        """
        with SqliteDict(self.sqlite_file_name) as db:
            try:
                return MLBStatDay(db[date], team_name, stat_name)

            except KeyError:
                scraper = WRCScraper(start_date=date)
                # {team_name: {stat_name: stat}}
                csv_list = scraper.scrape_all()
                all_teams_all_stats_for_day = self.transform_scraped(csv_list)  # type: nested dict
                for team in all_teams_all_stats_for_day:
                    for stat_name in all_teams_all_stats_for_day[team]:
                        to_write = MLBStatDay(team, stat_name, all_teams_all_stats_for_day[team][stat_name])
                        self.update_date(to_write)
        return self.read_date(date, team_name, stat_name)

    def update_date(self, date):
        """stores the date object in the database. will not overwrite existing fields unless new values are specified
        :param date: an MLBStatDay object
        :return:
        """
        pass

    def get_all_dates_in_year(self, year, team_name, stat_name):
        """
        :param year: yyyy
        :param team_name: 3-letter abbr
        :param stat_name: one of [wRC, wOBA]
        :return: [{"game_day": date, "stat_name": stat_value, ...}, ...]
        """
        pass

    def get_stat_date_range(self, iterable_of_datetime, team_name, stat_name):
        """
        :param iterable_of_datetime:
        :param team_name:
        :param stat_name:
        :return: list of MLBStatDay
        """
        #[float(daily_stat[d]) for d in lead_up_date_range if d in daily_stat]

    def read_ytd(self, datetime_obj, team_name, stat_name):
        """
        :param datetime_obj:
        :param team_name:
        :param stat_name:
        :return:
        """

    def write_ytd(self, datetime_obj, team_name, stat_name):
        """
        :param datetime_obj:
        :param team_name:
        :param stat_name:
        :return:
        """

    def transform_scraped(self, csv_list):
        """
        :param csv_list: a list of csv-like objects from the WRCScraper for a single date
        :return: a dict of {team: {stat_name: stat}}
        """
        scraped = {}
        return scraped
