#!/usr/bin/env python3
#
# Copyright (c) 2020-2026 The WfCommons Team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import argparse
import json
import jsonschema
import logging
import math
import os
import sys

from collections import Counter, deque

__author__ = "Rafael Ferreira da Silva"

logger = logging.getLogger(__name__)

SCHEMA_FILE_NAME = "wfcommons-schema.json"
SCHEMA_URL = f"https://raw.githubusercontent.com/wfcommons/wfformat/main/{SCHEMA_FILE_NAME}"
SCHEMA_FETCH_TIMEOUT_IN_SECONDS = 30

# tolerance used when comparing declared metrics against recomputed ones
METRICS_RELATIVE_TOLERANCE = 1e-9


class _Report:
    """
    Collect the problems found while validating a single instance file.
    """

    def __init__(self, instance_file, show_instance_file=False):
        """
        :param instance_file: instance file path
        :param show_instance_file: whether to prefix messages with the file path,
                                   which is only useful when validating several files
        """
        self.instance_file = instance_file
        self.errors = 0
        self.warnings = 0
        self._prefix = f"{instance_file}: " if show_instance_file else ""

    def error(self, message):
        self.errors += 1
        logger.error(f"{self._prefix}{message}")

    def warning(self, message):
        self.warnings += 1
        logger.warning(f"{self._prefix}{message}")


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
    :return: WfCommons JSON schema
    """
    if schema_file:
        # schema file provided
        logger.debug(f"Using schema file: {schema_file}")
        with open(schema_file, encoding="utf-8") as f:
            return json.load(f)

    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SCHEMA_FILE_NAME)
    if os.path.exists(schema_path):
        logger.debug(f"Using schema file: {schema_path}")
        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)

    # fetching latest schema file from GitHub repository
    logger.debug("Using latest schema file from GitHub repository.")
    import requests

    response = requests.get(SCHEMA_URL, timeout=SCHEMA_FETCH_TIMEOUT_IN_SECONDS)
    response.raise_for_status()
    return response.json()


def _collect_instance_files(paths):
    """
    List the instance files to be validated.
    :param paths: instance file paths, or paths to folders to be walked recursively
    :return: list of file paths
    """
    instance_files = []

    for path in paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                instance_files.extend(
                    os.path.join(root, f) for f in sorted(files) if f.endswith(".json"))
        else:
            instance_files.append(path)

    return instance_files


def _validate_instance(schema, instance_file, show_instance_file=False):
    """
    Validate a single instance file.
    :param schema: WfCommons JSON schema
    :param instance_file: instance file path
    :param show_instance_file: whether to prefix messages with the file path
    :return: the validation report
    """
    report = _Report(instance_file, show_instance_file)
    logger.debug(f"Instance file been evaluated: {instance_file}")

    try:
        with open(instance_file, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        report.error(f"unable to read instance file: {e}")
        return report

    _syntax_validation(schema, data, report)

    # the semantic checks below assume a structurally sound instance
    if report.errors > 0:
        logger.debug(f"Skipping semantic validation: {instance_file}")
        return report

    _semantic_validation(data, report)

    return report


def _syntax_validation(schema, data, report):
    """
    Validate the JSON workflow execution instance against the schema
    :param schema: WfCommons JSON schema
    :param data: JSON instance
    :param report: the validation report
    """
    # honor the draft the schema declares, rather than assuming one
    validator_class = jsonschema.validators.validator_for(schema)
    validator = validator_class(schema, format_checker=jsonschema.FormatChecker())

    for error in sorted(validator.iter_errors(data), key=str):
        location = " > ".join([str(e) for e in error.absolute_path]) or "<instance>"
        message = f"{location}: {error.message}"

        # a malformed timestamp or email does not make the instance unusable, and
        # "format" is an annotation rather than an assertion in JSON Schema
        if error.validator == "format":
            report.warning(message)
        else:
            report.error(message)


def _semantic_validation(data, report):
    """
    Validate the semantics of the JSON workflow execution instance
    :param data: JSON instance
    :param report: the validation report
    """
    workflow = data.get("workflow", {})
    specification = workflow.get("specification", {})
    execution = workflow.get("execution")

    tasks = specification.get("tasks", [])
    task_ids = _collect_ids(tasks, "id", "task", report)
    file_ids = _collect_ids(specification.get("files", []), "id", "file", report)

    _validate_dependencies(tasks, task_ids, report)
    _validate_file_references(tasks, specification, file_ids, report)

    level_widths = _compute_level_widths(tasks, report)
    _validate_specification_metrics(specification, level_widths, report)

    logger.debug('The workflow has %d tasks.' % len(task_ids))
    logger.debug('The workflow has %d files.' % len(file_ids))

    if execution is None:
        logger.debug('Skipping execution processing.')
        return

    _validate_execution(execution, task_ids, report)
    _validate_execution_metrics(execution, report)


def _collect_ids(items, key, kind, report):
    """
    Collect the identifiers of a list of items, reporting duplicates.
    :param items: list of dictionaries
    :param key: name of the property holding the identifier
    :param kind: kind of item, for logging purposes
    :param report: the validation report
    :return: set of identifiers
    """
    identifiers = set()

    for item in items:
        identifier = item.get(key)
        if identifier is None:
            continue
        if identifier in identifiers:
            report.error(f"The {kind} '{identifier}' is declared more than once.")
        identifiers.add(identifier)

    return identifiers


def _validate_dependencies(tasks, task_ids, report):
    """
    Verify that task dependencies refer to declared tasks, and that the parents and
    children declarations describe the same set of edges.
    :param tasks: list of specification tasks
    :param task_ids: set of declared task IDs
    :param report: the validation report
    """
    parents_of = {}
    children_of = {}

    for task in tasks:
        task_id = task.get("id")
        if task_id is None:
            continue

        for kind, key in (("parent", "parents"), ("child", "children")):
            _validate_dependency_references(task_id, task.get(key, []), kind, task_ids, report)

        parents_of[task_id] = set(task.get("parents", []))
        children_of[task_id] = set(task.get("children", []))

    # both ends of every dependency have to agree, as WfCommons tooling reads the
    # workflow graph through either one of them
    _validate_dependency_symmetry(parents_of, children_of, "parent", "child", report)
    _validate_dependency_symmetry(children_of, parents_of, "child", "parent", report)


def _validate_dependency_references(task_id, references, kind, task_ids, report):
    """
    Verify the parents or children declared by a single task.
    :param task_id: ID of the task holding the references
    :param references: list of referenced task IDs
    :param kind: kind of reference ("parent" or "child")
    :param task_ids: set of declared task IDs
    :param report: the validation report
    """
    for reference in references:
        if reference == task_id:
            report.error(f"Task '{task_id}' declares itself as its own {kind}.")
        elif reference not in task_ids:
            report.error(f"{kind.capitalize()} task '{reference}' is not declared "
                         f"in the list of workflow tasks.")

    if len(references) != len(set(references)):
        report.warning(f"Task '{task_id}' declares the same {kind} task more than once.")


def _validate_dependency_symmetry(relation, reverse_relation, kind, reverse_kind, report):
    """
    Verify that every declared dependency is mirrored by the task on its other end.
    :param relation: map of task IDs to the set of tasks they declare
    :param reverse_relation: map of task IDs to the set of tasks declaring the reverse
    :param kind: kind of the declared relation ("parent" or "child")
    :param reverse_kind: kind of the reverse relation ("child" or "parent")
    :param report: the validation report
    """
    for task_id, references in relation.items():
        for reference in references:
            # self references are reported as errors of their own
            if reference == task_id or reference not in reverse_relation:
                continue
            if task_id not in reverse_relation[reference]:
                report.warning(f"Task '{task_id}' declares '{reference}' as a {kind}, but task "
                               f"'{reference}' does not declare '{task_id}' as a {reverse_kind}.")


def _validate_file_references(tasks, specification, file_ids, report):
    """
    Verify that the files used by tasks are declared in the list of workflow files.
    :param tasks: list of specification tasks
    :param specification: workflow specification dictionary
    :param file_ids: set of declared file IDs
    :param report: the validation report
    """
    files_declared = "files" in specification
    referenced_file_ids = set()

    for task in tasks:
        task_id = task.get("id")

        for key in ("inputFiles", "outputFiles"):
            for file_id in task.get(key, []):
                referenced_file_ids.add(file_id)
                if files_declared and file_id not in file_ids:
                    report.error(f"File '{file_id}', used by task '{task_id}' as one of its "
                                 f"{key}, is not declared in the list of workflow files.")

    if not files_declared and referenced_file_ids:
        report.warning(f"{len(referenced_file_ids)} file(s) are used by tasks while the "
                       f"workflow declares no list of files.")

    for file_id in sorted(file_ids - referenced_file_ids):
        report.warning(f"The file '{file_id}' is declared but not used by any task.")


def _compute_level_widths(tasks, report):
    """
    Compute the width of each level of the workflow DAG, where a task with no
    parents is at level 0 and every other task is at one plus the maximum level of
    any of its parents. Detects cycles as a side effect.
    :param tasks: list of specification tasks
    :param report: the validation report
    :return: list of level widths, or None if the graph is not a DAG
    """
    task_ids = [task["id"] for task in tasks if "id" in task]
    index_of = {task_id: index for index, task_id in enumerate(task_ids)}

    parent_counts = [0] * len(task_ids)
    children = [[] for _ in task_ids]

    for task in tasks:
        task_id = task.get("id")
        if task_id is None:
            continue

        # duplicate and dangling dependencies are reported elsewhere; they are
        # ignored here so that the traversal reflects the actual graph
        for parent in set(task.get("parents", [])):
            if parent in index_of and parent != task_id:
                parent_counts[index_of[task_id]] += 1
                children[index_of[parent]].append(index_of[task_id])

    ready = deque(index for index, count in enumerate(parent_counts) if count == 0)
    level_widths = []
    number_processed = 0

    while ready:
        # tasks currently in the queue constitute exactly one level
        level_width = len(ready)
        level_widths.append(level_width)

        for _ in range(level_width):
            index = ready.popleft()
            number_processed += 1

            for child_index in children[index]:
                parent_counts[child_index] -= 1
                if parent_counts[child_index] == 0:
                    ready.append(child_index)

    if number_processed != len(task_ids):
        unresolved = [task_ids[index] for index, count in enumerate(parent_counts) if count > 0]
        preview = ", ".join(repr(task_id) for task_id in sorted(unresolved)[:5])
        report.error(f"The workflow graph contains a cycle: {len(unresolved)} task(s) are "
                     f"part of, or depend on, a cycle ({preview}).")
        return None

    return level_widths


def _validate_execution(execution, task_ids, report):
    """
    Verify that the execution section is consistent with the workflow specification.
    :param execution: workflow execution dictionary
    :param task_ids: set of task IDs declared in the specification
    :param report: the validation report
    """
    machines_declared = "machines" in execution
    machine_names = _collect_ids(execution.get("machines", []), "nodeName", "machine", report)
    executed_task_ids = set()

    for task in execution.get("tasks", []):
        task_id = task.get("id")
        if task_id is None:
            continue

        if task_id in executed_task_ids:
            report.error(f"The task '{task_id}' is declared more than once in the execution "
                         f"section.")
        executed_task_ids.add(task_id)

        if task_id not in task_ids:
            report.error(f"Task '{task_id}' of the execution section is not declared in the "
                         f"list of workflow tasks.")

        for machine_name in task.get("machines", []):
            if machines_declared and machine_name not in machine_names:
                report.error(f"Machine '{machine_name}', used by task '{task_id}', is not "
                             f"declared in the list of machines.")
            elif not machines_declared:
                report.warning(f"Task '{task_id}' ran on machine '{machine_name}' while the "
                               f"workflow declares no list of machines.")

    for task_id in sorted(task_ids - executed_task_ids):
        report.warning(f"The task '{task_id}' has no entry in the execution section.")

    logger.debug('The workflow has %d machines.' % len(machine_names))


def _validate_specification_metrics(specification, level_widths, report):
    """
    Verify the optional specification metrics against the workflow itself.
    :param specification: workflow specification dictionary
    :param level_widths: list of DAG level widths, or None if the graph is not a DAG
    :param report: the validation report
    """
    metrics = specification.get("metrics")
    if not metrics:
        return

    files = specification.get("files", [])
    expected = {
        "numberOfTasks": len(specification.get("tasks", [])),
        "numberOfFiles": len(files),
        "sumOfFileSizesInBytes": sum(f.get("sizeInBytes", 0) for f in files)
    }

    if level_widths:
        expected["numberOfLevels"] = len(level_widths)
        expected["minimumWidth"] = min(level_widths)
        expected["maximumWidth"] = max(level_widths)

    _compare_metrics(metrics, expected, "specification", report)


def _validate_execution_metrics(execution, report):
    """
    Verify the optional execution metrics against the workflow itself.
    :param execution: workflow execution dictionary
    :param report: the validation report
    """
    metrics = execution.get("metrics")
    if not metrics:
        return

    tasks = execution.get("tasks", [])
    expected = {
        "sumTaskRuntimesInSeconds":
            sum(t["runtimeInSeconds"] for t in tasks if "runtimeInSeconds" in t),
        "totalNumBytesRead": sum(t["readBytes"] for t in tasks if "readBytes" in t),
        "totalNumBytesWritten": sum(t["writtenBytes"] for t in tasks if "writtenBytes" in t)
    }

    _compare_metrics(metrics, expected, "execution", report)


def _compare_metrics(metrics, expected, section, report):
    """
    Compare declared metrics against the values recomputed from the instance.
    :param metrics: declared metrics dictionary
    :param expected: recomputed metrics dictionary
    :param section: name of the section holding the metrics, for logging purposes
    :param report: the validation report
    """
    for key, expected_value in expected.items():
        if key not in metrics:
            continue

        declared_value = metrics[key]
        if not math.isclose(declared_value, expected_value, rel_tol=METRICS_RELATIVE_TOLERANCE):
            report.error(f"The {section} metric '{key}' is declared as {declared_value}, but "
                         f"the instance data gives {expected_value}.")


def _report_summary(totals, number_of_instance_files, failed):
    """
    Report the outcome of the validation.
    :param totals: counts of valid/invalid instance files, errors, and warnings
    :param number_of_instance_files: number of instance files validated
    :param failed: whether the validation failed
    """
    if number_of_instance_files > 1:
        logger.info(f"{totals['valid']} of {number_of_instance_files} instance file(s) have a "
                    f"valid WfCommons JSON instance format "
                    f"({totals['errors']} error(s), {totals['warnings']} warning(s)).")
        return

    if failed:
        logger.error("The instance file is not a valid WfCommons JSON instance.")
        return

    logger.info("The instance file has a valid WfCommons JSON instance format.")
    if totals["warnings"]:
        logger.info(f"{totals['warnings']} warning(s) were reported.")


def main():
    # Application's arguments
    parser = argparse.ArgumentParser(description='Validate JSON file against wfcommons-schema.')
    parser.add_argument('data_files', metavar='JSON_FILE', nargs='+',
                        help='JSON instance file, or folder with instance files')
    parser.add_argument('-s', dest='schema_file', help='JSON schema file')
    parser.add_argument('--strict', action='store_true', help='Treat warnings as errors')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug messages to stderr')
    args = parser.parse_args()

    # Configure logging
    _configure_logging(args.debug)

    # load schema file
    try:
        schema = _load_schema(args.schema_file)
        jsonschema.validators.validator_for(schema).check_schema(schema)
    except Exception as e:
        logger.error(f"Unable to load the WfCommons JSON schema: {e}",
                     exc_info=logger.isEnabledFor(logging.DEBUG))
        return 1

    instance_files = _collect_instance_files(args.data_files)
    if not instance_files:
        logger.error("No JSON instance file to validate.")
        return 1

    # validate instance(s)
    totals = Counter()
    for instance_file in instance_files:
        report = _validate_instance(schema, instance_file, len(instance_files) > 1)
        totals["errors"] += report.errors
        totals["warnings"] += report.warnings
        totals["invalid" if report.errors else "valid"] += 1

    failed = totals["errors"] > 0 or (args.strict and totals["warnings"] > 0)
    _report_summary(totals, len(instance_files), failed)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
