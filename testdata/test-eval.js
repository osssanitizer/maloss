// http://www.tutorialsteacher.com/javascript/javascript-eval
eval("alert('this is executed by eval()')");



var result;

function Sum(val1, val2)
{
        return val1 + val2;
}

eval("result = Sum(5, 5);");

alert(result);



var str = '({"firstName":"Bill","lastName":"Gates"})';

var obj = eval(str);

obj.firstName; // Bill



// https://www.w3schools.com/Jsref/jsref_eval.asp
var x = 10;
var y = 20;
var a = eval("x * y") + "<br>";
var b = eval("2 + 2") + "<br>";
var c = eval("x + 17") + "<br>";

var res = a + b + c;



// Test non default eval functions
var res1 = Sum(a, b);
var res2 = Sum(Sum(a, b), c);



// Test object oriented functions
// https://www.w3schools.com/js/js_object_methods.asp
var person = {
    firstName: "John",
    lastName : "Doe",
    id       : 5566,
    fullName : function() {
        return this.firstName + " " + this.lastName;
    }
};

var name = person.fullName();



// Test built-in functions
var message = "Hello world!";
var x = message.toUpperCase();
var y = person.fullName().toUpperCase();

// Test obfuscation APIs
const buf = Buffer.from([0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x2c, 0x20, 0x57, 0x6f, 0x72, 0x6c, 0x64]);
// Creates a new Buffer containing the UTF-8 bytes of the string 'buffer'.
const buf = new Buffer([0x62, 0x75, 0x66, 0x66, 0x65, 0x72]);
