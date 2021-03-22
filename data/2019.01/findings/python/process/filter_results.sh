for I  in ls *.txt	
do
  file=${I##*/}
  echo $file
  grep -v "process=python*" $I | grep -v "collect2*" | grep -v "cc1*" | grep -v "runc*" | grep -v "x86_64-linux-gn*" | grep -v "process=gcc*"| grep -v "program=sh -c uname -p 2> /dev/null*" | grep -v "/usr/bin/print -r --*" | grep -v "parent_command=sh ./configure*"  | grep -v "parent_command=bash ./configure"  | grep -v "bash ./config.status" > "./filter/"$file
done

