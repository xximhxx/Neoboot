#!/bin/sh
set -e
REPOSITORY=${1:-}
case "$REPOSITORY" in
    ''|*[!A-Za-z0-9_./-]*) echo 'Usage: sh install.sh OWNER/REPO'; exit 2 ;;
esac
case "$REPOSITORY" in
    */*) ;;
    *) echo 'Enter OWNER/REPO'; exit 2 ;;
esac
TMPDIR_NEO=`mktemp -d /tmp/neoboot-installer.XXXXXX`
trap 'rm -rf "$TMPDIR_NEO"' EXIT HUP INT TERM
URL="https://github.com/$REPOSITORY/releases/latest/download/install.py"
if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error --proto '=https' "$URL" -o "$TMPDIR_NEO/install.py"
else
    wget -O "$TMPDIR_NEO/install.py" "$URL"
fi
for NEO_PYTHON in python3 python python2; do
    if command -v "$NEO_PYTHON" >/dev/null 2>&1; then
        "$NEO_PYTHON" "$TMPDIR_NEO/install.py" --repository "$REPOSITORY" --install --reinstall
        exit $?
    fi
done
echo 'A working Python installation is required.'
exit 1
