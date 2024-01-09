#!/usr/bin/env python3
#
# Copyright (c) 2021-2023 The WfCommons Team.
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
    "1.1",
    "1.2",
    "1.3",
    "1.4"
]
LATEST_VERSION = "1.4"


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

    if data["schemaVersion"] not in SUPPORTED_VERSIONS:
        logger.warning(f"Unable to migrate from version {data['schemaVersion']}: {instance_file}")
        return

    # from 1.0 or 1.1 to 1.2
    if data["schemaVersion"] == "1.0" or data["schemaVersion"] == "1.1":
        logger.debug(f"Migration to version 1.2: {instance_file}")
        data = _migrate_to_12(data)
        data = _migrate_to_13(data)
    
    if data["schemaVersion"] == "1.2":
        logger.debug(f"Migration to version 1.3: {instance_file}")
        data = _migrate_to_13(data)

    if data["schemaVersion"] == "1.3":
        logger.debug(f"Migration to version 1.4: {instance_file}")
        data = _migrate_to_14(data)

    if data["schemaVersion"] == LATEST_VERSION:
        logger.debug(f"Cleaning up: {instance_file}")
        data = _cleanup(data)

    # write output file
    with open(instance_file, "w") as outfile:
        logger.debug(f"Writing migrated instance to: {instance_file}")
        outfile.write(json.dumps(data, indent=4))


def _migrate_to_12(data):
    """
    Migrate instance data from version 1.0 or 1.1 to 1.2.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """
    data["schemaVersion"] = "1.2"
    task_id_counter = 0
    task_name_map = {}

    for task in data['workflow']['jobs']:
        # update task id and category
        if '_ID' in task['name']:
            task_name = task['name'].split('_ID')
            task['id'] = f"ID{task_name[1]}"
            task['category'] = task_name[0]
        else:
            task_name = task['name'].split('_')
            task_id_counter += 1
            task_id = f"ID{task_id_counter:07d}"
            task_new_name = f"{task['name']}_{task_id}"
            task_name_map[task['name']] = task_new_name
            task['name'] = task_new_name
            task['id'] = task_id
            task['category'] = task_name[0]

        # update task command
        task['command'] = {
            'program': task['category'],
            'arguments': task['arguments'] if 'arguments' in task else []
        }
        task.pop('arguments', None)

    if len(task_name_map) > 0:
        for task in data['workflow']['jobs']:
            for i in range(len(task['parents'])):
                if task['parents'][i] in task_name_map:
                    task['parents'][i] = task_name_map[task['parents'][i]]

    return data


def _migrate_to_13(data):
    """
    Migrate instance data from version 1.2 to 1.3.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """
    data["schemaVersion"] = "1.3"
    data["workflow"]["tasks"] = []

    for task in data["workflow"]["jobs"]:
        data["workflow"]["tasks"].append(task)

    data["workflow"].pop("jobs", None)

    return data


def _migrate_to_14(data):
    """
    Migrate instance data from version 1.2 to 1.3.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """
    data["schemaVersion"] = "1.4"

    data["workflow"]["makespanInSeconds"] = data["workflow"]["makespan"]
    data["workflow"].pop("makespan", None)
    
    for machine in data["workflow"]["machines"]:
        if "memory" in machine:
            machine["memoryInBytes"] = machine["memory"] * 1000
            machine.pop("memory", None)

    for task in data["workflow"]["tasks"]:
        task["runtimeInSeconds"] = task["runtime"]
        task.pop("runtime", None)

        if "bytesRead" in task:
            task["readBytes"] = task["bytesRead"] if "pegasus" in data["wms"]["name"] else task["bytesRead"] * 1000
        if "bytesWritten" in task:
            task["writtenBytes"] = task["bytesWritten"] if "pegasus" in data["wms"]["name"] else task["bytesWritten"] * 1000
        if "memory" in task:
            task["memoryInBytes"] = task["memory"] * 1000

        for file in task["files"]:
            file["sizeInBytes"] = file["size"]
            file.pop("size", None)

    return data

def _cleanup(data):
    """
    Cleanup instances from old format.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """

    if "makespan" in data["workflow"] and "makespanInSeconds" in data["workflow"]:
        data["workflow"].pop("makespan", None)
    
    for machine in data["workflow"]["machines"]:
        if "memory" in machine and "memoryInBytes" in machine:
            machine.pop("memory", None)

    for task in data["workflow"]["tasks"]:
        if "runtime" in task and "runtimeInSeconds" in task:
            task.pop("runtime", None)

        if "bytesRead" in task:
            task["readBytes"] = task["bytesRead"] if "pegasus" in data["wms"]["name"] else task["bytesRead"] * 1000
        if "bytesWritten" in task:
            task["writtenBytes"] = task["bytesWritten"] if "pegasus" in data["wms"]["name"] else task["bytesWritten"] * 1000
        if "memory" in task and "memoryInBytes" in task:
            task.pop("memory")

        for file in task["files"]:
            if "size" in file and "sizeInBytes" in file:
                file.pop("size", None)

    return data

def main():
    # Application's arguments
    parser = argparse.ArgumentParser(description="Migrate WfCommons Instances to latest WfFormat version.")
    parser.add_argument('instance', metavar='INSTANCE_FILE_OR_FOLDER',
                        help='JSON instance file or folder with instances')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug messages to stderr')
    args = parser.parse_args()

    # Configure logging
    _configure_logging(args.debug)

    logger.info(f"Migrating instance file(s) to version {LATEST_VERSION}.")

    # process instance(s)
    counter = 0
    if os.path.isdir(args.instance):
        for root, dirs, files in os.walk(args.instance):
            for f in files:
                if f.endswith(".json"):
                    _process_instance(os.path.join(root, f), LATEST_VERSION)
                    counter += 1
    else:
        _process_instance(args.instance, args.schema_version)
        counter = 1

    logger.info(f"Successfully migrated {counter} instance file(s).")


if __name__ == "__main__":
    main()
