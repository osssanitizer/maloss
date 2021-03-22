var esprima = require('esprima');

/*
JSPrime v0.1 beta
=================
The MIT License (MIT)

Copyright (c) 2013 Nishant Das Patnaik (nishant.dp@gmail.com)
Copyright (c) 2013 Sarathi Sabyasachi Sahoo (sarathisahoo@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/
var source = []; //["URL","documentURI","URLUnencoded","baseURI","cookie","referrer","location", "localStorage.getItem","sessionStorage.getItem","sessionStorage.key","responseText", "window.name", "websockets.onMessage","load","ajax","url.parse", "get", "val","data","value"];
var sink = []; //["eval","setTimeout","setInterval","execScript","document.write","document.writeln","innerHTML","href","src","html","after","append","appendTo","before","insertAfter","insertBefore","prepend","prependTo","replaceWith","parseHTML","jQuery","globalEval","appendChild","create","insert","setContent","setHTML"];
var sinkWithConstantParam = ["eval", "globalEval"];
var conditionalSink = []; //[".setAttribute(href|src"];
var positiveSource = []; //["decodeURIComponent"];
var negativeSource = []; //["encodeURIComponent", "Y.Escape.html","text"];
var blackList = [];
var blackListObj = [];
var semiBlackList = [];
var semiSource = [];
var redLine = [];
var isXSS = false;
var sourceData = [];
var resultData = [];
var resultColor = [];
var sourceDataOld = [];
var sourceDataToExecute = [];
var isSource = true;
var sinkResultArguments = [];
var sinkResultArgumentsObj = [];
var sourceList = [];
var sourceListObj = [];
var sourceListNames = [];
var convertedFunction = [];
var aOrange = [];
var aOrangeData = "";
var aRedData = "";
var aOtherData = "";

var code;
var real_variable_const;
var real_variable_var;
var timeout_val;

module.exports = function(real_variable_const_arg, real_variable_var_arg, convertedFunction_arg, source_arg, sink_arg, code, callback) {

    real_variable_const = real_variable_const_arg
    real_variable_var = real_variable_var_arg

    source = source_arg
    sink = sink_arg

    module.exports.analyzeArrays = analyzeArrays(code, real_variable_const, real_variable_var, function(temp) {
        results = temp;
    })
 
    callback(results)
}

function analyzeArrays(code, real_variable_const, real_variable_var, callback) {

    var sData = code;
    sourceDataToExecute = sData.split(/\n\r?/g);

    sourceData = sData.split(/\n\r?/g);
    sourceDataOld = sData.split(/\n\r?/g);

    parseJavascriptNativeFunction();

    // Source is the list of sources
    for (var i = 0; i < source.length; i++) {

        blackList = [];
        blackListObj = [];
        isXSS = false;
        isSource = true;

        checkFunctionsWithDirectSource(source[i]);
        checkAssignValue(real_variable_const, source[i], source[i], null);
        checkAssignValue(real_variable_var, source[i], source[i], null);

        if (blackList.length > 0) {
            checkSink();
        }

        checkSinkWithDirectSource(source[i], real_variable_var);
    }

    traverseHighLightsVariable();
    traverseHighLightsFunction();
    traverseHighLightsFunctionReturn();

    traverseHighLightsVariable();
    traverseHighLightsFunction();
    traverseHighLightsFunctionReturn();

    callback(writeResult(code));
}

function getCallingFunction(code_lines, line_number) {
    
    var function_name = ""
    
    // Iterate through lines in reverse
    for (var i = line_number; i > 0; i--) {
	// Check for functions
	if (code_lines[i].indexOf("function") != -1) {
	    // Ignore calback functions
	    if ((code_lines[i].indexOf("function(") == -1) && (code_lines[i].indexOf("function (") == -1)) {
		parsed_line = esprima.parse(code_lines[i] + "}")
		function_name = parsed_line.body[0].id.name
		break
	    }
	}
    }

    return function_name
}

function writeResult(code) {

    console.log(resultData)

    var code_lines = code.split('\n')
    var resultRow = "";
    
    for (var i = 0; i < resultData.length; i++) {
        var redIndex = resultColor.indexOf('red');
        if (resultColor[i] == '#FF00FF' && redIndex < i && redIndex != -1) {
            var temp = resultColor[i];
            resultColor[i] = resultColor[redIndex];
            resultColor[redIndex] = temp;

            var temp = resultData[i];
            resultData[i] = resultData[redIndex];
            resultData[redIndex] = temp;

        }
    }

    var results = {}
    var new_sources = []
    var new_sinks = []
    var malicious = "false"
    var active_source = false
    var active_sink = false

    for (var i = 0; i < resultData.length; i++) {
        var raw_line = resultData[i].split('#LINE#');
        var result = {};

	//console.log(resultColor[i])

        //Remove the trailing line number
        lineNumber = raw_line[1]
        aResultData = raw_line[0].trim()


        try {
            var parsed = esprima.parse(aResultData);

        } catch (e) {
            // this is used to deal with exceptions from callback functions
            var parsed = esprima.parse(aResultData + "})")
        }

        var function_type = parsed.body[0].type

        //Add location data to result
        result.row = lineNumber

        property = getCallingFunction(code_lines, lineNumber)
        
	// Source color
        if (resultColor[i] == "orange") {
	
	    // Find the function that calls the API
	    var function_line = ""
	    for (var j = (lineNumber-1); j > 0; j--) {
		if (code_lines[j].includes("function") == true) {
			function_line = code_lines[j]
			break
		}
	    }
	    
	    function_line = function_line.split("function")[1]
	    function_name = function_line.split("(")[0].trim()
            function_args = function_line.split("(")[1].split(")")[0].trim().split(",")
            
	    result.object = "test"	// this shouldn't ever actually be used, no need to fix
	    result.property = property
	    //result.argument_list = function_args

            var currentObject = parsed.body[0].declarations[0]
            result.reachable_object = currentObject.init.callee.object.name
            result.reachable_property = currentObject.init.callee.property.name

            result.startColumn = raw_line[0].indexOf(result.object)
            result.endColumn = raw_line[0].indexOf(result.property) + result.property.length

            // Process argument list    
            /*
		
	    result.reachable_argument_list = []
            var argument_list = currentObject.init.arguments
	    
            if (currentObject.type == "VariableDeclarator") {
                if (argument_list != undefined) {

                    var is_argument = false
                    var j = 0
                    while (is_argument == false) {

			if (argument_list[j] == undefined) {
			    is_argument = true
			} else if (argument_list[j].type != "Literal") {
                            is_argument = true
                        } else if (j >= (argument_list.length)) {
                            is_argument = true
                        } else {
                            result.reachable_argument_list.push(argument_list[j].raw)
                        }
                        j = j + 1
                    }
                } else {
                    argument_list = currentObject.init.object.arguments
                    var is_argument = false
                    var j = 0

                    if (argument_list[j] == undefined) {
			is_argument = true
		    } else if (argument_list[j].type != "Literal") {
                        is_argument = true
                    } else if (j >= (argument_list.length)) {
                        is_argument = true
                    } else {
                        result.reachable_argument_list.push(argument_list[j].raw)
                    }
                    j = j + 1
                }
            } else {
                argument_list = currentObject.init.object.arguments
		var is_argument = false
                var j = 0
                while (is_argument == false) {
                    if (argument_list[j] == undefined) {
			is_argument = true
		    } else if (argument_list[j].type != "Literal") {
                        is_argument = true
                    } else if (j >= (argument_list.length)) {
                        is_argument = true
                    } else {
                        result.reachable_argument_list.push(argument_list[j].raw)
                    }
                    j = j + 1
                }
            }
	    */
	    active_source = true

            new_sources.push(result)
            
	    if (active_sink) {
	    	malicious = "true"
	    }
        } else if (resultColor[i] == "red") {

	    result.object = "test"
	    result.property = property
	    result.argument_list = []

            var currentObject = parsed.body[0]
            result.reachable_object = currentObject.expression.callee.object.name
            result.reachable_property = currentObject.expression.callee.property.name

            result.startColumn = raw_line[0].indexOf(result.object)
            result.endColumn = raw_line[0].indexOf(result.property) + result.property.length

            // Process arguments
	    /*
            argument_list = currentObject.expression.arguments
            result.reachable_argument_list = []
            var is_argument = false
            var j = 0
            while (is_argument == false) {
                if (argument_list[j] == undefined) {
		    is_argument = true
		} else if (j >= (argument_list.length)) {
                    is_argument = true
                } else if (argument_list[j].type != "Identifier") {
                    is_argument = true
                } else {
                    result.reachable_argument_list.push(argument_list[j].name)
                }
                j = j + 1
            }
	    */
            new_sinks.push(result)
	    
	    active_sink = true

	    if (active_source) {
            	malicious = "true"
	    }
        }
    }
    if (results.length == 0) {
        results.push(false)
    }

    results.sources = new_sources
    results.sinks = new_sinks
    results.malicious = malicious

    return results
}

function doHighlight(color, line) {
    
    if (color == "orange")
        aOrangeData += line + ",";
    else if (color == "red")
        aRedData += line + ",";
    else if (color == "#FF00FF" || color == "yellow")
        aOtherData += line + ",";

    if (resultData.indexOf(sourceDataOld[line - 1] + "#LINE#" + (line)) == -1) {
        resultData.push(sourceDataOld[line - 1] + "#LINE#" + (line));
        resultColor.push(color);
    } else {
        resultColor[resultData.indexOf(sourceDataOld[line - 1] + "#LINE#" + (line))] = color;
    }
}

function getColorTextHeader(color) {
    if (color == "orange")
        return 'Active Source';
    if (color == "yellow")
        return 'Active Variable';
    if (color == "grey")
        return 'Non-Active Variable';
    if (color == "BurlyWood")
        return 'Non-Active Source';
    if (color == "#FF00FF")
        return 'Active Function';
    if (color == "red")
        return 'Active Sink';
    else
        return '';
}

function getColorTextDesc(color) {
    if (color == "orange")
        return 'Active Source is passed which is reached to the sink later';
    if (color == "yellow")
        return 'Active Source is passed through the variable';
    if (color == "grey")
        return 'Source is passed through the variable which could not reach to the sink';
    if (color == "BurlyWood")
        return 'Source that could not reach to the sink';
    if (color == "#FF00FF")
        return 'Source is passed through the function';
    if (color == "red")
        return 'XSS Found - Source reached to the sink';
    else
        return '';
}

function traverseHighLightsVariable() {
    for (var i = 0; i < real_variable_var.length; i++) {
        for (var j = 0; j < sinkResultArguments.length; j++) {
            if (sinkResultArguments[j] == real_variable_var[i].name && sourceListNames.indexOf(sinkResultArguments[j]) == -1) {
                if (aOrange.indexOf(real_variable_var[i].line) == -1) {
                    doHighlight("yellow", real_variable_var[i].line);
                }
                var args = real_variable_var[i].value.split("+");
                var isSink = false;
                for (var k = 0; k < args.length; k++) {
                    if (sinkResultArguments.indexOf(args[k]) == -1) {
                        isSink = true;
                        sinkResultArguments.push(args[k]);
                        sinkResultArgumentsObj.push(real_variable_var[i]);
                    }

                }
                if (isSink == true)
                    traverseHighLightsVariable(real_variable_var);
            }
        }
    }

}

function traverseHighLightsFunction() {
    for (var i = 0; i < real_func_names.length; i++) {
        for (var j = 0; j < sinkResultArguments.length; j++) {
            for (var k = 0; k < real_func_names[i].arguments.variables.length; k++) {
                if (sinkResultArguments[j] == real_func_names[i].arguments.variables[k]) {
                    //sinkResultArguments.push(real_func_names[i].name);
                    //doHighlight("blue",real_func_names[i].line);
                    traverseHighLightsFunctionCall(real_func_names[i].name, real_func_names[i].arguments.variables[k], k);

                }
            }

        }
    }

    for (var i = 0; i < real_func_call.length; i++) {
        for (var j = 0; j < sinkResultArguments.length; j++) {
            for (var k = 0; k < sinkResultArgumentsObj[j].arguments.variables.length; k++) {
                if (real_func_call[i].name == sinkResultArgumentsObj[j].arguments.variables[k]) {
                    if (sinkResultArgumentsObj.indexOf(real_func_call[i]) == -1) {
                        sinkResultArguments.push(real_func_call[i].name);
                        sinkResultArgumentsObj.push(real_func_call[i]);
                        traverseHighLightsFunction();
                    }
                }
            }

        }
    }

}

function traverseHighLightsFunctionCall(funcName, varName, pos) {
    for (var i = 0; i < real_func_call.length; i++) {
        if (real_func_call[i].name == funcName) {
            if (redLine.indexOf(real_func_call[i].line) == -1) {
                if (aOrange.indexOf(real_func_call[i].line) == -1) {
                    doHighlight("#FF00FF", real_func_call[i].line);
                }
                for (var j = 0; j < convertedFunction.length; j++) {
                    if (convertedFunction[j].name == real_func_call[i].name && convertedFunction[j].startScope == real_func_call[i].startScope && convertedFunction[j].endScope == real_func_call[i].endScope) {
                        doHighlight("#FF00FF", convertedFunction[j].line);
                        traverseConvertedFunction(convertedFunction[j]);
                    }
                }
            }
            if (sinkResultArguments.indexOf(real_func_call[i].arguments.variables[pos]) == -1) {
                sinkResultArguments.push(real_func_call[i].arguments.variables[pos]);
                sinkResultArgumentsObj.push(real_func_call[i]);
                traverseHighLightsFunction();
            }
        }
    }
}

function traverseConvertedFunction(obj) {
    for (var i = 0; i < convertedFunction.length; i++) {
        if (obj.value == convertedFunction[i].name && obj.startScope == convertedFunction[i].startScope && obj.endScope == convertedFunction[i].endScope) {
            doHighlight("#FF00FF", convertedFunction[i].line);
            traverseConvertedFunction(convertedFunction[i]);
        }
    }
}

function traverseHighLightsFunctionReturn() {
    for (var i = 0; i < real_func_names.length; i++) {
        for (var k = 0; k < real_func_names[i].returns.variables.length; k++) {
            if (real_func_names[i].returns.variables[k] != undefined) {
                var returnValue = real_func_names[i].returns.variables[k];
                for (var j = 0; j < sinkResultArguments.length; j++) {

                    if (sinkResultArguments[j] == real_func_names[i].name && sinkResultArguments.indexOf(returnValue) == -1) {
                        sinkResultArguments.push(returnValue);
                        sinkResultArgumentsObj.push(real_func_names[i]);
                    }
                }
            }
        }
    }
}

/*
 * Take an object in and iterate through it
 *
 *
 */
function checkAssignValue(obj, source, actualSource, sourceObj) {
    
    for (var i = 0; i < obj.length; i++) {
        // Might be able to remove this
        if (obj[i].value != undefined) {
            if (negativeSource.indexOf(obj[i].value) != -1) {
                obj[i].negativeSource = 1;
            }
            if (sourceObj) {
                if (sourceObj.negativeSource2 == 1 && positiveSource.indexOf(sourceObj.name) == -1) {
                    obj[i].negativeSource = 1;
                }
            }
            var multipleValue = obj[i].value.split("+");
            var isPass = false;

            for (var j = 0; j < multipleValue.length; j++) {
                var aVal = multipleValue[j].split(".");
                for (var k = 0; k < aVal.length; k++) {
                    if ((semiSource.indexOf(aVal[k]) != -1 || blackList.indexOf(aVal[k]) != -1) && sourceObj != null) {
                        semiSource.push(obj[i].name);
                        isPass = true;
                        break;
                    }
                }
            }

            if (obj[i].value.indexOf(actualSource) != -1 || multipleValue.indexOf(source) != -1 || isPass == true) {
                var isScope = true;
                for (var j = 0; j < multipleValue.length; j++) {
                    if (multipleValue[j] == source && sourceObj != null) {
                        if (sourceObj.startScope && obj[i].line) {
                            if (obj[i].line >= sourceObj.startScope && obj[i].line <= sourceObj.endScope) {
                                for (var k = i - 1; k >= 0; k--) {
                                    if (obj[k].name == multipleValue[j]) {
                                        if (obj[k] != sourceObj) {
                                            isScope = false;
                                        }
                                    }
                                }
                            } else {
                                isScope = false;
                            }
                            if (isScope == true) {
                                for (var k = 0; k < real_func_names.length; k++) {
                                    if (real_func_names[k].line == obj[i].startScope) {
                                        for (var p = 0; p < real_func_names[k].arguments.variables.length; p++) {
                                            if (real_func_names[k].arguments.variables[p] == multipleValue[j]) {
                                                isScope = false;
                                                for (var m = 0; m < real_func_call.length; m++) {
                                                    if (real_func_call[m].name == real_func_names[k].name) {
                                                        for (var n = 0; n < real_func_call[m].arguments.variables.length; n++) {
                                                            if (blackList.indexOf(real_func_call[m].arguments.variables[n]) != -1) {
                                                                isScope = true;
                                                                break;
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                }
                if (isScope == false) {
                    continue;
                }
                if (obj[i].value.indexOf(actualSource) != -1) {
                    isSource = true;
                }
                if (blackList.indexOf(obj[i].name) == -1) {
                    blackList.push(obj[i].name);
                    blackListObj.push(obj[i]);

                    if (isSource == true) {
                        doHighlight("orange", obj[i].line);
                        sourceList.push(obj[i].name + "#line#" + obj[i].line);
                        sourceListNames.push(obj[i].name);
                        sourceListObj.push(obj[i]);
                        semiSource.push(obj[i].name);
                    } 
		    /*else {
                        if (aOrange.indexOf(obj[i].line) == -1) {
                            doHighlight("grey", obj[i].line);
                        }
                    }*/

                    isSource = false;

                    checkAssignValue(real_variable_const, obj[i].name, actualSource, obj[i]);
                    checkAssignValue(real_variable_var, obj[i].name, actualSource, obj[i]);
                    //checkAssignValue(real_variable_obj,obj[i].name,actualSource,obj[i]);
                    checkFunctionCallee(obj[i].name, actualSource, obj[i]);
                    checkFunctionReturnValue(obj[i].name, actualSource, obj[i]);

                }
                isSource = false;
            }
        }
    }
}

function checkFunctionCallee(val, actualSource, sourceObj) {
    for (var i = 0; i < real_func_call.length; i++) {
        for (var j = 0; j < real_func_call[i].arguments.variables.length; j++) {
            var args = (real_func_call[i].arguments.variables[j] || "").split("+");
            for (var k = 0; k < args.length; k++) {

                if (args[k] == val) {
                    checkPassValueToFunction(real_func_call[i].name, args[k], j, actualSource, sourceObj);
                    if (real_func_call[i - 1]) {
                        sourceObj.value = real_func_call[i - 1].name;
                        checkRecursiveFunctionCallee(real_func_call[i - 1], real_func_call[i], actualSource, sourceObj, real_func_call, i);
                    }
                }
            }
        }
    }
}
    function checkRecursiveFunctionCallee(func, func2, actualSource, sourceObj, realFunc, pos) {
        var doRepeat = false;
        for (var j1 = 0; j1 < func.arguments.variables.length; j1++) {

            if (func.arguments.variables[j1] != undefined) {

                var args2 = func.arguments.variables[j1].split("+");

                for (var k1 = 0; k1 < args2.length; k1++) {
                    var aVal = args2[k1].split(".");

                    if (aVal[0] == func2.name) {
                        doRepeat = true;
                        checkPassValueToFunction(func.name, aVal[0], j1, actualSource, sourceObj);
                        break;
                    }
                }
            }
        }
        if (doRepeat == true) {
            pos--;
            if (realFunc[pos - 1]) {
                checkRecursiveFunctionCallee(realFunc[pos - 1], realFunc[pos], actualSource, sourceObj, realFunc, pos);
            }
        }
    }

    function checkPassValueToFunction(name, val, pos, actualSource, sourceObj) {
        for (var i = 0; i < real_func_names.length; i++) {
            if (name == real_func_names[i].name) {
                if (sourceObj.negativeSource == 1 && positiveSource.indexOf(real_func_names[i].name) == -1) {
                    real_func_names[i].negativeSource2 = 1;
                }
                blackList.push(real_func_names[i].arguments.variables[pos]);
                blackListObj.push(real_func_names[i]);
                //checkAssignValue(real_variable_obj,real_func_names[i].arguments.variables[pos],actualSource,sourceObj);
                checkAssignValue(real_variable_var, real_func_names[i].arguments.variables[pos], actualSource, sourceObj);
            }
        }
    }

    function checkFunctionReturnValue(val, actualSource, sourceObj) {
        for (var i = 0; i < real_func_names.length; i++) {
            for (var k = 0; k < real_func_names[i].returns.variables.length; k++) {
                var returnValue = "";
                if (real_func_names[i].returns.variables[k] != undefined) {
                    returnValue = real_func_names[i].returns.variables[k];
                }
                if (returnValue != "") {
                    aVal = returnValue.split(".");
                    if (blackList.indexOf(aVal[0]) != -1 && blackList.indexOf(real_func_names[i].name) == -1) {
                        blackList.push(real_func_names[i].name);
                        blackListObj.push(real_func_names[i]);
                        checkAssignValue(real_variable_var, real_func_names[i].name, actualSource, real_func_names[i]);
                    }
                }
            }
        }

    }

    function checkSinkWithDirectSource(source) {
        for (var i = 0; i < sink.length; i++) {
            for (var j = 0; j < real_func_call.length; j++) {
                if (real_func_call[j].name.indexOf(sink[i]) != -1) {
                    for (var k = 0; k < real_func_call[j].arguments.variables.length; k++) {
                        var args = real_func_call[j].arguments.variables[k].split("+");
                        for (var l = 0; l < args.length; l++) {
                            if (args[l].indexOf(source) != -1) {
                                if (real_func_call[j].startLine) {
                                    for (var lineCount = parseInt(real_func_call[j].startLine); lineCount <= parseInt(real_func_call[j].endLine); lineCount++) {
                                        doHighlight("red", lineCount);
                                        redLine.push(lineCount);
                                    }
                                } else {
                                    doHighlight("red", real_func_call[j].line);
                                    redLine.push(real_func_call[j].line)
                                }
                                isXSS = true;
                            }
                        }
                    }

                    if (sinkWithConstantParam && (sinkWithConstantParam.indexOf(sink[i]) != -1)) {
                        for (var k = 0; k < real_func_call[j].arguments.literals.length; k++) {
                            var args = real_func_call[j].arguments.literals[k].split("+");
                            for (var l = 0; l < args.length; l++) {
                                if (args[l].indexOf(source) != -1) {
                                    doHighlight("red", real_func_call[j].line);
                                    redLine.push(real_func_call[j].line);
                                    isXSS = true;
                                }
                            }
                        }
                    }
                }
            }

            for (var j = 0; j < real_variable_var.length; j++) {
                if (real_variable_var[j].name.indexOf(sink[i]) != -1) {
                    var multipleValue = real_variable_var[j].value.split("+");
                    for (var k = 0; k < multipleValue.length; k++) {
                        if (multipleValue[k].indexOf(source) != -1) {
                            doHighlight("red", real_variable_var[j].line);
                            redLine.push(real_variable_var[j].line);
                            sinkResultArguments.push(real_variable_var[j].name);
                            sinkResultArgumentsObj.push(real_variable_var[j]);
                            isXSS = true;
                        }
                    }
                }
            }

        }
    }

    function clone(obj) {
        if (null == obj || "object" != typeof obj) return obj;
        var copy = obj.constructor();
        for (var attr in obj) {
            if (obj.hasOwnProperty(attr)) copy[attr] = obj[attr];
        }
        return copy;
    }


    /*
     * Takes in a source from the designated list and checks to see if it is pressent in the code.
     *
     */
    function checkFunctionsWithDirectSource(source) {
        for (var j = 0; j < real_func_call.length; j++) {
            for (var k = 0; k < real_func_call[j].arguments.variables.length; k++) {
                var args = (real_func_call[j].arguments.variables[k] || "").split("+");
                for (var l = 0; l < args.length; l++) {
                    if (args[l].indexOf(source) != -1) {
                        for (var l2 = 0; l2 < real_variable_var.length; l2++) {
                            if (real_variable_var[l2].line == real_func_call[j].line) {
                                doHighlight("orange", real_variable_var[l2].line);
                                aOrange.push(real_variable_var[l2].line);

                                var newFunction = clone(real_variable_var[l2]);
                                newFunction.name = args[l];
                                real_variable_var.push(newFunction);
                                blackList.push(newFunction.name);
                                blackListObj.push(newFunction);

                                sourceList.push(real_variable_var[l2].name + "#line#" + newFunction.line);
                                sourceListNames.push(newFunction.name);
                                sourceListObj.push(newFunction);
                                semiSource.push(newFunction.name);
                                checkFunctionCallee(newFunction.name, newFunction.name, newFunction);

                                checkFunctionReturnValue(newFunction.name, newFunction.name, newFunction);

                                break;
                            }
                        }
                        for (var j1 = 0; j1 < real_func_names.length; j1++) {
                            if (real_func_names[j1].name == real_func_call[j].name && real_func_names[j1].arguments.variables[l]) {
                                doHighlight("orange", real_func_call[j].line);
                                aOrange.push(real_func_call[j].line);

                                blackList.push(args[l]);
                                blackListObj.push(real_func_call[j]);
                                blackList.push(real_func_names[j1].arguments.variables[l]);
                                blackListObj.push(real_func_call[j]);
                                break;
                            }
                        }
                    }
                    checkSourceRecursionInFunction(args[l], real_func_call[j]);
                }
            }
        }
    }

    function checkSourceRecursionInFunction(funcName, funcCall) {
        for (var m = 0; m < real_func_names.length; m++) {
            if (funcName == real_func_names[m].name) {
                for (var m2 = 0; m2 < real_func_names[m].returns.variables.length; m2++) {
                    funcCall.arguments.variables.push(real_func_names[m].returns.variables[m2]);
                }
                for (var m4 = 0; m4 < real_func_call.length; m4++) {
                    if (funcName == real_func_call[m4].name) {
                        funcName = real_func_call[m4].arguments.variables[0];
                        checkSourceRecursionInFunction(funcName, funcCall);
                    }
                }
            }
        }
    }

    function checkSink() {
        for (var i = 0; i < sink.length; i++) {
            for (var j = 0; j < blackList.length; j++) {
                checkInFunctionCall(sink[i], blackList[j], blackListObj[j]);
                checkInAssignToSink(sink[i], blackList[j], blackListObj[j]);
            }
        }

        for (var i = 0; i < conditionalSink.length; i++) {
            for (var j = 0; j < blackList.length; j++) {
                checkInFunctionCall(conditionalSink[i], blackList[j], blackListObj[j]);
            }
        }
    }

    function checkInFunctionCall(sink, val, sinkObj) {
        if (sinkObj.negativeSource == 1 || sinkObj.negativeSource2 == 1) {
            return;
        }

        var conditionalSinkObj = sink.split("(");
        sink = conditionalSinkObj[0];

        for (var i = 0; i < real_func_call.length; i++) {
            if (real_func_call[i].name) {
                if (real_func_call[i].name.indexOf(sink) != -1) {
                    for (var j = 0; j < real_func_call[i].arguments.variables.length; j++) {
                        var args = real_func_call[i].arguments.variables[j].split("+");
                        for (var k = 0; k < args.length; k++) {

                            for (var j1 = 0; j1 < real_func_call.length; j1++) {
                                if (real_func_call[j1].name == args[k] && real_func_call[j1].line == real_func_call[i].line) {
                                    for (var t = 0; t < real_func_call[j1].returns.variables.length; t++) {
                                        var returnValue = real_func_call[j1].returns.variables[t];
                                        if (blackList.indexOf(returnValue) != -1) {
                                            doHighlight("red", real_func_call[i].line);
                                            redLine.push(real_func_call[i].line);
                                            sinkResultArguments.push(returnValue);
                                            sinkResultArgumentsObj.push(real_func_call[i]);
                                            isXSS = true;
					    break;
                                        }
                                    }
                                }
                            }

                            if (args[k] == val) {
                                var isScope = true;
                                for (var p = 0; p < real_variable_var.length; p++) {
                                    if (real_variable_var[p].line <= real_func_call[i].line && real_variable_var[p].line > sinkObj.line) {
                                        if (real_variable_var[p].name == args[k]) {
                                            var obj = real_variable_var[p].value.split(".");
                                            if (obj[0] != real_variable_var[p].name && blackList.indexOf(obj[0]) == -1) {
                                                isScope = false;
                                                break;
                                            }
                                        }
                                    }

                                    if (sinkObj.name == real_variable_var[p].name) {
                                        if (sinkObj != real_variable_var[p] && !(sinkObj.startScope == real_variable_var[p].startScope && sinkObj.endScope == real_variable_var[p].endScope)) {
                                            isScope = false;
                                        } else {
                                            isScope = true;
                                        }
                                    }
                                    if (real_variable_var[p].line == real_func_call[i].line) {
                                        break;
                                    }
                                }

                                if (isScope == true) {
                                    if (real_func_call[i].line > sinkObj.endScope || real_func_call[i].line < sinkObj.startScope) {
                                        isScope = false;
                                    }
                                }
                               
                                for (var t = 0; t < real_func_names.length; t++) {
                                    if (real_func_names[t].line == real_func_call[i].startScope || real_func_names[t].line == (real_func_call[i].startScope - 1)) {
                                        for (var p = 0; p < real_func_names[t].arguments.variables.length; p++) {
                                            if (real_func_names[t].arguments.variables[p] == args[k]) {
                                                isScope = false;
                                            }
                                        }
                                        if (isScope == false) {
                                            for (var p = 0; p < real_func_call.length; p++) {
                                                if (real_func_call[p].name == real_func_names[t].name) {
                                                    for (var x = 0; x < real_func_call[p].arguments.variables.length; x++) {
                                                        if (blackList.indexOf(real_func_call[p].arguments.variables[x]) != -1) {
							    isScope = true;
                                                            sinkResultArguments.push(real_func_call[p].arguments.variables[x]);
                                                            sinkResultArgumentsObj.push(real_func_call[p]);
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                        if (isScope == true) {
                                            break;
                                        }
                                    }
                                }
                               
                                if (isScope == true) {
                                    if (conditionalSinkObj[1]) {
                                        isScope = false;
                                        var expectedValue = conditionalSinkObj[1].split("|");
                                        var params = real_func_call[i].arguments.literals;
                                        for (var e1 = 0; e1 < expectedValue.length; e1++) {
                                            if (params.indexOf(expectedValue[e1]) != -1) {
                                                isScope = true;
                                                break;
                                            }
                                        }
                                    }
				    else {
					doHighlight("red", real_func_call[i].line);
					redLine.push(real_func_call[i].line);
					sinkResultArguments.push(args[k]);
					sinkResultArgumentsObj.push(real_func_call[i]);
					isXSS = true;
				    }
				}
                            }
                        }
                    }
                    if (sinkWithConstantParam && (sinkWithConstantParam.indexOf(sink) != -1)) {
                        for (var j = 0; j < real_func_call[i].arguments.literals.length; j++) {
                            var args = real_func_call[i].arguments.literals[j].split("+");
                            for (var k = 0; k < args.length; k++) {
                                if (args[k] == val) {
                                    doHighlight("red", real_func_call[i].line);
                                    redLine.push(real_func_call[i].line);
                                    sinkResultArguments.push(args[k]);
                                    sinkResultArgumentsObj.push(real_func_call[i]);
                                    isXSS = true;
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    function checkInAssignToSink(sink, val, sinkObj) {
        if (sinkObj.negativeSource == 1 || sinkObj.negativeSource2 == 1) {
            return;
        }
        for (var i = 0; i < real_variable_var.length; i++) {
            if (real_variable_var[i].name.indexOf(sink) != -1) {
                var multipleValue = real_variable_var[i].value.split("+");
                for (var j = 0; j < multipleValue.length; j++) {
                    if (multipleValue[j] == val) {
                        var isScope = true;
                        for (var p = 0; p < real_variable_var.length; p++) {
                            if (sinkObj.name == real_variable_var[p].name) {

                                if (real_variable_var[p].line <= real_variable_var[i].line && real_variable_var[p].line > sinkObj.line) {
                                    var obj = real_variable_var[p].value.split(".")
                                    if (obj[0] != real_variable_var[p].name && blackList.indexOf(obj[0]) == -1) {
                                        isScope = false;
                                        break;
                                    }
                                }

                                if (sinkObj == real_variable_var[p] && !(sinkObj.startScope == real_variable_var[p].startScope && sinkObj.endScope == real_variable_var[p].endScope)) {
                                    isScope = false;
                                } else {
                                    sinkResultArguments.push(real_variable_var[p].name);
                                    sinkResultArgumentsObj.push(real_variable_var[p]);
                                    isScope = true;
                                }
                            }
                            if (real_variable_var[p].line == real_variable_var[i].line) {
                                break;
                            }
                        }
                        if (isScope == true) {
                            var isScope2 = false;
                            for (var k = 0; k < real_func_names.length; k++) {
                                if (real_func_names[k].line == real_variable_var[i].startScope || real_func_names[k].line == (real_variable_var[i].startScope - 1)) {
                                    for (var p = 0; p < real_func_names[k].arguments.variables.length; p++) {
                                        if (real_func_names[k].arguments.variables[p] == multipleValue[j]) {
                                            isScope = false;
                                        }
                                    }

                                    if (isScope == false) {
                                        for (var p = 0; p < real_func_call.length; p++) {
                                            if (real_func_call[p].name == real_func_names[k].name) {
                                                for (var x = 0; x < real_func_call[p].arguments.variables.length; x++) {
                                                    if (blackList.indexOf(real_func_call[p].arguments.variables[x]) != -1) {
                                                        isScope = true;
                                                        isScope2 = true;
                                                        sinkResultArguments.push(real_func_call[p].arguments.variables[x]);
                                                        sinkResultArgumentsObj.push(real_func_call[p]);
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                                if (isScope2 == true) {
                                    break;
                                }
                            }
                        }

                        if (isScope == true) {
                            if (real_variable_var[i].line > sinkObj.endScope || real_variable_var[i].line < sinkObj.startScope) {
                                isScope = false;
                            }
                        }
                        if (isScope == true) {
                            doHighlight("red", real_variable_var[i].line);
                            redLine.push(real_variable_var[i].line);
                            sinkResultArguments.push(val);
                            sinkResultArgumentsObj.push(real_variable_var[i]);
                            isXSS = true;
                        }
                        break;
                    }
                }
            }
        }
    }

    function parseJavascriptNativeFunction() {
        for (var i = 0; i < real_variable_var.length; i++) {
            var val = real_variable_var[i].value;
            var aVal = val.split(".")
            for (var j = 0; j < aVal.length; j++) {
                if (aVal[j] == "reverse") {
                    parseJavascriptNativeFunctionReverse(real_variable_const, aVal[0]);
                }
            }
        }
    }

    function parseJavascriptNativeFunctionReverse(real_variable_const, name) {
        for (var i = 0; i < real_variable_const.length; i++) {
            if (real_variable_const[i].name == name) {
                var data = real_variable_const[i].value.split("").reverse().join("");
                real_variable_const[i].value = data;
            }
        }
    }

