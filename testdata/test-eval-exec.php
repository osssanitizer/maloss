<?php
// http://php.net/manual/en/function.eval.php
// http://php.net/manual/en/function.exec.php
$string = 'cup';
$name = 'coffee';
$str = 'This is a $string with my $name in it.';
echo $str. "\n";
eval("\$str = \"$str\";");
echo $str. "\n";

// outputs the username that owns the running php/httpd process
// (on a system with the "whoami" executable in the path)
echo exec('whoami');
?>

<?php
// https://www.w3schools.com/php/func_misc_eval.asp
$string = "beautiful";
$time = "winter";

$str = 'This is a $string $time morning!';
echo $str. "<br>";

eval("\$str = \"$str\";");
echo $str;

function hello() {
    echo "hello\n";
}

class Foo {
    public function hello() { echo "hello\n"; }
    public function foo() { echo "foo\n"; }
}

class Bar {
    private $foo;
    public function __construct(Foo $foo) {
        $this->foo = $foo;
    }
    public function bar() {
        $this->foo->hello();
        $this->foo->bar();
    }
    public function getFoo() {
        return $this->foo;
    }
}

$foo = new Foo();
$foo->hello();
$foo->foo();

$bar = new Bar($foo);
$bar->bar();
$bar->getFoo()->hello();
$bar->getFoo()->foo();

?>

