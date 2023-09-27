import time

from playwright.sync_api import Playwright, sync_playwright, expect

js = """
Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
"""


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.add_init_script(js)
    page.goto("https://fix-price.com/")
    page.get_by_text("Москва").click()
    time.sleep(2)
    page.get_by_placeholder(text='Ваш город').type(text='Брянск', delay=0.5)
    time.sleep(10)
    page.get_by_text("Брянск").click()
    time.sleep(10)


    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
