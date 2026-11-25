#!/usr/bin/env bash
# Lo que no tiene que ver nadie, cifrado con la contraseña CLAVE_PRIVADA (AES-256, openssl).
#
# El repo es público: el historial (títulos y temas), los vídeos programados y el vídeo
# del día se guardan CIFRADOS. Sin la contraseña no se pueden abrir.
#
#   bash privado.sh abrir                     canales/privado.enc → historial y programados
#   bash privado.sh cerrar                    historial y programados → canales/privado.enc
#   bash privado.sh empaquetar CARPETA SALIDA.enc    el vídeo del día y sus archivos
#   bash privado.sh desempaquetar FICHERO.enc DESTINO   (en el PC, para ver el vídeo)
#
# En el PC (Git Bash):  CLAVE_PRIVADA='la-contraseña' bash privado.sh desempaquetar ...
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANALES="$AQUI/canales"
CERRADO="$CANALES/privado.enc"
FICHEROS=(circulo-cerrado-historial.md circulo-cerrado-programados.json)

morir() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }
[ -n "${CLAVE_PRIVADA:-}" ] || morir "Falta CLAVE_PRIVADA (el secreto con la contraseña)."

cifrar()   { openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:CLAVE_PRIVADA; }
descifrar(){ openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:CLAVE_PRIVADA; }

case "${1:-}" in
  abrir)
    if [ -f "$CERRADO" ]; then
      descifrar < "$CERRADO" | tar -xz -C "$CANALES" || morir "No se puede abrir privado.enc: ¿contraseña cambiada?"
      echo "==> Historial y programados abiertos."
    else
      echo "==> Todavía no hay privado.enc: es el primer vídeo."
    fi ;;
  cerrar)
    HAY=()
    for f in "${FICHEROS[@]}"; do [ -f "$CANALES/$f" ] && HAY+=("$f"); done
    [ ${#HAY[@]} -gt 0 ] || { echo "==> Nada que cerrar."; exit 0; }
    tar -cz -C "$CANALES" "${HAY[@]}" | cifrar > "$CERRADO.tmp"
    mv "$CERRADO.tmp" "$CERRADO"
    echo "==> Historial y programados cifrados en privado.enc." ;;
  empaquetar)
    CARPETA="${2:?falta la carpeta}"; SALIDA="${3:?falta el fichero de salida}"
    ( cd "$CARPETA" && tar -c --ignore-failed-read video.mp4 portada.jpg escenas.json resumen.json \
        guion.txt tiempos.json medidas.json dia.log claude.log imagenes 2>/dev/null || true ) | cifrar > "$SALIDA"
    echo "==> Paquete cifrado: $(du -h "$SALIDA" | cut -f1)" ;;
  desempaquetar)
    FICHERO="${2:?falta el fichero .enc}"; DESTINO="${3:?falta la carpeta de destino}"
    mkdir -p "$DESTINO"
    descifrar < "$FICHERO" | tar -x -C "$DESTINO" || morir "No se puede abrir: ¿contraseña bien puesta?"
    echo "==> Abierto en $DESTINO" ;;
  *) morir "Uso: privado.sh abrir | cerrar | empaquetar CARPETA SALIDA.enc | desempaquetar FICHERO.enc DESTINO" ;;
esac
