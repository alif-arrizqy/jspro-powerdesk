#!/bin/bash

echo 'install dependencies'
sudo apt-get install python3-pip
sudo apt-get install python3-dev
sudo apt-get install build-essential
sudo apt-get install libssl-dev -y
sudo apt-get install libffi-dev
sudo apt-get install python3-setuptools
sudo apt-get install nginx
sudo apt-get install hostapd

echo 'installing jspro-powerdesk requirements'
sudo pip3 install -r /var/lib/sundaya/jspro-powerdesk/requirements.txt

echo 'copy service'
sudo cp /var/lib/sundaya/jspro-powerdesk/dist/service/webapp.service /etc/systemd/system/

echo 'copy nginx config'
sudo cp /var/lib/sundaya/jspro-powerdesk/dist/nginx/joulestore-webapp /etc/nginx/sites-available/

echo 'create symlink'
sudo ln -s /etc/nginx/sites-available/joulestore-webapp /etc/nginx/sites-enabled

echo 'enable and start service'
sudo systemctl start webapp.service
sudo systemctl enable webapp.service
sudo systemctl restart nginx
# sudo ufw allow 'Nginx Full'

echo 'installing dnsmasq and hostapd'
sudo DEBIAN_FRONTEND=noninteractive apt install -y netfilter-persistent iptables-persistent
sudo apt-get install -y dnsmasq
sudo systemctl unmask hostapd
# sudo systemctl enable hostapd
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
sudo cp /var/lib/sundaya/jspro-powerdesk/dist/dnsmasq.conf /etc/dnsmasq.conf

sudo rfkill unblock wlan
sudo cp /var/lib/sundaya/jspro-powerdesk/dist/hostapd.conf /etc/hostapd/hostapd.conf

echo 'reboot....'
sudo systemctl reboot
