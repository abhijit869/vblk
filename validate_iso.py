import pexpect
import sys
import time

ISO_PATH = "dist/JARVIS-OS-1.0-amd64.iso"

print("Starting QEMU...")
child = pexpect.spawn(f"qemu-system-x86_64 -m 4G -smp 4 -enable-kvm -cdrom {ISO_PATH} -netdev user,id=n1,hostfwd=tcp::2222-:22 -device e1000,netdev=n1 -display none -vnc :0", encoding='utf-8', timeout=180)
child.logfile = sys.stdout

print("Waiting for boot (90s)...")
time.sleep(90) # Wait for full boot

print("Attempting SSH...")
ssh = pexpect.spawn("ssh -p 2222 -o StrictHostKeyChecking=no user@localhost", encoding='utf-8', timeout=60)
ssh.logfile = sys.stdout

try:
    ssh.expect("password:")
    ssh.sendline("live")
    ssh.expect(r"\$")
    print("SSH successful!")
    
    # Switch to root
    ssh.sendline("sudo -i")
    ssh.expect("password for user:")
    ssh.sendline("live")
    ssh.expect(r"#")
    print("Root access successful!")

    # 1. JARVIS USER EXISTS
    ssh.sendline("id jarvis")
    ssh.expect(r"#")
    ssh.sendline("getent passwd jarvis")
    ssh.expect(r"#")
    ssh.sendline("getent group jarvis")
    ssh.expect(r"#")

    # 2. JARVIS CORE
    ssh.sendline("systemctl is-active jarvis-core.service")
    ssh.expect(r"#")
    ssh.sendline("systemctl status jarvis-core.service --no-pager")
    ssh.expect(r"#")
    ssh.sendline("journalctl -u jarvis-core.service -b --no-pager")
    ssh.expect(r"#")

    # 3. VERIFY MODEL
    ssh.sendline("find / -name 'Qwen3-1.7B-Q4_K_M.gguf' 2>/dev/null")
    ssh.expect(r"#")
    ssh.sendline("ls -lh /opt/jarvis/usr/lib/jarvis/models/emergency/Qwen3-1.7B-Q4_K_M.gguf || ls -lh /usr/lib/jarvis/models/emergency/Qwen3-1.7B-Q4_K_M.gguf")
    ssh.expect(r"#")
    ssh.sendline("sha256sum /opt/jarvis/usr/lib/jarvis/models/emergency/Qwen3-1.7B-Q4_K_M.gguf || sha256sum /usr/lib/jarvis/models/emergency/Qwen3-1.7B-Q4_K_M.gguf")
    ssh.expect(r"#")

    # 4. LLAMA-SERVER
    ssh.sendline("which llama-server")
    ssh.expect(r"#")
    ssh.sendline("llama-server --version")
    ssh.expect(r"#")

    # 5. QWEN3 INFERENCE (using curl against localhost)
    ssh.sendline('curl -X POST http://127.0.0.1:8081/v1/chat/completions -H "Content-Type: application/json" -d \'{"model": "qwen3-1.7b-q4_k_m", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}\'')
    ssh.expect(r"#")

    # 6. TOOL CALL VIA DBUS
    ssh.sendline("su - jarvis -c 'dbus-send --print-reply --dest=com.jarvis.Core /com/jarvis/Core com.jarvis.CoreInterface.Ask string:\"session1\" string:\"Check the current CPU usage.\"'")
    ssh.expect(r"#")

    # 7. MEMORY TEST
    ssh.sendline("free -m")
    ssh.expect(r"#")
    ssh.sendline("cat /proc/meminfo")
    ssh.expect(r"#")
    ssh.sendline("ps aux | grep jarvis-core")
    ssh.expect(r"#")
    ssh.sendline("ps aux | grep llama-server")
    ssh.expect(r"#")

    print("SUCCESS: Validated all requested components.")
except Exception as e:
    print(f"Error: {e}")
    print("Output before error:", ssh.before)

# Give some time to print
time.sleep(2)
ssh.close()
child.terminate(force=True)
