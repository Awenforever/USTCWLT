import tempfile
import time
# reqyests
import requests
from requests.exceptions import ConnectionError
# rich
from rich.progress import Console
# selenium
from selenium import webdriver
# from selenium.webdriver.chromium.service import ChromiumService
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Callable
import urllib3
from urllib3.exceptions import InsecureRequestWarning

import os

# dotenv
from dotenv import load_dotenv


urllib3.disable_warnings(InsecureRequestWarning)

load_dotenv()
NAME = os.getenv('APP_NAME')
PASSWORD = os.getenv('APP_PASSWORD')
console = Console()


class Observable:
    """
    data descriptor -> instance property -> non-data descriptor (solely __get__) -> Class Var -> AttributeError
    __dict__: ignore __setattr__
    getattr: trigger __getattr__
    """
    def __init__(self, output_type: type):
        self._observer: Callable | None = None
        self._old_v = None
        self._new_v = None
        self._output_type = output_type

    def __set_name__(self, owner, name):
        self.name = name
        self._old_v = f'_{self.name}_old_v'
        self._new_v = f'_{self.name}_v'

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__[self._new_v]

    def __set__(self, instance, value):
        assert isinstance(value, self._output_type), \
        f'Expecting input `value` to be {self._output_type}, got {type(value)} instead.'

        if not hasattr(instance, self._old_v):
            setattr(instance, self._old_v, None)
        if not hasattr(instance, self._new_v):
            setattr(instance, self._new_v, value)
        if hasattr(instance, self._old_v) and hasattr(instance, self._new_v):
            instance.__dict__[self._old_v], instance.__dict__[self._new_v] = (
                instance.__dict__[self._new_v], value
            )
        if instance.__dict__[self._old_v] != instance.__dict__[self._new_v]:
            assert self._observer is not None, \
                f'Set Observer before assigning value to `{self.name}` with method `add_observer`.'
            self._observer(value)

    def set_observer(self, observer: Callable):
        self._observer = observer

class Wlt:
    DRIVER_PATH = r'C:\Program Files (x86)\Microsoft\EdgeWebDriver\msedgedriver.exe'
    connection = Observable(bool)  # class property

    def __init__(self, timeout: int = 10):
        Wlt.connection.set_observer(self._on_changed_status)
        self.connection = False
        self.timeout = timeout
        self.temp_user_data_dir = tempfile.mkdtemp(prefix='edge_temp_profile_')
        self.options = Options()

        # 使用独立的用户数据目录
        self.options.add_argument(f'--user-data-dir={self.temp_user_data_dir}')

        # 禁用首次运行行为和导入功能
        self.options.add_argument('--no-first-run')
        self.options.add_argument('--no-default-browser-check')
        self.options.add_argument('--disable-default-apps')
        self.options.add_argument('--disable-component-update')
        # self.options.add_argument('--no-proxy-server')
        # self.options.add_argument('--proxy-bypass-list=*')

        # 禁用特定的导入功能
        self.options.add_experimental_option('excludeSwitches', [
            'enable-automation',
            'enable-logging'
        ])

        # 无头模式配置
        # self.options.add_argument('--headless')
        # self.options.add_argument('--disable-gpu')
        # self.options.add_argument('--no-sandbox')
        # self.options.add_argument('--disable-dev-shm-usage')

    @staticmethod
    def _on_changed_status(status):
        if status:
            console.log('[italic bright_green]Network connection is reestablished successfully!')
        else:
            console.log('[italic bright_red]Network connection is disconnected...')

    def _reconnect(self):
        service = Service(executable_path=self.DRIVER_PATH)
        with webdriver.ChromiumEdge(service=service, options=self.options) as driver:
            driver.get('http://wlt.ustc.edu.cn/cgi-bin/ip')
            wait = WebDriverWait(driver, 30)
            # ele_name = driver.find_element(By.NAME, 'name')
            # ele_password = driver.find_element(By.NAME, 'password')
            ele_name = wait.until(EC.presence_of_element_located((By.NAME, 'name')))
            ele_name.send_keys(NAME)
            ele_password = wait.until(EC.presence_of_element_located((By.NAME, 'password')))
            ele_password.send_keys(PASSWORD)
            ele_submit = wait.until(EC.presence_of_element_located((By.NAME, 'set')))
            ele_submit.click()
            console.log('Successfully logged in!')
            time.sleep(5)

    def listening(self):
        console.log('Start listening...')
        while True:
            self.connection = self._network_connectivity_test()
            if not self.connection:
                console.log('Reconnecting ...')
                try:
                    self._reconnect()
                    console.log('Connection reestablished successfully.')
                except Exception as e:
                    console.log(f'Connection failed @{str(e)[:100]}')
                    console.log('Retrying...')
                time.sleep(self.timeout)


    @staticmethod
    def _network_connectivity_test() -> bool:
        test_urls = [
            'http://www.baidu.com',
            'http://www.qq.com',
            'http://www.163.com'
        ]
        for url in test_urls:
            try:
                response = requests.get(url, timeout=10, verify=False)
                response.raise_for_status()
                return True
            except Exception as e:
                console.log(f'Network disconnected @{e}.')
                continue
        return False

    def __del__(self):
        try:
            import shutil
            shutil.rmtree(self.temp_user_data_dir, ignore_errors=True)
        except Exception as e:
            console.print(e)


if __name__ == '__main__':
    wlt = Wlt(10)
    try:
        wlt.listening()
    except KeyboardInterrupt:
        pass
    finally:
        del wlt