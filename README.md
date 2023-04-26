[![DOI](https://zenodo.org/badge/252368853.svg)](https://zenodo.org/badge/latestdoi/252368853)


<a href="https://wfcommons.org" target="_blank"><img src="https://wfcommons.org/images/wfcommons-horizontal.png" width="350" /></a>

# WfFormat: The WfCommons JSON Schema

- Current schema version: `1.4`
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
- [ ] `wms`: An `object` to describe the workflow management system (WMS) used to run the workflow.
- [x] `workflow`: An `object` to describe the workflow characteristics and performance metrics.
- [ ] `author`: An `object` to describe the author/institution who created/generated the instance.

## WMS Property

The workflow management system property documents the WMS used to run the workflow. It is composed of the following sub-properties:

- [x] `name`: WMS name.
- [x] `version`: WMS version.
- [ ] `url`: URL for the main WMS website.

## Workflow Property

The workflow property is the **core** element of the instance file. It contains the workflow structure (tasks, depenencies, and files), as well as task characteristics and performance information. It is composed by the following sub-properties:

- [x] `makespanInSeconds`: Workflow turnaround time in _seconds_.
- [x] `executedAt`: Workflow start timestamp in the [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601) format (e.g., `2020-04-01T15:10:53-08:00`).
- [x] `tasks`: Sets of workflow tasks.
- [ ] `machines`: Sets of compute machines used for running the workflow tasks.

### Tasks Property

This property lists all tasks of the workflow describing their characteristics and performance metrics. Each task is described as an `object` property and is composed of 15 properties:

- [x] `name`: Full task ID or name (to be used as references in child/parent tasks).
- [ ] `id`: Task unique ID (e.g., ID0000001).
- [ ] `category`: Task category (can be used, for example, to define tasks that use the same program).
- [x] `type`: Task type (whether it is a `compute`, `transfer`, or an `auxiliary` task).
- [ ] `command`: Task command description.
- [ ] `parents`: List of parent tasks (reference to other workflow tasks, i.e. `name` property above).
- [ ] `files`: Sets of input/output data.
- [ ] `runtimeInSeconds`: Task runtime in _seconds_.
- [ ] `cores`: Number of cores required by the task (e.g., `1.5`).
- [ ] `avgCPU`: Average CPU utilization in % (e.g, `93.78`).
- [ ] `readBytes`: Total bytes read.
- [ ] `writtenBytes`: Total bytes written.
- [ ] `memoryInBytes`: Memory (resident set) size of the process in bytes.
- [ ] `energy`: Total energy consumption in kWh.
- [ ] `avgPower`: Average power consumption in W.
- [ ] `priority`: Task priority as an _integer_ value.
- [ ] `machine`: Node name of machine on which the task was run.

#### Command Property

The command property describes the program and arguments used by a task. The `command` is listed as an `object` property, and is composed of the following properties:

- [ ] `program`: Program name.
- [ ] `arguments`: List of task arguments.

#### Files Property

The files property lists all files used throughout the workflow execution. Each `file` is listed as an `object` property, and is composed of the following properties:

- [x] `name`: A human-readable _unique_ name for the file.
- [x] `sizeInBytes`: File size in bytes.
- [x] `link`: Whether it is an `input` or `output` data.

#### Machines Property

The machines property lists all different machines that were used for workflow tasks execution. It is composed of the following properties:

- [ ] `system`: Machine system (`linux`, `macos`, `windows`).
- [ ] `architecture`: Machine architecture (e.g., `x86_64`).
- [x] `nodeName`: Machine node name.
- [ ] `release`: Machine release.
- [ ] `memoryInBytes`: Total RAM memory in bytes.
- [ ] `cpu`: An `object` to describe the machine's CPU information.

The **`cpu`** property is composed of a `count` (number of CPU cores - supports fractions of cores expressed as float numbers), `speed` (CPU speed in MHz), and `vendor` (CPU vendor) properties.

## Author Property

The author property should contain the contact information about the person or team who created the instance. It is composed of the following properties:

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
