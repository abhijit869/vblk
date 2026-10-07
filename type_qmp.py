import socket, json, time, sys

def send_qmp(cmd):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 4444))
    s.recv(1024)
    s.sendall(json.dumps({"execute": "qmp_capabilities"}).encode() + b'\n')
    s.recv(1024)
    s.sendall(json.dumps(cmd).encode() + b'\n')
    res = s.recv(1024)
    s.close()
    return res

def type_string(text):
    for char in text:
        if char == '\n':
            key = "ret"
        elif char == ' ':
            key = "spc"
        elif char == '-':
            key = "minus"
        elif char == '.':
            key = "dot"
        elif char == '_':
            key = "shift-minus"
        else:
            key = char
        send_qmp({"execute": "send-key", "arguments": {"keys": [{"type": "qcode", "data": key}]}})
        time.sleep(0.5)

type_string("\n")
time.sleep(1)
type_string("u")
type_string("s")
type_string("e")
type_string("r")
type_string("\n")
time.sleep(5)
type_string("l")
type_string("i")
type_string("v")
type_string("e")
type_string("\n")
time.sleep(5)
type_string("sudo systemctl start ssh\n")
time.sleep(2)
type_string("live\n")
