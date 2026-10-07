#!/bin/bash
set -e
ISO_PATH="/workspaces/vblk/dist/JARVIS-OS-1.0-amd64.iso"

osirrox -indev "$ISO_PATH" -extract /live/vmlinuz /tmp/vmlinuz -extract /live/initrd.img /tmp/initrd.img || {
    osirrox -indev "$ISO_PATH" -extract /install/vmlinuz /tmp/vmlinuz -extract /install/initrd.gz /tmp/initrd.img || true
}

cat << 'EXPECT_SCRIPT' > /tmp/run_tests.exp
#!/usr/bin/expect -f
set timeout 300
spawn qemu-system-x86_64 -m 2048 -kernel /tmp/vmlinuz -initrd /tmp/initrd.img -append "boot=live components console=ttyS0" -cdrom /workspaces/vblk/dist/JARVIS-OS-1.0-amd64.iso -nographic
expect "jarvis login:" { send "jarvis\r" } timeout { puts "TEST INFRASTRUCTURE LIMITATION: No serial login prompt"; exit 1 }
expect "Password:" { send "live\r" }
expect "$ "

send "echo '--- SYSTEMD HEALTH ---' > /tmp/test_report.log\r"
expect "$ "
send "systemctl is-system-running >> /tmp/test_report.log\r"
expect "$ "
send "systemctl --failed --no-pager >> /tmp/test_report.log\r"
expect "$ "
send "systemctl is-active jarvis-core.service >> /tmp/test_report.log\r"
expect "$ "
send "systemctl is-active jarvis-eventbus.service >> /tmp/test_report.log\r"
expect "$ "
send "ls -ld /var/log/jarvis >> /tmp/test_report.log\r"
expect "$ "
send "ls -ld /var/lib/jarvis >> /tmp/test_report.log\r"
expect "$ "
send "systemctl show jarvis-core.service -p User -p ProtectSystem -p ReadWritePaths >> /tmp/test_report.log\r"
expect "$ "
send "journalctl -b -u jarvis-core.service --no-pager >> /tmp/test_report.log\r"
expect "$ "
send "journalctl -b -u jarvis-eventbus.service --no-pager >> /tmp/test_report.log\r"
expect "$ "
send "cat /tmp/test_report.log\r"
expect "$ "
send "sudo poweroff\r"
expect eof
EXPECT_SCRIPT

chmod +x /tmp/run_tests.exp
/tmp/run_tests.exp | tee reports/phase5_output.log
