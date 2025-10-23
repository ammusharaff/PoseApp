#!/usr/bin/env bash
set -e
pyinstaller --noconfirm --clean \
  --name PoseApp \
  --onefile \
  --add-data "models:models" \
  --add-data "assets:assets" \
  app/main.py
