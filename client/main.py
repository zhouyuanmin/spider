from selenium.common import exceptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from multiprocessing import Process
from selenium import webdriver
from pathlib import Path
from io import StringIO, BytesIO
from PIL import Image
import traceback
import requests
import logging
import hashlib
import random
import base64
import xlrd
import json
import time
import sys
import os
import re

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - line:%(lineno)d - %(levelname)s: %(message)s",
)

# 全局配置信息
base_dir = Path(__file__).resolve().parent
proxy = "http://127.0.0.1:4780"
window_width, window_height = (1250, 900)  # 需要根据分辨率来确定窗口大小
cookies_path = os.path.join(base_dir, "cookies.txt")
login_email = "lwang@techfocusUSA.com"
login_password = "Uz#.ZeF8WYqJ3im"

# 页面节点
page_elements = {
    "login_email": '//*[@id="inputEmailAddress"]',
    "login_password": '//*[@id="inputPassword"]',
    "login_button": '//*[@id="loginBtn"]',
    # "product_keywords": '//*[@id="searchText"]',
    # "part_search_button": '//*[@id="partSearchBtn"]',
    "product_items": '//*[@id="searchResultTbody"]/tr',
    # "product_href": '//*[@id="searchResultTbody"]/tr[1]/td/strong/a',
    "msrp": '//*[@class="msrp"]/span',
    "price_info": '//*[@class="price-info"]/a',
}


# 业务基础函数
def waiting_to_load(browser, count=10, sleep_time=1):
    """等待页面加载"""
    if sleep_time:
        time.sleep(sleep_time)
    while True:
        status = browser.execute_script("return document.readyState")
        if status == "complete":
            return True
        elif count <= 0:
            return False
        else:
            time.sleep(0.5)
            count -= 1


def scroll_to_bottom(browser, count=None):
    """滚动页面,到页面底部"""
    js = "return action=document.body.scrollHeight"
    height = 0
    new_height = browser.execute_script(js)

    while height < new_height:
        for i in range(height, new_height, 100):
            browser.execute_script("window.scrollTo(0, {})".format(i))
            time.sleep(0.5)
        browser.execute_script("window.scrollTo(0, {})".format(new_height - 1))
        height = new_height
        time.sleep(1)
        new_height = browser.execute_script(js)
        if count is None:
            continue
        else:
            count -= 1
            if count < 0:
                return False
    return True


def get_driver():
    if sys.platform.startswith("win32"):
        driver = os.path.join(base_dir, "chromedriver.exe")
    elif sys.platform.startswith("darwin"):
        driver = os.path.join(base_dir, "chromedriver")
    else:
        logging.error("不支持此类操作系统")
        sys.exit(0)
    return driver


def create_browser():
    global window_width
    global window_height
    options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_setting_values": {"notifications": 1}}
    options.add_experimental_option("prefs", prefs)
    options.add_argument(f"--proxy-server={proxy}")

    driver = get_driver()
    browser = webdriver.Chrome(driver, options=options)
    x, y = random.randint(10, 600), random.randint(10, 20)
    x, y = 20, 20
    browser.set_window_rect(x, y, width=window_width, height=window_height)
    return browser


def login(check=True):
    browser = create_browser()
    try:
        browser.get("https://ec.synnex.com/ecx/login.html")
        waiting_to_load(browser)
    except exceptions.TimeoutException as e:
        logging.warning("打开页面超时,重试一次")
        browser.get("https://ec.synnex.com/ecx/login.html")
        waiting_to_load(browser)

    browser.delete_all_cookies()
    with open(cookies_path, "r") as f:
        cookies_str = f.read()
        cookies = json.loads(cookies_str)
    for cookie in cookies:
        browser.add_cookie(cookie)
    browser.get("https://ec.synnex.com/ecx/landing.html")

    if not waiting_to_load(browser, sleep_time=5):
        browser.get("https://ec.synnex.com/ecx/landing.html")
        waiting_to_load(browser, sleep_time=5)

    if not check:  # 不判断登录状态
        return browser

    # 判断登录状态
    login_buttons = browser.find_elements_by_xpath(page_elements.get("login_email"))
    if login_buttons:
        login_email_textbox = browser.find_element_by_xpath(
            page_elements.get("login_email")
        )
        login_email_textbox.send_keys(login_email)
        login_password_textbox = browser.find_element_by_xpath(
            page_elements.get("login_password")
        )
        login_password_textbox.send_keys(login_password)
        login_button = browser.find_element_by_xpath(page_elements.get("login_button"))
        login_button.click()
        waiting_to_load(browser)
        return browser
    else:
        return browser


def get_dollar(text):
    if "$" not in text:
        raise
    else:
        dollar = float(text.strip("$"))
    return dollar


# 业务逻辑函数
def get_data(path, begin_line=17):
    excel_data = xlrd.open_workbook(filename=path)
    table = excel_data.sheets()[0]  # 第一个table
    parts = table.col_values(1)[begin_line:]  # 第2列
    manufacturers = table.col_values(2)[begin_line:]  # 第3列
    zipped = zip(parts, manufacturers)
    zipped = list(zipped)
    return zipped


def get_model_param_by_ec(browser, part):
    # 搜索与排序:PriceType=FederalGovtSPA,SortBy=Price(LowToHigh)
    url = f"https://ec.synnex.com/ecx/part/searchResult.html?begin=0&offset=20&keyword={part}&sortField=reference_price&spaType=FG"
    browser.get(url)
    waiting_to_load(browser)

    # 最低价产品(第一个)
    product_items = browser.find_elements_by_xpath(page_elements.get("product_items"))
    if product_items:
        msrp_divs = browser.find_elements_by_xpath(page_elements.get("msrp"))
        msrp = get_dollar(msrp_divs[0].text)
        federal_govt_spa_divs = browser.find_elements_by_xpath(
            page_elements.get("price_info")
        )
        federal_govt_spa = get_dollar(federal_govt_spa_divs[0].text)
        return {
            "msrp": msrp,
            "federal_govt_spa": federal_govt_spa,
        }
    else:
        # 无产品
        return {}
