from selenium.common import exceptions
from selenium import webdriver
from pathlib import Path
from io import StringIO
import xlsxwriter
import traceback
import datetime
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
from goods.models import Brand, ECGood, GSAGood

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - line:%(lineno)d - %(levelname)s: %(message)s",
)

# 全局配置信息
base_dir = Path(__file__).resolve().parent
proxy = "http://127.0.0.1:4780"  # 4,5,6,7
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
    "tbody": '//*[@id="resultList"]//tbody',
    # "product_href": '//*[@id="searchResultTbody"]/tr[1]/td/strong/a',
    "msrp": '//*[@class="msrp"]/span',
    "price_info": '//*[@class="price-info"]/a',
    "mfr_part_no": '//*[@id="searchResultTbody"]//tbody/tr[1]/td[1]/span',
    "search": '//*[@id="globalSearch"]',
    "product_list": '//*[@class="productListControl isList"]/app-ux-product-display-inline',
    "sources": './/span[@align="left"]',
    "item_a": './/div[@class="itemName"]/a',
    "mfr_name": './/div[@class="mfrName"]',
    "mfr_part_no_gsa": './/div[@class="mfrPartNumber"]',
    "product_name": '//h4[@role="heading"]',
    "product_description": '//div[@heading="Product Description"]/div',
    "description_strong": '//div[@heading="Vendor Description"]/strong',
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
    # logging.error(text)
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


def save_data_to_excel(path, data):
    work_book = xlsxwriter.Workbook(path)
    work_sheet = work_book.add_worksheet()
    row = 0  # 表头从第行列开始写
    for line in data:
        col = 0
        for value in line:
            work_sheet.write(row, col, value)
            col += 1
        row += 1
    work_book.close()


def get_model_param_by_ec(browser, part, manufacturer=""):
    """自带更新操作"""
    try:
        obj = ECGood.objects.get(part=part)
        if obj.ec_status:
            return
        if obj.federal_govt_spa or obj.msrp:
            obj.ec_status = True
            obj.save()
            return
        # return {}  # 存在则不需要再爬取
        logging.warning(f"EC:part={part},存在,需要更新数据")
    except ECGood.DoesNotExist:
        logging.warning(f"EC:part={part},不存在,需要爬取数据")
        pass
    # 判断是否需要登陆
    login_buttons = browser.find_elements_by_xpath(page_elements.get("login_email"))
    if login_buttons:
        browser.quit()
        logging.error("重新登陆")
        raise  # 抛出异常
    # 搜索与排序:PriceType=FederalGovtSPA,SortBy=Price(LowToHigh)
    url = f"https://ec.synnex.com/ecx/part/searchResult.html?begin=0&offset=20&keyword={part}&sortField=reference_price&spaType=FG"
    browser.get(url)
    time.sleep(5)
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
            # save_error_screenshot(browser, "ec", f"{part}_msrp")
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
            federal_govt_spa = 0

        mfr_part_no_divs = browser.find_elements_by_xpath(
            page_elements.get("mfr_part_no")
        )
        if mfr_part_no_divs:
            mfr_part_no = mfr_part_no_divs[0].text
        else:
            mfr_part_no = ""
        vendor_part_no = mfr_part_no
        # 直接处理
        try:
            obj = ECGood.objects.get(part=part)
        except ECGood.DoesNotExist:
            obj = ECGood(
                part=part,
                # manufacturer=manufacturer,
                mfr_part_no=mfr_part_no,
                vendor_part_no=vendor_part_no,
                msrp=msrp,
                federal_govt_spa=federal_govt_spa,
                ec_status=True,
            )
            obj.save()
        except:
            pass
        else:
            obj.mfr_part_no = mfr_part_no
            obj.vendor_part_no = vendor_part_no
            obj.msrp = msrp
            obj.federal_govt_spa = federal_govt_spa
            obj.ec_status = True
            obj.save()
        return {
            "mfr_part_no": mfr_part_no,
            "vendor_part_no": vendor_part_no,
            "msrp": msrp,
            "federal_govt_spa": federal_govt_spa,
        }
    else:
        # 无产品
        tbody = browser.find_elements_by_xpath(page_elements.get("tbody"))
        if tbody:  # 页面正常
            text = tbody[0].text
            if "Your search found no result." in text or "product in this page" in text:
                try:
                    obj, _ = ECGood.objects.get_or_create(part=part)
                    # obj.manufacturer = manufacturer
                    obj.ec_status = True
                    obj.save()
                except ECGood.DoesNotExist:
                    pass
                except:
                    pass
        else:  # 页面异常
            return {}


def get_model_param_by_gsa(browser, part):
    objs = GSAGood.objects.filter(part=part)
    if objs:
        return {}  # 存在则不需要再爬取
    else:
        logging.warning(f"part={part},不存在,需要爬取数据")
    # 搜索
    url = f"https://www.gsaadvantage.gov/advantage/ws/search/advantage_search?q=0:8{part}&db=0&searchType=0"
    browser.get(url)
    time.sleep(5)
    waiting_to_load(browser)

    product_divs = browser.find_elements_by_xpath(page_elements.get("product_list"))
    if product_divs:
        pass
    else:
        # 判断页面是否加载完成
        search_divs = browser.find_elements_by_xpath(page_elements.get("search"))
        if search_divs:
            product_divs = browser.find_elements_by_xpath(
                page_elements.get("product_list")
            )
            if not product_divs:
                return {}
        else:
            return {}

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
            product_name = url_div.text  # 有问题,取里面的数据
            mfr_name_div = product_div.find_element_by_xpath(
                page_elements.get("mfr_name")
            )
            manufacturer_name = mfr_name_div.text[4:].strip()
            # mfr_part_no_gsa字段
            mfr_part_no_gsa_div = product_div.find_element_by_xpath(
                page_elements.get("mfr_part_no_gsa")
            )
            mfr_part_no_gsa = mfr_part_no_gsa_div.text.strip()
            if source >= gsa_source_level:
                valid_source_urls.append(
                    [source, url, product_name, manufacturer_name, mfr_part_no_gsa]
                )
            elif not first_source_urls:
                first_source_urls.append(
                    [source, url, product_name, manufacturer_name, mfr_part_no_gsa]
                )
        # 排序,取前3
        valid_source_urls = sorted(valid_source_urls, key=lambda x: x[0], reverse=True)
        if len(valid_source_urls) > 3:
            valid_source_urls = valid_source_urls[0:3]

        if not valid_source_urls:  # 如果没有符合要求的,则采集第一个产品
            valid_source_urls = first_source_urls

        gsa_data = []
        # 到详细页采集数据
        for (
            source,
            url,
            product_name,
            manufacturer_name,
            mfr_part_no_gsa,
        ) in valid_source_urls:
            browser.get(url)
            waiting_to_load(browser)

            # # product_name 取里面的
            # product_name_divs = browser.find_elements_by_xpath(
            #     page_elements.get("product_name")
            # )
            # if product_name_divs:
            #     product_name = product_name_divs[0].text

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
            product_description2 = _product_description

            _description_divs_strong = browser.find_elements_by_xpath(
                page_elements.get("description_strong")
            )
            if _description_divs_strong:
                product_description2_strong = _description_divs_strong[0].text
            else:
                product_description2_strong = ""

            waiting_to_load(browser)
            product_description = description_div.text
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
                "part": part,
                "manufacturer_name": manufacturer_name,
                "product_name": product_name,
                "product_description": product_description,
                "product_description2_strong": product_description2_strong,
                "product_description2": product_description2,
                "gsa_advantage_price_1": gsa_advantage_prices[0],
                "gsa_advantage_price_2": gsa_advantage_prices[1],
                "gsa_advantage_price_3": gsa_advantage_prices[2],
                "coo": coo,
                "mfr_part_no_gsa": mfr_part_no_gsa,
                "url": url,
                "source": source,
            }
            # 直接存储
            obj = GSAGood(**item_data)
            obj.save()
            gsa_data.append(item_data)
        return gsa_data
    else:
        logging.warning(f"part={part}无产品")
        return []


def get_model_param_by_inm(browser, part):
    try:
        obj = ECGood.objects.get(part=part)
        if obj.inm_status:
            return
        if obj.ingram_micro_price:
            obj.inm_status = True
            obj.save()
            return
        logging.warning(f"INM:part={part},存在,需要更新数据")
    except ECGood.DoesNotExist:
        logging.warning(f"INM:part={part},不存在,需要爬取数据")
        pass
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
        obj, _ = ECGood.objects.get_or_create(part=part)
        obj.inm_status = True
        obj.ingram_micro_price = ingram_micro_price
        obj.save()
        return {"ingram_micro_price": ingram_micro_price}
    else:
        obj, _ = ECGood.objects.get_or_create(part=part)
        obj.inm_status = True
        obj.ingram_micro_price = 0
        obj.save()
        return {}


def save_to_model_ec(params):
    ec_good = ECGood(**params)
    ec_good.save()


def spider():
    # 浏览器准备
    browser_ec = login()
    browser_gsa = create_browser()
    browser_inm = create_browser()
    # 数据准备
    begin_row = 4
    data = get_data_by_excel(
        "/Users/myard/Downloads/Updated CPLAPR15手动重要.xlsx",
        begin_row=begin_row,
        cols=[1, 0],
    )
    parts = data[0]
    manufacturers = data[1]
    for i, part in enumerate(parts):
        if not part:  # 处理空格
            continue
        # 处理float数
        if isinstance(part, float):
            part = str(int(part))
        logging.info(f"index={i}:{i + begin_row},part:{part}")
        try:
            data_ec = get_model_param_by_ec(browser_ec, part, manufacturers[i])
            data_gsa_list = get_model_param_by_gsa(browser_gsa, part)
            data_inm = get_model_param_by_inm(browser_inm, part)
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"{part}_{int(time.time())}"
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            sys.exit(0)


def export(path, begin_row, begin_col, end_col, part_col, process=True):
    cols = list(range(begin_col, end_col + 1))
    excel_data = get_data_by_excel(path, begin_row, cols)
    parts = excel_data[part_col]
    data = []
    for i, part in enumerate(parts):
        if not part:
            continue
        if isinstance(part, float):
            part = str(int(part))
        row_data = []
        for item in excel_data:
            row_data.append(item[i])
        if i == 0:
            row_data.extend(
                [
                    "part",
                    "manufacturer",
                    "mfr_part_no",
                    "vendor_part_no",
                    "msrp",
                    "federal_govt_spa",
                    "ingram_micro_price",
                    # gsa
                    "manufacturer_name",
                    "product_name",
                    "product_description",
                    "product_description2_strong",
                    "product_description2",
                    "gsa_advantage_price_1",
                    "gsa_advantage_price_2",
                    "gsa_advantage_price_3",
                    "coo",
                    "mfr_part_no_gsa",
                    "url",
                    "source",
                    "min_price",
                    "description",
                ]
            )
            data.append(row_data)
            continue
        # 处理数据
        ec_objs = ECGood.objects.filter(part=part)
        if ec_objs:
            ec_obj = ec_objs[0]
        else:
            if process:
                continue
            else:
                ec_obj = ECGood(part=part)
        if ec_obj.federal_govt_spa == 0 and ec_obj.ingram_micro_price == 0:
            if process:
                continue
            else:
                pass
        gsa_objs = GSAGood.objects.filter(part=part)
        if (not process) and (not gsa_objs):
            gsa_obj = GSAGood(part=part)
            gsa_objs = [gsa_obj]

        for gsa_obj in gsa_objs:
            _row_data = []
            _row_data.extend(row_data)
            gsa_advantage_price_2 = float(gsa_obj.gsa_advantage_price_2)
            # 判断数值是否合理
            min_price = 0
            if (
                ec_obj.federal_govt_spa
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                min_price = ec_obj.federal_govt_spa
            if (
                ec_obj.ingram_micro_price
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                if min_price == 0:
                    min_price = ec_obj.ingram_micro_price
                else:
                    min_price = min(min_price, ec_obj.ingram_micro_price)
            if min_price or (not process):  # 数据合理
                # 处理描述
                description = ""
                if gsa_obj.product_description:
                    description = gsa_obj.product_description
                elif gsa_obj.product_description2:
                    description = gsa_obj.product_description2
                    if gsa_obj.product_description2_strong:
                        strong = (
                            gsa_obj.product_description2_strong.split("by")[-1]
                            .strip()
                            .strip(".")
                        )
                        description = description.replace(strong, "TechFocus LLC")
                    if "For further" in description:
                        description = description.split("For further")[0]
                    description += "For further information contact TechFocus at 304-906-8124 Or email lwang@techfocusUSA.com"
                else:
                    description = ""
                # 加数据
                _row_data.append(ec_obj.part)
                _row_data.append(ec_obj.manufacturer)
                _row_data.append(ec_obj.mfr_part_no)
                _row_data.append(ec_obj.vendor_part_no)
                _row_data.append(ec_obj.msrp)
                _row_data.append(ec_obj.federal_govt_spa)
                _row_data.append(ec_obj.ingram_micro_price)

                _row_data.append(gsa_obj.manufacturer_name)
                _row_data.append(gsa_obj.product_name)
                _row_data.append(gsa_obj.product_description)
                _row_data.append(gsa_obj.product_description2_strong)
                _row_data.append(gsa_obj.product_description2)
                _row_data.append(gsa_obj.gsa_advantage_price_1)
                _row_data.append(gsa_obj.gsa_advantage_price_2)
                _row_data.append(gsa_obj.gsa_advantage_price_3)
                _row_data.append(gsa_obj.coo)
                _row_data.append(gsa_obj.mfr_part_no_gsa)
                _row_data.append(gsa_obj.url)
                _row_data.append(gsa_obj.source)
                _row_data.append(min_price)
                _row_data.append(description)
                data.append(_row_data)

    save_data_to_excel("_done_未筛选.xlsx", data)


def get_gsa_by_brand_1(brand_id):
    """
    通过关键字查询到合适的产品,存储到数据库
    """
    brand = Brand.objects.get(pk=brand_id)
    browser = create_browser()
    price_params = [
        "&q=14:71",  # <1
        "&q=14:61&q=14:75",  # 1-5
        "&q=14:65&q=14:710",  # 5-10
        "&q=14:610&q=14:725",  # 10-25
        "&q=14:625&q=14:750",  # 25-50
        "&q=14:650&q=14:7100",  # 50-100
        "&q=14:6100&q=14:7250",  # 100-250
        "&q=14:6250&q=14:7500",  # 250-500
        "&q=14:6500",  # 500+
    ]
    # 1、外部爬取
    for price_param in price_params:
        for i in range(1, 11):  # 每页50个数据,最多10页
            url = (
                f"https://www.gsaadvantage.gov/advantage/ws/search/advantage_search?q=0:8{brand.key}&s=11&searchType=0&db=0&c=50&p={i}"
                + price_param
            )
            browser.get(url)
            time.sleep(5)
            waiting_to_load(browser)

            global_search_label = browser.find_elements_by_xpath(
                page_elements.get("search")
            )
            if global_search_label:
                # 页面加载完成
                product_divs = browser.find_elements_by_xpath(
                    page_elements.get("product_list")
                )
                if not product_divs:  # 无数据了,则跳出
                    break
                for product_div in product_divs:
                    source_divs = product_div.find_elements_by_xpath(
                        page_elements.get("sources")
                    )
                    if not source_divs:  # 有些产品,没有sources
                        continue
                    source_div = source_divs[0]
                    source = get_num(source_div.text)
                    if source >= brand.mini_sources:
                        url_div = product_div.find_element_by_xpath(
                            page_elements.get("item_a")
                        )
                        url = url_div.get_attribute("href")
                        product_name = url_div.text
                        mfr_name_div = product_div.find_element_by_xpath(
                            page_elements.get("mfr_name")
                        )
                        manufacturer_name = mfr_name_div.text[4:].strip()
                        # 厂家不包含关键词,则剔除
                        key_str = brand.note
                        keys = [_.lower() for _ in key_str.split(",")]
                        status = False
                        for key in keys:
                            if key in manufacturer_name.lower():
                                status = True
                                break
                        if not status:  # 厂家不包含关键词,则剔除
                            continue
                        mfr_part_no_gsa_div = product_div.find_element_by_xpath(
                            page_elements.get("mfr_part_no_gsa")
                        )
                        mfr_part_no_gsa = mfr_part_no_gsa_div.text.strip()
                        try:
                            objs = GSAGood.objects.filter(url=url)
                            if objs:
                                _obj = objs[0]
                                _obj.brand_key = brand.key
                                _obj.save()
                                continue
                            obj = GSAGood.objects.create(
                                brand_key=brand.key,
                                url=url,
                                product_name=product_name,
                                manufacturer_name=manufacturer_name,
                                mfr_part_no_gsa=mfr_part_no_gsa,
                                source=source,
                            )
                        except Exception as e:
                            logging.error(e)
            else:
                # 页面加载失败
                with open(f"{brand.key}_{i}.txt", "w+") as f:
                    f.write(f"{url}")
    browser.quit()


def get_gsa_by_brand_2(b):
    """通过详情页链接,爬取详情页信息"""
    browser = create_browser()
    # 2、内部爬取
    gsa_objs = GSAGood.objects.filter(gsa_status=False, delete_at__isnull=True)
    if b:
        count = gsa_objs.count()
        base = count // 4
        gsa_objs = gsa_objs[base * (b - 1) : base * b]
    for gas_obj in gsa_objs:
        logging.info(f"gas_obj.pk={gas_obj.pk}")
        if gas_obj.gsa_status:
            continue  # 爬取过
        browser.get(gas_obj.url)
        time.sleep(3)
        waiting_to_load(browser)

        # 增加判断是否需要邮编,有则跳过
        zip_div = browser.find_elements_by_xpath(page_elements.get("zip"))
        if zip_div:
            gas_obj.gsa_status = True
            gas_obj.save()
            continue

        global_search_label = browser.find_elements_by_xpath(
            page_elements.get("search")
        )
        if global_search_label:
            # 页面加载完成
            coo = ""
            sin = ""
            divs = browser.find_elements_by_xpath(page_elements.get("coo_divs"))
            for div in divs:
                text = div.text
                if "Country of Origin" in text:
                    coo = text[18:].strip()
                if "MAS/" in text:
                    sin = text[22:].strip()  # 有一个换行符

            description_divs = browser.find_elements_by_xpath(
                page_elements.get("description")
            )
            if description_divs:
                description_div = description_divs[0]
                browser.execute_script(
                    "window.scrollTo(0, {})".format(
                        description_div.location.get("y") - 160
                    )
                )
                product_description = description_div.text
            else:
                product_description = ""

            _description_divs = browser.find_elements_by_xpath(
                page_elements.get("product_description")
            )
            if _description_divs:
                _product_description = _description_divs[0].text
            else:
                _product_description = ""
            product_description2 = _product_description

            if len(product_description) >= 1000:
                product_description = product_description[0:1000]
            if len(product_description2) >= 1000:
                product_description2 = product_description2[0:1000]

            _description_divs_strong = browser.find_elements_by_xpath(
                page_elements.get("description_strong")
            )
            if _description_divs_strong:
                product_description2_strong = _description_divs_strong[0].text
            else:
                product_description2_strong = ""

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
            # 添加数据
            gas_obj.sin = sin
            gas_obj.product_description = product_description
            gas_obj.product_description2_strong = product_description2_strong
            gas_obj.product_description2 = product_description2
            gas_obj.gsa_advantage_price_1 = gsa_advantage_prices[0]
            gas_obj.gsa_advantage_price_2 = gsa_advantage_prices[1]
            gas_obj.gsa_advantage_price_3 = gsa_advantage_prices[2]
            gas_obj.coo = coo
            gas_obj.gsa_status = True
            gas_obj.save()
        else:
            pass
    browser.quit()


def get_ec_by_brand(half=False, refresh=False, ec=True, inm=False):
    if ec:
        browser_ec = login()
    else:
        browser_ec = None
    if inm:
        browser_inm = create_browser()
    else:
        browser_inm = None
    if refresh:
        gsa_objs = GSAGood.objects.filter(
            sin="33411", gsa_status=True, delete_at__isnull=True
        )  # 有效数据
        # 占位
        for gas_obj in gsa_objs:
            logging.info(f"gas_obj.pk={gas_obj.pk}")
            try:
                obj, _ = ECGood.objects.get_or_create(part=gas_obj.mfr_part_no_gsa)
            except Exception as e:
                logging.error(e)

    # 爬取数据
    ec_objs = ECGood.objects.filter(ec_status=False)
    if half:
        count = ec_objs.count()
        begin = count // 2
        ec_objs = ec_objs[begin:]
    for ec_obj in ec_objs:
        logging.info(f"ec_obj.pk={ec_obj.pk}")
        if ec and browser_ec:
            get_model_param_by_ec(browser_ec, ec_obj.part)
        if inm and browser_inm:
            get_model_param_by_inm(browser_inm, ec_obj.part)
    if ec and browser_ec:
        browser_ec.quit()
    if inm and browser_inm:
        browser_inm.quit()


def export_by_brand_key(brand_name, brand_key, process=True):
    data = []
    headers = [
        "品牌名称",
        "关键词",
        # ec
        "part",
        "mfr_part_no",
        "vendor_part_no",
        "msrp",
        "federal_govt_spa",
        "ingram_micro_price",
        # gsa
        "sin",
        "manufacturer_name",
        "product_name",
        "product_description",
        "product_description2_strong",
        "product_description2",
        "gsa_advantage_price_1",
        "gsa_advantage_price_2",
        "gsa_advantage_price_3",
        "coo",
        "mfr_part_no_gsa",
        "url",
        "source",
        "min_price",
        "description",
    ]
    data.append(headers)
    brands = Brand.objects.filter(key=brand_key)
    for brand in brands:
        gsa_objs = GSAGood.objects.filter(brand_key=brand.key, sin="33411")
        for gsa_obj in gsa_objs:
            ec_obj, _ = ECGood.objects.get_or_create(part=gsa_obj.mfr_part_no_gsa)
            _row_data = []
            # 处理数据
            key_str = brand.note
            keys = [_.lower() for _ in key_str.split(",")]
            status = False
            for key in keys:
                if key in gsa_obj.manufacturer_name.lower():
                    status = True
                    break
            if not status:  # 厂家不包含关键词,则剔除
                continue
            # source参与过滤
            if gsa_obj.source < brand.filter_sources:
                continue
            if ec_obj.federal_govt_spa == 0 and ec_obj.ingram_micro_price == 0:
                if process:
                    continue
                else:
                    pass
            gsa_advantage_price_2 = float(gsa_obj.gsa_advantage_price_2)
            # 判断数值是否合理
            min_price = 0
            if (
                ec_obj.federal_govt_spa
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                min_price = ec_obj.federal_govt_spa
            if (
                ec_obj.ingram_micro_price
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                if min_price == 0:
                    min_price = ec_obj.ingram_micro_price
                else:
                    min_price = min(min_price, ec_obj.ingram_micro_price)
            if min_price or (not process):  # 数据合理
                # 处理描述
                description = ""
                if gsa_obj.product_description:
                    description = gsa_obj.product_description
                elif gsa_obj.product_description2:
                    description = gsa_obj.product_description2
                    if gsa_obj.product_description2_strong:
                        strong = (
                            gsa_obj.product_description2_strong.split("by")[-1]
                            .strip()
                            .strip(".")
                        )
                        description = description.replace(strong, "TechFocus LLC")
                    if "For further" in description:
                        description = description.split("For further")[0]
                    description += "For further information contact TechFocus at 304-906-8124 Or email lwang@techfocusUSA.com"
                else:
                    description = ""
                # 加数据
                _row_data.append(brand.name)
                _row_data.append(brand.key)

                _row_data.append(ec_obj.part)
                _row_data.append(ec_obj.mfr_part_no)
                _row_data.append(ec_obj.vendor_part_no)
                _row_data.append(ec_obj.msrp)
                _row_data.append(ec_obj.federal_govt_spa)
                _row_data.append(ec_obj.ingram_micro_price)

                _row_data.append(gsa_obj.sin)
                _row_data.append(gsa_obj.manufacturer_name)
                _row_data.append(gsa_obj.product_name)
                _row_data.append(gsa_obj.product_description)
                _row_data.append(gsa_obj.product_description2_strong)
                _row_data.append(gsa_obj.product_description2)
                _row_data.append(gsa_obj.gsa_advantage_price_1)
                _row_data.append(gsa_obj.gsa_advantage_price_2)
                _row_data.append(gsa_obj.gsa_advantage_price_3)
                _row_data.append(gsa_obj.coo)
                _row_data.append(gsa_obj.mfr_part_no_gsa)
                _row_data.append(gsa_obj.url)
                _row_data.append(gsa_obj.source)
                _row_data.append(min_price)
                _row_data.append(description)
                data.append(_row_data)
    save_data_to_excel(
        f"{brand_name}_{brand_key}_done_{'筛选' if process else '未筛选'}.xlsx", data
    )


def export_by_brand(brand_name, process=True):
    data = []
    headers = [
        "品牌名称",
        "关键词",
        # ec
        "part",
        "mfr_part_no",
        "vendor_part_no",
        "msrp",
        "federal_govt_spa",
        "ingram_micro_price",
        # gsa
        "sin",
        "manufacturer_name",
        "product_name",
        "product_description",
        "product_description2_strong",
        "product_description2",
        "gsa_advantage_price_1",
        "gsa_advantage_price_2",
        "gsa_advantage_price_3",
        "coo",
        "mfr_part_no_gsa",
        "url",
        "source",
        "min_price",
        "description",
    ]
    data.append(headers)
    brands = Brand.objects.filter(name=brand_name)
    for brand in brands:
        gsa_objs = GSAGood.objects.filter(
            brand_key=brand.key, sin="33411", delete_at__isnull=True
        )
        for gsa_obj in gsa_objs:
            ec_obj, _ = ECGood.objects.get_or_create(part=gsa_obj.mfr_part_no_gsa)
            _row_data = []
            # 处理数据
            key_str = brand.note
            keys = [_.lower() for _ in key_str.split(",")]
            status = False
            for key in keys:
                if key in gsa_obj.manufacturer_name.lower():
                    status = True
                    break
            if not status:  # 厂家不包含关键词,则剔除
                continue
            # source参与过滤
            if gsa_obj.source < brand.filter_sources:
                continue
            if ec_obj.federal_govt_spa == 0 and ec_obj.ingram_micro_price == 0:
                if process:
                    continue
                else:
                    pass
            gsa_advantage_price_2 = float(gsa_obj.gsa_advantage_price_2)
            # 判断数值是否合理
            min_price = 0
            if (
                ec_obj.federal_govt_spa
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                min_price = ec_obj.federal_govt_spa
            if (
                ec_obj.ingram_micro_price
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                if min_price == 0:
                    min_price = ec_obj.ingram_micro_price
                else:
                    min_price = min(min_price, ec_obj.ingram_micro_price)
            if min_price or (not process):  # 数据合理
                # 处理描述
                description = ""
                if gsa_obj.product_description:
                    description = gsa_obj.product_description
                elif gsa_obj.product_description2:
                    description = gsa_obj.product_description2
                    if gsa_obj.product_description2_strong:
                        strong = (
                            gsa_obj.product_description2_strong.split("by")[-1]
                            .strip()
                            .strip(".")
                        )
                        description = description.replace(strong, "TechFocus LLC")
                    if "For further" in description:
                        description = description.split("For further")[0]
                    description += "For further information contact TechFocus at 304-906-8124 Or email lwang@techfocusUSA.com"
                else:
                    description = ""
                # 加数据
                _row_data.append(brand.name)
                _row_data.append(brand.key)

                _row_data.append(ec_obj.part)
                _row_data.append(ec_obj.mfr_part_no)
                _row_data.append(ec_obj.vendor_part_no)
                _row_data.append(ec_obj.msrp)
                _row_data.append(ec_obj.federal_govt_spa)
                _row_data.append(ec_obj.ingram_micro_price)

                _row_data.append(gsa_obj.sin)
                _row_data.append(gsa_obj.manufacturer_name)
                _row_data.append(gsa_obj.product_name)
                _row_data.append(gsa_obj.product_description)
                _row_data.append(gsa_obj.product_description2_strong)
                _row_data.append(gsa_obj.product_description2)
                _row_data.append(gsa_obj.gsa_advantage_price_1)
                _row_data.append(gsa_obj.gsa_advantage_price_2)
                _row_data.append(gsa_obj.gsa_advantage_price_3)
                _row_data.append(gsa_obj.coo)
                _row_data.append(gsa_obj.mfr_part_no_gsa)
                _row_data.append(gsa_obj.url)
                _row_data.append(gsa_obj.source)
                _row_data.append(min_price)
                _row_data.append(description)
                data.append(_row_data)
    save_data_to_excel(f"{brand_name}_done_{'筛选' if process else '未筛选'}.xlsx", data)


def load_brand():
    brand_name = "HP"
    string = "PRODESK,Workstation,Dock"
    note = "hp,hewlett"
    keys = [_.strip() for _ in string.split(",")]
    print(keys)
    for key in keys:
        Brand.objects.create(
            name=brand_name, key=key, mini_sources=8, filter_sources=8, note=note
        )


def delete_gsa():
    brand_name = "Dell"
    brand_objs = Brand.objects.filter(name=brand_name)
    for brand_obj in brand_objs:
        gsa_objs = GSAGood.objects.filter(brand_key=brand_obj.key)
        for gsa_obj in gsa_objs:
            # 厂家不包含关键词,则剔除
            key_str = brand_obj.note
            keys = [_.lower() for _ in key_str.split(",")]
            status = False
            for key in keys:
                if key in gsa_obj.manufacturer_name.lower():
                    status = True
                    break
            if not status:  # 厂家不包含关键词,则剔除
                gsa_obj.delete()


def get_gsa_by_url():
    browser = create_browser()
    key_urls = []
    for key, url in key_urls:
        brand = Brand.objects.get(key=key)
        browser.get(url)
        time.sleep(5)
        waiting_to_load(browser)

        global_search_label = browser.find_elements_by_xpath(
            page_elements.get("search")
        )
        if global_search_label:
            # 页面加载完成
            product_divs = browser.find_elements_by_xpath(
                page_elements.get("product_list")
            )
            if not product_divs:  # 无数据了,则跳出
                break
            for product_div in product_divs:
                source_divs = product_div.find_elements_by_xpath(
                    page_elements.get("sources")
                )
                if not source_divs:  # 有些产品,没有sources
                    continue
                source_div = source_divs[0]
                source = get_num(source_div.text)
                if source >= brand.mini_sources:
                    url_div = product_div.find_element_by_xpath(
                        page_elements.get("item_a")
                    )
                    url = url_div.get_attribute("href")
                    product_name = url_div.text
                    mfr_name_div = product_div.find_element_by_xpath(
                        page_elements.get("mfr_name")
                    )
                    manufacturer_name = mfr_name_div.text[4:].strip()
                    # 厂家不包含关键词,则剔除
                    key_str = brand.note
                    keys = [_.lower() for _ in key_str.split(",")]
                    status = False
                    for key in keys:
                        if key in manufacturer_name.lower():
                            status = True
                            break
                    if not status:  # 厂家不包含关键词,则剔除
                        continue
                    mfr_part_no_gsa_div = product_div.find_element_by_xpath(
                        page_elements.get("mfr_part_no_gsa")
                    )
                    mfr_part_no_gsa = mfr_part_no_gsa_div.text.strip()
                    try:
                        objs = GSAGood.objects.filter(url=url)
                        if objs:
                            _obj = objs[0]
                            _obj.brand_key = brand.key
                            _obj.save()
                            continue
                        obj = GSAGood.objects.create(
                            brand_key=brand.key,
                            url=url,
                            product_name=product_name,
                            manufacturer_name=manufacturer_name,
                            mfr_part_no_gsa=mfr_part_no_gsa,
                            source=source,
                        )
                    except Exception as e:
                        logging.error(e)
        else:
            # 页面加载失败
            with open(f"{brand.key}.txt", "w+") as f:
                f.write(f"{url}")
    logging.info("get_gsa_by_url运行结束")
    sys.exit(0)


def get_excel_to_mysql_gsa_detail(path):
    data = get_data_by_excel(path, begin_row=1, cols=[6, 9, 10, 11, 12, 13, 14, 15, 19])
    # sin, 6
    # product_description, 9
    # product_description2_strong, 10
    # product_description2, 11
    # gsa_advantage_price_1, 12
    # gsa_advantage_price_2, 13
    # gsa_advantage_price_3, 14
    # coo, 15
    # url, 19
    # gsa_status  # 状态
    sins = data[0]
    product_descriptions = data[1]
    product_description2_strongs = data[2]
    product_description2s = data[3]
    gsa_advantage_price_1s = data[4]
    gsa_advantage_price_2s = data[5]
    gsa_advantage_price_3s = data[6]
    coos = data[7]
    urls = data[8]
    for i, url in enumerate(urls):
        logging.info(f"{i}:{url}")
        try:
            gsa_obj = GSAGood.objects.get(url=url)
            if gsa_obj.gsa_status:
                continue

            if len(product_descriptions[i]) >= 1000:
                product_description = product_descriptions[i][0:1000]
            else:
                product_description = product_descriptions[i]
            if len(product_description2s[i]) >= 1000:
                product_description2 = product_description2s[i][0:1000]
            else:
                product_description2 = product_description2s[i]

            gsa_obj.sin = sins[i]
            gsa_obj.product_description = product_description
            gsa_obj.product_description2_strong = product_description2_strongs[i]
            gsa_obj.product_description2 = product_description2
            gsa_obj.gsa_advantage_price_1 = gsa_advantage_price_1s[i]
            gsa_obj.gsa_advantage_price_2 = gsa_advantage_price_2s[i]
            gsa_obj.gsa_advantage_price_3 = gsa_advantage_price_3s[i]
            gsa_obj.coo = coos[i]
            gsa_obj.gsa_status = True
            gsa_obj.save()
        except GSAGood.DoesNotExist:
            continue


def get_excel_to_mysql_ec_detail(path):
    data = get_data_by_excel(path, begin_row=1, cols=[5, 6, 7, 8, 9, 10, 11, 12])
    # part, 5
    # mfr_part_no, 6
    # vendor_part_no, 7
    # msrp, 8
    # federal_govt_spa, 9
    # ingram_micro_price, 10
    # ec_status 状态 11
    # inm_status 状态 12
    parts = data[0]
    mfr_part_nos = data[1]
    vendor_part_nos = data[2]
    msrps = data[3]
    federal_govt_spas = data[4]
    ingram_micro_prices = data[5]
    ec_statuses = data[6]
    inm_statuses = data[7]
    for i, part in enumerate(parts):
        logging.info(f"{i}:{part}")
        try:
            ec_obj = ECGood.objects.get(part=part)
            if ec_obj.ec_status:
                continue
            ec_obj.mfr_part_no = mfr_part_nos[i]
            ec_obj.vendor_part_no = vendor_part_nos[i]
            ec_obj.msrp = msrps[i]
            ec_obj.federal_govt_spa = federal_govt_spas[i]
            ec_obj.ingram_micro_price = ingram_micro_prices[i]
            ec_obj.ec_status = ec_statuses[i]
            ec_obj.inm_status = inm_statuses[i]
            ec_obj.save()
        except ECGood.DoesNotExist:
            # 没有则插入
            ec_obj = ECGood(part=part)
            ec_obj.mfr_part_no = mfr_part_nos[i]
            ec_obj.vendor_part_no = vendor_part_nos[i]
            ec_obj.msrp = msrps[i]
            ec_obj.federal_govt_spa = federal_govt_spas[i]
            ec_obj.ingram_micro_price = ingram_micro_prices[i]
            ec_obj.ec_status = ec_statuses[i]
            ec_obj.inm_status = inm_statuses[i]
            ec_obj.save()


def set_delete_gsa(i):
    brand_obj = Brand.objects.get(pk=i)
    index = 1
    while True:
        count = GSAGood.objects.filter(
            brand_key=brand_obj.key, delete_at__isnull=True
        ).count()
        if count <= 150:
            break
        elif count <= 200:
            if index >= 8:
                break
        elif count <= 300:
            if index >= 12:
                break
        else:
            if index >= 15:
                break
        now = datetime.datetime.now()
        objs = GSAGood.objects.filter(
            brand_key=brand_obj.key, source__lte=index
        ).update(delete_at=now)
        index += 1


if __name__ == "__main__":
    pass
    # 爬取
    # a1 = range(41, 44)
    # a2 = range(44, 47)
    # a3 = range(47, 50)
    # a4 = range(50, 53)
    # a = a1
    # for i in a:
    #     logging.info(f"i={i}")
    #     get_gsa_by_brand_1(i)  # 爬取gsa
    # 1.1单个关键词数据保持在一千以内
    # # 爬取2
    # while True:
    #     try:
    #         get_gsa_by_brand_2(0)  # 爬取补充gsa
    #     except Exception as e:
    #         logging.error(e)
    #     break
    # 3.ec和inm
    for i in range(100):
        logging.info(f"i={i}")
        try:
            get_ec_by_brand(half=False, refresh=True, ec=True, inm=False)  # ec和inm
        except Exception as e:
            logging.error(e)
    # # 导出
    # export_by_brand(brand_name="HP", process=True)
    # export_by_brand(brand_name="HP", process=False)
    # export_by_brand(brand_name="cisco", process=False)
    # export_by_brand(brand_name="LG", process=False)
    # export_by_brand(brand_name="Samsung", process=False)
    # export_by_brand(brand_name="Logitech", process=False)
    # brands = Brand.objects.filter(pk__gte=26)
    # for brand in brands:
    #     key = brand.key
    #     count = GSAGood.objects.filter(brand_key=key).count()
    #     print(f"{key}:{count}")
    """
    import datetime
    now = datetime.datetime.now()
    key = "HP Notebook"
    count = GSAGood.objects.filter(brand_key=key,source__gte=7).count()
    objs = GSAGood.objects.filter(brand_key=key,source__lte=6).update(delete_at=now)
    count = GSAGood.objects.filter(brand_key=key,delete_at__isnull=True).count()
    """
