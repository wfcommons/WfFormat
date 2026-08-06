[![DOI](https://zenodo.org/badge/252368853.svg)](https://zenodo.org/badge/latestdoi/252368853)&nbsp;&nbsp;
[![GitHub Release](https://img.shields.io/github/release/wfcommons/wfformat/all.svg)](https://github.com/wfcommons/wfformat/releases)

<a href="https://wfcommons.org" target="_blank"><img src="https://wfcommons.org/images/wfcommons-logo.png" width="350" /></a>

# WfFormat: The WfCommons JSON Schema

- Current schema version: `1.6`
- Schema file: [`wfcommons-schema.json`](wfcommons-schema.json) (JSON Schema draft [2020-12](https://json-schema.org/draft/2020-12/schema))
- Schema validator: [`wfcommons-validator.py`](wfcommons-validator.py) (see [Validator](#validator))
- Additional tooling: [`tools/`](tools/) (see [Tools](#tools))

## What's New in 1.6

- Optional [`metrics`](#metrics-property-specification) object under `workflow.specification`, summarizing workflow structure (task/file counts, aggregate file size, DAG levels and widths).
- Optional [`metrics`](#metrics-property-execution) object under `workflow.execution`, summarizing execution aggregates (total work, total bytes read/written).
- Task IDs in the specification and execution sections are now validated against a single shared definition (`$defs/taskId`), so the same character set and non-empty constraint apply to `id`, `parents`, and `children` alike.
- `createdAt`, `executedAt` (workflow), and `executedAt` (task) now carry a `date-time` format annotation.
- The schema was migrated from `http://json-schema.org/schema#` to JSON Schema draft 2020-12.

Because all 1.6 additions are optional, a valid 1.5 instance is structurally a valid 1.6 instance; only the `schemaVersion` string needs to change. The [migration tool](#migration) does this for you.

## Documentation

This documentation provides an overview of the WfCommons JSON schema. Although this documentation attempts to cover all aspects of the schema, we strongly recommend the use of a JSON schema validator before using your own workflow execution instances or workflow descriptions. Required properties are identified with a marked checkbox symbol.

Two conventions apply throughout:

- **`schemaVersion` is a closed enumeration.** The current schema accepts only the string `"1.6"`. Instances produced against an earlier version must be migrated (see [Migration](#migration)) before they will validate.
- **Unknown properties are permitted.** The schema does not set `additionalProperties: false` anywhere, so runtime systems may attach their own extra fields without failing validation. Only the properties documented below are interpreted by WfCommons tooling.

---

## General Instance Properties

- [x] `name`: Representative name for the instance name.
- [ ] `description`: A concise description of the instance. It should aid researchers to understand the purpose of the execution.
- [ ] `createdAt`: Schema creation date in the [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601) format (e.g., `2020-03-20T15:19:28-08:00`).
- [x] `schemaVersion`: Version of the schema from an enumerate (currently `1.6` only).
- [ ] [`runtimeSystem`](#runtime-system-property): An `object` to describe the runtime system used to execute the workflow.
- [x] [`workflow`](#workflow-property): An `object` to describe the workflow characteristics and performance metrics.
- [ ] [`author`](#author-property): An `object` to describe the author/institution who created/generated the instance.

## Runtime System Property

The **`runtimeSystem`** property documents the runtime system used to run the workflow. It has the following sub-properties:

- [x] `name`: runtime system name.
- [x] `version`: runtime system version.
- [ ] `url`: URL for the main runtime system website.

## Workflow Property

The **`workflow`** property is the **core** element of the instance file. It contains the workflow structure (tasks, dependencies, and files), as well as task characteristics and performance information. It is composed by the following sub-properties:

- [x] [`specification`](#specification-property): Workflow specification (does not contain any execution information).
- [ ] [`execution`](#execution-property): Workflow execution information.

A purely structural workflow description (e.g., a synthetic workflow, or a workflow that has not been run) is therefore a valid instance with only a `specification` section.

### Specification Property

- [x] [`tasks`](#tasks-property-specification): List of workflow tasks (at least one).
- [ ] [`files`](#files-property-specification): List of workflow files.
- [ ] [`metrics`](#metrics-property-specification): Summary metrics describing the workflow structure.

#### Tasks Property (Specification)

This property lists all tasks of the workflow describing their relationships and file dependencies. Each task is described as an `object` with 6 properties:

- [x] `name`: Task name (often set to the name of the program executed by a task or to some notion of task type or category).
- [x] `id`: Unique task ID (e.g., ID0000001). See [Identifier conventions](#identifier-conventions).
- [x] `parents`: List of parent tasks (reference to other workflow tasks by their `id`).
- [x] `children`: List of children tasks (reference to other workflow tasks by their `id`).
- [ ] `inputFiles`: List of the input file IDs
- [ ] `outputFiles`: List of output file IDs

`parents` and `children` are expected to be consistent with each other: if task `B` lists `A` as a parent, then `A` should list `B` as a child. The schema cannot express this constraint, but WfCommons tooling relies on it (the [metrics tool](#metrics) traverses the DAG through `children` while counting in-degrees from `parents`, and reports an error when the two disagree).

#### Files Property (Specification)

This property lists all data files in the workflow that are used as input/output by tasks. Each file is described as an `object` with 2 properties:

- [x] `id`: Unique file ID (e.g., a file name, a path, an arbitrary string). See [Identifier conventions](#identifier-conventions).
- [x] `sizeInBytes`: File size in bytes (non-negative `integer`).

#### Metrics Property (Specification)

The **`metrics`** property holds precomputed summary values that describe the workflow structure. It is purely derivative: every value can be recomputed from `tasks` and `files`, and is provided so that consumers can filter or index large instance collections without parsing the full DAG. All sub-properties are optional non-negative integers:

- [ ] `numberOfTasks`: Number of tasks in the workflow.
- [ ] `numberOfFiles`: Number of files in the workflow.
- [ ] `sumOfFileSizesInBytes`: Sum of the sizes of all files in bytes.
- [ ] `numberOfLevels`: Number of levels in the workflow DAG. A task with no parents is at level 0; every other task is at one plus the maximum level of any of its parents.
- [ ] `minimumWidth`: Minimum width (parallelism) over the levels in the workflow DAG.
- [ ] `maximumWidth`: Maximum width (parallelism) over the levels in the workflow DAG.

These values can be generated for an existing instance with the [metrics tool](#metrics).

### Execution Property

- [x] `makespanInSeconds`: Workflow overall execution time in _seconds_.
- [x] `executedAt`: Workflow start timestamp in the [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601) format (e.g., `2020-04-01T15:10:53-08:00`).
- [x] [`tasks`](#tasks-property-execution): List of workflow tasks (at least one).
- [ ] [`machines`](#machines-property-execution): List of compute machines used for running the workflow tasks (at least one, if present).
- [ ] [`metrics`](#metrics-property-execution): Summary metrics describing the workflow execution.

#### Tasks Property (Execution)

This property lists all tasks of the workflow describing their characteristics and performance metrics. Each task is described as an `object` property and is composed of 13 properties:

- [x] `id`: Task unique ID (e.g., ID0000001), matching a task `id` in the [specification](#tasks-property-specification).
- [x] `runtimeInSeconds`: Task runtime in _seconds_.
- [ ] `executedAt`: Task start timestamp in the [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601) format (e.g., `2020-04-01T15:10:53-08:00`).
- [ ] [`command`](#command-property-execution): An `object` to describe the task's command.
- [ ] `coreCount`: Number of cores required by the task, possibly fractional but no less than 1 (e.g., `1.5`).
- [ ] `avgCPU`: Average CPU utilization in % (e.g, `93.78`).
- [ ] `readBytes`: Total bytes read.
- [ ] `writtenBytes`: Total bytes written.
- [ ] `memoryInBytes`: Memory (resident set) size of the process in bytes.
- [ ] `energyInKWh`: Total energy consumption in kWh.
- [ ] `avgPowerInW`: Average power consumption in W.
- [ ] `priority`: Task priority as an _integer_ value.
- [ ] `machines`: List of node names of machines on which the task executed (each should match a `nodeName` in [`machines`](#machines-property-execution)).

##### Command Property (Execution)

The **`command`** property describes the program and arguments used by a task. It is composed of the following properties, both optional:

- [ ] `program`: Program name.
- [ ] `arguments`: List of task arguments.

#### Machines Property (Execution)

The **`machines`** property lists all different machines that were used for workflow tasks execution. It is composed of the following properties:

- [ ] `system`: Machine system (`linux`, `macos`, `windows`).
- [ ] `architecture`: Machine architecture (e.g., `x86_64`).
- [x] `nodeName`: Machine node name (hostname).
- [ ] `release`: Machine release.
- [ ] `memoryInBytes`: Total RAM memory in bytes (`integer`).
- [ ] [`cpu`](#cpu-property-execution): An `object` to describe the machine's CPU information.

##### CPU Property (Execution)

The **`cpu`** property describes the used CPUs. It has the following sub-properties, all optional:

- [ ] `coreCount`: Number of CPU cores, as an `integer` of at least 1. (Unlike a task's `coreCount`, a machine's core count is not fractional.)
- [ ] `speedInMHz`: CPU speed in MHz (`integer`).
- [ ] `vendor`: CPU vendor.

#### Metrics Property (Execution)

The **`metrics`** property holds precomputed aggregates over the execution tasks. Like the specification metrics, it is derivative and entirely optional:

- [ ] `sumTaskRuntimesInSeconds`: The sum of task runtimes, a measure of total work (non-negative `number`).
- [ ] `totalNumBytesRead`: The total number of bytes read in by tasks (non-negative `integer`).
- [ ] `totalNumBytesWritten`: The total number of bytes written out by tasks (non-negative `integer`).

## Author Property

The **`author`** property should contain the contact information about the person or team who created the instance. It is composed of the following properties:

- [x] `name`: Author name.
- [x] `email`: Author email.
- [ ] `institution`: Author institution.
- [ ] `country`: Author country (preferably country code, [ISO ALPHA-2 code](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)).

## Identifier Conventions

Task and file identifiers are constrained to a restricted character set so that they remain usable as keys, path fragments, and graph node labels across tools:

| Identifier | Where | Allowed characters |
| --- | --- | --- |
| Task ID | `specification.tasks[].id`, `parents[]`, `children[]`, `execution.tasks[].id` | `^[0-9a-zA-Z_.#:/-]+$` |
| File ID | `specification.files[].id`, `inputFiles[]`, `outputFiles[]` | `^[0-9a-zA-Z-_./:#]*$`, non-empty |

In practice both patterns permit the same characters: alphanumerics plus `_ . # : / -`. Notably, **spaces are not allowed**, which most commonly bites when a file ID is derived from a path or an argument string.

---

## Example

A minimal but complete instance exercising both the specification and execution sections:

```json
{
  "name": "my-workflow-instance",
  "description": "A two-task workflow executed on a single node",
  "createdAt": "2026-08-04T15:19:28-08:00",
  "schemaVersion": "1.6",
  "author": {
    "name": "Jane Doe",
    "email": "jane.doe@example.org",
    "institution": "Example University",
    "country": "US"
  },
  "runtimeSystem": {
    "name": "pegasus",
    "version": "5.0.6",
    "url": "https://pegasus.isi.edu"
  },
  "workflow": {
    "specification": {
      "tasks": [
        {
          "name": "split",
          "id": "ID0000001",
          "parents": [],
          "children": ["ID0000002"],
          "inputFiles": ["input.txt"],
          "outputFiles": ["chunk.txt"]
        },
        {
          "name": "analyze",
          "id": "ID0000002",
          "parents": ["ID0000001"],
          "children": [],
          "inputFiles": ["chunk.txt"],
          "outputFiles": ["result.txt"]
        }
      ],
      "files": [
        {"id": "input.txt", "sizeInBytes": 1024},
        {"id": "chunk.txt", "sizeInBytes": 512},
        {"id": "result.txt", "sizeInBytes": 128}
      ],
      "metrics": {
        "numberOfTasks": 2,
        "numberOfFiles": 3,
        "sumOfFileSizesInBytes": 1664,
        "numberOfLevels": 2,
        "minimumWidth": 1,
        "maximumWidth": 1
      }
    },
    "execution": {
      "makespanInSeconds": 14.2,
      "executedAt": "2026-08-04T15:20:00-08:00",
      "tasks": [
        {
          "id": "ID0000001",
          "runtimeInSeconds": 4.2,
          "executedAt": "2026-08-04T15:20:00-08:00",
          "command": {"program": "split", "arguments": ["-n", "2", "input.txt"]},
          "coreCount": 1,
          "avgCPU": 93.78,
          "readBytes": 1024,
          "writtenBytes": 512,
          "memoryInBytes": 4194304,
          "machines": ["node01.example.org"]
        },
        {
          "id": "ID0000002",
          "runtimeInSeconds": 10.0,
          "executedAt": "2026-08-04T15:20:04-08:00",
          "coreCount": 4,
          "readBytes": 512,
          "writtenBytes": 128,
          "machines": ["node01.example.org"]
        }
      ],
      "machines": [
        {
          "system": "linux",
          "architecture": "x86_64",
          "nodeName": "node01.example.org",
          "release": "5.15.0",
          "memoryInBytes": 34359738368,
          "cpu": {"coreCount": 8, "speedInMHz": 3600, "vendor": "AMD"}
        }
      ],
      "metrics": {
        "sumTaskRuntimesInSeconds": 14.2,
        "totalNumBytesRead": 1536,
        "totalNumBytesWritten": 640
      }
    }
  }
}
```

---

## Tools

| Script | Purpose |
| --- | --- |
| [`wfcommons-validator.py`](wfcommons-validator.py) | Validate instances against the schema (syntax) and check cross-references, graph structure, and metrics (semantics). |
| [`tools/wfcommons-migrate-instance.py`](tools/wfcommons-migrate-instance.py) | Migrate instance files from WfFormat 1.0–1.5 to 1.6. |
| [`tools/wfcommons-add-metrics-to-instance.py`](tools/wfcommons-add-metrics-to-instance.py) | Compute and add the optional `metrics` objects introduced in 1.6. |

### Validator

WfCommons provides a Python-based instance validator script for verifying the
syntax of JSON instance files, as well as their semantics.

**Prerequisite:** The validator script requires the Python's `jsonschema`
module, which can be installed as follows:

```
$ pip install jsonschema
```

Two optional installs extend what is checked: `pip install "jsonschema[format]"`
enables the `date-time`, `uri`, and `hostname` format checks (formats without an
installed checker are silently skipped), and `pip install requests` is needed
only when the schema has to be downloaded (see below).

The validator script signature is defined as follows:

```
usage: wfcommons-validator.py [-h] [-s SCHEMA_FILE] [--strict] [-d]
                              JSON_FILE [JSON_FILE ...]

Validate JSON file against wfcommons-schema.

positional arguments:
  JSON_FILE       JSON instance file, or folder with instance files

options:
  -h, --help      show this help message and exit
  -s SCHEMA_FILE  JSON schema file
  --strict        Treat warnings as errors
  -d, --debug     Print debug messages to stderr
```

The schema is resolved in this order: the file given with `-s`, then
`wfcommons-schema.json` sitting next to the script, and finally the latest
schema fetched from the WfFormat GitHub repository. Several files and folders
may be given at once, in which case each is validated independently and a
summary is printed. The script logs one message per problem and exits with
status `1` if any error was reported.

Problems are reported as **errors**, which make validation fail, or as
**warnings**, which do not (unless `--strict` is given). Beyond the schema
check, the semantic pass reports:

| Check | Level |
| --- | --- |
| Task, file, and machine identifiers are unique | error |
| `parents` and `children` refer to declared tasks, and no task depends on itself | error |
| `inputFiles`/`outputFiles` refer to declared files | error |
| Execution tasks refer to tasks declared in the specification | error |
| A task's `machines` refer to declared machines | error |
| The workflow graph is acyclic | error |
| Declared [`metrics`](#metrics-property-specification) agree with the instance data | error |
| `parents` and `children` describe the same set of edges | warning |
| A file is declared but used by no task, or a task has no execution entry | warning |
| A dependency or file is declared more than once | warning |
| A `format` annotation is violated (e.g., a malformed timestamp) | warning |

Semantic validation is skipped for an instance that already has schema errors,
since the structure it relies on cannot be trusted.

### Migration

`tools/wfcommons-migrate-instance.py` upgrades instances from any version in
1.0–1.5 to the current version, applying each intermediate migration step in
sequence. It accepts either a single JSON file or a directory, which it walks
recursively, migrating every `.json` file it finds.

```
usage: wfcommons-migrate-instance.py [-h] [-n] [-b] [-d] INSTANCE_FILE_OR_FOLDER

  -n, --dry-run   Report what would be migrated without writing any file
  -b, --backup    Keep the original instance as <INSTANCE_FILE>.bak
  -d, --debug     Print debug messages to stderr
```

**Instance files are rewritten in place** (pretty-printed with a 4-space
indent); use `--dry-run` to preview a run and `--backup` to keep the originals.
Instances already at version 1.6 are left untouched rather than reformatted.

When given a folder, every `.json` file is processed independently: files that
are not WfFormat instances, and files whose `schemaVersion` is unrecognized, are
skipped with a message, and a file that cannot be read or migrated is reported
without interrupting the run. The final summary counts each outcome, and the
exit status is non-zero if any file failed.

### Metrics

`tools/wfcommons-add-metrics-to-instance.py` computes the optional
[specification](#metrics-property-specification) and
[execution](#metrics-property-execution) metrics for an instance that is already
at version 1.6 or later, and writes out an instance containing them.

```
usage: python3 wfcommons-add-metrics-to-instance.py input.json [output.json]
```

If `output.json` is omitted, the input file is overwritten in place. The DAG
metrics are computed with a level-by-level topological traversal (linear in the
number of tasks and edges), and the script raises an error if it detects
duplicate task IDs, dangling child references, or a cycle.

Two current limitations to be aware of:

- The script expects `workflow.specification.files` to be present, even though
  the schema makes it optional.
- On an instance with no `workflow.execution` section, the output file is
  written as `null`, destroying the input when run in place. Pass an explicit
  output path when working with specification-only instances.

---

## License

This project is licensed under the terms of the
[GNU Lesser General Public License v3.0](LICENSE).
