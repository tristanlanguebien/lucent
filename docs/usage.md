# Usage

Now that your configuration module is ready, import your Codex:
```python
from lucent_config import codex
```

## Format a Convention
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

### Fixed Fields
You can use fixed fields to enforce some values (see fixed_fields in the configuration file).
```python
fields = {
    "project": "myAwesomeProject",
    "asset": "hammer01",
    "type": "character",  # should be "prop"
    "version": "001",
}
print(codex.convs.prop_maya_file.format(fields))
# >>> D:/projects/myAwesomeProject/library/env/hammer01/hammer01_v001.ma
```

!!! info
    In this example, `type` is incorrect and `extension` is omitted, but formatting still works thanks to fixed fields.

## Solve a String
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

## Transmutation
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

## Incrementation
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