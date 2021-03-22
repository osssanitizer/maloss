#!/bin/bash
echo "This script only has been tested on ubuntu 16.04! It doesn't work on debian! It may not work on other ubuntu versions!"

# docker
sudo apt-get update -yqq
sudo apt-get install -yqq \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-key fingerprint 0EBFCD88
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
sudo apt-get update -yqq
sudo apt-get install -yqq docker-ce
docker --version

# docker-compose
sudo curl -L https://github.com/docker/compose/releases/download/1.21.2/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version

# change the storage driver to overlay2, which is more performant
# https://docs.docker.com/v17.09/engine/userguide/storagedriver/overlayfs-driver/#configure-docker-with-the-overlay-or-overlay2-storage-driver
sudo systemctl stop docker
sudo sh -c 'echo "{\n\t\"storage-driver\": \"overlay2\"\n}" > /etc/docker/daemon.json'
sudo systemctl start docker

