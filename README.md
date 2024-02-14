# eet2mqtt
how to run  solmate 2 mqtt as a service

## operate eet.service
```bash
sudo systemctl daemon-reload
sudo systemctl restart eet.service
sudo systemctl stop eet.service
sudo systemctl start eet.service
sudo systemctl status eet.service -n 100
```

## edit service config

sudo vi "/etc/systemd/system/eet.service"

### eet.service
```bash
[Unit]
Description=eet Script
After=multi-user.target
Wants=network-online.target

[Service]
Type=notify
Environment=PYTHONUNBUFFERED=true
Restart=always
ExecStart=/usr/bin/python3 /home/user/eet2mqtt/sol2mqtt.py
WatchdogSec=60
RestartSec=20

[Install]
WantedBy=multi-user.target
```
