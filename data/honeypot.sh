#!/bin/bash

# dependencies
sudo apt-get install -yqq ssh 
# FIXME: disable these dependencies, because they break python dependencies
# pip install --user devpi-client
# pip install --user awscli azure-cli \
#     gcloud google-cloud-datastore google-cloud-language google-cloud-spanner \
#     google-cloud-storage google-cloud-translate google-cloud-logging \
#     ibm-cos-sdk oci-cli aliyuncli rackspace-monitoring-cli

# ssh keys for unix
ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa

# login credentials for package managers, e.g. npmjs, pypi, rubygems, maven, packagist
# additional package managers can also be considered, e.g. apt, nuget, yarn, jcenter, bow
cp data/npmjs.config ~/.npmrc
cp data/pypi.config  ~/.pypirc
mkdir -p ~/.gem && cp data/rubygems.config ~/.gem/credentials
mkdir -p ~/.m2 && cp data/maven.config ~/.m2/settings.xml
# packagist doesn't need local publish, since it allows submit on website
# apt (difficult to get in): https://askubuntu.com/questions/16446/how-to-get-my-software-into-ubuntu
# nuget: https://docs.microsoft.com/en-us/nuget/tools/cli-ref-sources
mkdir -p ~/.nuget/NuGet && cp data/nuget.config ~/.nuget/NuGet/NuGet.Config
cp data/yarnpkg.config ~/.yarnrc

# Bintray offers advanced support for several package formats.
# https://www.jfrog.com/confluence/display/BT/Working+With+Supported+Package+Formats
# Bower can be configured using JSON in a .bowerrc file. For example:
# https://bower.io/docs/config/
cp data/bower.config ~/.bowerrc

# login credentials for public services, e.g. docker, git (github, gitlab, bitbucket), vagrant
# docker container inside docker is discouraged
# https://stackoverflow.com/questions/27879713/is-it-ok-to-run-docker-from-inside-docker
mkdir -p ~/.docker && cp data/docker.config ~/.docker/config.json
sudo chown -R root:root /home/maloss/.docker
sudo chmod 0700 /home/maloss/.docker && sudo chmod 600 /home/maloss/.docker/config.json
cp data/git.config ~/.git-credentials
mkdir -p ~/.config/git/ && cp data/git.config ~/.config/git/credentials
mkdir -p ~/.vagrant.d/data/ && cp data/vagrant.config ~/.vagrant.d/data/vagrant_login_token

# login credentials for cloud providers, e.g. aws, azure, gcp, ibm, oracle, aliyun, rackspace, salesforce
# aws
mkdir -p ~/.aws/ && cp data/aws.config ~/.aws/config && cp data/aws.credentials ~/.aws/credentials
# azure
cp -r data/azure.config ~/.azure
# gcp, no default folders for credentials
# ibm, https://console.bluemix.net/docs/services/cloud-object-storage/libraries/python.html#using-python
mkdir -p ~/.bluemix/
# oracle
mkdir -p ~/.oci/
# aliyun
mkdir -p ~/.aliyun/
# rackspace
mkdir -p ~/.raxrc/
# salesforce
mkdir -p ~/.fuelsdk/

# local accounts credentials, passwd, shadow
# local machine details, installed packages, cpu, memory, running processes, generic files

