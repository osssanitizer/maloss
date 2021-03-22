<?php

$output = `ls -al`;
echo "<pre>$output</pre>";

$output = shell_exec('ls -lart');
echo "<pre>$output</pre>";

echo "Current date and time is: " . `date`;

$date = `date`;
echo "Current date and time is: $date";

echo exec('ls -l') . "\n";

?>
