#!/bin/bash

cd ../src

pip download --no-binary :all: --no-deps $1
pkg_file=`ls -t | head -n1`
shopt -s nocasematch

if [[ $pkg_file =~ $1.* ]]
then
   python main.py astgen $pkg_file $pkg_file.out -c ../config/test_astgen_python.config
fi

cd ../testdata
