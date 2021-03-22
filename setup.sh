#!/bin/bash
sudo apt-get update
sudo apt-get install -yqq git python python-pip python3 python3-pip htop nfs-common
# update pip version
sudo pip3 install --upgrade pip setuptools wheel
sudo pip2 install --upgrade pip setuptools wheel
hash -r
sudo ./setup_docker.sh
sudo pip3 install -r main/requirements3.txt --user
# pull the docker image
sudo docker pull malossscan/maloss

