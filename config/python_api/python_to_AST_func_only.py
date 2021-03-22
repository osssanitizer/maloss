import csv

sensitive_apis = 'sensitive_apis.csv'
reader = csv.DictReader(open(sensitive_apis, 'r'))
fieldnames = reader.fieldnames
rows = list(reader)

with open('../astgen_python_smt.func_only.config', 'w') as astgen_file:
    func_id = 1
    source_ids = []
    sink_ids = []
    source_sink_ids = []
    danger_ids = []
    for fname in fieldnames:
        if not fname:
            continue
        if fname in ['SourceType', 'SinkType', 'SourceSinkType', 'DangerType']:
            continue

        for row in rows:
            api = row[fname].strip()
            if not api:
                continue

            if '(' in api:
                if len(api.split('(')) > 2:
                    print("wrong api %s with two '(', this shouldn't happen!" % api)
                    exit(1)
                api = api.split('(')[0]
            if '.' in api:
                api_base, api_name = api.rsplit('.', 1)
            else:
                api_base, api_name = None, api

            astgen_file.write('apis {\n')
            astgen_file.write('\ttype: FUNCTION_DECL_REF_EXPR\n')
            astgen_file.write('\tname: "%s"\n' % api_name)
            astgen_file.write('\tfull_name: "%s"\n' % api)
            if api_base:
                astgen_file.write('\tbase_type: "%s"\n' % api_base)
            astgen_file.write('\tid: %s\n' % func_id)
            if fname == 'Sources':
                source_ids.append(str(func_id))
                astgen_file.write('\tfunctionality: SOURCE\n')
                astgen_file.write('\tsource_type: %s\n' % row['SourceType'].strip())
            elif fname == 'Sinks':
                sink_ids.append(str(func_id))
                astgen_file.write('\tfunctionality: SINK\n')
                astgen_file.write('\tsink_type: %s\n' % row['SinkType'].strip())
            elif fname == 'SourceSinks':
                source_sink_ids.append(str(func_id))
                astgen_file.write('\tfunctionality: SOURCE\n')
                astgen_file.write('\tsource_type: %s\n' % row['SourceSinkType'].strip())
            elif fname == 'Dangers':
                danger_ids.append(str(func_id))
                astgen_file.write('\tfunctionality: DANGER\n')
                astgen_file.write('\tsink_type: %s\n' % row['DangerType'].strip())
            else:
                raise Exception("Unexpected field name: %s" % fname)
            astgen_file.write('}\n')
            func_id += 1

    astgen_file.write('smt_formula: "(({0}) & ({1})) | ({2}) | ({3})"\n'.format(
        ' | '.join(source_ids), ' | '.join(sink_ids), ' | '.join(source_sink_ids), ' | '.join(danger_ids)))
    astgen_file.write('func_only: true')
