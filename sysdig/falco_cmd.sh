#!/bin/bash
CONFIGPATH=$1
INDIR=$2
if [ $# -eq 2 ]; then
    CONFIGPATH=$1
    INDIR=$2
    PROCESS=1
elif [ $# -eq 3 ]; then
    CONFIGPATH=$1
    INDIR=$2
    PROCESS=$3
else
    echo "Usage: $0 CONFIGPATH INDIR [PROCESS]"
    exit 1
fi

echo "Running $PROCESS falco analyzers"

# command line and read trace
# falco command
# falco -c $CONFIGPATH -e $INPATH
# ref: https://github.com/falcosecurity/falco/wiki/How-to-Install-Falco-from-Source
# -A flag can be used to enable more events, such as fork, stat, unlink etc.
# falco -A -c $CONFIGPATH -e $INPATH
# https://github.com/falcosecurity/falco/wiki/Falco-Rules
ls $INDIR | xargs -n1 -P$PROCESS -Iline falco -A -c $CONFIGPATH -e $INDIR/line

