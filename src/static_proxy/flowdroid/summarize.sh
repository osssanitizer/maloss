#!/bin/bash
if [ $# -eq 1 ]
then 
    JAR=$1
    OUTDIR=./
elif [ $# -eq 2 ]
then
    JAR=$1
    OUTDIR=$2
else
    echo "Usage: $0 JAR [OUTDIR]"
    exit 1
fi

# the command to run, e.g.
# ./summarize.sh ../../../malware/virustotal/20180619/JAR/2dd239093bd1e9c5a3d35025a54ffd7c3a5fe00a63660982fd3480f035aa3c97 ./output
# FIXME: improve this by analyzing classes with sensitive APIs uses and their parent classes.
# FIXME: add support for generating new sources/sinks (return of clz.foo is a source, param1 of clz.bar is a sink), e.g. soot-infoflow-android/SourcesAndSinks.txt
java -jar soot-infoflow-summaries/target/soot-infoflow-summaries-jar-with-dependencies.jar -lf -p $(pwd)/platforms/ $JAR $OUTDIR

