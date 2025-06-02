#!/usr/bin/env bash
# install.sh ─ szybka instalacja zależności dla backendu FastAPI + CLIPS

set -e          # przerwij skrypt przy pierwszym błędzie
set -u          # traktuj nie-zdefiniowane zmienne jako błąd
set -o pipefail # propaguj błędy w potokach

echo "👉 Tworzę wirtualne środowisko (./venv)…"
python -m venv venv

echo "👉 Aktywuję środowisko i aktualizuję pip…"
source venv/bin/activate
python -m pip install --upgrade pip

echo "👉 Instaluję zależności z requirements.txt…"
pip install -r requirements.txt

echo -e "\n✅ Gotowe! Aby pracować, pozostań w środowisku venv:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload"
