Prerequisites

- The frontend app must be running locally on port 5010 (default). Start it from `proyecto/frontend`:

```powershell
# create venv (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app/app.py
```

Run E2E

```powershell
# In another shell with the virtualenv active
python -m unittest tests.e2e_test
```

Notes

- The test uses headless Chrome via `webdriver-manager`. Ensure Chrome is installed on the host.
- If running in CI, consider using a dedicated Chrome image or a Selenium Grid.
