# scripts/build_windows.ps1
# Run in venv with deps installed
pyinstaller --noconfirm --clean `
  --name PoseApp `
  --onefile `
  --add-data "models;models" `
  --add-data "assets;assets" `
  app/main.py
