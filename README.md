# eet2mqtt
runnging solmate 2 mqtt as service


## service example:

## operate

sudo systemctl daemon-reload
sudo systemctl stop eet.service
sudo systemctl start eet.service
sudo systemctl restart eet.service
sudo systemctl status eet.service

## edit

sudo vi "/etc/systemd/system/eet.service"

## eet.service
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