#!/usr/bin/env python3
"""
Add metrics to a WfFormat 1.6 or later workflow instance JSON file.
"""

import json
import sys

from collections import defaultdict
from collections import Counter, defaultdict, deque



class Graph:
    """Graph data structure represented as an adjacency list using a dictionary."""

    def __init__(self):
        """Initialize the graph."""
        self.adj_dict = defaultdict(list)

    def add_node(self, node):
        """
        Add a node to the graph.

        Args:
            node (any): The node to add to the graph
        """
        self.adj_dict[node] = []

    def add_edge(self, u, v):
        """
        Add a directed edge to the graph. Prevents adding duplicate directed edges.

        Args:
            u (any): The node to start from
            v (any): The node to point to
        """
        if v not in self.adj_dict[u]:
            self.adj_dict[u].append(v)



def add_specification_metrics(data):
    if "metrics" not in data["workflow"]["specification"]:
        data["workflow"]["specification"]["metrics"] = {}

    # Number of tasks
    number_of_tasks = len(data["workflow"]["specification"]["tasks"])
    data["workflow"]["specification"]["metrics"]["numberOfTasks"] = number_of_tasks

    # Number of files
    number_of_files = len(data["workflow"]["specification"]["files"])
    data["workflow"]["specification"]["metrics"]["numberOfFiles"] = number_of_files

    # Sum of file sizes
    sum_file_sizes = sum([f["sizeInBytes"] for f in data["workflow"]["specification"]["files"]])
    data["workflow"]["specification"]["metrics"]["sumOfFileSizesInBytes"] = sum_file_sizes

    depth, min_width, max_width = compute_graph_metrics(data["workflow"]["specification"]["tasks"])

    data["workflow"]["specification"]["metrics"]["numberOfLevels"] = depth
    data["workflow"]["specification"]["metrics"]["minimumWidth"] = min_width
    data["workflow"]["specification"]["metrics"]["maximumWidth"] = max_width

    for key,value in data["workflow"]["specification"]["metrics"].items():
        sys.stderr.write(f"Added specification metric {key}: {value}\n")

    return data

def add_execution_metrics(data):
    if "execution" not in data["workflow"]:
        return

    if "metrics" not in data["workflow"]["execution"]:
            data["workflow"]["execution"]["metrics"] = {}

    # Sum of task runtimes
    sum = 0
    for task in data["workflow"]["execution"]["tasks"]:
        if "runtimeInSeconds" in task:
            sum += task["runtimeInSeconds"]
    if sum > 0:
        data["workflow"]["execution"]["metrics"]["sumTaskRuntimesInSeconds"] = sum

    # Total number of bytes read
    sum = 0
    for task in data["workflow"]["execution"]["tasks"]:
        if "readBytes" in task:
            sum += task["readBytes"]
    if sum > 0:
        data["workflow"]["execution"]["metrics"]["totalNumBytesRead"] = sum

    # Total number of bytes written
    sum = 0
    for task in data["workflow"]["execution"]["tasks"]:
        if "writtenBytes" in task:
            sum += task["writtenBytes"]
    if sum > 0:
        data["workflow"]["execution"]["metrics"]["totalNumBytesWritten"] = sum

    for key,value in data["workflow"]["execution"]["metrics"].items():
        sys.stderr.write(f"Added execution metric {key}: {value}\n")

    return data

from collections import deque


def compute_graph_metrics(tasks):
    """
    Compute workflow DAG level metrics.

    A root is at level 0. Every other task is at one plus the
    maximum level of any of its parents.

    Returns:
        tuple:
            number_of_levels,
            minimum_level_width,
            maximum_level_width
    """
    number_of_tasks = len(tasks)

    # Explicit behavior for an empty workflow.
    if number_of_tasks == 0:
        return 0, 0, 0

    # Mapping IDs to integer indices lets the frequently updated state
    # below use compact Python lists rather than dictionaries keyed by
    # task-ID strings.
    id_to_index = {}

    for index, task in enumerate(tasks):
        task_id = task["id"]

        if task_id in id_to_index:
            raise ValueError(f"Duplicate task ID: {task_id!r}")

        id_to_index[task_id] = index

    # This assumes the parents and children declarations agree, as they
    # should in a valid WfFormat instance.
    remaining_parents = [
        len(task["parents"])
        for task in tasks
    ]

    ready = deque(
        index
        for index, parent_count in enumerate(remaining_parents)
        if parent_count == 0
    )

    level_widths = []
    number_processed = 0

    while ready:
        # Tasks currently in the queue constitute exactly one level.
        level_width = len(ready)
        level_widths.append(level_width)

        # Fix the iteration count so that children made ready during
        # this iteration are processed as part of the next level.
        for _ in range(level_width):
            task_index = ready.popleft()
            task = tasks[task_index]
            number_processed += 1

            for child_id in task["children"]:
                try:
                    child_index = id_to_index[child_id]
                except KeyError as exc:
                    raise ValueError(
                        f"Task {task['id']!r} references unknown "
                        f"child task {child_id!r}"
                    ) from exc

                remaining_parents[child_index] -= 1

                if remaining_parents[child_index] == 0:
                    ready.append(child_index)
                elif remaining_parents[child_index] < 0:
                    raise ValueError(
                        "Inconsistent parent/child declarations or "
                        f"duplicate edge ending at task {child_id!r}"
                    )

    if number_processed != number_of_tasks:
        unresolved = [
            tasks[index]["id"]
            for index, parent_count in enumerate(remaining_parents)
            if parent_count > 0
        ]

        preview = ", ".join(repr(task_id) for task_id in unresolved[:5])

        raise ValueError(
            "The workflow graph contains a cycle or has inconsistent "
            f"parent/child declarations; {len(unresolved)} tasks were "
            f"not processed"
            + (f" ({preview})" if preview else "")
        )

    return (
        len(level_widths),
        min(level_widths),
        max(level_widths),
    )

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 wfcommons-add-metrics-to-instance.py input.json [output.json]")
        print("  If output.json is ommitted the input file is overwritten in place")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path

    with open(input_path, "r") as f:
        data = json.load(f)

    data = add_specification_metrics(data)
    data = add_execution_metrics(data)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    sys.stderr.write(f"Wrote new instance file with metrics to {output_path}\n")

if __name__ == "__main__":
    main()
