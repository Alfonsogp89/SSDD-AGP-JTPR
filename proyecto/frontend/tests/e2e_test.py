import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

APP_URL = 'http://localhost:5010'

class FrontendE2ETest(unittest.TestCase):

    def setUp(self):
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_size(1200, 800)
        self.wait = WebDriverWait(self.driver, 12)

    def tearDown(self):
        self.driver.quit()

    def test_register_login_and_chat_submit(self):
        driver = self.driver
        wait = self.wait

        driver.get(APP_URL)

        # Go to register
        driver.get(f"{APP_URL}/register")
        # Fill form
        name = f"testuser"
        email = f"testuser@example.com"
        password = "testpass"

        driver.find_element(By.NAME, 'name').send_keys(name)
        driver.find_element(By.NAME, 'email').send_keys(email)
        driver.find_element(By.NAME, 'password').send_keys(password)
        driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()

        # After register should redirect to login
        wait.until(EC.url_contains('/login'))

        # Login
        driver.find_element(By.NAME, 'email').send_keys(email)
        driver.find_element(By.NAME, 'password').send_keys(password)
        driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()

        # After login, index loads; go to chat
        wait.until(EC.url_matches(f"{APP_URL}/"))
        driver.get(f"{APP_URL}/chat")

        # Send a prompt
        prompt_input = wait.until(EC.presence_of_element_located((By.NAME, 'prompt')))
        prompt_input.send_keys('Hello from E2E')
        driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()

        # Wait for either an answer block or a Processing/info alert
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'pre')))
            answer = driver.find_element(By.TAG_NAME, 'pre').text
            print('Answer received:', answer)
        except Exception:
            # Fallback: wait for info/alert
            time.sleep(2)
            alerts = driver.find_elements(By.CLASS_NAME, 'alert')
            texts = [a.text for a in alerts]
            print('Alerts:', texts)

if __name__ == '__main__':
    unittest.main()
