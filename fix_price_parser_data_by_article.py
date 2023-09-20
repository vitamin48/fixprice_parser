import datetime
import json
import time
import requests
from pathlib import Path
import pandas as pd
import re

import urllib
from urllib.request import urlopen as uReq
from tqdm import tqdm

from selenium.webdriver import Chrome
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class InfoFixPrice:
    """Получение информации по артикулу"""

    def __init__(self):
        self.save_path = f'{str(Path(__file__).parents[1])}'
        self.__options = Options()
        self.__options.add_argument("--start-maximized")
        self.__options.add_argument('--blink-settings=imagesEnabled=false')
        self.__service = Service('chromedriver.exe')
        self.browser = webdriver.Chrome(service=self.__service, options=self.__options)
        self.__main_url = 'https://fix-price.com/'

        self.bad_brand_list = []
        self.res_df = pd.DataFrame()

        self.stocks = []
        self.price = []

        self.name = []
        self.description = []

        self.brand = []
        self.code = []
        self.packing_width = []  # ширина
        self.packing_height = []  # высота
        self.package_length = []  # длина
        self.weight = []
        self.country = []
        self.properties_extra = []
        self.url_img = []

        self.bad_req_list = []

    def read_articles_from_txt(self):
        with open('fix_price_articles.txt', 'r', encoding='utf-8') as file:
            articles = [f'{line}'.rstrip() for line in file]
            return articles

    def set_city(self):
        # self.__options.add_argument('--blink-settings=imagesEnabled=true')
        self.browser.get(f'{self.__main_url}about/contacts')
        self.browser.implicitly_wait(20)
        time.sleep(2)
        geo = self.browser.find_element(By.XPATH, '//*[@id="app-header"]/header/div/div[1]/div[1]/div[1]/span')
        geo.click()
        self.browser.implicitly_wait(5)
        time.sleep(2)
        currentcity = self.browser.find_element(By.XPATH, '//*[@id="modal"]/div/div[4]/form/input')
        currentcity.click()
        time.sleep(1)
        self.browser.implicitly_wait(3)
        currentcity.clear()
        self.browser.implicitly_wait(3)
        currentcity.send_keys('Брянск')
        time.sleep(3)
        city = self.browser.find_element(By.XPATH, '//*[@id="modal"]/div/div[4]/div/div[1]')
        city.click()
        self.browser.implicitly_wait(10)
        time.sleep(2)
        save = self.browser.find_element(By.XPATH, '//*[@id="modal"]/div/div/div/button[2]')
        save.click()
        self.browser.implicitly_wait(10)
        time.sleep(5)
        address = self.browser.find_element(By.XPATH,
                                            '//*[@id="app-header"]/header/div/div[1]/div[1]/div[2]/div/div[1]')
        address.click()
        self.browser.implicitly_wait(10)
        time.sleep(3)
        choose_shop = self.browser.find_element(By.XPATH, '//*[@id="modal"]/div/div/div/div[3]/div/div[2]/div')
        choose_shop.click()
        self.browser.implicitly_wait(10)
        time.sleep(5)
        find_shop = self.browser.find_element(By.XPATH, '//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]'
                                                        '/div[2]/div[1]/div[1]/div[1]/input')
        find_shop.click()
        find_shop.clear()
        find_shop.send_keys('г.Брянск, ул.Бежицкая, д.1Б')
        self.browser.implicitly_wait(10)
        time.sleep(7)
        set_shop = self.browser.find_element(By.XPATH, '//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]'
                                                       '/div[5]/div/div[1]')
        set_shop.click()
        self.browser.implicitly_wait(10)
        time.sleep(1)
        set_shop2 = self.browser.find_element(By.XPATH, '//*[1]/ymaps/div/div/button/span')
        set_shop2.click()
        self.browser.implicitly_wait(10)
        time.sleep(5)
        final_shop = self.browser.find_element(By.XPATH, '//*[@id="app-header"]/header/div/div[1]/div[1]/div[2]'
                                                         '/div/div[2]')
        if final_shop.text == 'г.Брянск, ул.Бежицкая, д.1Б':
            return
        else:
            self.set_city()

    def get_data_from_articles(self, articles):
        for art in tqdm(articles):
            a: int = 1
            while a < 3:
                try:
                    count_products = None
                    self.browser.get(f'{self.__main_url}catalog/{art}')
                    self.browser.implicitly_wait(20)
                    # time.sleep(1)
                    # status_code = self.browser.execute_script('return window.performance.getEntries()[0].response.status')
                    # print(f'status code: {status_code}')
                    soup = BeautifulSoup(self.browser.page_source, 'lxml')
                    offline_only = soup.find('div', string=re.compile('Товар доступен только в магазинах'))
                    if offline_only:
                        if offline_only.text == 'Товар доступен только в магазинах':
                            a = 3
                            print(f'{bcolors.WARNING}Товар доступен только в магазинах{bcolors.ENDC} {art}')
                            raise Exception('Товар доступен только в магазинах')
                    variant = soup.find('div', string=re.compile('Вариант'))
                    if variant:
                        print()
                    # st = soup.find('div', text=re.compile('В наличи'))
                    try:
                        stock_on = self.browser.find_element(By.XPATH, '//*[contains(text(), "В наличии")]')
                    except Exception as exp_stock_on:
                        try:
                            stock_off = self.browser.find_element(By.XPATH, '//*[contains(text(), "Нет в наличии")]')
                        except Exception as exp_stock_off:
                            pass
                        else:
                            a = 3
                            print(f'{bcolors.WARNING}Нет в наличии{bcolors.ENDC} {art}')
                            raise Exception('Нет в наличии')
                    if a < 3:
                        # add_to_basket = WebDriverWait(self.browser, 5).until(
                        #     EC.presence_of_element_located((By.XPATH, '//*[@id="__layout"]'
                        #                                               '/div/div/div[3]/div/div/div/div/div[2]'
                        #                                               '/div[2]/div[6]/button[1]')))
                        add_to_basket = WebDriverWait(self.browser, 5).until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="__layout"]/div/div/div[3]/div/div/div'
                                                                      '/div/div[2]/div[2]/div[5]/button[1]')))

                        add_to_basket.click()
                        # ожидание, пока элемент не прогрузится
                        # count_products = WebDriverWait(self.browser, 5).until(
                        #     EC.presence_of_element_located((By.XPATH, '//*[@id="__layout"]/div/div/div[3]'
                        #                                               '/div/div/div/div/div[2]/div[2]/div[5]/div[1]'
                        #                                               '/div/div/div[2]/div/input')))
                        count_products = WebDriverWait(self.browser, 5).until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="__layout"]/div/div/div[3]/div/div/div'
                                                                      '/div/div[2]/div[2]/div[4]/div[1]/div/div/div[2]'
                                                                      '/div/input')))
                except Exception as exp:
                    exp_arg = exp.args
                    if exp_arg:
                        if exp.args[0] == 'Нет в наличии':
                            self.bad_req_list.append(f'Нет в наличии: {art}')
                            with open('out_of_stock.txt', 'a') as output:
                                output.write(art + '\n')
                        elif exp.args[0] == 'Товар доступен только в магазинах':
                            self.bad_req_list.append(f'Товар доступен только в магазинах: {art}')
                            with open('out_of_stock.txt', 'a') as output:
                                output.write(art + '\n')
                    else:
                        a += 1
                        if a >= 3:
                            self.bad_req_list.append(art)
                        else:
                            print(f'Ошибка:\n{exp}\n\nTRY: {a}')
                        time.sleep(3)
                        self.browser.get('https://fix-price.com/cart')
                        try:
                            remove = WebDriverWait(self.browser, 3).until(
                                EC.presence_of_element_located((By.XPATH, '//*[@id="__layout"]/div/div/div[3]'
                                                                          '/div/div/div/div/div[1]/div[1]/div[2]/div[1]'
                                                                          '/button/span')))
                        except Exception as exp:
                            print(exp)
                        else:
                            remove.click()
                else:
                    if count_products:
                        count_products.click()
                        count_products.clear()
                        count_products.send_keys('1000')
                        stocks = count_products.get_attribute('value')
                        self.stocks.append(stocks)
                        # soup = BeautifulSoup(self.browser.page_source, 'lxml')
                        self.get_data_from_soup(soup)
                        self.check_control_sum()
                        a = 3
                        print(f' {bcolors.OKGREEN}[+]{bcolors.ENDC} {art}')
                        with open('available_in_stock.txt', 'a') as output:
                            output.write(art + '\n')

    def get_data_from_soup(self, soup):
        name = soup.find('div', class_='product-details').next.attrs['content']
        self.name.append(name)
        price = soup.find('div', class_='price-quantity-block').next.next.next.attrs['content']
        self.price.append(int(round(float(price))))
        description = soup.find('div', class_='product-details').find('div', class_='description')
        if description:
            description = description.text
            self.description.append(description)
        else:
            self.description.append('-')
        product_images = soup.find('div', class_='product-images')
        img_list = []
        swiper_wrapper = product_images.find('div', class_='swiper-wrapper')
        if swiper_wrapper:
            for sw in swiper_wrapper:
                len_contents = len(sw.next.contents)
                if len_contents > 7:
                    img = sw.next.contents[6].attrs['src']
                    img = img.replace('800x800/', '')
                    img_list.append(img)
                else:
                    img_list.append('-+'
                                    ' ')
        else:
            img = \
                soup.find('div', class_='product-images').find('div', class_='zoom-on-hover').contents[
                    6].attrs[
                    'src']
            img = img.replace('800x800/', '')
            img_list.append(img)
            img_list.append('-')
        self.url_img.append(img_list)
        properties_block = soup.find('div', class_='properties-block')
        properties = properties_block.find('div', class_='properties')
        properties_list = ['Бренд', 'Код', 'Ширина', 'Высота', 'Длина', 'Вес', 'Страна']
        check_list = []
        for my_property in properties:
            title = my_property.find('span', class_='title').text
            value = my_property.find('span', class_='value').text
            if title == 'Бренд':
                self.brand.append(value)
                check_list.append('Бренд')
            elif title == 'Код товара':
                self.code.append(value)
                check_list.append('Код')
            elif title == 'Ширина, мм.' or title == 'Ширина упаковки, мм.':
                self.packing_width.append(int(value))
                check_list.append('Ширина')
            elif title == 'Высота, мм.' or title == 'Высота упаковки, мм.':
                self.packing_height.append(int(value))
                check_list.append('Высота')
            elif title == 'Длина, мм.' or title == 'Длина упаковки, мм.':
                self.package_length.append(int(value))
                check_list.append('Длина')
            elif title == 'Вес, гр.' or title == 'Вес упаковки, гр.':
                self.weight.append(int(value))
                check_list.append('Вес')
            elif title == 'Страна производства':
                self.country.append(value)
                check_list.append('Страна')
        dif_pr = list(set(properties_list) - set(check_list))
        if dif_pr:
            for dpr in dif_pr:
                if dpr == 'Бренд':
                    self.brand.append('Noname')
                elif dpr == 'Код':
                    self.code.append('-')
                elif dpr == 'Ширина':
                    self.packing_width.append('-')
                elif dpr == 'Высота':
                    self.packing_height.append('-')
                elif dpr == 'Длина':
                    self.package_length.append('-')
                elif dpr == 'Вес':
                    self.weight.append('-')
                elif dpr == 'Страна':
                    self.country.append('-')
        properties_extra = properties_block.find('div', class_='extra-properties')
        if properties_extra:
            properties_extra = properties_extra.find('div', class_='panel')
            self.properties_extra.append(properties_extra.text)
        else:
            self.properties_extra.append('-')

    def check_control_sum(self):
        if len(self.code) == len(self.name) == len(self.price) == len(self.stocks) == len(self.brand) == \
                len(self.description) == len(self.weight) == len(self.packing_width) == len(self.packing_height) == \
                len(self.package_length) == len(self.country) == len(self.url_img):
            return
        else:
            print()

    def create_df(self):
        self.res_df.insert(0, 'Артикул', [f'p_{x}' for x in self.code])
        self.res_df.insert(1, 'Название', self.name)
        self.res_df.insert(2, 'Цена FixPrice', self.price)
        self.res_df.insert(3, 'Цена для OZON', [390 if x * 4 < 390 else round(x * 3) for x in self.price])
        self.res_df.insert(4, 'Остаток на Бежицкой 1Б', self.stocks)
        self.res_df.insert(5, 'Брэнд', self.brand)
        self.res_df.insert(6, 'Описание', self.description)
        self.res_df.insert(7, 'Вес', self.weight)
        self.res_df.insert(8, 'Ширина', self.packing_width)
        self.res_df.insert(9, 'Высота', self.packing_height)
        self.res_df.insert(10, 'Длина', self.package_length)
        self.res_df.insert(11, 'Производитель', self.country)
        self.res_df.insert(12, 'Ссылка на главное фото товара', [x[0] for x in self.url_img])
        self.res_df.insert(13, 'Ссылки на фото товара', [' '.join(map(str, x)) for x in [x[1:] for x in self.url_img]])
        self.res_df.insert(14, 'Доп.контент', self.properties_extra)

    def create_xls(self):
        """Создание файла excel из 1-го DataFrame"""
        file_name = f'FP_{self.code[0]}_{self.code[-1]}.xlsx'
        writer = pd.ExcelWriter(file_name, engine_kwargs={'options': {'strings_to_urls': False}})
        self.res_df.to_excel(writer, sheet_name='FixPrice', index=False, na_rep='NaN', engine='openpyxl')
        # Auto-adjust columns' width
        for column in self.res_df:
            column_width = max(self.res_df[column].astype(str).map(len).max(), len(column)) + 2
            col_idx = self.res_df.columns.get_loc(column)
            writer.sheets[f'{"FixPrice"}'].set_column(col_idx, col_idx, column_width)
        writer.sheets["FixPrice"].set_column(1, 1, 30)
        writer.sheets["FixPrice"].set_column(6, 6, 30)
        writer.sheets["FixPrice"].set_column(12, 12, 30)
        writer.sheets["FixPrice"].set_column(13, 13, 30)
        writer.sheets["FixPrice"].set_column(14, 14, 30)
        # writer.sheets[sheet].set_column(17, 17, 30)
        writer.close()

    def write_txt_articles_with_bad_req(self):
        with open('articles_with_bad_req.txt', 'a') as output:
            for row in self.bad_req_list:
                output.write(str(row) + '\n')

    def start(self):
        articles = self.read_articles_from_txt()
        self.set_city()
        self.get_data_from_articles(articles)
        self.create_df()
        self.create_xls()
        self.write_txt_articles_with_bad_req()


def send_logs_to_telegram(message):
    bot_token = '6456958617:AAF8thQveHkyLLtWtD02Rq1UqYuhfT4LoTc'
    chat_id = '128592002'

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    data = {"chat_id": chat_id, "text": message}
    response = requests.post(url, data=data)
    return response.json()


def main():
    t1 = datetime.datetime.now()
    print(f'Start: {t1}')
    send_logs_to_telegram(message=f'Start: {t1}')
    try:
        InfoFixPrice().start()
    except Exception as exp:
        print(exp)
        res = send_logs_to_telegram(message=f'Произошла ошибка!\n\n\n{exp}')
        print(res)
    t2 = datetime.datetime.now()
    print(f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    main()
