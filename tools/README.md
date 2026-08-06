## Useful scripts

See the [Tools section of the main README](../README.md#tools) for detailed
usage notes and known limitations.

### wfcommons-migrate-instance.py

Script to migrate an instance file from an older WfFormat version (1.0 through
1.5) to the current version, applying each intermediate migration step in
sequence. Accepts a single JSON file or a folder, which is walked recursively.
**Instance files are rewritten in place.** Invoke without command-line arguments
to see usage.


### wfcommons-add-metrics-to-instance.py

Script to augment an instance file with specification and execution metrics,
which were introduced as optional content in WfFormat 1.6. Writes to the given
output file, or overwrites the input file in place if none is given. Invoke
without command-line arguments to see usage.
