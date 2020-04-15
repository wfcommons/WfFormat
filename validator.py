#!/usr/bin/env python3
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
import logging
import os
import requests

__author__ = "Rafael Ferreira da Silva"

logger = logging.getLogger(__name__)


def _configure_logging(debug):
    """
    Configure the application's logging.
    :param debug: whether debugging is enabled
    """
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def _load_schema(schema_file):
    """
    Load the schema file
    :param schema_file: JSON schema file
    """
    if schema_file:
        # schema file provided
        logger.debug("Using schema file: " + schema_file)
        return json.loads(open(schema_file).read())

    else:
        schema_path = os.path.dirname(os.path.abspath( __file__ )) + "/workflow-schema.json"
        if os.path.exists(schema_path):
            logger.debug("Using schema file: " + schema_path)
            return json.loads(open(schema_path).read())
        else:
            # fetching latest schema file from GitHub repository
            url = 'https://raw.githubusercontent.com/workflowhub/workflow-schema/master/workflow-schema.json'
            response = requests.get(url)
            logger.debug("Using latest schema file from GitHub repository.")
            return json.loads(response.content)


def _syntax_validation(schema, data):
    """
    Validate the JSON workflow execution trace agains the schema
    :param schema: WorkflowHub JSON schema
    :param data: JSON trace
    """
    v = jsonschema.Draft4Validator(schema)
    has_error = False
    for error in sorted(v.iter_errors(data), key=str):
        msg = ' > '.join([str(e) for e in error.relative_path]) \
              + ': ' + error.message
        logger.error(msg)
        has_error = True

    if has_error:
        exit(1)


def _semantic_validation(data):
    """
    Validate the semantics of the JSON workflow excecution trace
    :param data: JSON trace
    """
    has_error = False

    machine_ids = []
    if 'machines' in data['workflow']:
        for m in data['workflow']['machines']:
            machine_ids.append(m['nodeName'])
    else:
        logger.debug('Skipping machines processing.')

    job_ids = []
    for j in data['workflow']['jobs']:
        job_ids.append(j['name'])
        if 'machine' in j and j['machine'] not in machine_ids:
            logger.error('Machine "%s" is not declared in the list of machines.' % j['machine'])
            has_error = True

    # since jobs may be declared out of order, their dependencies are only verified here
    for j in data['workflow']['jobs']:
        for p in j['parents']:
            if p not in job_ids:
                logger.error('Parent job "%s" is not declared in the list of workflow jobs.' % p['parentId'])
                has_error = True

    logger.debug('The workflow has %d jobs.' % len(job_ids))
    logger.debug('The workflow has %d machines.' % len(machine_ids))

    if has_error:
        exit(1)


def main():
    # Application's arguments
    parser = argparse.ArgumentParser(description='Validate JSON file against workflow-schema.')
    parser.add_argument('-s', dest='schema_file', help='JSON schema file')
    parser.add_argument('data_file', metavar='JSON_FILE', help='JSON data file')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug messages to stderr')
    args = parser.parse_args()

    # Configure logging
    _configure_logging(args.debug)

    # load schema file
    schema = _load_schema(args.schema_file)

    # read data file
    data = json.loads(open(args.data_file).read())
    logger.debug("Trace file been evaluated: " + args.data_file)

    # validate against schema
    _syntax_validation(schema, data)

    # semantic validation
    _semantic_validation(data)

    logger.info('The trace file has a valid WorkflowHub JSON trace format.')


if __name__ == '__main__':
    main()
