#!/bin/bash

sudo apt-get install -yqq mono-complete
# How to install nuget from command line
# FIXME: For 16.04 4.5.1 is the latest that works
# https://stackoverflow.com/questions/38118548/how-to-install-nuget-from-command-line-on-linux
sudo curl https://dist.nuget.org/win-x86-commandline/v4.5.1/nuget.exe -o /usr/lib/nuget/NuGet.exe
