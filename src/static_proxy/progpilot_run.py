import os
import json
import yaml
import logging
import tempfile
import proto.python.ast_pb2 as ast_pb2

from os.path import basename, dirname, abspath, join
from proto.python.ast_pb2 import AstLookupConfig, AstNode, FileInfo
from proto.python.module_pb2 import ModuleResult, ModuleSummary, ModuleStatic
from util.job_util import read_proto_from_file, write_proto_to_file, exec_command

package_directory = dirname(abspath(__file__))


def get_matching_api(node, apis, fuzzy=False):
    # FIXME: base type is not reported
    logging.info("there are %d apis", len(apis))
    name2api = {api.name: api for api in apis}
    # there are 55 apis, there are 53 apis with unique names
    # there are 120 apis, there are 118 apis with unique names
    logging.info("there are %d apis with unique names", len(name2api))
    if node['name'] in name2api:
        return name2api[node['name']]
    elif fuzzy:
        # longest name match
        matched_apis = [(name, api) for name, api in name2api.items() if name in node['name']]
        if len(matched_apis):
            return sorted(matched_apis, key=lambda k: len(k[0]), reverse=True)[0][1]
    # it's normal to have a node not listed in our astgen config. it may come from progpilot sources/sinks.
    return None


def get_matching_info(node, info_nodes, fuzzy=False):
    # FIXME: base type is not reported
    logging.info("there are %d nodes", len(info_nodes))
    name2info = {an['name']: an for an in info_nodes}
    # there are 133 nodes, there are 126 nodes with unique names
    # there are 267 nodes, there are 251 nodes with unique names
    logging.info("there are %d nodes with unique names", len(name2info))
    if node['name'] in name2info:
        return name2info[node['name']]
    elif fuzzy:
        # longest name match
        matched_infos = [(name, info) for name, info in name2info.items() if name in info['name']]
        if len(matched_infos):
            return sorted(matched_infos, key=lambda k: len(k[0]), reverse=True)[0][1]
    logging.error("fail to find node info for node %s", node)
    return None


def get_source_node(src, source_apis, all_sources):
    # The source name may not be in apis, but in all_sources
    source_node = AstNode()
    info = get_matching_info(node=src, info_nodes=all_sources, fuzzy=True)
    if not info:
        return source_node
    if 'is_function' in info and info['is_function']:
        source_node.type = AstNode.FUNCTION_DECL_REF_EXPR
    else:
        source_node.type = AstNode.VARIABLE_DECL_REF_EXPR
    # set the name and other information
    api = get_matching_api(node=src, apis=source_apis, fuzzy=True)
    if api:
        source_node.id = api.id
        source_node.name = api.name
        source_node.base_type = api.base_type
        source_node.full_name = api.full_name
        source_node.source = src['name']
    else:
        source_node.name = info['name']
        if 'instanceof' in info:
            source_node.base_type = info['instanceof']
        source_node.full_name = get_progpilot_name(entry=info)
        source_node.source = src['name']
    # set the location
    source_file_info = FileInfo()
    source_file_info.filename = basename(src['file'])
    source_file_info.relpath = dirname(src['file'])
    source_node.range.start.row = src['row']
    source_node.range.start.column = src['column']
    source_node.range.start.file_info.CopyFrom(source_file_info)
    source_node.range.end.CopyFrom(source_node.range.start)
    return source_node


def get_sink_node(sink, sink_apis, all_sinks):
    # The sink name may not be in apis, but in all_sinks
    sink_node = AstNode()
    info = get_matching_info(node=sink, info_nodes=all_sinks)
    if not info:
        return sink_node
    sink_node.type = AstNode.FUNCTION_DECL_REF_EXPR
    # set the name and other information
    api = get_matching_api(node=sink, apis=sink_apis)
    if api:
        sink_node.id = api.id
        sink_node.name = api.name
        sink_node.base_type = api.base_type
        sink_node.full_name = api.full_name
        sink_node.source = sink['name']
    else:
        sink_node.name = info['name']
        if 'instanceof' in info:
            sink_node.base_type = info['instanceof']
        sink_node.full_name = get_progpilot_name(entry=info)
        sink_node.source = sink['name']
    # set the location
    sink_file_info = FileInfo()
    sink_file_info.filename = basename(sink['file'])
    sink_file_info.relpath = dirname(sink['file'])
    sink_node.range.start.row = sink['row']
    sink_node.range.start.column = sink['column']
    sink_node.range.start.file_info.CopyFrom(sink_file_info)
    sink_node.range.end.CopyFrom(sink_node.range.start)
    return sink_node


def get_propagate_node(hop):
    propagate_node = AstNode()
    propagate_node.name = hop['name']
    propagate_file_info = FileInfo()
    propagate_file_info.filename = basename(hop['file'])
    propagate_file_info.relpath = dirname(hop['file'])
    propagate_node.range.start.row = hop['row']
    propagate_node.range.start.column = hop['column']
    propagate_node.range.start.file_info.CopyFrom(propagate_file_info)
    propagate_node.range.end.CopyFrom(propagate_node.range.start)
    return propagate_node


def set_result(result, apis, all_sources, all_sinks, flows):
    # FIXME: progpilot doesn't report instanceof in the detection results now, so we have to ignore base type.
    all_source_set = set(get_progpilot_name(entry) for entry in all_sources)
    all_sink_set = set(get_progpilot_name(entry) for entry in all_sinks)
    source_apis = [api for api in apis if api.full_name in all_source_set]
    sink_apis = [api for api in apis if api.full_name in all_sink_set]
    for flow in flows:
        nodes = []
        # the sink node
        nodes.append({'name': flow['sink_name'], 'row': flow['sink_line'], 'column': flow['sink_column'],
                      'file': flow['sink_file']})
        # the namely source node
        nodes.append({'name': flow['source_name'][0], 'row': flow['source_line'][0], 'column': flow['source_column'][0],
                      'file': flow['source_file'][0]})
        # iterate through the tainted nodes
        for taint_flow in flow['tainted_flow']:
            for taint_node in taint_flow:
                nodes.append({'name': taint_node['flow_name'], 'row': taint_node['flow_line'],
                              'column': taint_node['flow_column'], 'file': taint_node['flow_file']})
        # iterate the list in reverse order
        nodes.reverse()

        flow_pb = result.flows.add()
        source_node = get_source_node(src=nodes[0], source_apis=source_apis, all_sources=all_sources)
        sink_node = get_sink_node(sink=nodes[-1], sink_apis=sink_apis, all_sinks=all_sinks)
        flow_pb.source.CopyFrom(source_node)
        flow_pb.sink.CopyFrom(sink_node)
        for hop_node in nodes[1:-1]:
            propagate_node = get_propagate_node(hop=hop_node)
            flow_pb.hops.add().CopyFrom(propagate_node)
        # the flow info
        flow_pb.info.name = flow['vuln_name']
        flow_pb.info.cwe = flow['vuln_cwe']
        flow_pb.info.type = flow['vuln_type']


def set_summary(summary, apis, all_sources, all_sinks, new_sources, new_sinks, new_sanitizers=None, new_validators=None):
    logging.debug("not implemented yet!")


def reformat(apis_file, all_sources, all_sinks, json_result_file, outfile):
    try:
        results = json.load(open(json_result_file, 'r'))
    except Exception as e:
        logging.error("failed to load progpilot results in json: %s", json_result_file)
        return None

    logging.warning("there are %d sources and %d sinks checked!", len(all_sources), len(all_sinks))
    # load the astgen config from file
    config = AstLookupConfig()
    read_proto_from_file(config, apis_file, binary=False)
    logging.warning("loaded config with %d apis to check!", len(config.apis))

    result = ModuleResult()
    set_result(result=result, apis=config.apis, all_sources=all_sources, all_sinks=all_sinks, flows=results)
    summary = ModuleSummary()
    set_summary(summary=summary, apis=config.apis, all_sources=all_sources, all_sinks=all_sinks, new_sources=None, new_sinks=None)
    static = ModuleStatic()
    static.flows.MergeFrom(result.flows)
    static.dangers.MergeFrom(result.dangers)
    static.sources.MergeFrom(summary.sources)
    static.sinks.MergeFrom(summary.sinks)
    static.taint_wrappers.MergeFrom(summary.taint_wrappers)
    write_proto_to_file(proto=static, filename=outfile, binary=False)


def get_progpilot_name(entry):
    if 'instanceof' in entry:
        return '%s::%s' % (entry['instanceof'], entry['name'])
    else:
        return entry['name']


def is_in_progpilot_entries(progpilot_entries, new_entry):
    for entry in progpilot_entries:
        if get_progpilot_name(entry) == get_progpilot_name(new_entry):
            return True
    return False


def ast_to_progpilot(config_path, out_path, new_sources_path, new_sinks_path, new_configuration_path,
                     sources_path=join(package_directory, "../../config/php_api/progpilot_sources.json"),
                     sinks_path=join(package_directory, "../../config/php_api/progpilot_sinks.json"),
                     configuration_path=join(package_directory, "../../config/static_php_progpilot.yml")):
    progpilot_sources = json.load(open(sources_path, 'r'))
    progpilot_sinks = json.load(open(sinks_path, 'r'))
    config = AstLookupConfig()
    read_proto_from_file(config, config_path, binary=False)
    maloss_sources = []
    maloss_sinks = []
    for api in config.apis:
        # TODO: add support for instantiable field in API comparison
        if api.functionality == ast_pb2.SOURCE:
            api_json = {'name': api.name, 'is_function': True, 'language': 'php'}
            if not config.func_only and api.base_type:
                api_json['instanceof'] = api.base_type
            if api.arg_nodes and len(api.arg_nodes):
                raise Exception("Cannot handle arg_nodes for Sources now: %s" % api)
            maloss_sources.append(api_json)
        elif api.functionality in (ast_pb2.SINK, ast_pb2.DANGER):
            api_json = {'name': api.name, 'language': 'php', 'attack': 'maloss_sink', 'cwe': 'CWE_89'}
            if not config.func_only and api.base_type:
                api_json['instanceof'] = api.base_type
            if api.arg_nodes and len(api.arg_nodes):
                for api_arg in api.arg_nodes:
                    api_json.setdefault('parameters', [])
                    api_json['parameters'].append({'id': api_arg.id})
            else:
                # TODO: all sinks must have parameters (?)
                continue
            maloss_sinks.append(api_json)
    # combine to get all sources and sinks
    all_sources = progpilot_sources['sources'] + [ms for ms in maloss_sources if not is_in_progpilot_entries(
        progpilot_entries=progpilot_sources['sources'], new_entry=ms)]
    all_sinks = progpilot_sinks['sinks'] + [ms for ms in maloss_sinks if not is_in_progpilot_entries(
        progpilot_entries=progpilot_sinks['sinks'], new_entry=ms)]
    json.dump({'sources': all_sources}, open(new_sources_path, 'w'), indent=2)
    json.dump({'sinks': all_sinks}, open(new_sinks_path, 'w'), indent=2)
    progpilot_config = yaml.load(open(configuration_path, 'r'))
    progpilot_config['inputs']['setSources'] = new_sources_path
    progpilot_config['inputs']['setSinks'] = new_sinks_path
    progpilot_config['outputs']['setOutfile'] = out_path
    yaml.dump(progpilot_config, open(new_configuration_path, 'w'))
    return all_sources, all_sinks


def progpilot_run(pkg_path, config_path, out_path):
    """
    Run progpilot on customized config.

    Example commands:
    php progpilot/builds/progpilot.phar --configuration progpilot/projects/example_config/configuration.yml ../../testdata/test-eval-exec.php
    php progpilot/builds/progpilot.phar --configuration ../../config/static_php_progpilot.yml ../../testdata/test-eval-exec.php
    """
    # Convert astgen_php_smt.config to progpilot sources/sinks/progpilot.yml file
    logging.warning("Generating progpilot config file from input config file")
    temp_sources_path = tempfile.NamedTemporaryFile(suffix=".json")
    temp_sinks_path = tempfile.NamedTemporaryFile(suffix=".json")
    temp_configuration_path = tempfile.NamedTemporaryFile(suffix=".yml")
    temp_result_path = tempfile.NamedTemporaryFile(suffix=".json")
    all_sources, all_sinks = ast_to_progpilot(
        config_path=config_path, out_path=temp_result_path.name, new_sources_path=temp_sources_path.name,
        new_sinks_path=temp_sinks_path.name, new_configuration_path=temp_configuration_path.name)

    # Run progpilot on given package, output JSON-formatted results
    logging.warning("Running progpilot analysis on %s with sources %s sinks %s and config %s", pkg_path,
                    temp_sources_path.name, temp_sinks_path.name, temp_configuration_path.name)
    progpilot_cmd = ['php', 'progpilot/builds/progpilot.phar', '--configuration', temp_configuration_path.name, pkg_path]
    exec_command('progpilot', progpilot_cmd, cwd=package_directory)

    # Format progpilot (.json) results into proper protobuf outputs
    logging.warning("Converting results in %s to protobuf format", temp_result_path.name)
    reformat(apis_file=config_path, all_sources=all_sources, all_sinks=all_sinks,
             json_result_file=temp_result_path.name, outfile=out_path)
