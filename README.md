[![DOI](https://zenodo.org/badge/252368853.svg)](https://zenodo.org/badge/latestdoi/252368853)&nbsp;&nbsp;
[![GitHub Release](https://img.shields.io/github/release/wfcommons/wfformat/all.svg)](https://github.com/wfcommons/wfformat/releases)

<a href="https://wfcommons.org" target="_blank"><img src="https://wfcommons.org/images/wfcommons-horizontal.png" width="350" /></a>

# WfFormat: The WfCommons JSON Schema

- Current schema version: `1.5`
- Schema file: `wfcommons-schema.json`
- Schema validator: `wfcommons-validator.py` (see documentation at the end of this file)

## Documentation

This documentation provides an overview of the WfCommons JSON schema. Although this documentation attempts to cover all aspects of the schema, we strongly recommend the use of a JSON schema validator before using your own workflow execution instances or workflow descriptions. Required properties are identified with a marked checkbox symbol.

---

## General Instance Properties

- [x] `name`: Representative name for the instance name.
- [ ] `description`: A concise description of the instance. It should aid researchers to understand the purpose of the execution.
- [ ] `createdAt`: Schema creation date in the [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601) format (e.g., `2020-03-20T15:19:28-08:00`).
- [x] `schemaVersion`: Version of the schema from an enumerate.
- [ ] [`runtimeSystem`](#runtime-system-property): An `object` to describe the runtime system used to execute the workflow.
- [x] [`workflow`](#workflow-property): An `object` to describe the workflow characteristics and performance metrics.
- [ ] [`author`](#author-property): An `object` to describe the author/institution who created/generated the instance.

## Runtime System Property

The **`runtimeSystem`** property documents the runtime system used to run the workflow. It has the following sub-properties:

- [x] `name`: runtime system name.
- [x] `version`: runtime system version.
- [ ] `url`: URL for the main runtime system website.

## Workflow Property

The **`workflow`*** property is the **core** element of the instance file. It contains the workflow structure (tasks, depenencies, and files), as well as task characteristics and performance information. It is composed by the following sub-properties:

- [x] [`specification`](#specification-property): Workflow specification (does not contain any execution information).
- [ ] [`execution`](#execution-property): Workflow execution information.

### Specification Property

- [x] [`tasks`](#tasks-property-specification): List of workflow tasks.
- [ ] [`files`](#files-property-specification): List of workflow files.

#### Tasks Property (Specification)

This property lists all tasks of the workflow describing their relationships and file dependencies. Each task is described as an `object` with 5 properties:

- [x] `name`: Task name (often set to the name of the program executed by a task or to some notion of task type or category).
- [x] `id`: Unique task ID (e.g., ID0000001).
- [x] `parents`: List of parent tasks (reference to other workflow tasks by their `id`).
- [x] `children`: List of children tasks (reference to other workflow tasks by their `id`).
- [ ] `inputFiles`: List of the input file IDs
- [ ] `outputFiles`: List of output file IDs

#### Files Property (Specification)

This property lists all data files in the workflow that are used as input/output by tasks. Each file is described as an `object` with 2 properties:

- [x] `id`: Unique file ID (e.g., a file name, a path, an arbitrary string)
- [x] `sizeInBytes`: File size in bytes

### Execution Property

- [x] `makespanInSeconds`: Workflow overall execution time in _seconds_.
- [x] `executedAt`: Workflow start timestamp in the [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601) format (e.g., `2020-04-01T15:10:53-08:00`).
- [x] `tasks`: List of workflow tasks.
- [ ] [`machines`](#machines-property-execution): List of compute machines used for running the workflow tasks.

#### Tasks Property (Execution)

This property lists all tasks of the workflow describing their characteristics and performance metrics. Each task is described as an `object` property and is composed of 11 properties:

- [x] `id`: Task unique ID (e.g., ID0000001).
- [x] `runtimeInSeconds`: Task runtime in _seconds_.
- [ ] `executedAt`: Task start timestamp in the [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601) format (e.g., `2020-04-01T15:10:53-08:00`).
- [ ] [`command`](#command-property-execution): An `object` to describe the task’s command.
- [ ] `coreCount`: Number of cores required by the task, possibly fractional (e.g., `1.5`).
- [ ] `avgCPU`: Average CPU utilization in % (e.g, `93.78`).
- [ ] `readBytes`: Total bytes read.
- [ ] `writtenBytes`: Total bytes written.
- [ ] `memoryInBytes`: Memory (resident set) size of the process in bytes.
- [ ] `energyInKWh`: Total energy consumption in kWh.
- [ ] `avgPowerInW`: Average power consumption in W.
- [ ] `priority`: Task priority as an _integer_ value.
- [ ] `machines`: List of node names of machines on which the task executed.

##### Command Property (Execution)

The **`command`** property describes the program and arguments used by a task. It is composed of the following properties:

- [ ] `program`: Program name.
- [ ] `arguments`: List of task arguments.

#### Machines Property (Execution)

The **`machines`** property lists all different machines that were used for workflow tasks execution. It is composed of the following properties:

- [ ] `system`: Machine system (`linux`, `macos`, `windows`).
- [ ] `architecture`: Machine architecture (e.g., `x86_64`).
- [x] `nodeName`: Machine node name.
- [ ] `release`: Machine release.
- [ ] `memoryInBytes`: Total RAM memory in bytes.
- [ ] [`cpu`](#cpu-property-execution): An `object` to describe the machine's CPU information.

##### CPU Property (Execution)

The **`cpu`** property describes the used  CPUs. It has the following sub-properties:

- [ ] `coreCount`: Number of CPU cores - supports fractions of cores expressed as float numbers.
- [ ] `speedInMHz`: CPU speed in MHz.
- [ ] `vendor`: CPU vendor.

## Author Property

The **`author`** property should contain the contact information about the person or team who created the instance. It is composed of the following properties:

- [x] `name`: Author name.
- [x] `email`: Author email.
- [ ] `institution`: Author institution.
- [ ] `country`: Author country (preferably country code, [ISO ALPHA-2 code](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2).

---

## Validator

WfCommons provides a Python-based instance validator script for verifying the
syntax of JSON instance files, as well as their semantics, e.g., whether all files
and parents IDs refer to valid entries.

**Prerequisite:** The validator script requires the Python's `jsonschema` and
`requests` modules, which can be installed as follows:

```
$ pip install jsonschema
$ pip install requests
```

The validator script signature is defined as follows:

```
usage: wfcommons-validator.py [-h] [-s SCHEMA_FILE] [-d] JSON_FILE

Validate JSON file against wfcommons-schema.

positional arguments:
  JSON_FILE       JSON instance file

optional arguments:
  -h, --help      show this help message and exit
  -s SCHEMA_FILE  JSON schema file
  -d, --debug     Print debug messages to stderr
```
