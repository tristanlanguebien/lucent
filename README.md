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


## Requirements
- Python >= 3.9

Note: The new type annotation syntax was introduced in Python 3.9 (PEP 585), and while there is no plan for removal
at the moment, using modern annotations is more future-proof.

## Installation
Use your preferred package installer:

```pip install lucent-codex```

```uv add lucent-codex```

```poetry add lucent-codex```

To try it quickly, Lucent provides an example configuration for testing purposes:

```python
from lucent.lucent_example_config import codex

print(codex.convs.asset_maya_file.human_readable_pattern())
```

## Creating your own configuration file

Create a new module `lucent_config.py`

💡 Lucent's configuration is done with a python file to allow for syntax highlighting and autocompletion, which becomes handy when you start to manage hundreds of naming conventions.

### Rules

First, let's define a set of Rules.

A Rule defines the allowed structure of a field, using a regular expression.

```python
from lucent import Rule, Rules, Convention, Conventions, Codex

class MyRules(Rules):
    # The default Rule is mandatory. In this example, only letters and numbers are allowed.
    default = Rule(r"[a-zA-Z0-9]+")

    # To help the end user, you can provide examples (they will appear in error messages).
    extension = Rule(r"[a-zA-Z0-9]+", examples=["mp3", "png", "mov"])

    # Here are a few more simple examples.
    project = Rule(r"[a-zA-Z]+", examples=["mySuperProject"])
    asset = Rule(r"([a-z]+)([A-Z][a-z]*)*(\d{2})", examples=["peach00", "redApple01", "philip02", "cassie05"])
    type = Rule(r"[a-z]+", examples=["prop", "character", "environment"])
    group = Rule(r"[a-z]+", examples=["main", "secondary", "tertiary"])
    season = Rule(r"s\d{3}", examples=["s001"])
    episode = Rule(r"ep\d{3}", examples=["ep001"])
    sequence = Rule(r"sq\d{3}", examples=["sq001"])
    shot = Rule(r"sh\d{4}[A-Z]?", examples=["sh0010", "sh0010A"])
    version = Rule(r"\d{3}", examples=["001", "002", "003"])

    # Rules are basically regular expressions with extra features. Feel free to get creative.
    frame = Rule(r"\d{4}|#{4}|%04d", examples=["0001", "####", "%04d"])
```

### Conventions
Now, let's define the Conventions.

A Convention is a basically a template made up of fields, environment variables and... other Conventions.
```python

class MyConventions(Conventions):
    # Here's a simple Convention with a field.
    project_root = Convention("D:/projects/{project}")

    # A Convention can reference other Conventions.
    library_dir = Convention("{@project_root}/library")
    asset_dir = Convention("{@library_dir}/{type}/{asset}")

    # Some fields can be fixed. In this example, files ending with '.mp4' will not match,
    # and the template can be formatted without providing an extension field.
    asset_maya_file = Convention("{@asset_dir}/{asset}_v{version}.{extension}", fixed_fields={"extension": "ma"})
    asset_publish_file = Convention(
        "{@asset_dir}/publish/v{version}/someSubdir/{asset}_v{version}.{extension}", fixed_fields={"extension": "ma"}
    )

    # Fixed fields can also be used to add extra constraints to an existing Convention.
    prop_maya_file = Convention("{@asset_maya_file}", fixed_fields={"type": "prop"})

    # Conventions may also use environment variables.
    user_dir = Convention("{@project_root}/users/{$USERNAME}")

    # Be creative, Lucent can be used for more than just paths!
    # Just be careful with characters that need to be escaped.
    say_hello = Convention("Hello {friend}, my name is {$USERNAME}")
    database_query = Convention('{{"asset_name": "asset"}}')
    maya_asset_dag_path = Convention("|assets|{type}|{type}_{asset}")
    unique_id_with_datetime = Convention("{item_name}_{year}_{month}_{day}_{hour}_{min}_{sec}_{uuid}")
    api_route = Convention("https://api.example.com/{project}/{asset}")
```

### Codex
Finally, let's wrap everything into the Codex.

The Codex is the top-level container that brings together all Rules and Conventions,
and exposes methods for parsing, formatting, file discovery, and much more.

```python
class MyCodex(Codex):
    # This notation may look redundant, but it is required for proper auto-completion.
    convs: MyConventions = MyConventions()
    rules: MyRules = MyRules()

# A Codex instance can be created at the module level so it can be used throughout your project.
# Conventions use caching to improve performance, so avoid creating multiple instances of your Codex
codex = MyCodex()
```

Congratulations, your codex is ready to use!
```python
from lucent_config import codex
codex.solve("D:/projects/myAwesomeProject")
# >>> (Convention(name='project_root', template='D:/projects/{project}', fixed_fields={}), {'project': 'myAwesomeProject'})
```

### Full Code
```python
from lucent import Rule, Rules, Convention, Conventions, Codex


class MyRules(Rules):
    default = Rule(r'[a-zA-Z0-9]+')
    extension = Rule(r'[a-zA-Z0-9]+', examples=['mp3', 'png', 'mov'])
    project = Rule(r'[a-zA-Z]+', examples=['mySuperProject'])
    asset = Rule(r'([a-z]+)([A-Z][a-z]*)*(\d{2})', examples=['peach00', 'redApple01', 'philip02', 'cassie05'])
    type = Rule(r'[a-z]+', examples=['prop', 'character', 'environment'])
    season = Rule(r's\d{3}', examples=['s001'])
    episode = Rule(r'ep\d{3}', examples=['ep001'])
    sequence = Rule(r'sq\d{3}', examples=['sq001'])
    shot = Rule(r'sh\d{4}[A-Z]?', examples=['sh0010', 'sh0010A'])
    version = Rule(r'\d{3}', examples=["001", "002", "003"])
    frame = Rule(r'\d{4}|#{4}|%04d', examples=['0001', '####', '%04d'])


class MyConventions(Conventions):
    project_root = Convention('D:/projects/{project}')
    library_dir = Convention('{@project_root}/library')
    asset_dir = Convention('{@library_dir}/{type}/{asset}')
    asset_maya_file = Convention('{@asset_dir}/{asset}_v{version}.{extension}', fixed_fields={'extension': 'ma'})
    prop_maya_file = Convention('{@asset_maya_file}', fixed_fields={'type': 'prop', 'extension': 'ma'})
    user_dir = Convention('{@project_root}/users/{$USERNAME}')
    say_hello = Convention('Hello {friend}, my name is {$USERNAME}')
    database_query = Convention('{{"asset_name": "asset"}}')
    maya_asset_dag_path = Convention('|assets|{type}|{type}_{asset}')
    unique_id_with_datetime = Convention('{item_name}_{year}_{month}_{day}_{hour}_{min}_{sec}_{uuid}')
    api_route = Convention('https://api.example.com/{project}/{asset}')


class MyCodex(Codex):
    convs: MyConventions = MyConventions()
    rules: MyRules = MyRules()


codex = MyCodex()
```

## Usage

Now that your configuration module is ready, import your Codex:
```python
from lucent_config import codex
```

### Format a Convention
To format a Convention, provide a dictionary that describes the value of each field.
```python
fields = {
    'project': 'myAwesomeProject',
    'asset': 'bob01',
    'type': 'character'
}
print(codex.convs.asset_dir.format(fields))
# >>> D:/projects/myAwesomeProject/library/character/bob01
```

#### Fixed Fields
You can use fixed fields to enforce some values (see fixed_fields in the configuration file).
```python
# In this example, "type" is incorrect, and "extension" was omitted.
fields = {
    "project": "myAwesomeProject",
    "asset": "hammer01",
    "type": "character",  # should be "prop"
    "version": "001",
}
print(codex.convs.prop_maya_file.format(fields))
# >>> D:/projects/myAwesomeProject/library/env/hammer01/hammer01_v001.ma
```

### Solve a String
Let's solve a string to identify the Convention and extract fields.
```python
my_string = '|assets|character|character_littleGirl06'
conv, fields = codex.solve(string=my_string)
print(conv.name)
# >>> maya_asset_dag_path
print(fields)
# >>> {'type': 'character', 'asset': 'littleGirl06'}
```

Alternatively, you can use the get_fields() and get_convention() methods.
```python
path = "D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma"
print(codex.get_fields(path))
# >>> {'project': 'myAwesomeProject', 'type': 'fx', 'asset': 'sparks01', 'version': '035', 'extension': 'ma'}
print(codex.get_convention(path).name)
# >>> asset_maya_file
```

### Transmutation
Let's now see how to convert one string/path into another.

Here is an example to convert a string to the same Convention, but using other values for fields.
```python
source = "D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma"
print(codex.transmute(source, fields={"version": "042"}))
# >>> D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v042.ma
```

And more importantly, here is how to convert from to Convention to another Convention
```python
source = "D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma"
print(codex.transmute(source, target_convention=codex.convs.maya_asset_dag_path))
# >>> |assets|fx|fx_sparks01
```

## About Path objects

Please note that all methods involving formatting and parsing support Path objects, but will always use strings with forward slashes under the hood. Thus, it is heavily advised to only use forward slashes in your Conventions unless you know what you are doing.


For instance, this will fail on windows, because WindowsPath use backwards slashes
```python
from pathlib import Path

path = Path("D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma")
try:
    codex.transmute(str(path), target_convention=codex.convs.maya_asset_dag_path)
except Exception as err:
    print(err)
# >>> The provided string does not match any convention : D:\projects\myAwesomeProject\library\fx\sparks01\sparks01_v035.ma
```

And this will work fine, because Lucent properly uses forward slashes under the hood
```python
from pathlib import Path

path = Path("D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma")
result = codex.transmute(path, target_convention=codex.convs.maya_asset_dag_path)
print(result)
# >>> |assets|fx|fx_sparks01
```

### Incrementation
An increment method is available out of the box.
```python
source = Path("D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma")
print(codex.increment(source, field_to_increment="version"))
# >>> D:\projects\myAwesomeProject\library\fx\sparks01\sparks01_v036.ma
```

## File Search
Conventions can also be used to search for files.
```python
paths = codex.convs.asset_dir.get_paths()
paths = codex.convs.asset_dir.get_paths_sorted_by_date()
```

It’s also possible to provide a custom callback to sort the results as you like.
```python
def sort_callback(paths):
    return sorted(paths, key=lambda x: codex.get_fields(x)["asset"])

codex.convs.asset_dir.get_paths(sort_callback=sort_callback)
```

## Convention/Rule match

Lucent provides methods to quickly check if a string matches a Convention or a Rule

Convention
```python
string = "D:/projects/mySuperProject"
# Using the equality operator
conv = codex.get_convention(string)
print(conv == codex.convs.project_root)
# >>> True

# Using conv.match()
print(codex.convs.asset_dir.match(string))
# >>> False
```

Rule
```python
rule = codex.rules.asset
string = "hello world"
if not rule.match(string):
    print(rule.get_mismatch_message(string))
# >>> The field "hello world" does not respect the rule (asset:"([a-z]+)([A-Z][a-z]*)*(\d{2})")
# >>> Example : peach00, redApple01, philip02, cassie05
```

## Field generators
Lucent has a couple of field generators to help you.
```python
fields = {"item_name": "spoon"}
fields.update(codex.get_uuid_field())
fields.update(codex.get_datetime_fields())
print(codex.convs.unique_id_with_datetime.format(fields))
# >>> spoon_2025_11_07_16_43_01_570dab8a1005421bac4091a8eff1a3ae
```

## Convention Representations
As regular expressions can be a bit daunting for the end user, Lucent provides a few ways to print out Conventions in a more appealing form, and come out with examples

```python
print(codex.convs.asset_maya_file.human_readable_pattern())
# >>> D:/projects/{project}/library/{type}/{asset}/{asset}_v{version}.ma
```

```python
print(codex.convs.asset_maya_file.glob_pattern())
# >>> D:/projects/*/library/*/*/*_v*.ma
```

```python
print(codex.convs.asset_maya_file.human_readable_example_pattern())
# >>> D:/projects/mySuperProject/library/prp/peach00/peach00_v001.ma
```

```python
print(codex.convs.asset_maya_file.generate_examples(num=2))
# >>> ['D:/projects/mySuperProject/library/chr/cassie05/cassie05_v003.ma',
#      'D:/projects/mySuperProject/library/env/redApple01/redApple01_v002.ma']
```

```python
print(codex.convs.asset_maya_file.regex_pattern)
# >>> ^D:/projects/(?P<project_0>[a-zA-Z]+)/library/(?P<type_0>[a-z]+)/(?P<asset_0>([a-z]+)([A-Z][a-z]*)*(\d{2}))/(?P<asset_1>([a-z]+)([A-Z][a-z]*)*(\d{2}))_v(?P<version_0>\d{3}).(?P<extension_0>ma)$
```

```python
print(codex.human_readable)
# >>> Lucent Configuration:

# Rules:
#   - asset    : "([a-z]+)([A-Z][a-z]*)*(\d{2})"
#   - default  : "[a-zA-Z0-9]+"
#   - episode  : "ep\d{3}"
#   - extension: "[a-zA-Z0-9]+"
#   - frame    : "\d{4}|#{4}|%04d"
#   - project  : "[a-zA-Z]+"
#   - season   : "s\d{3}"
#   - sequence : "sq\d{3}"
#   - shot     : "sh\d{4}[A-Z]?"
#   - type     : "[a-z]+"
#   - version  : "\d{3}"

# Conventions:
#   - project_root           : "D:/projects/{project}"
#   - library_dir            : "D:/projects/{project}/library"
#   - asset_dir              : "D:/projects/{project}/library/{type}/{asset}"
#   - asset_maya_file        : "D:/projects/{project}/library/{type}/{asset}/{asset}_v{version}.{extension}"
#   - prop_maya_file         : "D:/projects/{project}/library/{type}/{asset}/{asset}_v{version}.{extension}"
#   - user_dir               : "D:/projects/{project}/users/{$USERNAME}"
#   - say_hello              : "Hello {friend}, my name is {$USERNAME}"
#   - api_route              : "https://api.example.com/{project}/{asset}"
#   - unique_id_with_datetime: "{item_name}_{year}_{month}_{day}_{hour}_{min}_{sec}_{uuid}"
#   - database_query         : "{{"asset_name": "asset"}}"
#   - maya_asset_dag_path    : "|assets|{type}|{type}_{asset}"
```

## Lucent Watcher

lucent_watcher is an extension module for lucent that monitors filesystem events relevant to a Codex.

For more informations, please visit the [lucent_watcher github page](https://github.com/tristanlanguebien/lucent_watcher)

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
and managing names according to the established conventions.

## Acknowledgements
- **Big Company:** while being a personal project, Lucent was tested and improved there, so shoutout to the team!
- **Lucidity team:** The years I've spent working with Lucidity were a great inspiration for Lucent.
- **The VFX/Animation community**