## Creating your own configuration file

Create a new module `lucent_config.py` :memo:

??? question "Why a `.py` configuration file?"
    Lucent uses a Python file for configuration to enable syntax highlighting and autocompletion, which is helpful when you manage hundreds of naming conventions.

    Also, storing everything in a single object enables caching, which can improve performance.

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
    asset = Rule(
        r"([a-z]+)([A-Z][a-z]*)*(\d{2})",
        examples=["peach00", "redApple01", "philip02", "cassie05"]
    )
    type = Rule(r"[a-z]+", examples=["prop", "character", "environment"])
    group = Rule(r"[a-z]+", examples=["main", "secondary", "tertiary"])
    season = Rule(r"s\d{3}", examples=["s001"])
    episode = Rule(r"ep\d{3}", examples=["ep001"])
    sequence = Rule(r"sq\d{3}", examples=["sq001"])
    shot = Rule(r"sh\d{4}[A-Z]?", examples=["sh0010", "sh0010A"])
    version = Rule(r"\d{3}", examples=["001", "002", "003"])

    # Rules are basically regular expressions with extra features. Get creative!
    frame = Rule(r"\d{4}|#{4}|%04d", examples=["0001", "####", "%04d"])
```

!!! success "Recommended"
    The default value we recommend is letters and digits, mainly to exclude special characters and spaces, which are known to cause issues in paths and across multiple DCCs.

!!! warning "Not Recommended"
    Avoid characters universally understood as separators like `_`, `-` or `.`: you will risk making fields detection quite complicated.

    ??? question "What if I need separators within a field?"
        We recommend using:

        - camelcase (`exampleOfMultiPartField`)
            or
        - kebabcase (`example-of-multi-part-field`)
        
        in conjunction with being very strict about what are considered field separators (for instance, having `_` as your universal separator).

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
    asset_maya_file = Convention(
        "{@asset_dir}/{asset}_v{version}.{extension}",
        fixed_fields={"extension": "ma"}
    )
    asset_publish_file = Convention(
        "{@asset_dir}/publish/v{version}/someSubdir/{asset}_v{version}.{extension}",
        fixed_fields={"extension": "ma"}
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