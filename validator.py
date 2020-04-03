#!/usr/bin/env python
#
# Copyright (c) 2020 The WorkflowHub Team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import argparse
import json
import jsonschema
import urllib

parser = argparse.ArgumentParser(description='Validate JSON file against workflow-schema.')
parser.add_argument('-s', dest='schema_file', help='JSON schema file')
parser.add_argument('data_file', metavar='JSON_FILE', help='JSON data file')
args = parser.parse_args()

# load schema file
if args.schema_file:
    # schema file provided
    schema = json.loads(open(args.schema_file).read())
else:
    # fetching schema file from GitHub repository
    url = 'https://raw.githubusercontent.com/workflowhub/workflow-schema/master/workflow-schema.json'
    response = urllib.urlopen(url)
    schema = json.loads(response.read())

# read data file
data = json.loads(open(args.data_file).read())

# validate against schema
v = jsonschema.Draft4Validator(schema)
has_error = False
for error in sorted(v.iter_errors(data), key=str):
    msg = '[ERROR] ' + ' > '.join([str(e) for e in error.relative_path]) \
          + ': ' + error.message
    print(msg)
    has_error = True

if has_error:
    exit(1)

# semantic validation
job_ids = []
for j in data['workflow']['jobs']:
    job_ids.append(j['name'])

# since jobs may be declared out of order, their dependencies are only verified here
for j in data['workflow']['jobs']:
    for p in j['parents']:
        if p not in job_ids:
            print('[ERROR] Parent job "%s" is not declared in the list of workflow jobs.' % p['parentId'])
            has_error = True

if has_error:
    exit(1)
else:
    print('The JSON file is a valid workflow schema.')
