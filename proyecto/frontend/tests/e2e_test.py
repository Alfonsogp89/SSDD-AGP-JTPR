"""
Tests E2E con Selenium — Proyecto SSDD 25-26
=============================================
Flujo cubierto:
  1. Registro de nuevo usuario
  2. Login con credenciales válidas
  3. Acceso a la pantalla de Chat (requiere autenticación)
  4. Crear un nuevo diálogo
  5. Seleccionar el diálogo creado
  6. Enviar un prompt
  7. Esperar y verificar la respuesta del asistente
  8. Logout
  9. Verificar que /chat redirige a login tras logout
"""

import time
import uuid
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

APP_URL = "http://localhost:5010"
TEST_PASSWORD = "selenium_pass_123"
TEST_NAME = "Selenium User"
TEST_PROMPT = "Hola, ¿cuál es la capital de Francia?"


def _chrome_driver():
    """Crea y devuelve un driver Chrome en modo headless."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


class Test01Registration(unittest.TestCase):
    """Prueba el registro de un nuevo usuario."""

    def setUp(self):
        self.driver = _chrome_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.email = f"selenium-{uuid.uuid4().hex[:8]}@example.com"

    def tearDown(self):
        self.driver.quit()

    def test_register_new_user(self):
        driver = self.driver
        wait = self.wait

        driver.get(f"{APP_URL}/register")

        wait.until(EC.presence_of_element_located((By.NAME, "name")))
        driver.find_element(By.NAME, "name").send_keys(TEST_NAME)
        driver.find_element(By.NAME, "email").send_keys(self.email)
        driver.find_element(By.NAME, "password").send_keys(TEST_PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()

        # Tras el registro debe redirigir al login
        wait.until(EC.url_contains("/login"))
        self.assertIn("/login", driver.current_url)


class Test02LoginAndLogout(unittest.TestCase):
    """Prueba login con credenciales válidas e inválidas, y logout."""

    def setUp(self):
        self.driver = _chrome_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.email = f"selenium-{uuid.uuid4().hex[:8]}@example.com"
        # Registrar usuario antes de los tests de login
        driver = self.driver
        driver.get(f"{APP_URL}/register")
        self.wait.until(EC.presence_of_element_located((By.NAME, "name")))
        driver.find_element(By.NAME, "name").send_keys(TEST_NAME)
        driver.find_element(By.NAME, "email").send_keys(self.email)
        driver.find_element(By.NAME, "password").send_keys(TEST_PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        self.wait.until(EC.url_contains("/login"))

    def tearDown(self):
        self.driver.quit()

    def _login(self, email, password):
        driver = self.driver
        driver.get(f"{APP_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()

    def test_login_valid_credentials(self):
        self._login(self.email, TEST_PASSWORD)
        self.wait.until(EC.url_matches(f"{APP_URL}/$"))
        self.assertNotIn("/login", self.driver.current_url)

    def test_login_invalid_credentials(self):
        self._login(self.email, "wrong_password_xyz")
        # Debe permanecer en /login con mensaje de error
        time.sleep(1)
        self.assertIn("/login", self.driver.current_url)
        page_source = self.driver.page_source
        self.assertTrue(
            "Invalid" in page_source or "invalid" in page_source or "error" in page_source.lower()
        )

    def test_logout_redirects(self):
        self._login(self.email, TEST_PASSWORD)
        self.wait.until(EC.url_matches(f"{APP_URL}/$"))
        self.driver.get(f"{APP_URL}/logout")
        # Tras logout no debe poder acceder a /chat
        self.driver.get(f"{APP_URL}/chat")
        time.sleep(1)
        self.assertIn("/login", self.driver.current_url)


class Test03ChatFlow(unittest.TestCase):
    """Prueba el flujo completo del chat: crear diálogo → prompt → respuesta."""

    def setUp(self):
        self.driver = _chrome_driver()
        self.wait = WebDriverWait(self.driver, 20)
        self.email = f"selenium-{uuid.uuid4().hex[:8]}@example.com"
        self.dialogue_name = f"test-dialogue-{uuid.uuid4().hex[:6]}"
        # Registrar + Login
        driver = self.driver
        driver.get(f"{APP_URL}/register")
        self.wait.until(EC.presence_of_element_located((By.NAME, "name")))
        driver.find_element(By.NAME, "name").send_keys(TEST_NAME)
        driver.find_element(By.NAME, "email").send_keys(self.email)
        driver.find_element(By.NAME, "password").send_keys(TEST_PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        self.wait.until(EC.url_contains("/login"))
        driver.find_element(By.NAME, "email").send_keys(self.email)
        driver.find_element(By.NAME, "password").send_keys(TEST_PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        self.wait.until(EC.url_matches(f"{APP_URL}/$"))

    def tearDown(self):
        self.driver.quit()

    def _go_to_chat(self):
        self.driver.get(f"{APP_URL}/chat")
        self.wait.until(EC.presence_of_element_located((By.ID, "create-dialogue")))

    def test_create_dialogue(self):
        """Verifica que se puede crear un diálogo nuevo."""
        self._go_to_chat()
        driver = self.driver
        wait = self.wait

        name_input = driver.find_element(By.ID, "new-dialogue-name")
        name_input.send_keys(self.dialogue_name)
        driver.find_element(By.ID, "create-dialogue").click()

        # El diálogo debe aparecer en la lista
        wait.until(EC.presence_of_element_located((By.ID, "dialogues")))
        time.sleep(1)  # Esperar que la lista se actualice vía JS
        dialogues_ul = driver.find_element(By.ID, "dialogues")
        self.assertIn(self.dialogue_name, dialogues_ul.text)

    def test_delete_dialogue(self):
        """Verifica que se puede eliminar un diálogo."""
        self._go_to_chat()
        driver = self.driver
        wait = self.wait

        name_input = driver.find_element(By.ID, "new-dialogue-name")
        name_input.send_keys(self.dialogue_name)
        driver.find_element(By.ID, "create-dialogue").click()

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#dialogues .list-group-item")))
        delete_btn = driver.find_element(By.CSS_SELECTOR, "#dialogues .list-group-item button.btn-danger")
        delete_btn.click()

        wait.until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()

        wait.until(lambda d: self.dialogue_name not in d.find_element(By.ID, "dialogues").text)

    def test_send_prompt_and_receive_response(self):
        """Crea un diálogo, envía un prompt y verifica que aparece la respuesta."""
        self._go_to_chat()
        driver = self.driver
        wait = self.wait

        # Crear diálogo
        name_input = driver.find_element(By.ID, "new-dialogue-name")
        name_input.send_keys(self.dialogue_name)
        driver.find_element(By.ID, "create-dialogue").click()
        time.sleep(1)

        # Seleccionar el diálogo (click en el primer item de la lista)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#dialogues .list-group-item")))
        first_dialogue = driver.find_element(By.CSS_SELECTOR, "#dialogues .list-group-item")
        first_dialogue.click()
        time.sleep(0.5)

        # Escribir y enviar el prompt
        prompt_input = driver.find_element(By.ID, "prompt-input")
        prompt_input.send_keys(TEST_PROMPT)
        driver.find_element(By.ID, "send-prompt").click()

        # Esperar a que aparezca el mensaje del usuario en el panel de mensajes
        wait.until(lambda d: "user:" in d.find_element(By.ID, "messages").text)
        messages_box = driver.find_element(By.ID, "messages")
        self.assertIn(TEST_PROMPT, messages_box.text)

        # Esperar la respuesta del asistente (hasta 40 segundos)
        print("\n[E2E] Esperando respuesta del asistente...")
        deadline = time.time() + 40
        while time.time() < deadline:
            time.sleep(2)
            messages_box = driver.find_element(By.ID, "messages")
            if "assistant:" in messages_box.text:
                break
        else:
            self.fail("El asistente no respondió en 40 segundos")

        # Verificar que el área de mensajes contiene una respuesta del asistente
        self.assertIn("assistant:", messages_box.text)
        print(f"[E2E] Respuesta recibida: {messages_box.text[:200]}")


class Test04AccessControl(unittest.TestCase):
    """Verifica que las rutas protegidas redirigen a login si no hay sesión."""

    def setUp(self):
        self.driver = _chrome_driver()
        self.wait = WebDriverWait(self.driver, 10)

    def tearDown(self):
        self.driver.quit()

    def test_chat_requires_login(self):
        self.driver.get(f"{APP_URL}/chat")
        self.wait.until(EC.url_contains("/login"))
        self.assertIn("/login", self.driver.current_url)

    def test_profile_requires_login(self):
        self.driver.get(f"{APP_URL}/profile")
        self.wait.until(EC.url_contains("/login"))
        self.assertIn("/login", self.driver.current_url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
