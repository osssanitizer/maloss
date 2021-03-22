import csv

sensitive_apis = 'sensitive_apis.csv'
reader = csv.DictReader(open(sensitive_apis, 'r'))
fieldnames = reader.fieldnames
rows = list(reader)

with open('../astgen_php_smt.config', 'w') as astgen_file:
    func_id = 1
    source_ids = []
    sink_ids = []
    danger_ids = []
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

            astgen_file.write('apis {\n')
            astgen_file.write('\ttype: FUNCTION_DECL_REF_EXPR\n')
            astgen_file.write('\tname: "%s"\n' % api_name)
            astgen_file.write('\tfull_name: "%s"\n' % api)
            if api_base:
                astgen_file.write('\tbase_type: "%s"\n' % api_base)
            if api_args and len(api_args):
                for api_arg in api_args:
                    astgen_file.write('\targ_nodes {\n')
                    astgen_file.write('\t\tid: %d\n' % int(api_arg))
                    astgen_file.write('\t}\n')
            astgen_file.write('\tid: %s\n' % func_id)
            if fname == 'Sources':
                source_ids.append(str(func_id))
                astgen_file.write('\tfunctionality: SOURCE\n')
                astgen_file.write('\tsource_type: %s\n' % row['SourceType'].strip())
            elif fname == 'Sinks':
                sink_ids.append(str(func_id))
                astgen_file.write('\tfunctionality: SINK\n')
                astgen_file.write('\tsink_type: %s\n' % row['SinkType'].strip())
            elif fname == 'Dangers':
                danger_ids.append(str(func_id))
                astgen_file.write('\tfunctionality: DANGER\n')
                astgen_file.write('\tsink_type: %s\n' % row['DangerType'].strip())
            else:
                raise Exception("Unexpected field name: %s" % fname)
            astgen_file.write('}\n')
            func_id += 1

    astgen_file.write('smt_formula: "(({0}) & ({1})) | ({2})"'.format(
        ' | '.join(source_ids), ' | '.join(sink_ids), ' | '.join(danger_ids)))
