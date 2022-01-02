import sys
import os
from time import sleep
from typing import Tuple

from selenium.webdriver import Edge

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import TimeoutException

from revasbot.revas_console import RevasConsole as console
from revasbot.revas_core import RevasCore
from revasbot.revas_pandas import RevasPandas

class RevasSelenium:
    def __init__(self, usr_name: str, passwd: str) -> None:
        caps = DesiredCapabilities().EDGE.copy()
        caps['pageLoadStrategy'] = 'eager'

        self.driver = Edge(capabilities=caps)
        # self.driver.maximize_window()
        self.driver.set_window_size(800, 600)
        self.driver.minimize_window()

        self.driver.get('https://gry.revas.pl/')

        self.usr_name = usr_name
        self.passwd = passwd

        self.url = ''
        self.game_name = ''
        self.game_id = ''
        self.download_path = os.path.expanduser('~/Downloads')

    def login(self) -> None:
        self.driver.find_element(By.ID, 'logEmail').send_keys(self.usr_name)
        self.driver.find_element(
            By.ID, 'logPassword'
        ).send_keys(self.passwd + Keys.RETURN)

        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'join_btn'))
        )

        games = RevasCore.get_games(self.driver)
        self.game_id = RevasCore.choose_game(games)

        self.get_schedule()
        self.driver.find_element(By.ID, f'join_btn_{self.game_id}').click()

        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'game_url'))
        )

        url = self.driver.current_url

        self.url = url[:url.index('.pl/') + 4]
        self.game_name = url[8 : url.index('.')]

    def get_data_count(self, mod: str) -> int:
        self.driver.get(self.url + mod + '.php')

        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'light-well-item'))
            )

            count = len(self.driver.find_elements(By.CLASS_NAME, 'light-well-item'))
        except TimeoutException:
            count = 6

        return count

    def get_xlsx(self, item_data: Tuple[str, str, str, str]) -> str:
        id_name, item_id, mod, action = item_data

        download_url = \
            self.url + \
            f'ajax.php?mod={mod}&action={action}-export-to-exel&{id_name}=' + \
            f'{item_id}&tab=empty&atype=json'

        self.driver.set_page_load_timeout(2)
        self.driver.get(download_url)
        
        sleep(1)

        for down_file in os.listdir(self.download_path):
            if (
                'Dostawca' in down_file or
                'Wymagania dotyczące usługi' in down_file or
                'Lista pracowników dostępnych na rynku pracy' in down_file or
                'Historia rachunku' in down_file
            ):
                return down_file

        return ''

    def get_schedule(self) -> None:
        schedule_path = self.driver.find_element(
            By.XPATH,
            f'//TR[TD/BUTTON/@playergameid={self.game_id}]/TD/A[@data-toggle]'
        ).get_attribute('href')

        self.driver.get(schedule_path)

        table = WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'table-in-modal-dialog'))
        )

        rows = table.find_elements(By.TAG_NAME, 'tr')

        arr = []

        for row in rows:
            cells = row.find_elements(By.XPATH, './*')

            if cells[0].tag_name == 'th':
                arr.append([cell.text for cell in cells])
            else:
                arr.append([
                    cells[0].text,
                    cells[1].text,
                    not (cells[2].find_element(By.XPATH, './*').tag_name == 'hr' or
                    'blocked' in cells[2].find_element(By.XPATH, './*').get_attribute('src'))
                ])

            # print(cells[2].find_element(By.XPATH, './*').tag_name)

        # print(dir(rows[0]))

        # table_text = table.text.split('\n')

        RevasPandas.muli_dim_arr_to_csv(
            arr,
            os.path.join(os.getcwd(), f'download/schedule/{self.game_id}.csv')
        )

        self.driver.get_screenshot_as_file(
            os.path.join(os.getcwd(), f'download/schedule/{self.game_id}.png')
        )
        self.driver.minimize_window()

        console.debug(schedule_path)
        self.driver.back()

    def quit(self, timeout: float=0) -> None:
        sleep(timeout)

        self.driver.quit()
        sys.exit()