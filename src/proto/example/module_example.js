var fs = require("fs");
var ast_pb = require("../javascript/ast_pb");
var module_pb = require("../javascript/module_pb");
var cp = require('child_process'); 

var results;

function getSourceNode(package_results) {
    	var sourceNode = new ast_pb.AstNode();
	
	var source = package_results.sources[0]
	
	sourceNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL_REF_EXPR)
	sourceNode.setName(source.property)
		 
	    sourceNode.setFullName(source.object + "." + source.property)
	    sourceNode.setBaseType(source.object)
	    sourceNode.setArgumentsList(source.argument_list)
	    
    return sourceNode;
}

function getSinkNode(package_results) {
    var sinkNode = new ast_pb.AstNode();

    var sink = package_results.sinks[0] 

    sinkNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL_REF_EXPR)
	    sinkNode.setName(sink.property)
	    sinkNode.setFullName(sink.object + "." + sink.property)
	    sinkNode.setBaseType(sink.object)
	    sinkNode.setArgumentsList(sink.argument_list)

    return sinkNode;
}

function getPropagateNode(package_results) {
    var propagateNode = new ast_pb.AstNode();
    return propagateNode;
}

function getDangerNode() {
    var dangerNode = new ast_pb.AstNode();

	    dangerNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL_REF_EXPR)
	    dangerNode.setName("exec")
	    dangerNode.setFullName("subprocess.exec")
	    dangerNode.setBaseType("subprocess")
	    dangerNode.setArgumentsList(["\"rm\"", "\"-rf\"", "\"/\""])
	    // TODO: look up the id in the config protobuf
	    dangerNode.id = 66
	    // source code location
	    dangerFileInfo = new ast_pb.FileInfo()
	    dangerFileInfo.filename = "danger_filename.py"
	    dangerFileInfo.relpath = "relpath/to/dir"

    return dangerNode;
}

function getSourceSummary(moduleSource, package_results, file_name, file_location) {

    var file_name_stripped = file_name.replace(".js", "")
	
	var sourceNode = new ast_pb.AstNode();
	
	var source = package_results.sources[0]
	
	sourceNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL)
	sourceNode.setName(source.property)
		 
	    sourceNode.setFullName(file_name_stripped + "." + source.property)
	    sourceNode.setBaseType(file_name_stripped)
	    sourceNode.setArgumentsList(source.argument_list)

    // Add reachable nodes
    var new_source = moduleSource.addReachableSources()
     
    var reachable_node = new ast_pb.AstNode();
    
    reachable_node.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL_REF_EXPR)
    reachable_node.setName(source.reachable_property)
    reachable_node.setFullName(source.reachable_object + "." + source.reachable_property)
    reachable_node.setBaseType(source.reachable_object)
    reachable_node.setArgumentsList(source.reachable_argument_list)

    var file_info = new ast_pb.FileInfo
    file_info.setFilename(file_name)
    file_info.setRelpath(file_location)

    var begin_loc = new ast_pb.SourceLocation
    begin_loc.setRow(source.row);
    begin_loc.setColumn(source.startColumn);
    begin_loc.setFileInfo(file_info);

    var end_loc = new ast_pb.SourceLocation
    end_loc.setRow(source.row);
    end_loc.setColumn(source.endColumn);
    end_loc.setFileInfo(file_info);

    var test_range = new ast_pb.SourceRange
    test_range.setStart(begin_loc)
    test_range.setEnd(end_loc)
     
    reachable_node.setRange(test_range)
    
    var id
    for (var i = 0; i < config.array[0].length; i++) {
	node = config.array[0][i]
	if (node[2] == source.object + "." + source.property) {
		id = node[12]
	}
    }
    reachable_node.setId(id)

    new_source.setNode(reachable_node)   
    moduleSource.setNode(sourceNode);
    return moduleSource;
}

function getSinkSummary(moduleSink, package_results, file_name, file_location) {
   
    var file_name_stripped = file_name.replace(".js", "")
    var sinkNode = new ast_pb.AstNode();

    var sink = package_results.sinks[0] 
    sinkNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL)
    sinkNode.setName(sink.property)
    sinkNode.setFullName(file_name_stripped + "." + sink.property)
    sinkNode.setBaseType(file_name_stripped)
    sinkNode.setArgumentsList(sink.argument_list)

    // Add reachable nodes
    var new_sink = moduleSink.addReachableSinks()
     
    var reachable_node = new ast_pb.AstNode();

    reachable_node.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL_REF_EXPR)
    reachable_node.setName(sink.reachable_property)
    reachable_node.setFullName(sink.reachable_object + "." + sink.reachable_property)
    reachable_node.setBaseType(sink.reachable_object)
    reachable_node.setArgumentsList(sink.reachable_argument_list)

    var file_info = new ast_pb.FileInfo
    file_info.setFilename(file_name)
    file_info.setRelpath(file_location)

    var begin_loc = new ast_pb.SourceLocation
    begin_loc.setRow(sink.row);
    begin_loc.setColumn(sink.startColumn);
    begin_loc.setFileInfo(file_info);

    var end_loc = new ast_pb.SourceLocation
    end_loc.setRow(sink.row);
    end_loc.setColumn(sink.endColumn);
    end_loc.setFileInfo(file_info);

    var test_range = new ast_pb.SourceRange
    test_range.setStart(begin_loc)
    test_range.setEnd(end_loc)
     
    //reachable_node.range = test_range
    reachable_node.setRange(test_range)
   
    var id
    for (var i = 0; i < config.array[0].length; i++) {
	    node = config.array[0][i]
	    if (node[2] == sink.object + "." + sink.property) {
		    id = node[12]
	    }
    }
    reachable_node.setId(id)

    new_sink.setNode(reachable_node) 
    moduleSink.setNode(sinkNode);
   
    return moduleSink;
}

function setResult(result, package_results) {
    
    var sourceNode = getSourceNode(package_results);
    var sinkNode = getSinkNode(package_results);
    //var propagateNode = getPropagateNode(package_results);
    sourceNode.setSourceType(ast_pb.SOURCE_FILE);
    sinkNode.setSinkType(ast_pb.SINK_NETWORK);
    var flow = new module_pb.ModuleFlow();
    flow.setSource(sourceNode);
    flow.setSink(sinkNode);
    flow.setSource(flowSource);
    flow.setSink(flowSink);
    result.addFlows(flow);

    /*var dangerNode = getDangerNode();
    var danger = new module_pb.ModuleDanger();
    danger.setSink(dangerNode)
    result.addDangers(danger);*/

}

function setSummary(summary, package_results, file_name, file_location) {
    
    //var sourceNode = new ast_pb.AstNode();
    //sourceNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL);
	
    var moduleSource = new module_pb.ModuleSource();
    moduleSource = getSourceSummary(moduleSource, package_results, file_name, file_location);
         
    //var sinkNode = new ast_pb.AstNode();
    //sinkNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL);
    
    var moduleSink = new module_pb.ModuleSink();
    moduleSink = getSinkSummary(moduleSink, package_results, file_name, file_location);	

    summary.addSources(moduleSource);
    summary.addSinks(moduleSink);
}

// load the astgen config from file
var configStr = fs.readFileSync("../../../config/astgen_javascript_smt.config.pb");
var config = ast_pb.AstLookupConfig.deserializeBinary(configStr);
console.log("loaded config with " + config.getApisList().length + " apis to check!");

// Process input
var target_package = process.argv[2]
processInput(target_package, target_package, config.getApisList(), function(package_results, file_name, file_location) {
	processResults(package_results, file_name, file_location)
})


function processInput(input, original_input, source_sink_list, callback) {
	var analyze_result;
	if (fs.lstatSync(input).isDirectory()) {
		fs.readdir(input, function(err, files) {
			if (err) return console.log(err);

			files.forEach( function(file) {
				processInput(input + file, original_input, source_sink_list, callback) //input + "/" + file
			});
		});
	}
	else {
		if (input.substring(input.length - 3, input.length) == '.js') {
			fs.readFile(input, 'utf8', function (err, code) {
				if (err) {
					throw err;
				}

				source_sink_list = JSON.stringify(source_sink_list)
				var ls = cp.fork("../../../../jsprime/engine.js", [code, source_sink_list])
				var timeout_val = setTimeout(function() { ls.kill() }, 20000);
				
				ls.on('message', (msg) => {
					  callback(JSON.parse(msg), input, original_input)
					  clearTimeout(timeout_val)
				});
			});
		}
	}
}


function processResults(package_results, file_location, original_location) {


	file_name = file_location.split('/').pop()
	relative_path = "/" + original_location.replace(file_location, "")
	
	if (package_results.malicious == 'true') {

		// initialize result and summary
		var result = new module_pb.ModuleResult();
		var summary = new module_pb.ModuleSummary();

		// compute and fill the results into protobuf
		setResult(result, package_results);
		setSummary(summary, package_results, file_name, relative_path);

		var package_name = target_package.split('/').pop()

		// output protobuf message in binary format
		var moduleResultPbFname = package_name + "_result_js.pb";
		var moduleSummaryPbFname = package_name + "_summary_js.pb";

		// output protobuf message in binary format
		fs.writeFileSync(moduleResultPbFname, result.serializeBinary());
		fs.writeFileSync(moduleSummaryPbFname, summary.serializeBinary());
	}
}
