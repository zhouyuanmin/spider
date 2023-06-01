from selenium.common import exceptions
from selenium import webdriver
from pathlib import Path
from io import StringIO
import traceback
import logging
import random
import xlrd
import json
import time
import sys
import os
import re

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spider.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
from goods.models import Good, ECGood

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
login_password = "/4WM9ZAtB6c8ph6"
gsa_source_level = 3  # gsa网站source最低值

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
    "mfr_part_no": '//*[@id="searchResultTbody"]//tbody/tr[1]/td[1]/span',
    "product_list": '//*[@class="productListControl isList"]/app-ux-product-display-inline',
    "sources": './/span[@align="left"]',
    "item_a": './/div[@class="itemName"]/a',
    "mfr_name": './/div[@class="mfrName"]',
    "product_description": '//div[@heading="Product Description"]/div',
    "description": '//div[@heading="Vendor Description"]/div',
    "gsa_advantage_price": '//table[@role="presentation"]/tbody//strong',
    "zip": '//input[@id="zip"]',
    "search_msrp": '//*[@id="search-container"]//div[@class="css-j7qwjs"]',
    "main_view": '//*[@id="main-view"]/div/div[1]/div/div[1]',
    "coo_divs": '//*[@id="main"]//li',
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


def update_cookies(browser):
    cookies = browser.get_cookies()
    cookies_str = json.dumps(cookies)
    with open(cookies_path, "w") as f:
        f.write(cookies_str)
    return True


def get_dollar(text):
    if "$" not in text:
        logging.error(text)
        raise
    else:
        text = text.replace(",", "")  # 处理逗号
        dollar = float(text.strip("$"))
    return dollar


def get_msrp(text):
    _text = re.findall(r"\$[\d.,]+", text)
    if _text:
        return get_dollar(_text[0])
    logging.error(text)
    return 0


def get_num(text):
    num = re.findall(r"\d+", text)
    if num:
        return int(num[0])
    else:
        logging.error(text)
        raise


def save_error_screenshot(browser, sign, detail):
    time_str = str(int(time.time() * 1000))
    file_name = f"{sign}_{time_str}_{detail}.png"
    file_name = os.path.join(base_dir, "error", file_name)
    browser.get_screenshot_as_file(file_name)


# 业务逻辑函数
def get_data(path, begin_line=0, count=None, part_line=1, manufacturer_line=2):
    excel_data = xlrd.open_workbook(filename=path)
    table = excel_data.sheets()[0]  # 第一个table
    parts = table.col_values(part_line)[begin_line:]  # 第2列
    manufacturers = table.col_values(manufacturer_line)[begin_line:]  # 第3列
    zipped = zip(parts, manufacturers)
    zipped = list(zipped)
    if count:
        zipped = zipped[:count]
    return zipped


def get_data_by_excel(path, begin_row, cols):
    excel_data = xlrd.open_workbook(filename=path)
    table = excel_data.sheets()[0]  # 第一个table
    data = []
    for i in cols:
        data.append(table.col_values(i)[begin_row:])
    return data


def get_model_param_by_ec(browser, part):
    try:
        obj = ECGood.objects.get(part=part)
        return {
            "mfr_part_no": obj.mfr_part_no,
            "vendor_part_no": obj.vendor_part_no,
            "msrp": obj.msrp,
            "federal_govt_spa": obj.federal_govt_spa,
        }
    except ECGood.DoesNotExist:
        # logging.warning(f"part={part},不存在")
        pass
    # 搜索与排序:PriceType=FederalGovtSPA,SortBy=Price(LowToHigh)
    url = f"https://ec.synnex.com/ecx/part/searchResult.html?begin=0&offset=20&keyword={part}&sortField=reference_price&spaType=FG"
    browser.get(url)
    waiting_to_load(browser)

    # 最低价产品(第一个)
    product_items = browser.find_elements_by_xpath(page_elements.get("product_items"))
    if product_items:
        msrp_divs = browser.find_elements_by_xpath(page_elements.get("msrp"))
        if not msrp_divs:
            time.sleep(3)
            msrp_divs = browser.find_elements_by_xpath(page_elements.get("msrp"))
        if msrp_divs:
            msrp = get_dollar(msrp_divs[0].text)
        else:
            save_error_screenshot(browser, "ec", f"{part}_msrp")
            msrp = 0

        federal_govt_spa_divs = browser.find_elements_by_xpath(
            page_elements.get("price_info")
        )
        if not federal_govt_spa_divs:
            time.sleep(3)
            federal_govt_spa_divs = browser.find_elements_by_xpath(
                page_elements.get("price_info")
            )
        if federal_govt_spa_divs:
            federal_govt_spa = get_dollar(federal_govt_spa_divs[0].text)
        else:
            save_error_screenshot(browser, "ec", f"{part}_federal_govt_spa")
            federal_govt_spa = 0

        mfr_part_no_divs = browser.find_elements_by_xpath(
            page_elements.get("mfr_part_no")
        )
        if mfr_part_no_divs:
            mfr_part_no = mfr_part_no_divs[0].text
        else:
            save_error_screenshot(browser, "ec", f"{part}_mfr_part_no")
            mfr_part_no = ""
        vendor_part_no = mfr_part_no
        return {
            "mfr_part_no": mfr_part_no,
            "vendor_part_no": vendor_part_no,
            "msrp": msrp,
            "federal_govt_spa": federal_govt_spa,
        }
    else:
        # 无产品
        return {}


def get_model_param_by_gsa(browser, part):
    # 搜索
    url = f"https://www.gsaadvantage.gov/advantage/ws/search/advantage_search?q=0:8{part}&db=0&searchType=0"
    browser.get(url)
    waiting_to_load(browser)

    product_divs = browser.find_elements_by_xpath(page_elements.get("product_list"))
    if product_divs:
        pass
    else:
        time.sleep(5)
        product_divs = browser.find_elements_by_xpath(page_elements.get("product_list"))

    if product_divs:
        valid_source_urls = []
        first_source_urls = []
        for product_div in product_divs:
            source_divs = product_div.find_elements_by_xpath(
                page_elements.get("sources")
            )
            if not source_divs:  # 有些产品,没有sources
                continue
            source_div = product_div.find_element_by_xpath(page_elements.get("sources"))
            source = get_num(source_div.text)
            url_div = product_div.find_element_by_xpath(page_elements.get("item_a"))
            url = url_div.get_attribute("href")
            product_name = url_div.text
            mfr_name_div = product_div.find_element_by_xpath(
                page_elements.get("mfr_name")
            )
            manufacturer_name = mfr_name_div.text[4:].strip()
            if source >= gsa_source_level:
                valid_source_urls.append([source, url, product_name, manufacturer_name])
            elif not first_source_urls:
                first_source_urls.append([source, url, product_name, manufacturer_name])
        # 排序,取前3
        valid_source_urls = sorted(valid_source_urls, key=lambda x: x[0], reverse=True)
        if len(valid_source_urls) > 3:
            valid_source_urls = valid_source_urls[0:3]

        if not valid_source_urls:  # 如果没有符合要求的,则采集第一个产品
            valid_source_urls = first_source_urls

        gsa_data = []
        # 到详细页采集数据
        for source, url, product_name, manufacturer_name in valid_source_urls:
            browser.get(url)
            waiting_to_load(browser)

            description_divs = browser.find_elements_by_xpath(
                page_elements.get("description")
            )
            if not description_divs:
                waiting_to_load(browser)
                time.sleep(10)
                # 增加判断是否需要邮编,有则跳过
                zip_div = browser.find_elements_by_xpath(page_elements.get("zip"))
                if zip_div:
                    continue
            description_divs = browser.find_elements_by_xpath(
                page_elements.get("description")
            )
            if not description_divs:
                continue

            # 获取Country of Origin（coo）
            coo = ""
            divs = browser.find_elements_by_xpath(page_elements.get("coo_divs"))
            for div in divs:
                text = div.text
                if "Country of Origin" in text:
                    coo = text[18:].strip()

            description_div = browser.find_element_by_xpath(
                page_elements.get("description")
            )
            browser.execute_script(
                "window.scrollTo(0, {})".format(description_div.location.get("y") - 160)
            )
            _description_divs = browser.find_elements_by_xpath(
                page_elements.get("product_description")
            )
            if _description_divs:
                _product_description = _description_divs[0].text
            else:
                _product_description = ""
            waiting_to_load(browser)
            product_description = _product_description + description_div.text
            gsa_advantage_price_divs = browser.find_elements_by_xpath(
                page_elements.get("gsa_advantage_price")
            )[1:]
            gsa_advantage_prices = [0, 0, 0]
            for i, div in enumerate(gsa_advantage_price_divs):
                if i >= 3:  # 0,1,2
                    break
                text = div.text
                if "$" in text:
                    gsa_advantage_prices[i] = get_dollar(text)
            item_data = {
                "source": source,
                "url": url,
                "product_name": product_name,
                "manufacturer_name": manufacturer_name,
                "product_description": product_description,
                "gsa_advantage_price_1": gsa_advantage_prices[0],
                "gsa_advantage_price_2": gsa_advantage_prices[1],
                "gsa_advantage_price_3": gsa_advantage_prices[2],
                "coo": coo,
            }
            gsa_data.append(item_data)
        return gsa_data
    else:
        logging.warning(f"part={part}无产品")
        return []


def get_model_param_by_inm(browser, part):
    url = f"https://usa.ingrammicro.com/cep/app/product/productsearch?displaytitle={part}&keywords={part}&sortBy=relevance&page=1&rowsPerPage=8"
    browser.get(url)
    waiting_to_load(browser)

    # 判断网页是否加载完成
    main_view_divs = []
    for i in range(3):
        main_view_divs = browser.find_elements_by_xpath(page_elements.get("main_view"))
        if main_view_divs:
            break
        else:
            time.sleep(3)
    if not main_view_divs:
        logging.error(f"inm_{part}_load_page")
        save_error_screenshot(browser, "inm", f"{part}_load_page")

    search_msrp_divs = browser.find_elements_by_xpath(page_elements.get("search_msrp"))
    if search_msrp_divs:
        pass
    else:
        time.sleep(5)
        search_msrp_divs = browser.find_elements_by_xpath(
            page_elements.get("search_msrp")
        )
    if search_msrp_divs:
        time.sleep(3)
        text = search_msrp_divs[0].text
        ingram_micro_price = get_msrp(text)
        return {"ingram_micro_price": ingram_micro_price}
    else:
        return {}


def save_to_model(params):
    source = params.pop("source")
    url = params.pop("url")
    note_kv = {"source": source, "url": url}
    params["note"] = json.dumps(note_kv)
    good = Good(**params)
    good.save()


def save_to_model_ec(params):
    ec_good = ECGood(**params)
    ec_good.save()


def save_to_model_inm(part, ingram_micro_price):
    objs = Good.objects.filter(part=part)
    objs.update(ingram_micro_price=ingram_micro_price)


def spider():
    browser_ec = login()
    browser_gsa = create_browser()
    begin = 1
    data = get_data("33411HistoricalSaleSelectedUniqueAllPricesNeeded.xlsx", begin)
    error_count = 0
    index = 1
    for part, manufacturer in data:
        time.sleep(5)  # 基础是10秒每个
        # 处理float数
        if isinstance(part, float):
            part = str(int(part))
        logging.info(
            f"index={index}:{index + begin},part:{part},manufacturer:{manufacturer}"
        )
        index += 1
        try:
            data_ec = get_model_param_by_ec(browser_ec, part)
            data_gsa_list = get_model_param_by_gsa(browser_gsa, part)
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"{part}_{manufacturer}_{int(time.time())}"
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            browser_ec.get_screenshot_as_file(f"{file_name}_ec.png")
            browser_gsa.get_screenshot_as_file(f"{file_name}_gsa.png")
            # 运行出现错误10次
            if error_count >= 10:  # 遇到问题,直接停止
                sys.exit(0)
            else:
                error_count += 1
        else:
            for data_gsa in data_gsa_list:
                param_kvs = {
                    "part": part,
                    "manufacturer": manufacturer,
                }
                param_kvs.update(data_ec)
                param_kvs.update(data_gsa)
                save_to_model(param_kvs)


def spider_ec():
    browser_ec = login()
    data = get_data("productListsQuoteAll.xlsx")
    error_count = 0
    index = 1
    for part, manufacturer in data:
        print(f"index:{index},part:{part},manufacturer:{manufacturer}")
        index += 1
        try:
            data_ec = get_model_param_by_ec(browser_ec, part)
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"{part}_{manufacturer}_{int(time.time())}"
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            browser_ec.get_screenshot_as_file(f"{file_name}_ec.png")
            # 运行出现错误10次
            if error_count >= 0:  # 遇到问题,直接停止
                sys.exit(0)
            else:
                error_count += 1
        else:
            param_kvs = {
                "part": part,
                "manufacturer": manufacturer,
            }
            param_kvs.update(data_ec)
            save_to_model_ec(param_kvs)


def spider_inm():
    browser_inm = create_browser()
    begin = 0
    data = get_data("33411HistoricalSaleSelectedUniqueAllPricesNeeded.xlsx", begin)
    error_count = 0
    index = 1
    for part, manufacturer in data:
        # time.sleep(5)  # 基础是10秒每个
        # 处理float数
        if isinstance(part, float):
            part = str(int(part))
        logging.info(
            f"index={index}:{index + begin},part:{part},manufacturer:{manufacturer}"
        )
        index += 1
        try:
            data_inm = get_model_param_by_inm(browser_inm, part)
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"{part}_{manufacturer}_{int(time.time())}"
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            # browser_inm.get_screenshot_as_file(f"{file_name}_inm.png")
            # 运行出现错误10次
            if error_count >= 10:  # 遇到问题,直接停止
                sys.exit(0)
            else:
                error_count += 1
        else:
            ingram_micro_price = data_inm.get("ingram_micro_price", 0)
            save_to_model_inm(part, ingram_micro_price)


def spider_coo():
    browser = create_browser()
    begin = 1
    data = Good.objects.filter(id__gt=begin)
    for obj in data:
        logging.info(f"id={obj.pk}")
        if obj.coo:  # 已经有了就不用爬取了
            continue
        note = obj.note
        if note:
            url = json.loads(note).get("url")
        else:
            continue

        browser.get(url)
        waiting_to_load(browser)
        time.sleep(3)
        description_divs = browser.find_elements_by_xpath(
            page_elements.get("description")
        )
        if not description_divs:
            waiting_to_load(browser)
            # time.sleep(20)
            # 增加判断是否需要邮编,有则跳过
            zip_div = browser.find_elements_by_xpath(page_elements.get("zip"))
            if zip_div:
                continue
            # browser.get(url)
            # waiting_to_load(browser)
            # time.sleep(3)
        coo = ""
        divs = browser.find_elements_by_xpath(page_elements.get("coo_divs"))
        for div in divs:
            text = div.text
            if "Country of Origin" in text:
                coo = text[18:].strip()
        obj.coo = coo
        obj.save()


def spider_gsa():
    browser_gsa = create_browser()
    begin = 3420
    data = get_data(
        "PCI Brand Q2 GSA Dealer Pricing File 5-1-23TAAOnly爬虫加价格.xlsx",
        begin,
        part_line=2,
        manufacturer_line=0,
    )
    error_count = 0
    index = 1
    for part, manufacturer in data:
        # 处理float数
        if isinstance(part, float):
            part = str(int(part))
        logging.info(
            f"index={index}:{index + begin},part:{part},manufacturer:{manufacturer}"
        )
        index += 1
        try:
            data_gsa_list = get_model_param_by_gsa(browser_gsa, part)
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"{part}_{manufacturer}_{int(time.time())}"
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            browser_gsa.get_screenshot_as_file(f"{file_name}_gsa.png")
            # 运行出现错误10次
            if error_count >= 10:  # 遇到问题,直接停止
                sys.exit(0)
            else:
                error_count += 1
        else:
            for data_gsa in data_gsa_list:
                param_kvs = {
                    "part": part,
                    "manufacturer": manufacturer,
                }
                param_kvs.update(data_gsa)
                save_to_model(param_kvs)


if __name__ == "__main__":
    spider_gsa()
