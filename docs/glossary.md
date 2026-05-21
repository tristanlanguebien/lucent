## Glossary

### Field
A small unit of text within a template. Each field represents a variable 
part of the convention and may or may not follow a specific Rule.

### Rule
Defines the allowed structure of a field. A Rule is built around a regular
expression pattern that specifies which values are considered valid.

### Rules
A collection of Rule objects that describe all valid fields within the Codex.
Rules are shared across all Conventions.

### Convention
Describes a concrete naming pattern that combines multiple fields into a
single template. Each Convention references one or more Rules to validate
its fields and can also include fixed values.

### FixedFields
A set of constant field values. These values are checked when parsing and
enforced when formatting, ensuring specific fields always retain
predetermined content.

### Conventions
A registry of all Convention objects within the Codex.

### Codex
The top-level container that brings together all Rules and Conventions.
It defines a complete naming framework capable of validating, resolving,
and managing naming conventions.