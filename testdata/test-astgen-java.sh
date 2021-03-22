#!/bin/bash

cd ../src

python main.py astgen ../testdata/protobuf-java-3.5.1.jar ../testdata/protobuf-java-3.5.1.jar.out -c ../config/astgen_java_smt.config -l java
