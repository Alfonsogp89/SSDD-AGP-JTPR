# Tests E2E — Selenium

## Requisitos previos

Asegúrate de tener el stack completo levantado:

```powershell
# Desde la raíz del proyecto
docker compose -f docker-compose-devel.yml up -d
```

Y en el directorio `frontend`, activa el venv:

```powershell
cd proyecto/frontend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecutar los tests

```powershell
# Con el venv activo:
python -m unittest tests.e2e_test -v
```

O un test concreto:

```powershell
python -m unittest tests.e2e_test.Test03ChatFlow.test_send_prompt_and_receive_response -v
```

## Tests incluidos

| Clase | Test | Descripción |
|---|---|---|
| `Test01Registration` | `test_register_new_user` | Registro y redirección a login |
| `Test02LoginAndLogout` | `test_login_valid_credentials` | Login correcto → index |
| `Test02LoginAndLogout` | `test_login_invalid_credentials` | Login erróneo → error en página |
| `Test02LoginAndLogout` | `test_logout_redirects` | Logout → /chat redirige a login |
| `Test03ChatFlow` | `test_create_dialogue` | Crear diálogo y verificar en lista |
| `Test03ChatFlow` | `test_send_prompt_and_receive_response` | Enviar prompt y recibir respuesta del asistente |
| `Test04AccessControl` | `test_chat_requires_login` | /chat sin sesión → /login |
| `Test04AccessControl` | `test_profile_requires_login` | /profile sin sesión → /login |

## Notas

- Los tests usan **Chrome en modo headless** vía `webdriver-manager` (se descarga automáticamente).
- El test de respuesta del asistente espera hasta **40 segundos** por la respuesta gRPC.
- Cada ejecución genera un email único (`selenium-XXXXXXXX@ssdd.test`) para evitar conflictos con datos anteriores.
