import json
import time
import requests
from pathlib import Path

import urllib
from urllib.request import urlopen as uReq

from selenium.webdriver import Chrome
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Keys, ActionChains

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


class FixPriceArticles:
    def __init__(self):
        self.save_path = f'{str(Path(__file__).parents[1])}'
        self.__main_url = 'https://fix-price.com'
        self.catalog = 'catalog'
        self.all_art = []
        self.options = Options()
        self.options.add_argument("--start-maximized")
        self.service = Service('chromedriver.exe')
        self.bad_brand_list = []

    def read_catalogs_from_txt(self):
        """Считывает и возвращает список актуальных каталогов из файла"""
        with open('catalogs.txt', 'r', encoding='utf-8') as file:
            catalogs = [f'{line}'.rstrip() for line in file]
            return catalogs

    def write_txt_file_all_articles(self):
        with open('fix_price_articles.txt', 'a') as output:
            for row in self.all_art:
                output.write(str(row[9:]) + '\n')

    def get_catalogs(self):
        catalog_urls = []
        """Получить список с каталогами (Новинки, сейчас покупаю и т.д.)
        Сделано 1 раз. Далее результат в файл catalog.txt, потому как отсеяны пересекающиеся категории.
        Например: газ.вода есть в разделе напитки и в разделе сейчас покупают, поэтому раздел сейчас покупают убран"""
        r = requests.get(f'{self.__main_url}/catalog')
        soup = BeautifulSoup(r.text, 'lxml')
        tiles_wrapper = soup.find('div', class_='tiles-wrapper').findAll('a', href=True)
        for url in tiles_wrapper:
            print(url.attrs['href'])
            catalog_urls.append(url.attrs['href'])
        return catalog_urls

    def get_arts_in_catalogs(self, catalogs):
        """Получить список товаров из каталога, проход по всем страницам"""
        # url = 'https://fix-price.com/catalog/produkty-i-napitki?sort=sold&page='
        for i in range(len(catalogs)):
            url = f'{self.__main_url}/{catalogs[i]}'
            page = 1
            print(f'{bcolors.OKGREEN}{catalogs[i]}{bcolors.ENDC}')
            while True:
                try:
                    print(page)
                    r = requests.get(f'{url}?sort=sold&page={page}')
                    time.sleep(1)
                    soup = BeautifulSoup(r.text, 'lxml')
                    products = soup.find('div', class_='products').find_all('div', class_='description')
                    if products:
                        for descr in products:
                            print(descr.next_element.attrs['href'])
                            self.all_art.append(descr.next_element.attrs['href'])
                        page += 1
                        print()
                    else:
                        break
                except Exception as exp:
                    print(f'{bcolors.FAIL}ERROR: {exp}{bcolors.ENDC}')
                    time.sleep(10)
                    continue

    def start(self):
        # catalog_urls = self.get_catalogs()
        catalogs = self.read_catalogs_from_txt()
        self.get_arts_in_catalogs(catalogs)
        self.write_txt_file_all_articles()
        print()


if __name__ == '__main__':
    FixPriceArticles().start()
