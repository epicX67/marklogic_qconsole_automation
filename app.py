import os
import time
import warnings
import yaml

from dotenv import load_dotenv
from lxml import etree
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC

# For clipboard access
from tkinter import Tk

os.system('color')
warnings.filterwarnings("ignore", category=DeprecationWarning)
env_file = open(os.path.dirname(
    os.path.realpath(__file__)) + r"/env.yaml", "r")
env = yaml.safe_load(env_file)

HEADLESS = env.get("HEADLESS") if env.get("HEADLESS") != None else False
SIMULATE_SLOWNESS = env.get("SIMULATE_SLOWNESS") if env.get(
    "SIMULATE_SLOWNESS") != None else False
WEBDRIVER = env.get("WEBDRIVER") if env.get("WEBDRIVER") != None else "driver/"
BROWSER = env.get("BROWSER") if env.get("BROWSER") != None else "CHROME"
URL = env.get("ML_CONSOLE_URL") if env.get(
    "ML_CONSOLE_URL") != None else "http://localhost:8000"
USERNAME = env.get("DB_USERNAME") if env.get("DB_USERNAME") != None else "xxxx"
PASSWORD = env.get("DB_PASSWORD") if env.get("DB_PASSWORD") != None else "xxxx"
NS_KEY = env.get("NS_KEY") if env.get("NS_KEY") != None else "xxxx"
NS = env.get("NS") if env.get("NS") != None else "xxxx"


class Log:
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    PASS = '\033[92m'

    @staticmethod
    def info(msg):
        print(f"ML_CLI Info  :: {msg}")

    @staticmethod
    def err(msg):
        print(f"{Log.FAIL}ML_CLI Error :: {msg}{Log.ENDC}")

    @staticmethod
    def warn(msg):
        print(f"{Log.WARNING}ML_CLI Warn  :: {msg}{Log.ENDC}")


class MarkLogicQConsole:

    def __init__(self, configs):
        self.driver = MarkLogicQConsole.__init_driver__(configs)
        self.initialization = self.login(configs)

        self.files = []

        pass

    @staticmethod
    def __init_driver__(configs):
        browser = configs["BROWSER"]
        driver_path = configs["WEBDRIVER"]
        options = None
        driver = None

        if browser == "EDGE":
            options = webdriver.EdgeOptions()
        elif browser == "CHROME":
            options = webdriver.ChromeOptions()
        elif browser == "FIREFOX":
            options = webdriver.FirefoxOptions()
        else:
            options = webdriver.IeOptions()

        if configs["HEADLESS"]:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36"
            options.headless = True
            options.add_argument(f'user-agent={user_agent}')
            options.add_argument("--window-size=1920,1080")
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument("--disable-extensions")
            options.add_argument("--proxy-server='direct://'")
            options.add_argument("--proxy-bypass-list=*")
            options.add_argument("--start-maximized")
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')

        if browser == "EDGE":
            driver = webdriver.Edge(driver_path, options=options)
        elif browser == "CHROME":
            driver = webdriver.Chrome(driver_path, options=options)
        elif browser == "FIREFOX":
            driver = webdriver.Firefox(driver_path, options=options)
        else:
            driver = webdriver.Ie(driver_path, options=options)

        if configs["SIMULATE_SLOWNESS"]:
            driver.set_network_conditions(offline=False,
                                          latency=100,
                                          download_throughput=500 * 1024,
                                          upload_throughput=500 * 1024)

        driver.maximize_window()
        return driver

    def close(self):
        self.driver.close()

    def login(self, configs):
        username = configs["USER"]["USERNAME"]
        password = configs["USER"]["PASSWORD"]
        url = configs["URL"]
        upsetup = f'{username}:{password}@'
        preUrl = url[:url.find('//') + 2]
        postUrl = url[url.find('//') + 2:]

        self.driver.get(preUrl + upsetup + postUrl)
        # self.driver.get(f"http://{username}:{password}@localhost:8000")
        wait(self.driver, 100).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="source-databases"]/option')))

        wait(self.driver, 10).until(
            EC.text_to_be_present_in_element((By.ID, "username"), username))
        user = self.driver.find_elements(By.ID, "username")

        if len(user) == 0:
            Log.err("Login Failed")
            return False
        else:
            Log.info("Login Successful...")
            Log.info(f"Welcome {username}")
            return True

    def is_active(self):
        if not self.initialization:
            Log.err("Not allowed. Exiting...")
            return False

        return True

    def wait_till_busy(self):
        wait(self.driver, 1)
        wait(self.driver, 100).until(
            EC.invisibility_of_element_located((By.ID, "server-side-spinner")))
        return

    def select_database(self, database):
        db_elem = f'//*[@id="source-databases"]/option[text() = "{database}"]'
        if not self.is_active():
            return
        db = None
        try:
            wait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, db_elem)))
            db = self.driver.find_element(By.XPATH,
                                          db_elem)
        except Exception as e:
            print(e)
            Log.err(f"Database [{database}] is not available")
            return False
        else:
            db.click()
            Log.info(f'Database [{database}] selected for operation')
            return True

    def explore(self):
        if not self.is_active():
            return False

        try:
            explore_btn = self.driver.find_element(By.XPATH,
                                                   '//*[@id="explore-source-btn"]')
            explore_btn.click()
            self.wait_till_busy()
            return True
        except Exception:
            return False

    def search(self, search):
        if not self.is_active():
            return False

        self.explore()
        wait(self.driver, 1)

        search_input = self.driver.find_element(By.XPATH,
                                                '//*[@id="filter-by-uri-input"]')
        search_input.send_keys(search)
        search_input.send_keys(Keys.ENTER)
        self.wait_till_busy()
        wait(self.driver, 1)

        files = self.driver.find_elements(By.XPATH,
                                          '//*[@id="explore-results-space"]/table/tbody/tr[not(@class="results-header")]/td[2]/a'
                                          )

        if len(files) == 0:
            Log.warn(f"No match found for this search [{search}]")
            return []

        # Clearing previous search results
        self.files = files

        ret = []
        for file in files:
            ret.append(file.text)

        return ret

    def get_result_list(self):
        files = self.driver.find_elements(By.XPATH,
                                          '//*[@id="explore-results-space"]/table/tbody/tr[not(@class="results-header")]/td[2]/a'
                                          )

        return files

    def get_file(self, fileName):
        self.files = self.get_result_list()

        for file in self.files:
            if file.text == fileName:
                Log.info(f'File [{fileName}] found')
                file.click()

                # Render as text
                try:
                    wait(self.driver, 10).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, '//select[@class="render-as"]')))

                    self.driver.find_element(
                        By.XPATH,
                        '//select[@class="render-as"]/option[@value="text"]'
                    ).click()

                except Exception as e:
                    print(e)
                    return None

                textData = self.driver.find_element(By.XPATH,
                                                    '//div[@id="explore-file-doc"]/*/*[@class="resultItem"]/*/*/code'
                                                    )
                RAW = textData.text

                # Going Back
                self.driver.find_element(By.ID, "button-back").click()

                parser = etree.XMLParser(ns_clean=False)
                xml = etree.fromstring(bytes(RAW, encoding='utf8'), parser)
                return {"fileName": fileName, "xml": xml}

        Log.err(f'File [{fileName}] not found')
        return None

    # New method to get data
    def get_file_n(self, fileName):
        self.files = self.get_result_list()

        for file in self.files:
            if file.text == fileName:
                Log.info(f'File [{fileName}] found')
                file.click()

                # Render as text
                try:
                    wait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.ID, 'explore-edit-doc-btn'))
                    )

                    self.driver.find_element(
                        By.ID,
                        'explore-edit-doc-btn'
                    ).click()

                    wait(self.driver, 10).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, '//*[@id="explore-file-doc"]/div//*[@class="CodeMirror-lines"]')))

                except Exception as e:
                    print(e)
                    return None

                ac = ActionChains(self.driver)
                ac.key_down(Keys.CONTROL).send_keys(
                    'a').key_up(Keys.CONTROL).perform()
                ac.key_down(Keys.CONTROL).send_keys(
                    'c').key_up(Keys.CONTROL).perform()

                RAW = Tk().clipboard_get()
                Tk().clipboard_clear()

                # Going Back
                self.driver.find_element(
                    By.ID, 'explore-cancel-doc-changes-btn').click()
                wait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="button-back" and @class="clickable"]')))
                self.driver.find_element(By.ID, "button-back").click()

                parser = etree.XMLParser(ns_clean=False)
                xml = etree.fromstring(bytes(RAW, encoding='utf8'), parser)
                return {"fileName": fileName, "xml": xml}

        Log.err(f'File [{fileName}] not found')
        return None


class Report:
    def __init__(self):
        self.fileName = []
        self.exists_on_db1 = []
        self.exists_on_db2 = []
        self.target = []
        self.expected = []
        self.got = []
        self.status = []
        self.reason = []
        pass

    def push(self, fileName, db1, db2, target, expected, got):
        self.fileName.append(fileName)
        self.exists_on_db1.append("Yes" if db1 else "No")
        self.exists_on_db2.append("Yes" if db2 else "No")
        self.target.append(target)
        self.expected.append(expected)
        self.got.append(got)

        reason = ""
        status = True

        if not db1:
            reason = "File Not found on first DB"
            status = False

        if not db2:
            reason = "File Not found on second DB"
            status = False

        if expected != got:
            reason = "Different value in both files"
            status = False

        self.status.append("Passed" if status else "Failed")
        self.reason.append(reason)

    def extract(self, path):
        preDf = {
            "File Name": self.fileName,
            "Exists (DB1)": self.exists_on_db1,
            "Exists (DB2)": self.exists_on_db2,
            "Target": self.target,
            "Expected": self.expected,
            "Got": self.got,
            "Status": self.status,
            "Reason": self.reason
        }

        df = pd.DataFrame(preDf)
        writer = pd.ExcelWriter(path, engine='xlsxwriter')
        df.to_excel(writer, index=False)
        writer.close()


def main(db1, db2, search):
    # driver.maximize_window()
    MLCLI = MarkLogicQConsole({
        "HEADLESS": HEADLESS,
        "SIMULATE_SLOWNESS": SIMULATE_SLOWNESS,
        "WEBDRIVER": WEBDRIVER,
        "BROWSER": BROWSER,
        "URL": URL,
        "USER": {
            "USERNAME": USERNAME,
            "PASSWORD": PASSWORD
        }
    })

    subDBFiles = []
    subDBFileData = []
    if MLCLI.select_database(db1):
        subDBFiles = MLCLI.search(search)

    for file in subDBFiles:
        nFile = MLCLI.get_file(file)
        if nFile != None:
            subDBFileData.append(nFile)

    finalDBFiles = []
    finalDBFileData = []
    if MLCLI.select_database(db2):
        finalDBFiles = MLCLI.search(search)

    for file in finalDBFiles:
        nFile = MLCLI.get_file(file)
        if nFile != None:
            finalDBFileData.append(nFile)

    MLCLI.close()

    ns = {NS_KEY: NS}

    report = Report()

    for file in subDBFileData:

        found = False
        for fFile in finalDBFileData:
            if file["fileName"] == fFile["fileName"]:
                found = True

                # Compare XML
                XML1 = file["xml"]
                XML2 = fFile["xml"]
                target = ".//claim:PublicId"

                publicId = XML1.findall(target, ns)[0].text
                publicId2 = XML2.findall(target, ns)[0].text
                print(
                    f'Comparing file [{file["fileName"]}] from both database')
                print(
                    f"Comparing public id of both xmls. [{Log.PASS + 'Passed' + Log.ENDC if publicId == publicId2 else Log.FAIL + 'failed' + Log.ENDC}]"
                )

                if publicId != publicId2:
                    print(
                        f'Expected value :: [{publicId}]\t\tGot :: [{publicId2}]'
                    )

                report.push(file["fileName"], True, True,
                            target, publicId, publicId2)

        if not found:
            print(
                f"File [{Log.FAIL + file['fileName'] + Log.ENDC}] not exists on FinalDB")

            report.push(file["fileName"], True, False,
                        "", "", "")

    timestamp = time.strftime('_%m-%d-%Y_%H%M', time.localtime())
    report.extract(f"report{timestamp}.xlsx")


# start point
main("SubDB", "FinalDB", "/claim*")


# # testing
# MLCLI = MarkLogicQConsole({
#     "HEADLESS": HEADLESS,
#     "SIMULATE_SLOWNESS": SIMULATE_SLOWNESS,
#     "WEBDRIVER": WEBDRIVER,
#     "BROWSER": BROWSER,
#     "URL": URL,
#     "USER": {
#         "USERNAME": USERNAME,
#         "PASSWORD": PASSWORD
#     }
# })

# MLCLI.select_database("SubDB")
# files = MLCLI.search("/claim*")
# print(MLCLI.get_file_n(files[0]))
# # MLCLI.close()
