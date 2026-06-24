# SSH Connection to Jetson (flexmotion)

## Device Info

| Field | Value |
|-------|-------|
| Hostname | `flexmotion` |
| IP | `172.16.33.233` (static) |
| Username | `flexmotion` |
| Password | `flexmotion@123` |
| OS | Ubuntu 24.04 LTS (Linux for Tegra aarch64) |
| Network | NITC-WIFI-Academic (college WiFi) |

---

## Basic SSH

```bash
ssh flexmotion@172.16.33.233
```

---

## After Every Reboot

The college WiFi uses a captive portal. After powering on the Jetson, you need to log in via browser before SSH works.

**If you have physical monitor access:**
- Open Firefox on the Jetson desktop and log into the portal.

**If you don't have a monitor (headless):**
- Use VNC — see [VNC_VIEWER.md](VNC_VIEWER.md) to access the Jetson desktop remotely and log into the portal from there.

---

## SSH with Port Forwarding (for VNC tunnel)

```bash
ssh -L 5901:localhost:5901 flexmotion@172.16.33.233
```

Keep this terminal open — it creates a tunnel for VNC.

---

## Run a Command Remotely Without Logging In

```bash
ssh flexmotion@172.16.33.233 "<command>"
```

Example:
```bash
ssh flexmotion@172.16.33.233 "hostname -I"
```

---

## Static IP Setup (already configured)

Static IP was set via NetworkManager:

```bash
sudo nmcli con mod "NITC-WIFI-Academic" \
  ipv4.addresses 172.16.33.233/21 \
  ipv4.gateway 172.16.32.1 \
  ipv4.dns "8.8.8.8,8.8.4.4" \
  ipv4.method manual
sudo nmcli con up "NITC-WIFI-Academic"
```

---

## Troubleshooting

**SSH times out:**
- Jetson may not be connected to WiFi yet — wait 30 seconds after boot and retry.
- Portal may not be logged in — use VNC to login via browser first.

**Connection refused:**
- SSH service may not be running: power cycle the Jetson.

**Wrong IP:**
```bash
ssh flexmotion@172.16.33.233 "ip addr show wlP1p1s0"
```
Should show `172.16.33.233/21`.
