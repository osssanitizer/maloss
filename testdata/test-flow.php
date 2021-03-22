<?php

$some_var = $_GET["secret"];
$homepage = file_get_contents('http://www.example.com/');
echo $homepage;
$content = $homepage . ' ' . $homepage;

exec($homepage);
eval($some_var);

curl_exec($homepage);
curl_exec($content);
curl_exec($some_var);

$mysqli = new mysqli("localhost", "my_user", "my_password", "world");
$mysqli->query($some_var);

$link = mysqli_connect("localhost", "my_user", "my_password", "world");
mysqli_query($link, $some_var);

?>
