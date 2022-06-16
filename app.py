import os
import warnings

from dotenv import load_dotenv
from lxml import etree

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC

warnings.filterwarnings("ignore", category=DeprecationWarning)
load_dotenv()
HEADLESS = True if os.getenv("HEADLESS") == "True" else False
SIMULATE_SLOWNESS = True if os.getenv("SIMULATE_SLOWNESS") == "True" else False
WEBDRIVER = os.getenv("WEBDRIVER")
BROWSER = os.getenv("BROWSER")
URL = os.getenv("ML_CONSOLE_URL")


class Log:

    @staticmethod
    def info(msg):
        print(f"ML_CLI Info  :: {msg}")

    @staticmethod
    def err(msg):
        print(f"ML_CLI Error :: {msg}")


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
                                          latency=900,
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
        if not self.is_active():
            return
        db = None
        try:
            wait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="source-databases"]/option')))
            db = self.driver.find_element_by_xpath(
                f'//*[@id="source-databases"]/option[text() = "{database}"]')
        except Exception:
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
            explore_btn = self.driver.find_element_by_xpath(
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

        search_input = self.driver.find_element_by_xpath(
            '//*[@id="filter-by-uri-input"]')
        search_input.send_keys(search)
        search_input.send_keys(Keys.ENTER)
        self.wait_till_busy()
        wait(self.driver, 1)

        files = self.driver.find_elements_by_xpath(
            '//*[@id="explore-results-space"]/table/tbody/tr[not(@class="results-header")]/td[2]/a'
        )

        if len(files) == 0:
            Log.info(f"No match found for this search [{search}]")
            return []

        # Clearing previous search results
        self.files = files

        ret = []
        for file in files:
            ret.append(file.text)

        return ret

    def get_result_list(self):
        files = self.driver.find_elements_by_xpath(
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

                textData = self.driver.find_element_by_xpath(
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


def main(db1, db2, search):
    # driver.maximize_window()
    MLCLI = MarkLogicQConsole({
        "HEADLESS": HEADLESS,
        "SIMULATE_SLOWNESS": SIMULATE_SLOWNESS,
        "WEBDRIVER": WEBDRIVER,
        "BROWSER": BROWSER,
        "URL": URL,
        "USER": {
            "USERNAME": os.getenv("DB_USERNAME"),
            "PASSWORD": os.getenv("DB_PASSWORD")
        }
    })

    MLCLI.select_database(db1)
    subDBFiles = MLCLI.search(search)
    subDBFileData = []

    for file in subDBFiles:
        nFile = MLCLI.get_file(file)
        if nFile != None:
            subDBFileData.append(nFile)

    MLCLI.select_database(db2)
    finalDBFiles = MLCLI.search(search)
    finalDBFileData = []

    for file in finalDBFiles:
        nFile = MLCLI.get_file(file)
        if nFile != None:
            finalDBFileData.append(nFile)

    MLCLI.close()

    ns = {os.getenv("NS_KEY"): os.getenv("NS")}

    for file in subDBFileData:

        found = False
        for fFile in finalDBFileData:
            if file["fileName"] == fFile["fileName"]:
                found = True

                # Compare XML
                XML1 = file["xml"]
                XML2 = fFile["xml"]

                publicId = XML1.findall(".//claim:PublicId", ns)[0].text
                publicId2 = XML2.findall(".//claim:PublicId", ns)[0].text
                print(
                    f'Comparing file [{file["fileName"]}] from both database')
                print(
                    f"Comparing public id of both xmls. [{'Passed' if publicId == publicId2 else 'failed'}]"
                )

                if publicId != publicId2:
                    print(
                        f'Expected value :: [{publicId}]\t\tGot :: [{publicId2}]'
                    )
                break

        if not found:
            print(f"File [{file['fileName']}] not exists on FinalDB")


#start point
main("SubDB", "FinalDB", "faf")