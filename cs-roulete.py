import undetected_chromedriver as uc
from selenium import webdriver

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as expect
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
import webbrowser
import pyautogui
url = "https://csgoempire.com/"
def abc():
    
    from selenium import webdriver

    options = webdriver.ChromeOptions()

    options.add_argument('--user-data-dir=F:/roulete/telegram-integration/profile/')

    options.add_argument('--profile-directory=Profile 8')

    chrome_path="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe %s"
    webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(chrome_path))
    webbrowser.get('chrome').open_new_tab(url)
    print("going to login")
    driver = uc.Chrome(options=options)
    driver.get(url)
    element = WebDriverWait(driver, 10).until(
        lambda x: x.find_element(by=By.XPATH, value="//input[@placeholder='Enter bet amount...']"))
    element.send_keys("0.01")
    bet_buttons = WebDriverWait(driver, 10).until(
        lambda x: x.find_element(by=By.XPATH, value="//span[text()='Place Bet']")
    )
    bet_buttons.click()

    print("done")


abc()
