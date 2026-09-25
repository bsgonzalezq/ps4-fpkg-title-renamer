#!/usr/bin/env bash
# Install / verify prerequisites for ps4-title-renamer: Python 3.8+ and git.
# Supports apt (Debian/Ubuntu), dnf (Fedora/RHEL), pacman (Arch), zypper (openSUSE) and Homebrew (macOS).
set -euo pipefail

MIN_PY="3.8"
cd "$(dirname "$0")"

SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null; then SUDO="sudo"; fi

install_pkgs() {
    echo "Installing: $*"
    if command -v apt-get >/dev/null; then
        $SUDO apt-get update && $SUDO apt-get install -y "$@"
    elif command -v dnf >/dev/null; then
        $SUDO dnf install -y "$@"
    elif command -v pacman >/dev/null; then
        # Arch names the package "python", not "python3"
        $SUDO pacman -S --needed --noconfirm "${@/python3/python}"
    elif command -v zypper >/dev/null; then
        $SUDO zypper install -y "$@"
    elif command -v brew >/dev/null; then
        brew install "${@/python3/python}"
    else
        echo "No supported package manager found. Install manually: $*" >&2
        exit 1
    fi
}

missing=()
command -v python3 >/dev/null || missing+=(python3)
command -v git >/dev/null || missing+=(git)
if [ ${#missing[@]} -gt 0 ]; then
    install_pkgs "${missing[@]}"
fi

# Python version check
if ! python3 -c "import sys; sys.exit(sys.version_info < tuple(map(int, '$MIN_PY'.split('.'))))"; then
    echo "Python $MIN_PY+ required, found $(python3 --version 2>&1). Please upgrade Python." >&2
    exit 1
fi

# No third-party packages today; this keeps working if any are added later
if [ -s requirements.txt ] && grep -qv '^\s*\(#\|$\)' requirements.txt; then
    python3 -m pip install --user -r requirements.txt
fi

chmod +x ps4_rename.py

echo
echo "OK: $(python3 --version 2>&1), $(git --version)"
python3 ps4_rename.py -h >/dev/null && echo "OK: ps4_rename.py runs. Try: ./ps4_rename.py --help"
