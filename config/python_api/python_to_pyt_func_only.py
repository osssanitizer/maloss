import csv
import json

def main():
    sensitive_apis = 'sensitive_apis.csv'
    reader = csv.DictReader(open(sensitive_apis, 'r'))
    fieldnames = reader.fieldnames
    rows = list(reader)

    sources = []
    sinks = {}

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

            if fname == 'Sources':
                sources.append(api_name)
            elif fname == 'Sinks':
                sinks[api_name] = {} # TODO: add (optional) sanitizers as values
            elif fname == 'SourceSinks': # classifying as sources for now
                sources.append(api_name)
            elif fname == 'Dangers': # classifying as sources for now
                sources.append(api_name)
            else:
                raise Exception("Unexpected field name: %s" % fname)

    trigger_words = {}
    trigger_words["sources"] = sources
    trigger_words["sinks"] = sinks

    # TODO: update all_trigger_words.pyt location to reflect location in actual repo
    with open('/home/maloss/Desktop/malenv/pyt/pyt/vulnerability_definitions/all_trigger_words.pyt', 'w') as pyt_file:
        json.dump(trigger_words, pyt_file, indent=4)

if __name__ == '__main__':
    main()
