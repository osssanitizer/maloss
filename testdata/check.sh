ls *.out | while read line; do diff $line $line.expected; done
