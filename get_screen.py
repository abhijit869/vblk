import socket, json, time
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 4444))
time.sleep(0.5)
s.sendall(b'{"execute": "qmp_capabilities"}\n')
time.sleep(0.5)
s.sendall(b'{"execute": "screendump", "arguments": {"filename": "/workspaces/vblk/reports/secboot_error.ppm"}}\n')
time.sleep(0.5)
s.close()
