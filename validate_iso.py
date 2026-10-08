import pexpect
import sys
import time
import os

ISO_PATH = "dist/JARVIS-OS-1.0-amd64.iso"
REPORT_PATH = "reports/final-validation.md"
BOOT_LOG = "reports/qemu-bios-boot.log"

def log(msg):
    print(f"\n[VALIDATOR] {msg}")

def assert_cmd(ssh, cmd, expected=None):
    ssh.sendline(cmd)
    ssh.expect(r"# ")
    output = ssh.before.strip()
    print(f"> {cmd}\n{output}")
    if expected and expected not in output:
        log(f"FAIL: Expected '{expected}' not found in output of '{cmd}'")
        return False
    return True

def test_vm(mem="4G", smp="4", uefi=False):
    log(f"Testing VM with mem={mem}, smp={smp}, uefi={uefi}")
    cmd = f"sudo qemu-system-x86_64 -m {mem} -smp {smp} -enable-kvm -cdrom {ISO_PATH} -netdev user,id=n1,hostfwd=tcp::22222-:22 -device e1000,netdev=n1 -vnc :0 -monitor stdio -serial file:{BOOT_LOG}"
    if uefi:
        cmd += " -bios /usr/share/ovmf/OVMF.fd"
        
    child = pexpect.spawn(cmd, encoding='utf-8', timeout=180)
    
    log("Sending Enter to bootloader...")
    for _ in range(6):
        time.sleep(5)
        child.sendline('sendkey ret')
    log("Waiting 180s for boot...")
    time.sleep(180)
    
    ssh = None
    try:
        log("Connecting to guest via SSH (port 22222)...")
        for attempt in range(30):
            try:
                ssh = pexpect.spawn("ssh -p 22222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null jarvis@localhost", encoding='utf-8', timeout=10)
                ssh.logfile = sys.stdout
                idx = ssh.expect(["password:", pexpect.EOF, pexpect.TIMEOUT], timeout=10)
                if idx == 0:
                    log("SSH prompt reached.")
                    break
                ssh.close()
                ssh = None
            except Exception:
                if ssh:
                    ssh.close()
                    ssh = None
            time.sleep(5)
            
        if not ssh:
            log("FAIL: Unable to connect via SSH")
            return False

        ssh.sendline("jarvis")
        ssh.expect(r"\$")
        
        ssh.sendline("sudo -i")
        idx = ssh.expect(["password for jarvis:", r"# "], timeout=15)
        if idx == 0:
            ssh.sendline("jarvis")
            ssh.expect(r"# ")
        
        # Systemd
        assert_cmd(ssh, "systemctl is-system-running || true")
        assert_cmd(ssh, "systemctl --failed --no-pager")
        
        log("Waiting for jarvis-core.service to become active (model loading)...")
        for _ in range(60):
            ssh.sendline("systemctl is-active jarvis-core.service")
            ssh.expect(r"# ")
            if "active" in ssh.before:
                log("jarvis-core.service is active!")
                break
            time.sleep(2)
        else:
            log("FAIL: jarvis-core.service did not become active")
            return False
        
        # Jarvis user
        assert_cmd(ssh, "id jarvis")
        assert_cmd(ssh, "getent passwd jarvis")
        
        # Model
        ssh.sendline("find / -type f -name 'Qwen3-1.7B-Q4_K_M.gguf' 2>/dev/null")
        ssh.expect(r"# ")
        output_lines = [l.strip() for l in ssh.before.strip().splitlines() if l.strip() and not l.strip().startswith("find")]
        model_path = output_lines[-1] if output_lines else ""
        if not model_path:
            log("FAIL: Model not found")
            return False
            
        assert_cmd(ssh, f"ls -lh {model_path}")
        assert_cmd(ssh, f"sha256sum {model_path}", "d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5")
        
        # Llama Server
        assert_cmd(ssh, "which llama-server")
        assert_cmd(ssh, "llama-server --version")
        
        # API endpoints
        assert_cmd(ssh, "curl -sSf http://127.0.0.1:8081/health", "status")
        assert_cmd(ssh, "curl -sSf http://127.0.0.1:8081/v1/models", "id")
        assert_cmd(ssh, "curl -sSf -X POST http://127.0.0.1:8081/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\": \"qwen3-1.7b-q4_k_m\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}], \"max_tokens\": 10}'", "choices")
        
        # DBUS Tool Call
        assert_cmd(ssh, "su - jarvis -c 'dbus-send --system --print-reply --dest=com.jarvis.Core /com/jarvis/Core com.jarvis.CoreInterface.Ask string:\"session2\" string:\"Check the current CPU usage.\"'", "string \"")
        
        # Firewall
        assert_cmd(ssh, "ss -lntup")
        assert_cmd(ssh, "iptables -L")
        
        # File Explorer
        assert_cmd(ssh, "cat /usr/share/applications/jarvis-files.desktop")
        
        # Memory
        assert_cmd(ssh, "free -m")
        assert_cmd(ssh, "ps aux | grep -E 'jarvis|llama'")
        
        return True
    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
        child.terminate(force=True)
        time.sleep(5)

def main():
    if not os.path.exists(ISO_PATH):
        log(f"ISO not found at {ISO_PATH}")
        sys.exit(1)
        
    os.system(f"file {ISO_PATH}")
    os.system(f"ls -lh {ISO_PATH}")
    os.system(f"sha256sum {ISO_PATH}")
    os.system(f"xorriso -indev {ISO_PATH} -toc")
    
    # 4GB test
    res_4g = test_vm("4G", "4", False)
    
    # 2GB test
    res_2g = test_vm("2G", "2", False)
    
    log(f"4G Test: {'PASS' if res_4g else 'FAIL'}")
    log(f"2G Test: {'PASS' if res_2g else 'FAIL'}")

if __name__ == "__main__":
    main()
