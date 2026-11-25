#!/usr/bin/env bash
# Paso 1 del vídeo de Círculo Cerrado: Claude escribe escenas.json y resumen.json.
#
#   cd CARPETA_DEL_VIDEO && bash .../automatizacion/guion.sh
#
# Claude SOLO escribe (no monta nada): así el vídeo de 12 min gasta del plan Pro más o
# menos lo mismo que un short. Necesita CLAUDE_CODE_OAUTH_TOKEN (claude setup-token).
# Opcional: IDEA="..." para mandar la historia del día; HISTORIAL=ruta al historial.
set -euo pipefail
export LC_ALL=C.UTF-8

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIEF="$AQUI/canales/circulo-cerrado.md"
HISTORIAL="${HISTORIAL:-$AQUI/canales/circulo-cerrado-historial.md}"
FECHA="$(TZ=Europe/Madrid date +%Y-%m-%d)"
MODELO="${CLAUDE_MODEL:-claude-sonnet-5-5}"   # Sonnet: con Opus se acaba el límite del Pro
IDEA="${IDEA:-}"

aviso() { printf '\n==> %s\n' "$1"; }
morir() { printf '\nERROR: %s\n' "$1" >&2; exit 1; }

command -v claude >/dev/null || morir "No encuentro el comando 'claude'."
command -v python3 >/dev/null || morir "No encuentro python3."
[ -f "$BRIEF" ] || morir "No existe el brief: $BRIEF"
if [ -n "${MODAL_TASK_ID:-}" ] && [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}${ANTHROPIC_API_KEY:-}" ]; then
  morir "Falta CLAUDE_CODE_OAUTH_TOKEN en el secreto de Modal (sale de: claude setup-token)."
fi

# --- El encargo: prompt.md + brief + historial (+ idea) ----------------------
{
  sed -e "s|{{FECHA}}|$FECHA|g" -e "s|{{COMPROBAR}}|$AQUI/comprobar_guion.py|g" "$AQUI/prompt.md"
  printf '\n---\n\n## El brief del canal\n\n'
  cat "$BRIEF"
  printf '\n---\n\n## Lo que ya has contado en este canal (no lo repitas)\n\n'
  if [ -s "$HISTORIAL" ]; then cat "$HISTORIAL"; else echo "Todavía nada: este es el primero."; fi
  if [ -n "$IDEA" ]; then
    printf '\n---\n\n## La idea de hoy (manda sobre la elección de historia)\n\n%s\n' "$IDEA"
  fi
} > encargo.md

# --- Claude escribe ----------------------------------------------------------
# Sin nadie delante, cualquier herramienta que pida permiso se queda bloqueada
# (fallo 1 de Curiosidades). Le dejamos solo escribir en esta carpeta y lanzar
# el comprobador.
aviso "Claude escribe el guion (modelo $MODELO)"
set +e
claude -p "$(cat encargo.md)" \
  --model "$MODELO" \
  --max-turns "${MAX_TURNS:-40}" \
  --permission-mode acceptEdits \
  --allowedTools "Read" "Write" "Edit" "Bash(python3:*)" \
  --verbose 2>&1 | tee claude.log
SALIO=${PIPESTATUS[0]}
set -e
[ "$SALIO" -eq 0 ] || morir "Claude ha terminado mal (código $SALIO). Mira claude.log."

# --- ¿Vale lo que ha escrito? -------------------------------------------------
python3 "$AQUI/comprobar_guion.py" . || morir "El guion no pasa la comprobación. Mira claude.log."
aviso "Guion listo."
