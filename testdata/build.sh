#!/bin/bash

# build the java tests
# https://stackoverflow.com/questions/4597866/java-creating-jar-file
javac Test*.java
mkdir test_classes && mv Test*.class test_classes
jar cf Test.jar test_classes
rm -r test_classes

# FIXME: run the classes
# java -cp Test.jar test_classes.TestEval
