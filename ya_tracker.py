from time import sleep
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options


class ProcessData:
    """
    Класс, отвечающий за получение и обработку данных
    страниц.
    """
    def __init__(self, repo_id) -> None:
        # id папки
        self.repo_id = repo_id

    def get_page(self, driver: webdriver.Remote):
        # получение страницы
        url = f'https://disk.yandex.ru/d/{self.repo_id}'

        driver.get(url)

    def extract_data(self, page_source):
        # получение даты последнего изменения
        last_date = None

        soup = BeautifulSoup(page_source, 'html.parser')

        dates = soup.find_all(
            'div',
            class_='listing-item__column listing-item__column_date'
        )

        if dates:
            last_date = (
                max(
                    datetime.strptime(date.text, "%d.%m.%Y").date()
                    for date in dates
                )
            )

        return last_date


class ClickElements:
    """
    Класс, отвечающий за поиск и клик элементов.
    """
    def find_clickable_folders(self, source):
        # Поиск элементов для клика
        soup = BeautifulSoup(source, 'html.parser')
        click_names: List[BeautifulSoup] = soup.find_all(
            'div',
            class_=(
                'listing-item listing-item_theme_row listing-item_size_m '
                'listing-item_type_dir js-prevent-deselect'
            )
        )

        return [
            elem.find(
                'div',
                class_='listing-item__title listing-item__title_overflow_clamp'
            )['aria-label'] for elem in click_names
        ]

    def click_folder(self, folder_name, driver: webdriver.Remote):
        # Ожидание, пока элемент с нужным aria-label станет кликабельным
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    f"div[aria-label='{folder_name}']"
                )
            )
        )

        # дабл клик по папке
        actions = ActionChains(driver)
        actions.double_click(element).perform()

        sleep(3)

    def call_back(self, driver: webdriver.Remote):
        # вернуться на прошлую вкладку
        driver.back()


class YaTracker(ClickElements, ProcessData):
    """
    Класс, начинающий программы.
    """
    def __init__(self, repo_id) -> None:
        super().__init__(repo_id)

    def get_browser_options(self):
        browser_options = Options()

        browser_options.add_argument("--no-sandbox")
        browser_options.add_argument("--disable-gpu")
        browser_options.add_argument("--start-maximized")

        return browser_options

    def process_folders(self, driver: webdriver.Remote, max_date=None):
        # рекурсивный вызов папок и выявление последней даты

        page_source = driver.page_source
        folders = self.find_clickable_folders(page_source)

        if folders:
            for folder in folders:
                self.click_folder(folder, driver)
                current_date = self.process_folders(driver, max_date)
                self.call_back(driver)

                if current_date \
                        and (max_date is None or current_date > max_date):
                    max_date = current_date

        else:
            current_folder_date = self.extract_data(page_source)

            if current_folder_date \
                    and (max_date is None or current_folder_date > max_date):
                max_date = current_folder_date

        return max_date

    def start_selenium(self):
        # запуск браузера и получение экземпляра driver

        browser_options = self.get_browser_options()

        with webdriver.Remote(
            command_executor='http://localhost:4444/wd/hub',
            options=browser_options
        ) as driver:

            self.get_page(driver)

            max_date = self.process_folders(driver)

            return max_date


def main():
    tracker = YaTracker('your_folder_id')
    last_change = tracker.start_selenium()
    print(f"LAST CHANGE OCCURED: {last_change}")


if __name__ == "__main__":
    main()
