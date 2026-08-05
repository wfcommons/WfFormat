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

    # Calculate graph metrics
    # Build graph of tasks
    graph, top_level_nodes = Graph(), set()
    for task in data["workflow"]["specification"]['tasks']:
     if len(task['parents']) == 0:
         top_level_nodes.add(task['id'])
     for child in task['children']:
         graph.add_edge(task['id'], child)

    # Calculate levels and depth
    depth, levels = 0, defaultdict(int)
    for node in top_level_nodes:
     queue = deque([node])
     while queue:
         task = queue.popleft()
         for child_node in graph.adj_dict[task]:
             levels[child_node] = max(1 + levels[task], levels[child_node])
             queue.append(child_node)
             depth = max(depth, levels[child_node])
    depth += 1

    # Calculate min and max width from levels
    counter = Counter()
    for level in levels.values():
     counter[level] += 1
    most_common = counter.most_common()
    min_width, max_width = most_common[-1][1], most_common[0][1]

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
