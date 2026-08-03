import socket

# find LAN IP
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # no packet sent, just picks the outgoing interface
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        ip = "localhost"
    return ip