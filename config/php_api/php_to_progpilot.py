import json
import csv

# the listed items are all functions, variables/arrays such as _GET, are directly borrowed from progpilot.
progpilot_sources = json.load(open('progpilot_sources.json', 'r'))
progpilot_sinks = json.load(open('progpilot_sinks.json', 'r'))

# read and parse apis from sensitive_apis.csv
# if the functions
sensitive_apis = 'sensitive_apis.csv'
reader = csv.DictReader(open(sensitive_apis, 'r'))
fieldnames = reader.fieldnames
rows = list(reader)
maloss_sources = []
maloss_sinks = []

for fname in fieldnames:
    if not fname:
        continue
    if fname in ['SourceType', 'SinkType', 'DangerType']:
        continue

    for row in rows:
        api = row[fname].strip()
        if not api:
            continue

        api_args = None
        if '::' in api:
            api_base, api_name = api.split('::')
            if ':' in api_name:
                api_name_parts = api_name.split(':')
                api_name = api_name_parts[0]
                api_args = api_name_parts[1:]
                api = '%s::%s' % (api_base, api_name)
        else:
            api_base, api_name = None, api
            if ':' in api_name:
                api_name_parts = api_name.split(':')
                api_name = api_name_parts[0]
                api_args = api_name_parts[1:]
                api = api_name

        if fname == 'Sources':
            # {"name": "pg_fetch_result", "is_function": true, "language": "php"},
            # {"name": "fetch_array", "is_array": true, "instanceof": "mysqli_result", "is_function": true, "language": "php"},
            api_json = {'name': api_name, 'is_function': True, 'language': 'php'}
            if api_base:
                api_json['instanceof'] = api_base
            if api_args and len(api_args):
                raise Exception("Cannot handle api_args for Sources now: %s" % api_args)
            maloss_sources.append(api_json)
        elif fname == 'Sinks':
            # {"name": "zip_open", "parameters": [{"id": 1}], "language": "php", "attack": "file_disclosure", "cwe": "CWE_200"},
            # {"name": "query", "instanceof": "mysqli", "parameters": [{"id": 1, "conditions": "QUOTES"}], "language": "php", "attack": "sql_injection", "cwe": "CWE_89"},
            api_json = {'name': api_name, 'language': 'php', 'attack': 'maloss_sink', "cwe": "CWE_89"}
            if api_base:
                api_json['instanceof'] = api_base
            if api_args and len(api_args):
                for api_arg in api_args:
                    api_json.setdefault('parameters', [])
                    api_json['parameters'].append({'id': int(api_arg)})
            else:
                # TODO: all sinks must have parameters (?)
                continue
            maloss_sinks.append(api_json)
        elif fname == 'Dangers':
            # FIXME: all dangers are kindly of performing dangerous operations, they can be sinks as well
            api_json = {'name': api_name, 'language': 'php', 'attack': 'maloss_sink', "cwe": "CWE_89"}
            if api_base:
                api_json['instanceof'] = api_base
            if api_args and len(api_args):
                for api_arg in api_args:
                    api_json.setdefault('parameters', [])
                    api_json['parameters'].append({'id': int(api_arg)})
            else:
                # TODO: dangers may or may not be sinks (have parameters)
                continue
            maloss_sinks.append(api_json)
        else:
            raise Exception("Unexpected field name: %s" % fname)


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


all_sources = progpilot_sources['sources'] + [ms for ms in maloss_sources if not is_in_progpilot_entries(
    progpilot_entries=progpilot_sources['sources'], new_entry=ms)]
all_sinks = progpilot_sinks['sinks'] + [ms for ms in maloss_sinks if not is_in_progpilot_entries(
    progpilot_entries=progpilot_sinks['sinks'], new_entry=ms)]

source_outfile = '../static_php_sources.json'
sink_outfile = '../static_php_sinks.json'
json.dump({"sources": all_sources}, open(source_outfile, 'w'), indent=2)
json.dump({"sinks": all_sinks}, open(sink_outfile, 'w'), indent=2)
