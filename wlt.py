# local
import os
import tempfile
import time
from pathlib import Path
from typing import Callable
import zipfile
import shutil
import winreg
import subprocess
import urllib3
# dotenv
from dotenv import load_dotenv
# rich
from rich.progress import Console
# selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib3.exceptions import InsecureRequestWarning

# requests
import requests

urllib3.disable_warnings(InsecureRequestWarning)

load_dotenv()
NAME = os.getenv('APP_NAME')
PASSWORD = os.getenv('APP_PASSWORD')
console = Console()


def is_driver_version_compatible(driver_path, edge_version):
    try:
        # 获取 WebDriver 的版本号
        result = subprocess.run([driver_path, '--version'], capture_output=True, text=True)
        driver_version = result.stdout.strip().split()[3]  # 提取版本号部分

        # 比较前三段版本号
        driver_parts = driver_version.split('.')[:3]
        edge_parts = edge_version.split('.')[:3]

        return driver_parts == edge_parts
    except Exception as e:
        print(f"错误：{e}")
        return False


def get_edge_version():
    try:
        reg_path = r"SOFTWARE\Microsoft\Edge\BLBeacon"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            version, _ = winreg.QueryValueEx(key, "version")
            return version
    except Exception as e:
        print(f"Error retrieving Edge version: {e}")
        return None


def setup_edge_webdriver(version):
    base_url = f"https://msedgedriver.microsoft.com/{version}/edgedriver_win64.zip"
    zip_path = "edgedriver_win64.zip"
    extract_dir = "extracted_driver"

    print(f"Downloading from: {base_url}")
    response = requests.get(base_url)
    with open(zip_path, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    target_dir = os.path.expanduser(r"~\EdgeWebDriver")
    os.makedirs(target_dir, exist_ok=True)

    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file == "msedgedriver.exe":
                shutil.move(os.path.join(root, file), os.path.join(target_dir, file))
                print(f"msedgedriver.exe moved to {os.path.join(target_dir, file)}")
                return

    print("msedgedriver.exe not found in the extracted files.")


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
    DRIVER_PATH = Path(r'~\EdgeWebDriver\msedgedriver.exe').expanduser()
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

        self.options.add_argument('--allow-running-insecure-content')
        self.options.add_argument('--ignore-certificate-errors')

        # 禁用自动HTTPS升级
        self.options.add_experimental_option('prefs', {
            'profile.default_content_setting_values.insecure_ssl': 1,
            'profile.managed_default_content_settings.images': 1
        })

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
            driver.get('http://wlt.ustc.edu.cn/')
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
            if self.connection:
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
    e_version = get_edge_version()

    if Wlt.DRIVER_PATH.exists():
        if not is_driver_version_compatible(Wlt.DRIVER_PATH, e_version):
            setup_edge_webdriver(e_version)
    else:
        setup_edge_webdriver(e_version)

    wlt = Wlt(10)
    try:
        wlt.listening()
    except KeyboardInterrupt:
        pass
    finally:
        del wlt
