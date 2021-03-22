#!/bin/bash

# dependencies
apt-get install -yqq python python-pip python-dev python3 python3-pip python3-dev npm ruby-full rubygems-integration ruby-all-dev php php-mbstring php-all-dev maven curl openjdk-8-jdk
# install python3.6 on ubuntu 16.04
# http://ubuntuhandbook.org/index.php/2017/07/install-python-3-6-1-in-ubuntu-16-04-lts/
apt-get install -yqq software-properties-common
add-apt-repository ppa:jonathonf/python-3.6 -y
apt-get update -yqq
apt-get install -yqq python3.6 python3.6-dev
# install pip3 for python
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.6 -
echo "pip3.6 --version $(pip3.6 --version)"
echo "python3.6 --version $(python3.6 --version)"
# install composer
curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/bin --filename=composer
# https://www.rosehosting.com/blog/how-to-install-node-js-on-ubuntu-16-04/
# default nodejs is 4.2.6, install latest version 8.11.3
curl -sL https://deb.nodesource.com/setup_8.x | bash -
apt-get install -yqq nodejs

####################################################################
# dependencies for astgen job and other analyses
####################################################################
# python dependencies
pip3 install --upgrade pip setuptools wheel
pip2 install --upgrade pip setuptools wheel
# FIXME: How do I clear Bash's cache of paths to executables?
# https://unix.stackexchange.com/questions/5609/how-do-i-clear-bashs-cache-of-paths-to-executables
hash -r
# make python3.6 the default version
# http://ubuntuhandbook.org/index.php/2017/07/install-python-3-6-1-in-ubuntu-16-04-lts/
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 1
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 2
# test the python and pip versions
echo "pip3 --version $(pip3 --version)"
echo "python3 --version $(python3 --version)"
echo "pip3.6 --version $(pip3.6 --version)"
echo "python3.6 --version $(python3.6 --version)"
echo "pip3.5 --version $(pip3.5 --version)"
echo "python3.5 --version $(python3.5 --version)"
echo "pip2 --version $(pip2 --version)"
echo "python2 --version $(python2 --version)"

# install python dependencies
pip2 install -r src/requirements.txt
pip3 install -r src/requirements3.txt

# javascript dependencies
# install node 2.5.0+ and npm 2.6.1+
# NOTE: currently we use python esprima package to parse javascript packages.
cd src/proto/javascript && npm update && cd ../../../
cd src/pm_proxy/scripts && npm update && cd ../../../

# ruby dependencies, parser creates a binary ruby-parse.
# install ruby 2.5+
gem install parser
gem install google-protobuf -v 3.6.1
gem install gem-path -v 0.6.2

# php dependencies, parser
# install php 7.2.6+
# install composer 1.6.2+
cd src/static_proxy && composer update && cd ../..

# java dependencies
# install maven 3.3.9+
cd src/static_proxy/astgen-java/ && mvn clean compile assembly:single && cd ../../../

# csharp dependencies

####################################################################
# dependencies for static job (including taint and danger analysis)
####################################################################
# python dependencies
# included in src/requirements3.txt

# javascript dependencies
cd src/static_proxy/jsprime && npm update && cd ../../../

# ruby dependencies
# TODO: use our brakeman or the default brakeman
# cd src/static_proxy/brakeman && gem build brakeman.gemspec && gem install ./brakeman-4.5.1.gem && cd ../../../
gem install brakeman -v 4.6.1

# php dependencies
cd src/static_proxy/progpilot && ./build.sh && cd ../../../

# java dependencies
cd src/static_proxy/flowdroid && ./build.sh && cd ../../../

# csharp dependencies

