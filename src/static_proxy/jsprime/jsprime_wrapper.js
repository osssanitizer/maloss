var fs = require("fs");
var ast_pb = require("../../proto/javascript/ast_pb");
var module_pb = require("../../proto/javascript/module_pb");
var cp = require('child_process'); 

var results;

function getSourceNode(source, package_name) {
	
    var sourceNode = new ast_pb.AstNode();
    //var source = package_results.sources[0]

    sourceNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL_REF_EXPR)
    sourceNode.setName(source.property)		 
    sourceNode.setFullName(package_name + "." + source.property)
    sourceNode.setBaseType(package_name)
    sourceNode.setArgumentsList(source.argument_list)
    
    return sourceNode;
}

function getSinkNode(sink, package_name) {
    
    var sinkNode = new ast_pb.AstNode();
    //var sink = package_results.sinks[0] 

    sinkNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL_REF_EXPR)
    sinkNode.setName(sink.property)
    sinkNode.setFullName(package_name + "." + sink.property)
    sinkNode.setBaseType(package_name)
    sinkNode.setArgumentsList(sink.argument_list)

    return sinkNode;
}

function getPropagateNode(package_results) {
    var propagateNode = new ast_pb.AstNode();
    return propagateNode;
}

function getSourceSummary(moduleSource, source, file_name, file_location) {

    var file_name_stripped = file_name.replace(".js", "")
	
	var sourceNode = new ast_pb.AstNode();
	//var source = package_results.sources[0]
	
	sourceNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL)
	sourceNode.setName(source.property)
		 
	sourceNode.setFullName(file_name_stripped + "." + source.property)
	sourceNode.setBaseType(file_name_stripped)
	sourceNode.setArgumentsList(source.argument_list)

    // Add reachable nodes
    //var new_source = moduleSource.addReachableSources()
     
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

    //new_source.setNode(reachable_node)   
    //moduleSource.addReachableSources(reachable_node);
    return reachable_node;
}

function getSinkSummary(moduleSink, sink, file_name, file_location) {
   
    var file_name_stripped = file_name.replace(".js", "")
    var sinkNode = new ast_pb.AstNode();

    //var sink = package_results.sinks[0] 
    sinkNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL)
    sinkNode.setName(sink.property)
    sinkNode.setFullName(file_name_stripped + "." + sink.property)
    sinkNode.setBaseType(file_name_stripped)
    sinkNode.setArgumentsList(sink.argument_list)

    // Add reachable nodes
    //var new_sink = moduleSink.addReachableSinks()
    
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
     
    reachable_node.setRange(test_range)
   
    var id
    for (var i = 0; i < config.array[0].length; i++) {
	    node = config.array[0][i]
	    if (node[2] == sink.object + "." + sink.property) {
		    id = node[12]
	    }
    }
    reachable_node.setId(id)
  
    return reachable_node;
}

function setStatic(object, package_results, file_name, file_location, package_name) {

    var unique_ss = [];
    var existing_ss = [];

    // Rotate through the flows
    for (var i = 0; i < package_results.sources.length; i++) {
	   
	    var sourceNode = getSourceNode(package_results.sources[i], package_name);   
	    var moduleSource = new module_pb.ModuleSource();
	    reachable_source = getSourceSummary(moduleSource, package_results.sources[i], file_name, file_location);
	    moduleSource.addReachableSources(reachable_source)
	    moduleSource.setNode(sourceNode)

	    var sinkNode = getSinkNode(package_results.sinks[i], package_name); 
	    var moduleSink = new module_pb.ModuleSink();

	    reachable_sink = getSinkSummary(moduleSink, package_results.sinks[i], file_name, file_location);	
	    moduleSink.addReachableSinks(reachable_sink)
	    moduleSink.setNode(sinkNode)

	    var flow = new module_pb.ModuleFlow();
	    flow.setSource(reachable_source);
	    flow.setSink(reachable_sink);
	    object.addFlows(flow);
		
	    //object.addSources(moduleSource);
	    //object.addSinks(moduleSink);

	    // Check to see whether or not sources and sinks were already included in flows
            package_results.sources_sinks.forEach(function(source_sink) { 
		var id_code = source_sink.object.name + source_sink.property.name + source_sink.loc.start.line
	
	    	if ((source_sink.object.name + "." + source_sink.property.name) == package_results.sources[i].reachable_object + "." + package_results.sources[i].reachable_property) {
		}
		else if ((source_sink.object.name + "." + source_sink.property.name) == package_results.sinks[i].reachable_object + "." + package_results.sinks[i].reachable_property) {
		}
		else {
			if (existing_ss.indexOf(id_code) > -1) {
				console.log("Merideth")
			}
			else {
				console.log(id_code)
				unique_ss.push(source_sink)
				existing_ss.push(id_code)
			}
		}
	    })
    }

    console.log(unique_ss)
    unique_ss.forEach(function(source_sink) { 
	 
	 if (source_sink.source_sink == "SOURCE") {

		var sourceNode = new ast_pb.AstNode();
		sourceNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL_REF_EXPR)
    		sourceNode.setName(source_sink.calling_function)		 
    		sourceNode.setFullName(package_name + "." + source_sink.calling_function)
    		sourceNode.setBaseType(package_name)

	 	var moduleSource = new module_pb.ModuleSource();

	    	var temp = []
	    	temp.reachable_property = source_sink.property.name
            	temp.reachable_object = source_sink.object.name
	    	temp.row = source_sink.loc.start.line
		temp.startColumn = source_sink.loc.start.column
		temp.endColumn = source_sink.loc.end.column
	
    		reachable_source = getSourceSummary(moduleSource, temp, file_name, file_location);
    		moduleSource.addReachableSources(reachable_source)
    		moduleSource.setNode(sourceNode)
	    	object.addSources(moduleSource);

	 } else if (source_sink.source_sink == "SINK") {

		var sinkNode = new ast_pb.AstNode();
		sinkNode.setType(ast_pb.AstNode.NodeType.FUNCTION_DECL_REF_EXPR)
    		sinkNode.setName(source_sink.calling_function)		 
    		sinkNode.setFullName(package_name + "." + source_sink.calling_function)
    		sinkNode.setBaseType(package_name)

	    	var temp = []
	    	temp.reachable_property = source_sink.property.name
            	temp.reachable_object = source_sink.object.name
	    	temp.row = source_sink.loc.start.line
		temp.startColumn = source_sink.loc.start.column
		temp.endColumn = source_sink.loc.end.column
	
	    	var moduleSink = new module_pb.ModuleSink();
	        reachable_sink = getSinkSummary(moduleSink, temp, file_name, file_location);
	        moduleSink.addReachableSinks(reachable_sink)
	        moduleSink.setNode(sinkNode)
    		object.addSinks(moduleSink);
	 }
    })
}

// Process input
var target_package = process.argv[2]
var package_location = process.argv[3]
var config_location = process.argv[4]
var output_location = process.argv[5]
console.log("target package " + target_package + ", located at " + package_location + ", config at " + config_location + ", output to " + output_location);

// load the astgen config from file
var configStr = fs.readFileSync(config_location);
var config = ast_pb.AstLookupConfig.deserializeBinary(configStr);
console.log("loaded config with " + config.getApisList().length + " apis to check!");

var output_stream = fs.createWriteStream(output_location)

processInput(package_location, package_location, config.getApisList(), function(package_results, file_name, file_location) {
	processResults(package_results, file_name, file_location)
})


function processInput(input, original_input, source_sink_list, callback) {
	var analyze_result;
	if (fs.lstatSync(input).isDirectory()) {
		fs.readdir(input, function(err, files) {
			if (err) return console.log(err);

			files.forEach( function(file) {
				processInput(input + "/" + file, original_input, source_sink_list, callback)
			});
		});
	}
	else {
		if (input.substring(input.length - 3, input.length) == '.js') {
			
			source_sink_list = JSON.stringify(source_sink_list)

			/* FIXME: kill the forked process when the timeout is triggered. potentially the cause for crashing of root partition. */
			var ls = cp.fork("./engine.js", [input, source_sink_list])
			var timeout_val = setTimeout(function() { ls.kill() }, 30000);
				
			ls.on('message', (msg) => {
				callback(JSON.parse(msg), input, original_input)
				clearTimeout(timeout_val)
			});
		}
	}
}


function processResults(package_results, file_location, original_location) {

        split_path = file_location.split('/')
	file_name = split_path[split_path.length - 1]
	package_name = target_package.split('.')[0]
	
	relative_path = "." + file_location.replace(original_location, "")

	console.log("Malicious: " + package_results.malicious)

	if (package_results.malicious == 'true') {

		var results = new module_pb.ModuleStatic();

		// compute and fill the results into protobuf
		setStatic(results, package_results, file_name, relative_path, package_name);
		
		output_stream.write(results.serializeBinary(), (err) => {
			if (err) throw err;
			console.log('The file has been saved!');

			console.log(file_name)
			console.log(output_location)
		})
	}
}
