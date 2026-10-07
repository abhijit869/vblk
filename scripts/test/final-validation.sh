#!/bin/bash
set -e
RAM=${1:-2048}
CPU=${2:-2}
ISO="dist/JARVIS-OS-1.0-amd64.iso"
echo "=== BOOTING ISO IN QEMU WITH ${RAM}MB RAM, ${CPU} vCPUs ==="

qemu-system-x86_64 -m $RAM -smp $CPU -cdrom $ISO -boot d -display none \
  -qmp tcp:localhost:4444,server,nowait \
  -netdev user,id=n1,hostfwd=tcp::2223-:22 -device e1000,netdev=n1 &
QEMU_PID=$!

sleep 5
# Send Enter key to GRUB to boot default immediately
echo '{"execute": "qmp_capabilities"}' > qmp.cmds
echo '{"execute": "send-key", "arguments": {"keys": [{"type": "qcode", "data": "ret"}]}}' >> qmp.cmds
nc -N localhost 4444 < qmp.cmds > /dev/null

echo "Waiting for SSH to become available..."
MAX_RETRIES=60
RETRY=0
while ! sshpass -p live ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2223 user@localhost 'echo "SSH UP"' >/dev/null 2>&1; do
    sleep 5
    RETRY=$((RETRY+1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "FAIL: SSH never came up"
        kill $QEMU_PID
        exit 1
    fi
done

echo "SSH IS UP. Running validations inside VM..."
sshpass -p live ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2223 user@localhost << 'VM_SCRIPT'
set -e
echo "--- SYSTEMD STATUS ---"
sudo systemctl is-system-running || true
sudo systemctl --failed --no-pager || true

echo "--- JARVIS SERVICES ---"
sudo systemctl is-active jarvis-core.service || true
sudo systemctl is-active jarvis-eventbus.service || true

echo "--- LOCAL AI TEST ---"
sudo systemctl start jarvis-local-ai.service || true
sleep 10
curl -s http://127.0.0.1:8081/v1/models || echo "FAILED"

echo "--- OFFLINE TEST (KILLING NETWORK) ---"
sudo iptables -A OUTPUT -p tcp --dport 80 -j DROP
sudo iptables -A OUTPUT -p tcp --dport 443 -j DROP

echo "Running offline tool call test..."
echo '{"prompt": "What is the CPU?", "tools": ["get_cpu_usage"]}' > test.json
curl -s -X POST http://127.0.0.1:8081/v1/chat/completions -d @test.json || echo "TOOL CALL FAILED"
VM_SCRIPT

echo "=== VALIDATION COMPLETE ==="
echo '{"execute": "qmp_capabilities"}' > qmp.cmds
echo '{"execute": "quit"}' >> qmp.cmds
nc -N localhost 4444 < qmp.cmds > /dev/null
kill $QEMU_PID 2>/dev/null || true
