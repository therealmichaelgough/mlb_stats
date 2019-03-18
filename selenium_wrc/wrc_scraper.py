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


HEADER = "Season,Tm,PA,BB%,K%,BB/K,AVG,OBP,SLG,OPS,ISO,BABIP,wRC,wRAA,wOBA,wRC+"
LINUX_CHROMEDRIVER = "chromedriver_linux"
WINDOWS_CHROMEDRIVER = "chromedriver.exe"
MAC_CHROMEDRIVER = "chromedriver_mac"

logger = logging.getLogger("WRCScraper")
#logger.setLevel("DEBUG")
hdlr = logging.FileHandler('wrc_scraper.log')
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
#hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

class WRCScraper:
    #table_xpath = '//*[@id="react-drop-test"]/div[2]/div/div[2]/div/div[1]/table'
    table_xpath = '//*[@id="react-drop-test"]/div[2]/div/div[1]/div/div[1]/table'
    export_data_xpath = '//*[@id="react-drop-test"]/div[2]/a'
    os.chdir("..")
    home = os.getcwd()
    data_dir = os.path.join(home, "data")

    def __init__(self, start_date, end_date, sleep_time=None):
        self.start_time = time.time()
        self.start_date = start_date
        if sleep_time is None:
            sleep_time = 10
        self.sleep_time = sleep_time
        if end_date is None:
            self.end_date = self.start_date
        else:
            self.end_date = end_date

        self.wrc_url = "https://www.fangraphs.com/leaders/splits-leaderboards?splitArr=&strgroup=season&statgroup=2&startDate={}&endDate={}&filter=&position=B&statType=team&autoPt=false&players=&pg=0&pageItems=30&sort=9,1&splitArrPitch=&splitTeams=false".format(
            self.start_date, self.end_date)

        self.webdriver_dir = os.path.join(WRCScraper.home, "web_driver")
        #time.sleep(4)

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
        prefs = {"download.default_directory": self.download_directory,
                 "profile.default_content_settings.popups": 0}

        opts.add_experimental_option("prefs", prefs)
        try:
            driver = webdriver.Chrome(self.chromedriver_path, chrome_options=opts)
        except Exception as e:
            raise Exception("{}, {}".format(e, self.__dict__))
        driver.set_page_load_timeout(self.sleep_time)
        return driver
        #self.set_cookies()
        #self.state = "login"

    def scrape_wrc_all(self):
        print "scraping wRC+ for {} to {}".format(self.start_date, self.end_date)

        #print "pausing for page load?"
        #time.sleep(self.sleep_time + 1)

        try:
            self.driver.get(self.wrc_url)
            logger.debug("finding WRC table")
            table = WebDriverWait(self.driver, self.sleep_time).until(
                EC.presence_of_element_located((By.XPATH, self.table_xpath))

            )
            logger.debug("table found: {}".format(table.__dict__))
            export = WebDriverWait(self.driver, self.sleep_time).until(
                EC.presence_of_element_located((By.XPATH, self.export_data_xpath)))
            logger.debug("clicking on export..")
            coordinates = export.location_once_scrolled_into_view  # returns dict of X, Y coordinates
            #self.driver.execute_script('window.scrollTo({}, {});'.format(coordinates['x'], coordinates['y']))

            export.click()
            logger.debug("clicked")
            time.sleep(1)
        except TimeoutException:
            print "no stats found for {} to {}".format(self.start_date, self.end_date)
            self.save_empty_csv()
        except Exception as e:
            raise e
        finally:
            self.driver.quit()
            print "finished in {}".format(time.time() - self.start_time)
            self.rename_download()


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