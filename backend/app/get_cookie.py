from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class Cookie():

    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")

    def get_cookies(self, url):
        driver = webdriver.Chrome(options=self.chrome_options)
        driver.get(url)

        driver.implicitly_wait(5)

        cookies = driver.get_cookies()
        driver.quit()

        cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        return cookies_dict
