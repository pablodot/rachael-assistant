#!/bin/bash
# deploy.sh — Despliega Rachael en dracones02-servidor-ia
# Uso: ./deploy.sh [--skip-rsync] [--skip-deps] [--skip-llm]
set -e

SERVER="dracones02-servidor-ia"
REMOTE_DIR="~/codigo/her/v3"
LLM_MODEL="qwen2.5:14b-instruct-q8_0"

SKIP_RSYNC=false
SKIP_DEPS=false
SKIP_LLM=false

for arg in "$@"; do
  case $arg in
    --skip-rsync) SKIP_RSYNC=true ;;
    --skip-deps)  SKIP_DEPS=true ;;
    --skip-llm)   SKIP_LLM=true ;;
  esac
done

echo "═══════════════════════════════════════════════════════"
echo "  Rachael — Deploy → $SERVER"
echo "═══════════════════════════════════════════════════════"

# ── 1. Parar servicios locales ──────────────────────────────
echo ""
echo "▶ Parando servicios locales..."
docker compose down 2>/dev/null || true
pkill -f "browser-agent/main.py" 2>/dev/null || true
echo "  ✓ Servicios locales parados"

# ── 2. Sincronizar proyecto al servidor ────────────────────
if [ "$SKIP_RSYNC" = false ]; then
  echo ""
  echo "▶ Sincronizando proyecto al servidor..."
  ssh "$SERVER" "mkdir -p $REMOTE_DIR"
  rsync -av --progress \
    --exclude '.git' \
    --exclude 'chromium-profile' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.venv' \
    /home/pablo/codigo/her/v3/ \
    "$SERVER:$REMOTE_DIR/"
  echo "  ✓ Rsync completado"
fi

# ── 3. Instalar dependencias del sistema ──────────────────
if [ "$SKIP_DEPS" = false ]; then
  echo ""
  echo "▶ Instalando dependencias del sistema (xvfb, python3-venv)..."
  ssh "$SERVER" "sudo apt-get update -qq && sudo apt-get install -y xvfb python3-venv python3-pip"
  echo "  ✓ Dependencias del sistema instaladas"

  # ── 4. Entorno Python para browser-agent ─────────────────
  echo ""
  echo "▶ Creando venv e instalando dependencias Python del browser-agent..."
  ssh "$SERVER" "
    set -e
    cd $REMOTE_DIR/browser-agent
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r requirements.txt -q
    .venv/bin/playwright install chromium --with-deps
    echo '  ✓ Python env listo'
  "
fi

# ── 5. Crear .env del browser-agent ──────────────────────
echo ""
echo "▶ Creando browser-agent/.env en el servidor..."
ssh "$SERVER" "cat > $REMOTE_DIR/browser-agent/.env" <<'EOF'
BROWSER_HOST=0.0.0.0
BROWSER_PORT=8001
BROWSER_HEADLESS=false
BROWSER_SLOW_MO=50
BROWSER_CHROMIUM_PROFILE_DIR=./chromium-profile
EOF
echo "  ✓ .env creado"

# ── 6. Levantar servicios Docker ──────────────────────────
echo ""
echo "▶ Levantando servicios Docker en el servidor..."
ssh "$SERVER" "cd $REMOTE_DIR && docker compose pull --quiet && docker compose up -d --build"
echo "  ✓ Docker services up"

# ── 7. Arrancar browser-agent ─────────────────────────────
echo ""
echo "▶ Arrancando browser-agent con Xvfb..."
ssh "$SERVER" "
  pkill -f 'browser-agent/main.py' 2>/dev/null || true
  nohup bash $REMOTE_DIR/browser-agent/start.sh > /tmp/browser-agent.log 2>&1 &
  sleep 2
  echo '  ✓ browser-agent arrancado (log: /tmp/browser-agent.log)'
"

# ── 8. Tirar modelo LLM ───────────────────────────────────
if [ "$SKIP_LLM" = false ]; then
  echo ""
  echo "▶ Descargando modelo LLM: $LLM_MODEL"
  echo "  (esto puede tardar varios minutos dependiendo de la conexión)"
  ssh "$SERVER" "docker exec rachael-llm-runtime ollama pull $LLM_MODEL"
  echo "  ✓ Modelo $LLM_MODEL descargado"
fi

# ── 9. Verificación ───────────────────────────────────────
echo ""
echo "▶ Verificando servicios..."
sleep 3

BA_STATUS=$(ssh "$SERVER" "curl -sf http://localhost:8001/health && echo OK" 2>/dev/null || echo "FAIL")
API_STATUS=$(ssh "$SERVER" "curl -sf http://localhost:8000/health && echo OK" 2>/dev/null || echo "FAIL")

echo "  browser-agent :8001 → $BA_STATUS"
echo "  api-core      :8000 → $API_STATUS"

echo ""
echo "═══════════════════════════════════════════════════════"
if [[ "$BA_STATUS" == *"OK"* ]] && [[ "$API_STATUS" == *"OK"* ]]; then
  echo "  ✅ Rachael desplegada en $SERVER"
else
  echo "  ⚠️  Algunos servicios aún no están listos."
  echo "     Espera unos segundos y comprueba:"
  echo "     ssh $SERVER 'curl localhost:8001/health && curl localhost:8000/health'"
fi
echo ""
echo "  Prueba:"
echo "  curl -X POST http://$SERVER:8000/v1/chat \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"message\": \"abre el país y dame los titulares de hoy\"}'"
echo "═══════════════════════════════════════════════════════"
