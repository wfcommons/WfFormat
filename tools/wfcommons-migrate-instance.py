#!/usr/bin/env python3
#
# Copyright (c) 2021 The WfCommons Team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import argparse
import json
import logging
import os

__author__ = "Rafael Ferreira da Silva"

logger = logging.getLogger(__name__)

SUPPORTED_VERSIONS = [
    "1.0",
    "1.1"
]
LATEST_VERSION = "1.2"


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


def _process_instance(instance_file, schema_version):
    """
    Process instance migration.
    :param instance_file: instance file path
    """
    data = json.loads(open(instance_file).read())

    if data['schemaVersion'] not in SUPPORTED_VERSIONS:
        logger.warning('Unable to migrate from version {}: {}'.format(data['schemaVersion'], instance_file))
        return

    # from 1.0 or 1.1 to 1.2
    if data['schemaVersion'] == "1.0" or data['schemaVersion'] == "1.1":
        logger.debug('Migration to version 1.2: {}'.format(instance_file))
        data = _migrate_to_12(data)

    # write output file
    with open(instance_file, 'w') as outfile:
        logger.debug('Writing migrated instance to: {}'.format(instance_file))
        outfile.write(json.dumps(data, indent=4))


def _migrate_to_12(data):
    """
    Migrate instance data from version 1.0 or 1.1 to 1.2.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """
    data['schemaVersion'] = "1.2"
    task_id_counter = 0

    for task in data['workflow']['jobs']:
        # update task id and category
        if '_ID' in task['name']:
            task_name = task['name'].split('_ID')
            task['id'] = 'ID{}'.format(task_name[1])
            task['category'] = task_name[0]
        else:
            task_name = task['name'].split('_')
            task_id_counter += 1
            task_id = 'ID{:07d}'.format(task_id_counter)
            task['name'] = '{}_{}'.format(task['name'], task_id)
            task['id'] = task_id
            task['category'] = task_name[0]

        # update task command
        task['command'] = {
            'program': task['category'],
            'arguments': task['arguments'] if 'arguments' in task else []
        }
        task.pop('arguments', None)

    return data


def main():
    # Application's arguments
    parser = argparse.ArgumentParser(description='Migrate WfCommons Instances.')
    parser.add_argument('-s', dest='schema_version', default=LATEST_VERSION,
                        help='Migrate to a specific schema version')
    parser.add_argument('instance', metavar='INSTANCE_FILE_OR_FOLDER',
                        help='JSON instance file or folder with instances')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug messages to stderr')
    args = parser.parse_args()

    # Configure logging
    _configure_logging(args.debug)

    logger.info('Migrating instance file(s) to version {}.'.format(args.schema_version))

    # process instance(s)
    counter = 0
    if os.path.isdir(args.instance):
        for root, dirs, files in os.walk(args.instance):
            for f in files:
                if f.endswith(".json"):
                    _process_instance(os.path.join(root, f), args.schema_version)
                    counter += 1
    else:
        _process_instance(args.instance, args.schema_version)
        counter = 1

    logger.info('Successfully migrated {} instance file(s).'.format(counter))


if __name__ == '__main__':
    main()
