# PyFileTransfer

Simplistic LAN file transfer script using python sockets.
Efficient for large files (tested with 3GB file).
Should compress files with 7z beforehand to increase speed.

---

Usage:
 - Server mode: python script.py server [port]
 - Client mode: python script.py client <host> <port> <filepath>
