#!/usr/bin/env python3
#
# Copyright (c) 2021-2026 The WfCommons Team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import argparse
import json
import logging
import os
import re
import shutil
import sys
import tempfile

from collections import Counter

__author__ = "Rafael Ferreira da Silva"

logger = logging.getLogger(__name__)

SUPPORTED_VERSIONS = [
    "1.0",
    "1.1",
    "1.2",
    "1.3",
    "1.4",
    "1.5",
    "1.6"
]
LATEST_VERSION = "1.6"

# Task IDs are restricted to this character set from WfFormat 1.5 onwards
# (see the "taskId" definition in wfcommons-schema.json).
TASK_ID_PATTERN = re.compile(r"^[0-9a-zA-Z_.#:/-]+$")

# Outcome of processing a single instance file
MIGRATED = "migrated"
UP_TO_DATE = "up-to-date"
SKIPPED = "skipped"
FAILED = "failed"

# Number of instance files between two progress messages
PROGRESS_INTERVAL = 100


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


def _is_debug():
    """
    :return: whether debug messages are being printed, in which case failures are
             also reported with their traceback
    """
    return logger.isEnabledFor(logging.DEBUG)


def _collect_instance_files(path):
    """
    List the instance files to be processed.
    :param path: instance file path, or path to a folder to be walked recursively
    :return: sorted list of file paths
    """
    if os.path.isfile(path):
        return [path]

    instance_files = []
    for root, _, files in os.walk(path):
        instance_files.extend(
            os.path.join(root, f) for f in files if f.endswith(".json"))

    return sorted(instance_files)


def _process_instance(instance_file, dry_run=False, backup=False):
    """
    Process instance migration.
    :param instance_file: instance file path
    :param dry_run: whether to report the migration without writing any file
    :param backup: whether to keep the original file as <instance_file>.bak
    :return: one of MIGRATED, UP_TO_DATE, SKIPPED, or FAILED
    """
    try:
        with open(instance_file, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.error(f"Unable to read instance file {instance_file}: {e}", exc_info=_is_debug())
        return FAILED

    # a folder may legitimately hold JSON files that are not WfFormat instances
    if not isinstance(data, dict) or "schemaVersion" not in data:
        logger.debug(f"Not a WfFormat instance file, skipping: {instance_file}")
        return SKIPPED

    version = data["schemaVersion"]

    if version not in SUPPORTED_VERSIONS:
        logger.warning(f"Unable to migrate from version {version}: {instance_file}")
        return SKIPPED

    if version == LATEST_VERSION:
        logger.debug(f"Already at version {LATEST_VERSION}: {instance_file}")
        return UP_TO_DATE

    try:
        data = _migrate(data, instance_file)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Unable to migrate {instance_file} from version {version}: {e!r}",
                     exc_info=_is_debug())
        return FAILED

    _check_task_ids(data, instance_file)

    if dry_run:
        logger.info(f"Would migrate from version {version}: {instance_file}")
        return MIGRATED

    try:
        if backup:
            shutil.copy2(instance_file, f"{instance_file}.bak")
        _write_instance(instance_file, data)
    except OSError as e:
        logger.error(f"Unable to write migrated instance to {instance_file}: {e}", exc_info=_is_debug())
        return FAILED

    logger.debug(f"Migrated from version {version}: {instance_file}")
    return MIGRATED


def _migrate(data, instance_file):
    """
    Apply every migration step needed to bring an instance to the latest version.
    :param data: instance data dictionary
    :param instance_file: instance file path, for logging purposes
    :return: instance data dictionary in the migrated form
    """
    if data["schemaVersion"] in ("1.0", "1.1"):
        logger.debug(f"Migration to version 1.2: {instance_file}")
        data = _migrate_to_12(data)

    if data["schemaVersion"] == "1.2":
        logger.debug(f"Migration to version 1.3: {instance_file}")
        data = _migrate_to_13(data)

    if data["schemaVersion"] == "1.3":
        logger.debug(f"Migration to version 1.4: {instance_file}")
        data = _migrate_to_14(data)

    if data["schemaVersion"] == "1.4":
        logger.debug(f"Cleaning up: {instance_file}")
        data = _cleanup(data)
        logger.debug(f"Migration to version 1.5: {instance_file}")
        data = _migrate_to_15(data)

    if data["schemaVersion"] == "1.5":
        logger.debug(f"Migration to version 1.6: {instance_file}")
        data = _migrate_to_16(data)

    return data


def _write_instance(instance_file, data):
    """
    Write an instance file, without leaving a truncated file behind if writing
    fails or is interrupted.
    :param instance_file: instance file path
    :param data: instance data dictionary
    """
    logger.debug(f"Writing migrated instance to: {instance_file}")

    directory = os.path.dirname(os.path.abspath(instance_file))
    descriptor, temporary_file = tempfile.mkstemp(dir=directory, suffix=".json.tmp")

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=4)
            outfile.write("\n")
        shutil.copymode(instance_file, temporary_file)
        os.replace(temporary_file, instance_file)
    except BaseException:
        if os.path.exists(temporary_file):
            os.remove(temporary_file)
        raise


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
            parents = task.get('parents', [])
            for i in range(len(parents)):
                if parents[i] in task_name_map:
                    parents[i] = task_name_map[parents[i]]

    return data


def _migrate_to_13(data):
    """
    Migrate instance data from version 1.2 to 1.3.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """
    data["schemaVersion"] = "1.3"

    _update_data(data["workflow"], "jobs", data["workflow"], "tasks")

    return data


def _migrate_to_14(data):
    """
    Migrate instance data from version 1.3 to 1.4.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """
    data["schemaVersion"] = "1.4"

    _update_data(data["workflow"], "makespan", data["workflow"], "makespanInSeconds")

    # "machines", "files", "runtime", and the byte counts below are all optional
    # in version 1.3, hence the guarded accesses
    for machine in data["workflow"].get("machines", []):
        if "memory" in machine:
            machine["memoryInBytes"] = machine.pop("memory") * 1000

    runtime_system = _runtime_system_name(data)

    for task in data["workflow"]["tasks"]:
        _update_data(task, "runtime", task, "runtimeInSeconds")
        _convert_byte_counts(task, runtime_system)

        if "memory" in task:
            task["memoryInBytes"] = task.pop("memory") * 1000

        for file in task.get("files", []):
            _update_data(file, "size", file, "sizeInBytes")

    return data


def _migrate_to_15(data):
    """
    Migrate instance data from version 1.4 to 1.5.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """
    data["schemaVersion"] = "1.5"

    for key in ("makespanInSeconds", "executedAt"):
        if key not in data["workflow"]:
            raise ValueError(f"missing required version 1.4 property 'workflow.{key}'")

    _update_data(data, "wms", data, "runtimeSystem")

    for machine in data["workflow"].get("machines", []):
        cpu = machine.get("cpu")
        if cpu:
            _update_data(cpu, "count", cpu, "coreCount")
            _update_data(cpu, "speed", cpu, "speedInMHz")

    tasks = data["workflow"]["tasks"]

    # Up to version 1.4 tasks refer to each other by name; from 1.5 onwards they
    # refer to each other by ID, and the two need not coincide. Every new task ID
    # is therefore computed up front, so that dependencies can be resolved
    # against a complete map in the pass below.
    task_ids = [_task_id(task, index) for index, task in enumerate(tasks)]
    reference_map = {}
    for task, task_id in zip(tasks, task_ids):
        for reference in (task.get("name"), task.get("id"), task_id):
            if reference and reference not in reference_map:
                reference_map[reference] = task_id

    specification = {"tasks": [], "files": []}
    execution = {
        "makespanInSeconds": data["workflow"].pop("makespanInSeconds"),
        "executedAt": data["workflow"].pop("executedAt"),
        "tasks": []
    }
    _update_data(data["workflow"], "machines", execution, "machines")

    file_producers = {}
    parents_of = {}
    children_of = {}

    for task, task_id in zip(tasks, task_ids):
        parents = _resolve_references(task.get("parents", []), reference_map, task_id, "parent")
        children = _resolve_references(task.get("children", []), reference_map, task_id, "child")

        # dependencies are declared on one end only, so record both directions
        for parent in parents:
            _append_unique(children_of.setdefault(parent, []), task_id)
        for child in children:
            _append_unique(parents_of.setdefault(child, []), task_id)
        _extend_unique(parents_of.setdefault(task_id, []), parents)
        _extend_unique(children_of.setdefault(task_id, []), children)

        specification_task = {
            "name": task["name"],
            "id": task_id,
            "parents": [],
            "children": [],
            "inputFiles": [],
            "outputFiles": []
        }

        _migrate_task_files(task, specification_task, specification["files"], file_producers)

        specification["tasks"].append(specification_task)
        execution["tasks"].append(_execution_task(task, task_id))

    data["workflow"].pop("tasks")
    data["workflow"]["specification"] = specification
    data["workflow"]["execution"] = execution

    tasks_map = {task["id"]: task for task in specification["tasks"]}

    for task in specification["tasks"]:
        task["parents"] = parents_of.get(task["id"], [])
        task["children"] = children_of.get(task["id"], [])

        # in case there are no declared dependencies, infer them from the files
        if not task["parents"]:
            for file_id in task["inputFiles"]:
                producer = file_producers.get(file_id)
                if producer and producer != task["id"]:
                    _append_unique(task["parents"], producer)
                    _append_unique(tasks_map[producer]["children"], task["id"])

    return data


def _migrate_task_files(task, specification_task, files, file_producers):
    """
    Move the files a task declares to the workflow-wide list of files, and record
    them as input or output files of that task.
    :param task: task dictionary in its version 1.4 form
    :param specification_task: specification task dictionary being built
    :param files: workflow-wide list of files, updated in place
    :param file_producers: map of file IDs to the ID of the task that writes them,
                           updated in place
    """
    for file in task.get("files", []):
        file_id = file["name"]
        if "path" in file:
            file_id = file["path"] + file_id

        if file_id not in file_producers:
            file_producers[file_id] = None
            files.append({
                "id": file_id,
                "sizeInBytes": file["sizeInBytes"]
            })

        if str(file.get("link", "")).lower() == "input":
            _append_unique(specification_task["inputFiles"], file_id)
        else:
            if not file_producers[file_id]:
                file_producers[file_id] = specification_task["id"]
            _append_unique(specification_task["outputFiles"], file_id)


def _execution_task(task, task_id):
    """
    Build the version 1.5 execution entry of a task.
    :param task: task dictionary in its version 1.4 form
    :param task_id: version 1.5 ID of the task
    :return: execution task dictionary
    """
    execution_task = {
        "id": task_id,
        "runtimeInSeconds": task.get("runtimeInSeconds", 0)
    }

    _update_data(task, "command", execution_task, "command")
    _update_data(task, "cores", execution_task, "coreCount")
    _update_data(task, "avgCPU", execution_task, "avgCPU")
    _update_data(task, "readBytes", execution_task, "readBytes")
    _update_data(task, "writtenBytes", execution_task, "writtenBytes")
    _update_data(task, "memoryInBytes", execution_task, "memoryInBytes")
    _update_data(task, "energy", execution_task, "energyInKWh")
    _update_data(task, "avgPower", execution_task, "avgPowerInW")
    _update_data(task, "priority", execution_task, "priority")

    if "machine" in task:
        execution_task["machines"] = [task["machine"]]

    return execution_task


def _migrate_to_16(data):
    """
    Migrate instance data from version 1.5 to 1.6.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """
    # Nothing to do here, as all new additions are optional items (the "metrics")
    # or small fixes to the schema itself
    data["schemaVersion"] = "1.6"
    return data


def _task_id(task, index):
    """
    Compute the version 1.5 ID of a task described in an earlier version.
    :param task: task dictionary
    :param index: position of the task in the list of workflow tasks
    :return: task ID
    """
    if "id" not in task:
        return f"{task['name']}_{index}"

    return task["name"] if task["id"] in task["name"] else f"{task['name']}_{task['id']}"


def _resolve_references(references, reference_map, task_id, kind):
    """
    Translate task references expressed as names into task IDs.
    :param references: list of task names or IDs
    :param reference_map: map of task names and old IDs to version 1.5 task IDs
    :param task_id: ID of the task holding the references, for logging purposes
    :param kind: kind of reference ("parent" or "child"), for logging purposes
    :return: list of task IDs, without duplicates
    """
    resolved = []

    for reference in references:
        target = reference_map.get(reference)
        if target is None:
            logger.warning(
                f"Task '{task_id}' declares an unknown {kind} task "
                f"'{reference}', which is kept as is.")
            target = reference
        _append_unique(resolved, target)

    return resolved


def _runtime_system_name(data):
    """
    Get the name of the runtime system that ran the workflow.
    :param data: instance data dictionary
    :return: lowercase runtime system name, or an empty string if undeclared
    """
    runtime_system = data.get("wms") or data.get("runtimeSystem") or {}
    return str(runtime_system.get("name", "")).lower()


def _convert_byte_counts(task, runtime_system):
    """
    Convert the pre-1.4 byte counts of a task, which are expressed in kilobytes
    by every runtime system but Pegasus.
    :param task: task dictionary
    :param runtime_system: lowercase runtime system name
    """
    scale = 1 if "pegasus" in runtime_system else 1000

    if "bytesRead" in task:
        task["readBytes"] = task.pop("bytesRead") * scale
    if "bytesWritten" in task:
        task["writtenBytes"] = task.pop("bytesWritten") * scale


def _append_unique(values, value):
    if value not in values:
        values.append(value)


def _extend_unique(values, new_values):
    for value in new_values:
        _append_unique(values, value)


def _update_data(src, src_key, dst, dst_key):
    if src_key in src:
        dst[dst_key] = src[src_key]
        src.pop(src_key)


def _check_task_ids(data, instance_file):
    """
    Report task IDs that the latest schema would reject, which happens when a
    task name in the original instance holds an unsupported character.
    :param data: migrated instance data dictionary
    :param instance_file: instance file path, for logging purposes
    """
    tasks = data.get("workflow", {}).get("specification", {}).get("tasks", [])
    invalid = sorted({
        task["id"] for task in tasks if not TASK_ID_PATTERN.match(task["id"])
    })

    if invalid:
        preview = ", ".join(repr(task_id) for task_id in invalid[:3])
        logger.warning(
            f"{instance_file}: {len(invalid)} task ID(s) hold characters that are "
            f"not allowed in WfFormat {LATEST_VERSION} ({preview}); "
            f"the migrated instance will not validate.")


def _cleanup(data):
    """
    Cleanup instances from old format.
    :param data: instance data dictionary
    :return: instance data dictionary in the migrated form
    """

    if "makespan" in data["workflow"] and "makespanInSeconds" in data["workflow"]:
        data["workflow"].pop("makespan", None)

    for machine in data["workflow"].get("machines", []):
        if "memory" in machine and "memoryInBytes" in machine:
            machine.pop("memory", None)

    runtime_system = _runtime_system_name(data)

    for task in data["workflow"]["tasks"]:
        if "runtime" in task and "runtimeInSeconds" in task:
            task.pop("runtime", None)

        _convert_byte_counts(task, runtime_system)

        if "memory" in task and "memoryInBytes" in task:
            task.pop("memory")

        for file in task.get("files", []):
            if "size" in file and "sizeInBytes" in file:
                file.pop("size", None)

    return data


def main():
    # Application's arguments
    parser = argparse.ArgumentParser(description="Migrate WfCommons Instances to latest WfFormat version.")
    parser.add_argument('instance', metavar='INSTANCE_FILE_OR_FOLDER',
                        help='JSON instance file or folder with instances')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='Report what would be migrated without writing any file')
    parser.add_argument('-b', '--backup', action='store_true',
                        help='Keep the original instance as <INSTANCE_FILE>.bak')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug messages to stderr')
    args = parser.parse_args()

    # Configure logging
    _configure_logging(args.debug)

    if not os.path.exists(args.instance):
        logger.error(f"No such instance file or folder: {args.instance}")
        return 1

    instance_files = _collect_instance_files(args.instance)
    if not instance_files:
        logger.warning(f"No JSON instance file found in: {args.instance}")
        return 0

    logger.info(f"Processing {len(instance_files)} JSON file(s), "
                f"migrating instances to version {LATEST_VERSION}.")

    # process instance(s)
    outcomes = Counter()
    for count, instance_file in enumerate(instance_files, start=1):
        outcomes[_process_instance(instance_file, args.dry_run, args.backup)] += 1
        if count % PROGRESS_INTERVAL == 0:
            logger.info(f"Processed {count} of {len(instance_files)} instance file(s).")

    logger.info(
        f"{'Would migrate' if args.dry_run else 'Successfully migrated'} "
        f"{outcomes[MIGRATED]} instance file(s): "
        f"{outcomes[UP_TO_DATE]} already at version {LATEST_VERSION}, "
        f"{outcomes[SKIPPED]} skipped, {outcomes[FAILED]} failed.")

    return 1 if outcomes[FAILED] else 0


if __name__ == "__main__":
    sys.exit(main())
