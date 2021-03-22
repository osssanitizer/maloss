#!/bin/bash

curl -L https://github.com/clue/phar-composer/releases/download/v1.0.0/phar-composer.phar -o phar-composer.phar
composertool=$(pwd)/phar-composer.phar
version="dev"
date=`date "+%Y%m%d-%H%M%S"`
newfile="progpilot_${version}${date}"
    
echo "Progpilot builder"
echo "Have you updated the version of progpilot in Console/Application.php file ? (optional)"

if [ -e ${composertool} ] 
then
    cd ./projects/phar
    rm composer.lock
    rm -rf ./vendor/
    composer install

    rm -rf ./vendor/progpilot/
    mkdir ./vendor/progpilot/
    mkdir ./vendor/progpilot/package
    cp -R ../../package/* ./vendor/progpilot/package

    rm -rf ../../builds/*
    mkdir -p ../../builds
        
    echo "generating phar"

    php -d phar.readonly=off ${composertool} build .
    mv ./rogpilot.phar ../../builds/${newfile}.phar
    cp  ../../builds/${newfile}.phar ../../builds/progpilot.phar

    rm composer.lock
    rm -rf ./vendor/
else

echo ""
echo "Error : ${composertool} doesn't exist"
echo "download the latest release of phar composer tool : https://github.com/clue/phar-composer/releases"
echo "and define the path of the tool in the composertool variable of this script"

fi

rm ${composertool}

