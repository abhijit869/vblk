#!/bin/bash
set -e
echo "=> Starting JARVIS Firewall Audit..."
# Check for active firewall mechanism
FW=""
if command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
    FW="ufw"
elif command -v iptables >/dev/null 2>&1 && sudo iptables -S | grep -q "\-P INPUT DROP"; then
    FW="iptables"
elif command -v nft >/dev/null 2>&1 && sudo nft list ruleset | grep -q "table inet filter"; then
    FW="nftables"
fi

if [ -z "$FW" ]; then
    echo "FAIL: No active firewall mechanism found!"
    exit 1
fi
echo "PASS: Active firewall is $FW"
exit 0
