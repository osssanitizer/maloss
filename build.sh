#!/bin/bash

git submodule init
git submodule update src/static_proxy/brakeman
git submodule update src/static_proxy/progpilot
git submodule update src/static_proxy/jsprime
git submodule update src/static_proxy/flowdroid
sudo docker build -t malossscan/maloss -t maloss .

