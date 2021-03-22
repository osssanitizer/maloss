import os
import json
import yaml
import shutil
import logging
import tempfile
import proto.python.ast_pb2 as ast_pb2

from os.path import basename, dirname, abspath, join
from proto.python.ast_pb2 import AstLookupConfig, AstNode, FileInfo
from proto.python.module_pb2 import ModuleResult, ModuleSummary, ModuleStatic
from util.job_util import read_proto_from_file, write_proto_to_file, exec_command


def get_source_node(src):
    return None


def get_sink_node(sink):
    sink_node = AstNode()
    if sink['user_input']:
        sink_node.full_name = sink['user_input']
    if sink['code']:
        sink_node.source = sink['code']
    sink_file_info = FileInfo()
    if sink['file']:
        sink_file_info.filename = basename(sink['file'])
        sink_file_info.relpath = dirname(sink['file'])
    if sink['row']:
        sink_node.range.start.row = sink['row']
    sink_node.range.start.file_info.CopyFrom(sink_file_info)
    return sink_node


def get_propagate_node(hop):
    return None


def set_result(result, apis, flows):
    scan_info = flows.get("scan_info", {})
    if not scan_info:
        return
    num_flows = scan_info.get("security_warnings", 0)
    logging.warning("there are %d flows (security warnings)!", num_flows)
    if num_flows == 0:
        return
    num_views = scan_info.get("number_of_views", 0)
    num_models = scan_info.get("number_of_models", 0)
    num_templates = scan_info.get("number_of_templates", 0)
    num_controllers = scan_info.get("number_of_controllers", 0)
    num_helpers = scan_info.get("number_of_helpers", 0)
    num_jobs = scan_info.get("number_of_jobs", 0)
    num_config = scan_info.get("number_of_config", 0)
    num_lib = scan_info.get("number_of_lib", 0)
    logging.warning("there are %d views, %d models, %d templates, %d controllers, %d helpers, %d jobs, %d config, %d lib!",
                    num_views, num_models, num_templates, num_controllers, num_helpers, num_jobs, num_config, num_lib)
    flow_warnings = flows.get("warnings", [])

    # FIXME: directly invoking brakeman on rails4 gives us 96 warnings, but the framework is 86 (82 w/ deduplication).
    logging.warning("there are %d warnings before deduplication!", len(flow_warnings))
    flows_set = set()
    for flow in flow_warnings:
        # we don't care about fingerprint, and remove it to allow deduplication
        flow['file'] = flow['file'].split('/', 2)[-1]
        flow['fingerprint'] = None
        flow['location'] = None
        flow_key = tuple(sorted(flow.items()))
        if flow_key in flows_set:
            continue
        else:
            flows_set.add(flow_key)

        nodes = []
        # the sink node
        nodes.append({'row': flow['line'], 'file': flow['file'], 'user_input': flow['user_input'],
                      'code': flow['code']})
        # FIXME: add the source node
        # FIXME: add the tainted nodes
        flow_pb = result.flows.add()
        sink_node = get_sink_node(sink=nodes[-1])
        flow_pb.sink.CopyFrom(sink_node)
        # the flow info
        flow_pb.info.name = flow['check_name']
        flow_pb.info.cwe = flow['warning_type']
        flow_pb.info.type = flow['confidence']
    logging.warning("there are %d warnings after deduplication!", len(result.flows))


def set_summary(summary, apis, all_sources, all_sinks, new_sources, new_sinks, new_sanitizers=None, new_validators=None):
    logging.debug("not implemented yet!")


def reformat(apis_file, json_result_file, outfile):
    try:
        results = json.load(open(json_result_file, 'r'))
    except Exception as e:
        logging.error("failed to load brakeman results in json: %s", json_result_file)
        return None

    # load the astgen config from file
    config = AstLookupConfig()
    read_proto_from_file(config, apis_file, binary=False)
    logging.warning("loaded config with %d apis to check!", len(config.apis))

    result = ModuleResult()
    set_result(result=result, apis=config.apis, flows=results)
    summary = ModuleSummary()
    set_summary(summary=summary, apis=config.apis, all_sources=None, all_sinks=None, new_sources=None, new_sinks=None)
    static = ModuleStatic()
    static.flows.MergeFrom(result.flows)
    static.dangers.MergeFrom(result.dangers)
    static.sources.MergeFrom(summary.sources)
    static.sinks.MergeFrom(summary.sinks)
    static.taint_wrappers.MergeFrom(summary.taint_wrappers)
    write_proto_to_file(proto=static, filename=outfile, binary=False)


def brakeman_run(pkg_path, config_path, out_path):
    """
    Run brakeman all checks.

    Example commands:
    brakeman --interprocedural -o brakeman_results.json -A rails2
    """
    # Convert astgen_ruby_smt.config to brakeman config, not necessary.
    logging.warning("brakeman currently doesn't allow customized APIs/checks, ignoring config %s", config_path)

    # Run brakeman on given package, output JSON-formatted results
    temp_brakeman_path = tempfile.mkdtemp(prefix="brakeman-")
    temp_result_path = tempfile.NamedTemporaryFile(suffix=".json")
    logging.warning("Running brakeman analysis on %s with default and optional checks", pkg_path)
    # try consider all code as views/models/controllers etc.
    # FIXME: app/views/, app/models/, app/controllers/, app/helpers/, app/templates, app/jobs/, config/, lib/
    abs_pkg_path = abspath(pkg_path)
    temp_rails_path = join(temp_brakeman_path, 'rails4')
    temp_app_path = join(temp_rails_path, 'app')
    os.makedirs(temp_app_path)
    os.symlink(abs_pkg_path, join(temp_app_path, 'views'))
    os.symlink(abs_pkg_path, join(temp_app_path, 'models'))
    os.symlink(abs_pkg_path, join(temp_app_path, 'controllers'))
    os.symlink(abs_pkg_path, join(temp_app_path, 'helpers'))
    os.symlink(abs_pkg_path, join(temp_app_path, 'templates'))
    os.symlink(abs_pkg_path, join(temp_app_path, 'jobs'))
    os.symlink(abs_pkg_path, join(temp_app_path, 'config'))
    os.symlink(abs_pkg_path, join(temp_app_path, 'lib'))
    logging.warning("app path: %s", temp_rails_path)
    brakeman_cmd = ['brakeman', '--interprocedural', '-o', temp_result_path.name, '-A', temp_rails_path]
    exec_command('brakeman', brakeman_cmd, cwd=temp_brakeman_path)

    # cleanup brakeman symlinks
    shutil.rmtree(temp_brakeman_path)

    # Format brakeman (.json) results into proper protobuf outputs
    reformat(apis_file=config_path, json_result_file=temp_result_path.name, outfile=out_path)
