#!/usr/bin/python
# add path to the proto messages
import sys
sys.path.append('../../')

# import the proto messages
import proto.python.ast_pb2 as ast_pb
from proto.python.ast_pb2 import AstNode, AstLookupConfig, FileInfo
from proto.python.module_pb2 import ModuleResult, ModuleSummary, ModuleStatic
from google.protobuf.text_format import MessageToString, Merge


def write_proto_to_file(proto, filename, binary=True):
    if binary:
        f = open(filename, "wb")
        f.write(proto.SerializeToString())
        f.close()
    else:
        f = open(filename, "w")
        f.write(MessageToString(proto))
        f.close()


def read_proto_from_file(proto, filename, binary=True):
    if binary:
        f = open(filename, "rb")
        proto.ParseFromString(f.read())
        f.close()
    else:
        f = open(filename, "r")
        Merge(f.read(), proto)
        f.close()


def get_mock_source_node():
    source_node = AstNode()
    # invocation detail
    source_node.type = AstNode.FUNCTION_DECL_REF_EXPR
    source_node.name = "read"
    source_node.full_name = "file.read"
    source_node.base_type = "file"
    source_node.arguments.extend(["\"/home/maloss/.ssh/id_rsa\"", "\"r\""])
    # TODO: look up the id in the config protobuf
    source_node.id = 22
    # source code location
    source_file_info = FileInfo()
    source_file_info.filename = "source_filename.py"
    source_file_info.relpath = "relpath/to/dir"
    source_node.range.start.row = 10
    source_node.range.start.column = 20
    source_node.range.start.file_info.CopyFrom(source_file_info)
    source_node.range.end.row = 10
    source_node.range.end.column = 40
    source_node.range.end.file_info.CopyFrom(source_file_info)
    return source_node


def get_mock_sink_node():
    sink_node = AstNode()
    # invocation detail
    sink_node.type = AstNode.FUNCTION_DECL_REF_EXPR
    sink_node.name = "send"
    sink_node.full_name = "network.send"
    sink_node.base_type = "network"
    sink_node.arguments.extend(["\"https://www.malicious.com\"", "\"non-blocking\""])
    # TODO: look up the id in the config protobuf
    sink_node.id = 88
    # source code location
    sink_file_info = FileInfo()
    sink_file_info.filename = "sink_filename.py"
    sink_file_info.relpath = "relpath/to/dir"
    sink_node.range.start.row = 200
    sink_node.range.start.column = 8
    sink_node.range.start.file_info.CopyFrom(sink_file_info)
    sink_node.range.end.row = 200
    sink_node.range.end.column = 100
    sink_node.range.end.file_info.CopyFrom(sink_file_info)
    return sink_node


def get_mock_propagate_node():
    # TODO: add propagate node if available
    propagate_node = AstNode()
    return propagate_node


def get_mock_danger_node():
    danger_node = AstNode()
    danger_node.type = AstNode.FUNCTION_DECL_REF_EXPR
    danger_node.name = "exec"
    danger_node.full_name = "subprocess.exec"
    danger_node.base_type = "subprocess"
    danger_node.arguments.extend(["\"rm\"", "\"-rf\"", "\"/\""])
    # TODO: look up the id in the config protobuf
    danger_node.id = 66
    # source code location
    danger_file_info = FileInfo()
    danger_file_info.filename = "danger_filename.py"
    danger_file_info.relpath = "relpath/to/dir"
    danger_node.range.start.row = 888
    danger_node.range.start.column = 0
    danger_node.range.start.file_info.CopyFrom(danger_file_info)
    danger_node.range.end.row = 888
    danger_node.range.end.column = 99
    danger_node.range.end.file_info.CopyFrom(danger_file_info)
    return danger_node


def set_result(result):
    # skip package_info for now
    source_node = get_mock_source_node()
    sink_node = get_mock_sink_node()
    propagate_node = get_mock_propagate_node()
    flow = result.flows.add()
    flow.source.CopyFrom(source_node)
    flow.source.source_type = ast_pb.SOURCE_FILE
    flow.sink.CopyFrom(sink_node)
    flow.sink.sink_type = ast_pb.SINK_NETWORK
    flow.hops.add().CopyFrom(propagate_node)

    danger_node = get_mock_danger_node()
    danger = result.dangers.add()
    danger.danger.CopyFrom(danger_node)


def set_summary(summary):
    # skip package_info for now
    # there is no id for new sources
    source = summary.sources.add()
    source.node.type = AstNode.FUNCTION_DECL
    source.node.name = "get"
    source.node.full_name = "requests.get"
    source.node.base_type = "requests"
    source.node.arguments.extend(["url", "mode"])
    # TODO: set the source range for source.node
    reachable_old_source = source.reachable_sources.add()
    reachable_old_source.CopyFrom(get_mock_source_node())
    reachable_old_source.source_type = ast_pb.SOURCE_NETWORK

    # the add() function returns reference
    sink = summary.sinks.add()
    sink.node.type = AstNode.FUNCTION_DECL
    sink.node.name = "post"
    sink.node.full_name = "requests.post"
    sink.node.base_type = "requests"
    sink.node.arguments.extend(["url", "mode", "data"])
    # TODO: set the source range for sink.node
    reachable_old_sink = sink.reachable_sinks.add()
    reachable_old_sink.CopyFrom(get_mock_sink_node())
    reachable_old_sink.sink_type = ast_pb.SINK_NETWORK


# load the astgen config from file
config = AstLookupConfig()
read_proto_from_file(config, '../../../config/astgen_python_smt.config', binary=False)
print("loaded config with %d apis to check!" % len(config.apis))


# initialize result and summary
result = ModuleResult()
summary = ModuleSummary()
static = ModuleStatic()

# compute and fill the results into protobuf
set_result(result)
set_summary(summary)
static.flows.MergeFrom(result.flows)
static.dangers.MergeFrom(result.dangers)
static.sources.MergeFrom(summary.sources)
static.sinks.MergeFrom(summary.sinks)

module_result_pb_fname = "module_result_py.pb"
module_result_txt_fname = "module_result_py.txt"
module_summary_pb_fname = "module_summary_py.pb"
module_summary_txt_fname = "module_summary_py.txt"
module_static_pb_fname = "module_static_py.pb"
module_static_txt_fname = "module_static_py.txt"

# output protobuf message, by default, the output is binary format
write_proto_to_file(result, module_result_pb_fname)
write_proto_to_file(summary, module_summary_pb_fname)
write_proto_to_file(static, module_static_pb_fname)
print("saved result to %s in binary format!" % module_result_pb_fname)
print("saved summary to %s in binary format!" % module_summary_pb_fname)
print("saved static to %s in binary format!" % module_static_pb_fname)

# output protobuf message, use the binary argument to generate text output
write_proto_to_file(result, module_result_txt_fname, binary=False)
write_proto_to_file(summary, module_summary_txt_fname, binary=False)
write_proto_to_file(static, module_static_txt_fname, binary=False)
print("saved result to %s in text format!" % module_result_txt_fname)
print("saved summary to %s in text format!" % module_summary_txt_fname)
print("saved static to %s in text format!" % module_static_txt_fname)

