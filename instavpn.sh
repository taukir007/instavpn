#!/bin/bash

# Check if the instavpn directory exists and remove it if it does
[ -d instavpn ] && rm -rf instavpn/

echo "Installing git, cron, python3"
if [[ ! -z $(which apt-get) ]]; then
    sudo apt-get update > /dev/null
    sudo apt-get install -y git cron python3 > /dev/null
    echo "Ok"
else
    echo "You must use Ubuntu"
    exit 1
fi

echo "Cloning git repo"
git clone https://github.com/taukir007/instavpn.git --quiet || exit 1
echo "Ok"

cd instavpn
sudo python3 install.py
