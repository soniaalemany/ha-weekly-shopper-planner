#!/usr/bin/env bash
# Prepara el entorno de desarrollo: venv, Home Assistant, pytest y enlace de la integración.
set -euo pipefail
cd "$(dirname "$0")/.."

# Home Assistant reciente exige Python >= 3.14 (comprueba `requires_python` en PyPI).
PYTHON="${PYTHON:-python3}"
command -v uv >/dev/null && USE_UV=1 || USE_UV=0

if [ "$USE_UV" = 1 ]; then
  uv venv --python "${PY_VERSION:-3.14}" .venv
  uv pip install --python .venv/bin/python -r requirements_dev.txt
else
  "$PYTHON" -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install -r requirements_dev.txt
fi

# Enlaza la integración dentro de la configuración de desarrollo
ln -sfn "$(pwd)/custom_components/weekly_shopper" config/custom_components/weekly_shopper

.venv/bin/python -c "import homeassistant.const as c; print('Home Assistant', c.__version__)"
echo "Listo. Arranca HA con:  .venv/bin/hass -c ./config   (http://localhost:8123)"
echo "Tests:                  .venv/bin/pytest"
