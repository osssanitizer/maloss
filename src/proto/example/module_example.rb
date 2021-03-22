# FIXME: this is needed for importing protobuf generated code.
$LOAD_PATH.unshift(File.expand_path('../ruby/', File.dirname(__FILE__)))
require "ast_pb"
require "module_pb"


def get_mock_source_node()
    source_node = Proto::AstNode.new
    return source_node
end


def get_mock_sink_node()
    sink_node = Proto::AstNode.new
    return sink_node
end


def get_mock_propagate_node()
    propagate_node = Proto::AstNode.new
    return propagate_node
end


def get_mock_danger_node()
    danger_node = Proto::AstNode.new
    return danger_node
end


def set_result(result)
    source_node = get_mock_source_node()
    sink_node = get_mock_sink_node()
    propagate_node = get_mock_propagate_node()
    flow = Proto::ModuleFlow.new
    flow.source = source_node
    flow.source.source_type = Proto::SourceType::SOURCE_FILE
    flow.sink = sink_node
    flow.sink.sink_type = Proto::SinkType::SINK_NETWORK
    flow.hops << propagate_node
    result.flows << flow

    danger_node = get_mock_danger_node()
    danger = Proto::ModuleDanger.new
    danger.danger = danger_node
    result.dangers << danger
end


def set_summary(summary)
    source_node = Proto::AstNode.new
    source_node.type = Proto::AstNode::NodeType::FUNCTION_DECL
    module_source = Proto::ModuleSource.new
    module_source.node = source_node
    summary.sources << module_source

    sink_node = Proto::AstNode.new
    sink_node.type = Proto::AstNode::NodeType::FUNCTION_DECL
    module_sink = Proto::ModuleSink.new
    module_sink.node = sink_node
    summary.sinks << module_sink
end


# load the astgen config from file
# https://stackoverflow.com/questions/130948/read-binary-file-as-string-in-ruby
configStr = File.open("../../../config/astgen_ruby_smt.config.pb", "rb") { |f| f.read }
# protobuf for ruby
# https://developers.google.com/protocol-buffers/docs/reference/ruby-generated
config = Proto::AstLookupConfig.decode(configStr)
puts "loaded config with #{config.apis.length} apis to check!"

# initialize result and summary
result = Proto::ModuleResult.new
summary = Proto::ModuleSummary.new
static = Proto::ModuleStatic.new

# compute and fill the results into protobuf
set_result(result)
set_summary(summary)
static.flows += result.flows
static.dangers += result.dangers
static.sources += summary.sources
static.sinks += summary.sinks

# output protobuf message in binary format
module_result_pb_fname = "module_result_rb.pb"
module_summary_pb_fname = "module_summary_rb.pb"
module_static_pb_fname = "module_static_rb.pb"

# output protobuf message in binary format
File.open(module_result_pb_fname, 'w') { |f| f.write(Proto::ModuleResult.encode(result)) }
File.open(module_summary_pb_fname, 'w') { |f| f.write(Proto::ModuleSummary.encode(summary)) }
File.open(module_static_pb_fname, 'w') { |f| f.write(Proto::ModuleStatic.encode(static)) }
