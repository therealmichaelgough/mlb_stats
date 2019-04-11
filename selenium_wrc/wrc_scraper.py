from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent
import time
import os
import argparse
import platform
import zipfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from graph_server.utilities import retrieve_cached_gameday_report
import datetime
#from graph_server.utilities import FANGRAPHS_COOKIES
from graph_server.utilities import FANGRAPHS_PW
from graph_server.utilities import FANGRAPHS_USERNAME
#from selenium.webdriver.common.action_chains import ActionChains
import pickle


HEADER = "Season,Tm,PA,BB%,K%,BB/K,AVG,OBP,SLG,OPS,ISO,BABIP,wRC,wRAA,wOBA,wRC+"
LINUX_CHROMEDRIVER = "chromedriver_linux"
WINDOWS_CHROMEDRIVER = "chromedriver.exe"
MAC_CHROMEDRIVER = "chromedriver_mac"

DATE_FORMAT = "%Y-%m-%d"

logger = logging.getLogger("WRCScraper")
#logger.setLevel("DEBUG")
hdlr = logging.FileHandler('wrc_scraper.log')
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
#hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

ENABLED_STATS = ["wRC", "wOBA", "wOBA_home", "wOBA_away"]

class WRCScraper:
    #table_xpath = '//*[@id="react-drop-test"]/div[2]/div/div[2]/div/div[1]/table'
    os.chdir("..")
    home = os.getcwd()
    data_dir = os.path.join(home, "data")

    def __init__(self, start_date, end_date=None, sleep_time=None, db_store=None, cookies_pkl="cookies.pkl"):
        if db_store is not None:
            self.db_store = db_store

        self.start_time = time.time()
        self.start_date = start_date.strftime(DATE_FORMAT)
        self.cookies_file_name = cookies_pkl
        self.cookies = self.load_cookies()

        if sleep_time is None:
            sleep_time = 15
        self.sleep_time = sleep_time
        if end_date is None:
            self.end_date = self.start_date
        else:
            self.end_date = end_date.strftime(DATE_FORMAT)

        self.fangraphs_url = "https://www.fangraphs.com/leaders/splits-leaderboards?splitArr=&strgroup=season&statgroup=2&startDate={}&endDate={}&filter=&position=B&statType=team&autoPt=false&players=&pg=0&pageItems=30&sort=9,1&splitArrPitch=&splitTeams=false".format(
            self.start_date, self.end_date)

        self.webdriver_dir = os.path.join(WRCScraper.home, "web_driver")
        #time.sleep(4)
        self.xpaths = {
            "home_button": '//*[@id="react-drop-test"]/div[1]/div[3]/div/div[2]/div[2]/div[1]',
            "sign_in": '//*[@id="linkAccount"]/div/div[1]',
            "username_input": '//*[@id="user_login"]',
            "password_input":'//*[@id="user_pass"]',
            "submit_sign_in": '//*[@id="wp-submit"]',
            "away_button": '//*[@id="react-drop-test"]/div[1]/div[3]/div/div[2]/div[2]/div[2]',
            "standard_tab": '//*[@id="root-buttons-stats"]/div[1]',
            "table": '//*[@id="react-drop-test"]/div[2]/div/div[1]/div/div[1]/table',
            "update_button": '//*[@id="button-update"]',
            "export_data_button": '//*[@id="react-drop-test"]/div[2]/a',
            "no_thanks_button": '//*[@id="my_popup"]/div[3]/a[2]'
        }

        if platform.system() == 'Darwin':

            self.chromedriver_path = os.path.join(self.webdriver_dir, MAC_CHROMEDRIVER)
        elif platform.system() == 'Windows':
            self.chromedriver_path = os.path.join(self.webdriver_dir, WINDOWS_CHROMEDRIVER)
        elif platform.system() == "Linux":
            self.chromedriver_path = os.path.join(self.webdriver_dir, LINUX_CHROMEDRIVER)
        self.download_directory = os.path.join(WRCScraper.data_dir, "tmp",
                                               "{}-{}".format(self.start_date, self.end_date))
        self.initialize_directories()
        self.driver = self.initialize_driver()

        self.download_original_name = "Splits Leaderboard Data .csv"
        self.download_secondary_name = "Splits Leaderboard Data  (1).csv"
        self.wrc_csv_name = WRCScraper.get_csv_name(self.start_date, self.end_date)

    def initialize_directories(self):
        for path in [self.data_dir, self.download_directory]:
            if not os.path.exists(path):
                os.makedirs(path)

    def load_cookies(self):
        try:
            cookies = pickle.load(open(self.cookies_file_name, "rb"))
        except IOError:
            cookies = {}
        return cookies


    @staticmethod
    def get_csv_name(start_date, end_date):
        if end_date is not None:
            end_date = "_" + end_date
        else:
            end_date = ""
        return os.path.join(WRCScraper.data_dir, "wrc_{}.csv".format(start_date + end_date))

    def rename_download(self):
        time.sleep(1)
        logger.debug("saving output file {} to {}".format(
            os.path.join(self.download_directory, self.download_original_name),
            os.path.join(self.data_dir, self.wrc_csv_name)))

        os.rename(os.path.join(self.download_directory, self.download_original_name), os.path.join(self.data_dir, self.wrc_csv_name))
        # file not found

        #os.remove(self.download_directory)

        #    os.rename(os.path.join(WRCScraper.data_dir, self.download_secondary_name), os.path.join(self.data_dir, self.wrc_csv_name))

    def save_empty_csv(self):
        with open(os.path.join(self.download_directory, self.download_original_name), 'w') as blank:
            blank.write(HEADER)

    def unzip_chromedriver(self):
        different_os_chromedrivers = {"Windows": "chromedriver_win32.zip",
                                      "Darwin": "chromedriver_mac64.zip",
                                      "Linux": "chromedriver_linux64.zip"}

        chromedriver_zip_file = os.path.join(self.webdriver_dir, different_os_chromedrivers[platform.system()])

        if not os.path.exists(self.chromedriver_path):
            with zipfile.ZipFile(chromedriver_zip_file, 'r') as zip_ref:
                zip_ref.extractall(self.webdriver_dir)

    def initialize_driver(self):
        #self.unzip_chromedriver()
        #time.sleep(4)

        opts = Options()
        ua = UserAgent()
        random_ua = ua.random
        opts.add_argument(random_ua)
        #opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--load-extension={}".format(os.path.join(self.webdriver_dir, 'adblock')))
        prefs = {"download.default_directory": self.download_directory,
                 "profile.default_content_settings.popups": 0}

        opts.add_experimental_option("prefs", prefs)
        try:
            driver = webdriver.Chrome(self.chromedriver_path, chrome_options=opts)
        except Exception as e:
            raise Exception("{}, {}".format(e, self.__dict__))
        driver.set_page_load_timeout(self.sleep_time)
        driver.get("https://www.fangraphs.com/")

        return driver
        #self.set_cookies()
        #self.state = "login"

    def scrape_all_split(self):
        all_split = []
        try:
            self.driver.get(self.fangraphs_url)
            logger.debug("finding WRC table")
            table = WebDriverWait(self.driver, self.sleep_time).until(
                EC.presence_of_element_located((By.XPATH, self.xpaths["table"]))

            )
            # HEADER =u'# Season Tm PA BB% K% BB/K AVG OBP SLG OPS ISO BABIP wRC wRAA wOBA wRC+'
            for row in table.text.split('\n')[1:]:
                fields = row.split()
                team_name = fields[2]
                wrc = fields[-1]
                woba = fields[-2]
                all_split.append({"team_name": team_name,
                                  "wRC": wrc,
                                  "wOBA": woba
                                  })
        except TimeoutException:
            print "no stats found for {} to {}".format(self.start_date, self.end_date)

        return all_split

    def extract_fields_from_table(self, table, mapping):
        """
        :param table: text from html table. assumed first row is header
        :param mapping: {field_name: column_number}
        :return: list of dictionaries of field names to field values extracted from html according to mapping
        """
        ret = []
        for row in table.text.split('\n')[1:]:
            extracted_row = {}
            fields = row.split()
            for field_name in mapping:
                extracted_row[field_name] = fields[mapping[field_name]]

            ret.append(extracted_row)
        return ret

    def navigate_and_scrape_table(self, navigate_button, mapping):
        split_button = WebDriverWait(self.driver, self.sleep_time).until(
            EC.presence_of_element_located((By.XPATH, self.xpaths[navigate_button+"_button"])))
        #ActionChains(self.driver).move_to_element(split_button).perform()
        #self.driver.execute_script("return arguments[0].scrollIntoView(true);", split_button)
        self.driver.find_element_by_tag_name('body').send_keys(Keys.HOME)
        split_button.click()
        time.sleep(1)
        WebDriverWait(self.driver, self.sleep_time).until(
            EC.presence_of_element_located((By.XPATH, self.xpaths["update_button"]))).click()
        standard_tab = WebDriverWait(self.driver, self.sleep_time).until(
            EC.presence_of_element_located((By.XPATH, self.xpaths["standard_tab"]))
        )
        #self.driver.execute_script("return arguments[0].scrollIntoView(true);", standard_tab)
        standard_tab.click()
        table = WebDriverWait(self.driver, self.sleep_time).until(
            EC.presence_of_element_located((By.XPATH, self.xpaths["table"])))
        return self.extract_fields_from_table(table, mapping)

    def sign_in(self, username, pw):
        self.add_cookies(self.cookies)
        self.driver.get("https://fangraphs.com")
        sign_in_button = WebDriverWait(self.driver, self.sleep_time).until(
            EC.presence_of_element_located((By.XPATH, self.xpaths["sign_in"])))
        if sign_in_button.text == "Sign In" or not self.cookies:
            sign_in_button.click()
            WebDriverWait(self.driver, self.sleep_time).until(
                EC.presence_of_element_located((By.XPATH, self.xpaths["username_input"]))).send_keys(username)
            WebDriverWait(self.driver, self.sleep_time).until(
                EC.presence_of_element_located((By.XPATH, self.xpaths["password_input"]))).send_keys(pw)
            WebDriverWait(self.driver, self.sleep_time).until(
                EC.presence_of_element_located((By.XPATH, self.xpaths["submit_sign_in"]))).click()
            self.add_cookies(self.driver.get_cookies())

    def add_cookies(self, cookies):
        for cookie in cookies:
            self.driver.add_cookie(cookie)
        pickle.dump(cookies, open(self.cookies_file_name, "wb"))

    def scrape_all(self):
        print "scraping dates: {}-{}".format(self.start_date, self.end_date)
        ret = {}
        try:
            try:
                gameday_report = retrieve_cached_gameday_report(
                    datetime.datetime.strptime(self.start_date, DATE_FORMAT))
            except IndexError:
                print "no games played on {}".format(self.start_date)
                raise IndexError

            self.sign_in(username=FANGRAPHS_USERNAME, pw=FANGRAPHS_PW)
            self.driver.get(self.fangraphs_url)
            #self.sign_in()

            scrape_mappings = {"away": {"wOBA": -2, "team_name": 2}, "home": {"wOBA": -2, "team_name": 2}}

            all_table = WebDriverWait(self.driver, self.sleep_time).until(
                EC.presence_of_element_located((By.XPATH, self.xpaths["table"]))
            )

            all_mapping = {"wRC": -1, "team_name": 2, "wOBA": -2}
            ret["all"] = self.extract_fields_from_table(all_table, all_mapping)
            for navigate_button in scrape_mappings:
                i, wait = 3, 1
                unscraped = True
                while i > 0 and unscraped:
                    try:
                        ret[navigate_button] = self.navigate_and_scrape_table(navigate_button, scrape_mappings[navigate_button])
                        unscraped = False
                    except Exception as e:
                        i -= 1
                        try:
                            membership_prompt = WebDriverWait(self.driver, 1).until(
                                EC.presence_of_element_located((By.XPATH, self.xpaths["no_thanks_button"])))
                            membership_prompt.click()
                        except:
                            self.driver.get(self.fangraphs_url)
                        print "failed scraping table: {}: {}. trying {} more times".format(navigate_button, e, i)
                        time.sleep(wait)
                        wait *=2
        except TimeoutException:
            # no table or no page => try again?
            self.driver.quit()
            self.sleep_time *=2
            self.initialize_driver()
            if datetime.datetime.today().date() == datetime.datetime.strptime(self.start_date, DATE_FORMAT).date():
                print "today's games not yet posted"
                return ret
            else:
                print "failed scrape - retrying"
                ret = self.scrape_all()
        except IndexError:
            # no games, return the default
            for split in ["all", "away", "home"]:
                ret[split] = []
        finally:
            self.driver.quit()
            print "finished in {}".format(time.time() - self.start_time)
            return ret


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start_date")
    parser.add_argument("-e", "--end_date")
    parser.add_argument("--sleep_time", required=False, default=10, type=float)
    args = parser.parse_args()
    #start_time = time.time()
    spider = WRCScraper(start_date=args.start_date, end_date=args.end_date, sleep_time=args.sleep_time)
    print "starting web scrape from fangraphs.com"
    spider.scrape_wrc_all()
    time.sleep(1)
    spider.rename_download()
    #spider.update_sqlite_from_csv(db_name=DB_NAME, csv_name=spider.wrc_csv_name)

    # calculate moving averages

    print "generating graph"
    #print "finished in {}s".format(time.time() - start_time)