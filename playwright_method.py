import time

from playwright.sync_api import Playwright, sync_playwright, expect


class FixParser():
    def __init__(self):
        self.js = """
        Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
        """

    def set_city(self):
        page = self.context.new_page()
        page.add_init_script(self.js)
        page.goto("https://fix-price.com/")
        page.get_by_text("Москва").click()
        time.sleep(2)
        page.get_by_placeholder(text='Ваш город').type(text='Брянск', delay=0.5)
        time.sleep(5)
        page.locator('//*[@id="modal"]/div/div[4]/div/div[1]').click()
        time.sleep(5)
        page.locator('//*[@id="modal"]/div/div/div/button[2]').click()
        page.locator('//*[@id="app-header"]/header/div/div[1]/div[1]/div[2]/div[2]/div[1]').click()
        page.locator('//*[@id="modal"]/div/div/div/div[3]/div/div[2]/div').click()  # выбрать магазин
        time.sleep(5)
        find_shop_placeholder = page.locator(
            '//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/input')
        find_shop_placeholder.click()
        find_shop_placeholder.type(text='г.Брянск, ул.Бежицкая, д.1Б', delay=1.5)
        time.sleep(5)
        page.locator('//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[5]/div/div[1]').click()
        time.sleep(5)
        page.locator('//*[1]/ymaps/div/div/button/span').click()
        time.sleep(15)

        # # ---------------------
        # context.close()
        # browser.close()

    def start(self):
        with sync_playwright() as playwright:
            self.browser = playwright.chromium.launch(headless=False)
            self.context = self.browser.new_context()
            self.set_city()


if __name__ == '__main__':
    FixParser().start()
