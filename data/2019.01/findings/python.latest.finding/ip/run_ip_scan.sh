file="list_ips.txt"
while IFS= read line
do
  echo "$line"
  ./ip_scan.sh $line >> ip_report.txt
  echo $'\n' >> ip_report.txt
done <"$file"
