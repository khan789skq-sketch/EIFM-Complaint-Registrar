EIFM UPDATED SOURCE - Android + Python API

Included: original WCC PDF and Word, Excel templates, EIFM logo, Flutter main.dart/pages.dart, Codemagic YAML, Python API and PDF generator.

Normal WCC: output is WCC.pdf, with original PDF as page 1, typed fields overlaid and Before/After photos on page 2 with address/footer. PPM WCC keeps previous checklist/package behavior.

Deploy Python backend to Render using: pip install -r backend_requirements.txt ; uvicorn main:app --host 0.0.0.0 --port $PORT
Flutter backend URL: https://eifm-wcc-api.onrender.com. Verify that this is your deployed Python service.
Codemagic: select codemagic.yaml > EIFM Android APK, not Default Workflow Editor. Do not remove original templates.

IMPORTANT: Source bundle is not APK build-tested or live-backend-tested here. Text overlay coordinates and photo crop UI should be checked with a real completed WCC. Crop fallback retains selected photo if native cropper fails; a device-level native freeze cannot be guaranteed fixed without testing.
