"""
Lucent is a system for defining, validating, and resolving naming conventions.

Lucent holds everything together within a Codex, which contains Conventions
(string templates made up of fields) and Rules (that define how fields should
behave).

## Core Concepts

Field
    A small unit of text within a template. Each field represents a variable
    part of the convention and may or may not follow a specific Rule.

Rule
    Defines the allowed structure of a field. A Rule is built around a regular
    expression pattern that specifies which values are considered valid.

Rules
    A collection of Rule objects that describe all valid fields within the Codex.
    Rules are shared across all Conventions.

Convention
    Describes a pattern that combines multiple fields into a
    single template. A Convention can reference other Conventions and can also include fixed fields.

FixedFields
    A set of constant field values. These values are checked when parsing and
    enforced when formatting, ensuring specific fields always retain
    predetermined value.

Conventions
    A registry of all Convention objects within the Codex.

Codex
    The top-level container that brings together all Rules and Conventions.
    It defines a complete naming framework capable of validating and resolving strings.
"""

from __future__ import annotations

import difflib
import itertools
import logging
import os
import random
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Callable, Optional, Set, Tuple

from lucent.errors import (
    LucentConventionNotFoundError,
    LucentDefaultRuleError,
    LucentFieldValueError,
    LucentFileNotFoundError,
    LucentInconsistentFieldsError,
    LucentMissingEnvironmentVariablesError,
    LucentMissingFieldsError,
    LucentParseError,
    LucentRecursionError,
    LucentRuleNotFoundError,
)


@dataclass
class Rule:
    """
    Defines the allowed structure of a single Field.

    A Rule is centered on a regular expression pattern which is used to
    validate field values.

    Args:
        pattern: Regular expression pattern (string).
        examples: Optional list of example strings that should match the pattern.
    """

    # The name will be automatically filled when initializing the Rules object
    name: str = dataclass_field(default="", init=False)

    # Fill only these
    pattern: str
    examples: list[str] = dataclass_field(default_factory=list[str])

    def __post_init__(self):
        self._normalize_pattern()
        self._verify_examples()

    def _normalize_pattern(self):
        """Remove leading ^ and trailing $ so patterns are normalized internally."""
        self.pattern = self.pattern.lstrip("^").rstrip("$")

    def _verify_examples(self):
        """Verify that provided examples match the pattern; raise ValueError otherwise."""
        if not self.examples:
            return

        for example in self.examples:
            _match = self.match(example)
            if not _match:
                raise ValueError(f"The example does not match the pattern : {example} | {self.pattern}")

    @cached_property
    def _compiled_pattern(self) -> re.Pattern[str]:
        """Return a compiled `re.Pattern` anchored to full match for this Rule."""
        return re.compile(rf"^{self.pattern}$")

    def match(self, string: str, raise_exception: bool = False) -> bool:
        """
        Returns whether or not the provided string respects the Rule

        Args:
            string: The string to match against the compiled pattern.

        Returns:
            bool: True if the pattern matches the beginning of the string, False otherwise.
        """
        result = bool(self._compiled_pattern.match(string))
        if not result and raise_exception:
            raise LucentFieldValueError(self.get_mismatch_message(string))
        return result

    def get_mismatch_message(self, string: str) -> str:
        """
        Returns a human readable message in case of mismatch, and provide examples if examples were provided
        when creating the Rule
        """
        message = f'The field "{string}" does not respect the rule ({self.name}:"{self.pattern}")'
        if self.examples:
            message += f"\nExample : {', '.join(self.examples)}"
        return message


class Rules:
    """
    Collection of Rule objects.
    This class gathers all Rule instances and ensures a default Rule exists (named "default").

    Raises:
        LucentDefaultRuleError: if a "default" Rule is not defined.
    """

    def __init__(self):
        super().__init__()
        self._rule_instances: list[Rule]
        self._register_rules()
        self._check_default()

    def _register_rules(self):
        """
        Register Rule instances so they can be accessed by name.
        """
        self._rule_instances = []
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            rule = getattr(self, attr)
            if isinstance(rule, Rule):
                rule.name = attr
                self._rule_instances.append(rule)

    def _check_default(self):
        """Ensure that a 'default' Rule exists; raise LucentDefaultRuleError if not."""
        if not any([rule.name == "default" for rule in self._rule_instances]):
            raise LucentDefaultRuleError('Please define a "default" rule')

    def get_rule_by_name(self, name: str) -> Rule:
        """Returns the Rule object that matches the provided name"""
        return getattr(self, name)


@dataclass
class Convention:
    """
    A Convention is a pattern made up of Fields, and follows the syntax:
    - {field_name} -> field
    - {@convention} -> reference to another convention
    - {$env_variable} -> environment variable

    Convention instances use Rules to validate the value of each Field
    Convention instances may include FixedFields ensuring specific fields always retain predetermined values

    Args:
        template: Template string
        fixed_fields: Optional mapping of field names to constant values.
    """

    # The name will be automatically filled when initializing the Conventions object
    name: str = dataclass_field(default="", init=False)

    # Fillable at creation
    template: str
    fixed_fields: dict[str, str] = dataclass_field(default_factory=dict[str, str])

    def __post_init__(self):
        self._codex: Codex

    @cached_property
    def expanded_fixed_fields(self) -> dict[str, str]:
        """
        Returns the fixed fields from the Convention, merged with the fixed fields of referenced Conventions
        Returns:
            dict: fully merged fixed_fields
        """
        return self._get_expanded_fixed_fields()

    def _get_expanded_fixed_fields(self) -> dict[str, str]:
        """
        Recursively resolve and merge fixed_fields from referenced Conventions.
        Returns:
            dict: fully merged fixed_fields
        """
        pattern = re.compile(r"{@([a-zA-Z0-9-_]+)}")

        def resolve(convention: Convention, recursion_depth=0):
            if recursion_depth > 30:
                raise LucentRecursionError(f"Too much recursion while resolving fixed_fields ({recursion_depth}).")

            merged = {}

            # Find referenced conventions in template
            for match in pattern.finditer(convention.template):
                reference = match.group(1)

                if reference == convention.name:
                    raise LucentRecursionError(f"A naming convention cannot reference itself: {convention.template}")

                try:
                    parent = self._codex.get_convention_by_name(reference)
                except LucentConventionNotFoundError:
                    raise LucentConventionNotFoundError(
                        f"Reference key '@{reference}' not found from description : {convention}"
                    ) from None

                # Recursively resolve parent first (top -> bottom)
                parent_fields = resolve(parent, recursion_depth + 1)
                merged.update(parent_fields)

            # Then apply current convention fixed_fields (override parents)
            if convention.fixed_fields:
                merged.update(convention.fixed_fields)

            return merged

        return resolve(self)

    def format(self, fields: dict[str, str] | None = None) -> str:
        """
        Format the Convention's template with provided fields.
        FixedFields and environment variables are filled in automatically.

        Args:
            fields: Mapping of field names to values to use when formatting.

        Returns:
            Formatted string.

        Raises:
            LucentMissingFieldsError: if required fields are missing.
            LucentMissingEnvironmentVariablesError: if required environment vars are missing.
            LucentFieldValueError: if any provided field value violates its Rule.
        """
        _fields: dict[str, str] = fields.copy() if fields else {}
        self._check_missing_fields(_fields)
        self._check_missing_environment_variables()
        _fields.update(self.expanded_fixed_fields)
        _fields.update(self.environment_variables_fields)
        _fields = self._fix_integer_fields(_fields)
        self._check_rules(_fields)
        return self.expanded_template.format(**_fields)

    def format_path(self, fields: dict[str, str] | None = None) -> Path:
        """
        Format the template and return a `pathlib.Path` object.

        Args:
            fields: Mapping of field names to values.

        Returns:
            Path object representing the formatted template.
        """
        return Path(self.format(fields))

    def parse(self, string: str | Path) -> dict[str, str]:
        """
        Parse a string according to the Convention.
        Extracted field values are returned as a dict.

        Args:
            string: The string or Path to parse. Please note that lucent uses strings internally,
            so all Path objects are converted to strings with forward slashes.

        Returns:
            dict : Mapping of field names to parsed values.

        Raises:
            LucentParseError: when the string does not match the convention.
            LucentMissingEnvironmentVariablesError: if required environment vars are missing.
            LucentInconsistentFieldsError: if a field appears multiple times with different values.
        """
        if isinstance(string, Path):
            string = string.as_posix()

        # Raise error if there is no match
        match = re.match(self.regex_pattern, string)
        if not match:
            error_message = [f'The provided string does not match the Convention "{self.name}":']
            error_message.append(f"  - string  : {string}")
            error_message.append(f"  - pattern : {self.human_readable_pattern()}")
            error_message.append(f"  - rules   : {self._relevant_rules}")
            raise LucentParseError("\n".join(error_message))

        # On rare occasions, the match can be empty. This is most likely due to characters not being
        # escaped properly, thus messing up the regular expression
        if match.span() == (0, 0):
            error_message = [f'The provided string does not match the Convention "{self.name}":']
            error_message.append(
                "It looks like the regular expression contains errors. Have you escaped special characters ?"
            )
            raise LucentParseError("\n".join(error_message))

        field_values: Defaultdict[str, Set[str]] = defaultdict(set)
        for group, value in match.groupdict().items():
            field = group.rsplit("_", 1)[0]
            field_values[field].add(value)

        error_fields = {field: values for field, values in field_values.items() if len(values) > 1}
        if not error_fields:
            return {field: list(values)[0] for field, values in field_values.items()}

        # Raise explicit error message
        error_message: list[str] = []
        for field, values in error_fields.items():
            error_message.append(f'Inconsistant values for field "{field}" : {values}')
        raise LucentInconsistentFieldsError("\n".join(error_message))

    @cached_property
    def expanded_template(self) -> str:
        """
        Return the template with references to other Conventions resolved.

        References use the {@other_convention} syntax and are expanded recursively.

        Returns:
            Template string with all {@...} references replaced.

        Raises:
            LucentRecursionError: when too much recursion is detected.
            LucentConventionNotFoundError: when a referenced Convention does not exist.
        """
        return self._get_expanded_template()

    def _get_expanded_template(self):
        """
        Internally resolve {@reference} tokens to the referenced Convention.template.

        Returns:
            The fully expanded template string.
        """
        pattern = re.compile(r"{@([a-zA-Z0-9-_]+)}")

        # Cover case where the user mistakenly references itself
        if f"{{@{self.name}}}" in self.template:
            raise LucentRecursionError(f"A naming convention cannot reference itself : {self.template}")

        def resolve(template: str, recursion_depth: int = 0):
            if recursion_depth > 10:
                raise LucentRecursionError(f"Too much recursion while resolving references ({recursion_depth}).")

            while True:
                match = pattern.search(template)
                if not match:
                    break
                reference: str = match.group(1)

                try:
                    convention = self._codex.get_convention_by_name(reference)
                except LucentConventionNotFoundError:
                    raise LucentConventionNotFoundError(
                        f"Reference key '@{reference}' not found from description : {self}"
                    ) from None

                resolved_template = resolve(
                    convention.template,
                    recursion_depth + 1,
                )
                template = template[: match.start()] + resolved_template + template[match.end() :]
            return template

        return resolve(self.template)

    @cached_property
    def required_fields(self) -> list[str]:
        """
        Return fields required to format the template that are not environment variables.

        Returns:
            List of unique field names required by the Convention.
        """
        fields = re.findall(r"\{(?!\$)([a-zA-Z0-9-_]+)\}", self.expanded_template)
        unique_fields: list[str] = []
        for field in fields:
            if field not in unique_fields:
                unique_fields.append(field)
        return unique_fields

    @cached_property
    def all_fields(self) -> list[str]:
        """
        Return all fields appearing in the template.

        Returns:
            List of unique field names (including those used as environment variables).
        """
        fields = re.findall(r"\{([a-zA-Z0-9-_]+)\}", self.expanded_template)
        unique_fields: list[str] = []
        for field in fields:
            if field not in unique_fields:
                unique_fields.append(field)
        return unique_fields

    @cached_property
    def mandatory_fields(self) -> list[str]:
        """
        Return fields the user must provide to format the template.

        Fields covered by fixed_fields are excluded.

        Returns:
            List of mandatory field names.
        """
        return [field for field in self.required_fields if field not in self.expanded_fixed_fields.keys()]

    @cached_property
    def required_environment_variables(self) -> list[str]:
        """
        Return names of environment variables used in the template.

        Environment variables use the {$NAME} syntax.

        Returns:
            List of environment variable names required by this Convention.
        """
        return re.findall(r"\{\$([a-zA-Z0-9-_]+)\}", self.expanded_template)

    @property
    def environment_variables_fields(self) -> dict[str, str]:
        """
        Return a mapping of environment variable placeholders to their values.

        Returns:
            Mapping like {"$VAR": "value"} extracted from the process environment.
        """
        fields: dict[str, str] = {}
        for environment_variable in self.required_environment_variables:
            fields[f"${environment_variable}"] = os.environ[environment_variable]
        return fields

    def human_readable_pattern(self, fields: dict[str, str] | None = None) -> str:
        """
        Produce a human-readable representation of the template with missing fields left
        as placeholders.

        Args:
            fields: Optional mapping used to prefill some fields.

        Returns:
            Formatted, human-readable template string.
        """
        _fields = fields.copy() if fields else {}
        _fields.update(self.environment_variables_fields)
        _fields.update(self.expanded_fixed_fields)
        for missing_field in self._get_missing_fields(_fields):
            _fields[missing_field] = f"{{{missing_field}}}"
        return self.expanded_template.format(**_fields)

    def human_readable_example_pattern(self, fields: dict[str, str] | None = None) -> str:
        """
        Produce a human-readable template where missing fields are replaced by example values
        from their associated Rules when possible.

        Args:
            fields: Optional mapping used to prefill some fields.

        Returns:
            Formatted example pattern.
        """
        _fields = fields.copy() if fields else {}
        _fields.update(self.environment_variables_fields)
        _fields.update(self.expanded_fixed_fields)
        for missing_field in self._get_missing_fields(_fields):
            rule = self._codex.get_rule_by_name(missing_field)
            if rule.examples:
                _fields[missing_field] = rule.examples[0]
            else:
                _fields[missing_field] = f"{{{missing_field}}}"
        return self.expanded_template.format(**_fields)

    def generate_examples(self, fields: dict[str, str] | None = None, num: int = 5):
        """
        Generate up to `num` unique example strings by combining example values
        from Rules for mandatory fields.

        Args:
            fields: Optional mapping to prefill some fields.
            num: Maximum number of distinct examples to generate.

        Returns:
            Either a single human-readable pattern string (if no examples available)
            or a sorted list of generated example strings.
        """
        fields = fields or {}
        field_rules_with_examples = [
            rule
            for rule in self._codex.rules._rule_instances
            if rule.name in self.mandatory_fields and rule.examples and rule.name not in fields
        ]
        if not field_rules_with_examples:
            return [self.human_readable_pattern(fields)]

        # Extract keys and lists
        keys = [rule.name for rule in field_rules_with_examples]
        lists = [rule.examples for rule in field_rules_with_examples]

        # Compute all possible unique combinations and truncate
        all_combos = list(itertools.product(*lists))
        random.shuffle(all_combos)
        combos = all_combos[: min(num, len(all_combos))]

        # Generate fields and solve
        random_fields = [dict(zip(keys, combo)) for combo in combos]
        for _fields in random_fields:
            _fields.update(fields)
        return sorted([self.human_readable_pattern(fields) for fields in random_fields])

    def glob_pattern(self, fields: dict[str, str] | None = None) -> str:
        """
        Produce a glob-style pattern for filesystem lookups where unspecified fields
        are replaced by '*' wildcards.

        Args:
            fields: Optional mapping used to prefill some fields.

        Returns:
            Glob-compatible pattern string.

        Raises:
            LucentFieldValueError: if provided fields violate their Rules.
            LucentMissingEnvironmentVariablesError: if required environment vars are missing.
        """
        _fields = fields.copy() if fields else {}
        self._check_rules(_fields)
        self._check_missing_environment_variables()
        _fields.update(self.expanded_fixed_fields)
        _fields.update(self.environment_variables_fields)
        for field in self._get_missing_fields(_fields):
            _fields[field] = "*"
        return self.expanded_template.format(**_fields)

    def _format_environment_variables(self) -> str:
        """Replace {$VARS} in the expanded template with their environment values."""
        self._check_missing_environment_variables()
        pattern = re.compile(r"\{\$([a-zA-Z0-9-_]+)\}")

        def expand_vars(match: re.Match[str]):
            return os.environ[match.group(1)]

        return pattern.sub(expand_vars, self.expanded_template)

    @cached_property
    def regex_pattern(self) -> str:
        """
        Construct a regular expression that matches the Convention as a whole.
        """

        _fields = {}
        self._check_missing_environment_variables()
        _fields.update(self.expanded_fixed_fields)
        _fields.update(self.environment_variables_fields)
        for field in self._get_missing_fields(_fields):
            rule = self._codex.get_rule_by_name(field, default=True)
            _fields[field] = rule.pattern

        template = self._format_environment_variables()
        field_pattern = re.compile(r"\{([a-zA-Z0-9-_]+)\}")

        # Split template into literal and fields segments
        parts: list[str] = []
        last_pos = 0
        field_counts: defaultdict[str, int] = defaultdict(int)

        for match in field_pattern.finditer(template):
            # Escape literal text before the placeholder
            literal = re.escape(template[last_pos : match.start()])
            parts.append(literal)

            # Append group representing the field
            field = match.group(1)
            count = field_counts[field]
            field_counts[field] += 1
            parts.append(f"(?P<{field}_{count}>{_fields[field]})")
            last_pos = match.end()

        # Add the tail literal part (after last placeholder)
        parts.append(re.escape(template[last_pos:]))

        # Join everything and anchor it
        result = "".join(parts)
        return f"^{result}$"

    def _get_missing_fields(self, fields: dict[str, str]) -> list[str]:
        """Return mandatory fields that are not present in the provided mapping."""
        _fields = [field for field in self.mandatory_fields if field not in fields]
        return list(set(_fields))

    def _check_missing_fields(self, fields: dict[str, str]) -> None:
        """Raise if required fields are missing for formatting."""
        missing_fields = self._get_missing_fields(fields)
        if missing_fields:
            raise LucentMissingFieldsError(
                f"Some of the fields needed to resolve the Convention are missing : {missing_fields}"
            )

    def _check_missing_environment_variables(self) -> None:
        """Raise if required environment variables are not defined."""
        missing = [env for env in self.required_environment_variables if not os.environ.get(env)]
        if missing:
            raise LucentMissingEnvironmentVariablesError(
                f"Some of the environment variables needed to resolve the Convention are missing : {missing}"
            )

    def _fix_integer_fields(self, fields: dict[str, str]) -> dict[str, str]:
        """
        Converts all fields provided as integer, and that can be automatically converted to str (thanks to the Rule that
        relates to the field)
        """
        _fields = fields.copy() if fields else {}
        for key, value in _fields.items():
            if key not in self.required_fields:
                continue
            if isinstance(value, int):
                _fields[key] = self._fix_integer_field(key, value)
        return _fields

    def _fix_integer_field(self, key: str, value: int) -> str:
        """
        Converts the provided integer field into a string, if examples were provided in the related Rule.
        Raises a LucentRuleNotFoundError if the Rule has no example

        Returns:
            string
        """
        rule = self._codex.get_rule_by_name(key, default=False)
        err = LucentRuleNotFoundError(f'Cannot format integer field "{key}" if no rule with examples is provided')
        if not rule:
            raise err
        if not rule.examples:
            raise err
        return str(value).zfill(len(rule.examples[0]))

    def _check_rules(self, fields: dict[str, str]) -> None:
        """
        Validate provided fields against their associated Rules.

        Args:
            fields: Mapping of field names to values.

        Raises:
            LucentFieldValueError: if any value does not match its Rule.
        """
        fields = fields.copy() if fields else {}
        fields = {k: v for k, v in fields.items() if k in self.mandatory_fields}
        for key, value in fields.items():
            # Do not validate environment variables
            if key.startswith("$"):
                continue

            rule = self._codex.get_rule_by_name(key, default=True)
            rule.match(value, raise_exception=True)

    def increment(
        self,
        string: str | Path,
        field_to_increment: str = "version",
        fields_to_enforce: dict[str, str] | None = None,
    ) -> str:
        """
        Increments a field from the provided string (by default, the "version" field)
        Additional fields may be set in the process.

        Args:
            string: string to modify
            field_to_increment: name of the field that needs to be incremented
            fields_to_enforce: additional fields to format

        Raises:
            LucentFieldValueError: if any value does not match its Rule.
        """
        fields_to_enforce = fields_to_enforce or {}
        _fields = self.parse(string)
        value = _fields.get(field_to_increment)
        if not value:
            raise LucentMissingFieldsError(f'The solved string does not have a "{field_to_increment}" field : {string}')

        # Increment value by one
        new_value = str(int(value) + 1).zfill(len(value))

        # Rebuild a new path
        new_fields = _fields.copy()
        new_fields.update(fields_to_enforce)
        new_fields[field_to_increment] = new_value
        result = self.format(new_fields)
        return result

    @cached_property
    def _relevant_rules(self) -> dict[str, str]:
        """
        Return a mapping of rule name -> pattern for all Rules that apply to this Convention.

        The default Rule is always included when relevant.
        """
        rules = {rule.name: rule.pattern for rule in self._codex.rules._rule_instances if rule.name in self.all_fields}
        return rules

    def get_paths(
        self,
        fields: dict[str, str] | None = None,
        sort_callback: Callable[[list[Path]], list[Path]] | None = None,
    ) -> list[Path]:
        """
        Resolve the Convention to a list of filesystem paths using globbing.

        Args:
            fields: Optional mapping to prefill some fields (may include wildcards).
            sort_callback: Optional function to sort the matched paths.

        Returns:
            List of Path objects strictly matching the Convention.
        """
        # Generate a glob pattern from the provided fields
        fields = fields.copy() if fields else {}
        glob_pattern = self.glob_pattern(fields)
        parts = Path(glob_pattern).parts

        src_dir_parts: list[str] = []
        pattern_parts: list[str] = []
        pattern_started = False
        for part in parts:
            if "*" in part:
                pattern_started = True
            if not pattern_started:
                src_dir_parts.append(part)
            else:
                pattern_parts.append(part)
        src_dir_str = "/".join(src_dir_parts)
        pattern_str = "/".join(pattern_parts)
        src_dir = Path(src_dir_str)

        # Get all files that match the glob pattern, which will need to be filtered
        # Do not seach for files if the pattern is fully resolved
        logging.info(f"Searching paths matching : {glob_pattern}")
        if not pattern_str:
            paths = [src_dir] if src_dir.exists() else []
        else:
            paths = list(src_dir.glob(pattern_str))

        # Only keep files that strictly match the convention
        _paths: list[Path] = []
        for path in paths:
            try:
                self.parse(path)
                _paths.append(path)
            except (LucentParseError, LucentMissingEnvironmentVariablesError, LucentInconsistentFieldsError):
                pass

        # Sort paths with the provided callback
        _sort_callback = sort_callback or sort_callback_alphabetical
        _paths = _sort_callback(_paths)
        return _paths

    def get_paths_sorted_by_date(self, fields: dict[str, str] | None = None) -> list[Path]:
        """
        Return matching paths sorted by filesystem modification time.
        """
        return self.get_paths(fields, sort_callback_date)

    def get_last_path(self, fields: Optional[dict[str, str]] = None, order: str = "alphabetical") -> Path:
        """
        Return the last path in the requested ordering.

        Args:
            fields: Optional mapping to prefill some fields.
                    All fields that are not provided will be replaced by wildcards
            order: "alphabetical" or "date".

        Returns:
            Last Path matching the convention.

        Raises:
            LucentFileNotFoundError if no path matches.
        """
        mapping = {
            "alphabetical": self.get_paths,
            "date": self.get_paths_sorted_by_date,
        }
        func = mapping[order]
        paths = func(fields)
        if not paths:
            raise LucentFileNotFoundError(
                f"No path matching the pattern was found : {self.human_readable_pattern(fields)}"
            )
        return paths[-1]

    def show_mismatch(self, string: str, fields: Optional[dict[str, str]] = None):
        """
        Compares the provided string against a ground truth string generated thanks to the provided fields
        """
        if self.match(string):
            logging.info(f"The provided string matches the Convention : {string}")
            return

        ground_truth = self.format(fields=fields)
        logging.info(f"Comparing :\n  - {string}\n  - {ground_truth}")
        matcher = difflib.SequenceMatcher(None, string, ground_truth)
        markers = [" "] * len(string)

        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            if opcode in ("replace", "delete", "insert"):
                if i1 == i2:
                    mark_pos = max(0, i1 - 1) if i1 > 0 else 0
                    markers[mark_pos] = "^"
                else:
                    for i in range(i1, i2):
                        markers[i] = "^"

        marker_str = "".join(markers)
        logging.warning(string)
        logging.warning(marker_str)

    def match(self, string: str | Path) -> bool:
        """Returns whether or not the string matches the template"""
        try:
            self.parse(string=string)
            return True
        except (LucentParseError, LucentInconsistentFieldsError):
            return False


class Conventions:
    """
    Registry class that collects Convention instances defined as attributes.

    When subclassed, any Convention attributes are discovered and their `name`
    attribute is filled with the attribute name.
    """

    def __init__(self):
        super().__init__()
        self._convention_instances: list[Convention]
        self._register_conventions()

    def _register_conventions(self):
        """
        Register Convention instances so they can be accessed by name
        """
        self._convention_instances = []
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            convention = getattr(self, attr)
            if isinstance(convention, Convention):
                convention.name = attr
                self._convention_instances.append(convention)


class Codex:
    """
    Top-level container that binds Rules and Conventions together.

    A Codex injects itself into all registered Convention instances so they
    can resolve references and access the shared Rules.

    Attributes:
        conventions: Class attribute holding the Conventions subclass instance.
        rules: Class attribute holding the Rules subclass instance.
    """

    convs: Conventions
    rules: Rules

    def __init__(self):
        self._inject_self_into_conventions()

    def _inject_self_into_conventions(self):
        """
        Inject this Codex into each Convention so Conventions can access shared rules
        and other Conventions via `self._codex`.
        """
        convention: Convention
        for convention in self.convs._convention_instances:
            convention._codex = self

    def get_convention_by_name(self, name: str) -> Convention:
        """
        Retrieve a registered Convention by name.

        Args:
            name: Name of the Convention to retrieve.

        Returns:
            Convention instance.

        Raises:
            LucentConventionNotFoundError: when the named Convention does not exist.
        """
        try:
            result = getattr(self.convs, name)
        except AttributeError:
            raise LucentConventionNotFoundError(f'No convention named "{name}" was found') from None
        return result

    def get_rule_by_name(self, name: str, default: bool = False) -> Rule:
        """
        Retrieve a Rule by name.

        Args:
            name: Name of the Rule.
            default: When True, return the 'default' Rule instead of raising if not found.

        Returns:
            Rule instance or None (if default is False and not found).

        Raises:
            LucentRuleNotFoundError: when the Rule is not found and default is False.
        """
        try:
            result = getattr(self.rules, name)
        except AttributeError:
            if default:
                return getattr(self.rules, "default")
            else:
                raise LucentRuleNotFoundError(f'No rule named "{name}" was found') from None
        return result

    def solve(
        self, string: str | Path, conventions: list[Convention] | None = None, reverse: bool = False
    ) -> Tuple[Convention, dict[str, str]]:
        """
        Iterates through available Conventions (or a provided subset) and tries to parse the string.
        Returns a tuple containing the matching Convention and the fields deduced from the parsing operation

        Args:
            string: The string to resolve.
            conventions: Optional list of Convention instances to limit search.
            reverse: Whether to iterate conventions in reverse order.

        Returns:
            Tuple containing the matching Convention and the fields deduced from the parsing operation

        Raises:
            LucentParseError: if no Convention matches.
        """
        if isinstance(string, Path):
            string = string.as_posix()

        _conventions = conventions or []
        if not _conventions:
            conventions = self.convs._convention_instances
        else:
            conventions = [convention for convention in self.convs._convention_instances if convention in _conventions]

        # Assuming conventions are written from less to more specific, Codex may be reversed
        # so the function returns the most specific Convention
        if reverse:
            conventions.reverse()

        for convention in conventions:
            try:
                fields = convention.parse(string)
                return convention, fields
            except (LucentParseError, LucentMissingEnvironmentVariablesError, LucentInconsistentFieldsError):
                pass

        if _conventions:
            message = [f"The provided string does not match any of the provided conventions : {string}"]
            message += [f"  - {convention.name}" for convention in _conventions]
            raise LucentParseError("\n".join(message))
        else:
            raise LucentParseError(f"The provided string does not match any convention : {string}")

    def get_fields(
        self, string: str, conventions: list[Convention] | None = None, reverse: bool = True
    ) -> dict[str, str]:
        """
        Parse a string and return its fields.

        Args:
            string: The string to parse.
            conventions: Optional list to limit search.
            reverse: Whether to iterate conventions in reverse order.

        Returns:
            Mapping of field names to values.
        """
        conventions = conventions or []
        _, fields = self.solve(string, conventions, reverse)
        return fields

    def get_convention(
        self, string: str | Path, conventions: list[Convention] | None = None, reverse: bool = True
    ) -> Convention:
        """
        Return the Convention that matches the provided string.

        Args:
            string: The string to resolve.
            conventions: Optional list to limit candidate Conventions.
            reverse: Whether to search in reverse order.

        Returns:
            Convention instance that matched the string.
        """
        conventions = conventions or []
        convention, _ = self.solve(string, conventions, reverse)
        return convention

    def transmute(
        self,
        string: str | Path,
        target_convention: Optional[Convention] = None,
        fields: Optional[dict[str, str]] = None,
        conventions: list[Convention] | None = None,
    ) -> str:
        """
        Parse a string and re-format it using another Convention.

        Args:
            string: Source string to parse.
            target_convention: Convention to format to. If None, the source Convention is reused.
            fields: Optional fields to override parsed values.
            conventions: Optional list to limit candidate Conventions when parsing.

        Returns:
            Reformatted string according to the target Convention.
        """
        fields = fields.copy() if fields else {}
        conventions = conventions or []
        solved_convention, solved_fields = self.solve(string, conventions=conventions)
        convention = target_convention if target_convention else solved_convention
        _fields = solved_fields.copy()
        _fields.update(fields)
        result = convention.format(_fields)
        return result

    def increment(
        self,
        string: str | Path,
        field_to_increment: str = "version",
        fields_to_enforce: Optional[dict[str, str]] = None,
        conventions: list[Convention] | None = None,
        reverse: bool = False,
    ) -> str:
        """
        Increments a field from the provided string (by default, the "version" field)
        Additional fields may be set in the process.

        Args:
            string: string to modify
            field_to_increment: name of the field that needs to be incremented
            fields_to_enforce: additional fields to format
            conventions: Optional list to limit candidate Conventions when parsing.
            reverse: Whether to iterate over conventions in reverse order.

        Returns:
            source string, with a field incremented by one
        """
        conventions = conventions or []
        convention = self.get_convention(string, conventions, reverse)
        result = convention.increment(string, field_to_increment, fields_to_enforce)
        return result

    def get_datetime_fields(self) -> dict[str, str]:
        """Return a mapping of current datetime fields (year, month, day, hour, min, sec)."""
        return get_datetime_fields()

    def get_uuid_field(self) -> dict[str, str]:
        """Return a mapping containing a generated uuid value for the 'uuid' field."""
        return get_uuid_field()

    @cached_property
    def human_readable(self) -> str:
        """Returns a human readable version of the codex, detailing its Rules and Conventions"""
        lines = ["Lucent Configuration:", ""]

        # Rules
        lines += ["Rules:"]
        max_rule_name = max([len(rule.name) for rule in self.rules._rule_instances])
        for rule in self.rules._rule_instances:
            spaces = max_rule_name - len(rule.name)
            spaces = " " * spaces
            lines.append(f'  - {rule.name}{spaces}: "{rule.pattern}"')

        # Conventions
        lines += ["", "Conventions:"]
        sorted_convs = sorted(self.convs._convention_instances, key=lambda x: x.expanded_template)
        max_conv_name = max([len(conv.name) for conv in sorted_convs])
        for conv in sorted_convs:
            spaces = max_conv_name - len(conv.name)
            spaces = " " * spaces
            lines.append(f'  - {conv.name}{spaces}: "{conv.expanded_template}"')
        return "\n".join(lines)


def sort_callback_alphabetical(paths: list[Path]) -> list[Path]:
    """Return matching paths sorted lexicographically."""
    return sorted(paths)


def sort_callback_date(paths: list[Path]) -> list[Path]:
    """Return matching paths sorted by date."""
    return sorted(paths, key=lambda x: os.path.getmtime(x))


def get_datetime_fields() -> dict[str, str]:
    """Return a mapping of datetime values for common fields (year, month, day, hour, min, sec)."""
    now = datetime.now()
    fields: dict[str, str] = {
        "year": now.strftime("%Y"),
        "month": now.strftime("%m"),
        "day": now.strftime("%d"),
        "hour": now.strftime("%H"),
        "min": now.strftime("%M"),
        "sec": now.strftime("%S"),
    }
    return fields


def get_uuid_field() -> dict[str, str]:
    """Return a mapping containing a generated UUID hex string under the 'uuid' key."""
    fields: dict[str, str] = {"uuid": str(uuid.uuid4().hex)}
    return fields
