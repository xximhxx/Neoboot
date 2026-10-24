#!/bin/sh
# NeoBoot 10 - MOD BY: Ibrahem Hamdan
# Installer / updater. Used by the plugin's "update" menu and can be run by hand:
#   wget -qO- --no-check-certificate https://raw.githubusercontent.com/xximhxx/Neoboot/main/iNB.sh | sh
REPO="https://raw.githubusercontent.com/xximhxx/Neoboot/main"
IPK_URL="$REPO/NeoBoot-Ibrahem-Hamdan.ipk"
IPK=/tmp/neoboot.ipk

rm -f "$IPK" /tmp/ver.txt > /dev/null 2>&1
echo "NeoBoot 10 (MOD BY: Ibrahem Hamdan) - downloading ..."
if command -v wget > /dev/null 2>&1; then
    wget -q --no-check-certificate -O "$IPK" "$IPK_URL" 2> /dev/null || wget -q -O "$IPK" "$IPK_URL" 2> /dev/null
fi
if [ ! -s "$IPK" ] && command -v curl > /dev/null 2>&1; then
    curl -kLs -o "$IPK" "$IPK_URL"
fi
if [ ! -s "$IPK" ] && command -v fullwget > /dev/null 2>&1; then
    fullwget --no-check-certificate -O "$IPK" "$IPK_URL"
fi
if [ ! -s "$IPK" ]; then
    echo "Download failed. Check the internet connection and try again."
    exit 1
fi
# an .ipk is an 'ar' archive: reject html error pages / truncated downloads
if [ "`head -c 8 "$IPK"`" != "!<arch>" ]; then
    echo "Downloaded file is not a valid ipk."
    rm -f "$IPK"
    exit 1
fi
echo "Installing ..."
opkg install --force-reinstall --force-overwrite "$IPK"
RET=$?
rm -f "$IPK" /tmp/.upneo > /dev/null 2>&1
exit $RET
