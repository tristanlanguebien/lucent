# Lucent

Lucent is a system for defining, validating, and resolving naming conventions.

Lucent holds everything together within a Codex, which contains Conventions
(string templates made up of fields) and Rules (that define how fields should
behave).

## Why yet another string formatter?

There are existing solutions mostly used by the 3D animation community (Lucidity being a major influence for Lucent), all of which showed recurring limitations that justified building something new:

- **Added everyday features**: unified field validation, file discovery, cross-pattern conversion, incrementation, overrides, human-readable representations... All methods are available from a single Codex object, no extra code needed.
- **Developer ergonomics**: extra care was taken to make config files easy to write and easy to read, build a structure that allows autocompletion, and provide helpful error messages.
- **Path handling**: treating paths and strings as the same type leads to subtle bugs, since paths have OS-specific behaviors and character restrictions that plain strings don't.
- **Python 3.9+ design**: modern codebases shouldn't have to carry the weight of Python 2.7, especially since the VFX Reference Platform moved to Python 3 years ago.
- **Performance at scale**: individual string parsing is fast, but with hundreds of templates and thousands of files to resolve, unoptimized implementations add up quickly.
