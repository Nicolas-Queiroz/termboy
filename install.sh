#!/usr/bin/env bash
# Instala o termboy em ~/.local/bin. Só precisa de Python 3.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null 2>&1 || { echo "Precisa do python3 instalado."; exit 1; }
mkdir -p "$HOME/.local/bin"
install -m 755 "$DIR/termboy" "$HOME/.local/bin/termboy"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) echo "Pronto! Rode: termboy" ;;
  *) printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$HOME/.bashrc"
     echo "Pronto! Abra um terminal novo e rode: termboy" ;;
esac
