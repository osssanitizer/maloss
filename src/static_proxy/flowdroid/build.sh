#!/bin/bash

export ANDROID_JARS=$(pwd)/platforms/
export DROIDBENCH=$(pwd)/droidbench/

mvn -DskipTests install
