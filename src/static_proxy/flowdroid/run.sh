#!/bin/bash

if [ $# -eq 1 ]
then
    APK=$1
    SOURCES_SINKS=soot-infoflow-android/SourcesAndSinks.txt
elif [ $# -eq 2 ]
then
    APK=$1
    SOURCES_SINKS=$2
else
    echo "Usage: $0 APK [SOURCES_SINKS]"
    exit 1
fi

# the command to run, e.g.
#
# ./run.sh ./soot-infoflow-android/testAPKs/SourceSinkDefinitions/SourceToSink1.apk ./soot-infoflow-android/testAPKs/SourceSinkDefinitions/sourcesAndSinks.xml
java -jar soot-infoflow-cmd/target/soot-infoflow-cmd-jar-with-dependencies.jar -cp -a $APK -p $(pwd)/platforms/ -s $SOURCES_SINKS

# access path length, table 5 in thesis
# reference http://tuprints.ulb.tu-darmstadt.de/5937/7/Thesis.pdf
# -al 5
#
# APK=./soot-infoflow-android/testAPKs/SourceSinkDefinitions/SourceToSink1.apk
# SOURCES_SINKS=./soot-infoflow-android/testAPKs/SourceSinkDefinitions/sourcesAndSinks.xml
# APK=./droidbench/apk/AndroidSpecific/DirectLeak1.apk
# SOURCES_SINKS=../../../config/static_java_SourcesAndSinks.txt
# java -jar soot-infoflow-cmd/target/soot-infoflow-cmd-jar-with-dependencies.jar -cp -a $APK -p $(pwd)/platforms/ -s $SOURCES_SINKS -o results.xml
# java -jar soot-infoflow-cmd/target/soot-infoflow-cmd-jar-with-dependencies.jar -cp -a $APK -p $(pwd)/platforms/ -s $SOURCES_SINKS -pb results.txt
#
# additional test APK
# ./droidbench/apk/Callbacks/LocationLeak1.apk
# ./droidbench/apk/Callbacks/LocationLeak2.apk
# ./droidbench/apk/Callbacks/LocationLeak3.apk
# ./droidbench/apk/AndroidSpecific/DirectLeak1.apk
# ./droidbench/apk/AndroidSpecific/PrivateDataLeak2.apk
# ./droidbench/apk/AndroidSpecific/PrivateDataLeak3.apk
# ./droidbench/apk/AndroidSpecific/PrivateDataLeak1.apk
