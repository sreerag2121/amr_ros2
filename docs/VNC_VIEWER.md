# VNC Remote Desktop Access to Jetson

Access the Jetson desktop remotely without a physical monitor.

## Requirements

| Component | Details |
|-----------|---------|
| VNC Server (Jetson) | TigerVNC (`tigervnc-standalone-server`) |
| VNC Client (laptop) | Remmina (snap) |
| Desktop Environment | XFCE4 |
| Display | `:1` (virtual, port `5901`) |

---

## Connecting (Every Time)

### Step 1 — SSH tunnel (keep this terminal open)

```bash
ssh -L 5901:localhost:5901 flexmotion@172.16.33.233
```

### Step 2 — Open Remmina on laptop (new terminal)

```bash
remmina -c vnc://localhost:5901
```

Enter VNC password when prompted.

### Step 3 — Login to college portal inside VNC

Open Firefox inside the VNC window and log into NITC-WIFI-Academic portal.

---

## Troubleshooting

**VNC server not running after reboot:**
```bash
ssh flexmotion@172.16.33.233
sudo systemctl restart vncserver@1.service
```

**Port already in use on laptop:**
```bash
fuser -k 5901/tcp
```

**Black screen in Remmina:**
```bash
ssh flexmotion@172.16.33.233
sudo pkill -9 Xtigervnc
vncserver :1
```
