"""
This file is a configuration example for Lucent. It goes over everything you need to know to
use Lucent effectively.
"""

from pathlib import Path

from lucent import Codex, Convention, Conventions, Rule, Rules
from lucent.errors import LucentParseError


# First, let's define a set of Rules.
# A Rule defines the allowed structure of a field, using a regular expression.
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


# Now, let's define the Conventions.
# A Convention describes a template that can be resolved by providing field values.
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


# Finally, let's wrap everything into the Codex.
# The Codex is the top-level container that brings together all Rules and Conventions,
# and exposes methods for parsing and formatting.
class MyCodex(Codex):
    # This notation may look redundant, but it is required for proper auto-completion.
    convs: MyConventions = MyConventions()
    rules: MyRules = MyRules()


# A Codex instance can be created at the module level so it can be used throughout your project.
# Conventions use caching to improve performance, so avoid creating multiple instances of your Codex
codex = MyCodex()


def example_format_convention():
    # Format a Convention
    fields = {"project": "myAwesomeProject", "asset": "bob01", "type": "character"}
    result = codex.convs.asset_dir.format(fields)
    print(result)
    # >>> D:/projects/myAwesomeProject/library/character/bob01


def example_fixed_fields():
    # Note that fixed fields are automatically filled.
    # In this example, "type" is incorrect, and "extension" was omitted.
    fields = {
        "project": "myAwesomeProject",
        "asset": "hammer01",
        "type": "character",  # should be "prop"
        "version": "001",
    }
    result = codex.convs.prop_maya_file.format(fields)
    print(result)
    # >>> D:/projects/myAwesomeProject/library/env/hammer01/hammer01_v001.ma


def example_solve():
    # Solve a string to identify the Convention and extract fields.
    my_string = "|assets|character|character_littleGirl06"
    conv, fields = codex.solve(string=my_string)
    print(conv.name)
    # >>> maya_asset_dag_path

    print(fields)
    # >>> {'type': 'character', 'asset': 'littleGirl06'}


def example_solve_conv_and_fields():
    # Alternatively, you can use the get_fields() and get_convention() methods.
    path = "D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma"
    fields = codex.get_fields(path)
    conv = codex.get_convention(path)
    print(conv.name)
    # >>> asset_maya_file

    print(fields)
    # >>> {'project': 'myAwesomeProject', 'type': 'fx', 'asset': 'sparks01', 'version': '035', 'extension': 'ma'}


def example_transmute():
    # Let's now see how to convert one string/path into another.
    source = "D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma"
    result = codex.transmute(source, fields={"version": "042"})
    print(result)
    # >>> D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v042.ma

    result = codex.transmute(source, target_convention=codex.convs.maya_asset_dag_path)
    print(result)
    # >>> |assets|fx|fx_sparks01


def example_path_objects():
    # Please note that all methods involving formatting support Path objects, but will always return a string.
    # Under the hood, Lucent converts paths into posix, so it is heavily advised to
    # only use forward slashes in your Conventions
    path = Path("D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma")
    try:
        codex.transmute(str(path), target_convention=codex.convs.maya_asset_dag_path)
        # >>> Will fail on windows, because WindowsPath use backwards slashes
    except LucentParseError as err:
        print(err)

    result = codex.transmute(path, target_convention=codex.convs.maya_asset_dag_path)
    print(result)
    # >>> Will work fine, because Lucent properly uses forward slashes under the hood


def example_increment():
    # An increment method is available out of the box.
    source = Path("D:/projects/myAwesomeProject/library/fx/sparks01/sparks01_v035.ma")
    result = codex.increment(source, field_to_increment="version")
    print(result)
    # >>> D:\projects\myAwesomeProject\library\fx\sparks01\sparks01_v036.ma


def example_file_discovery():
    # Conventions can also be used to search for files.
    paths = codex.convs.asset_dir.get_paths()

    # Sorting methods are available out of the box
    paths = codex.convs.asset_dir.get_paths_sorted_by_date()

    # It’s also possible to provide a custom callback to sort the results as you like.
    def sort_callback(paths):
        return sorted(paths, key=lambda x: codex.get_fields(x)["asset"])

    paths = codex.convs.asset_dir.get_paths(sort_callback=sort_callback)


def example_field_generators():
    # A couple of field generators are here to help you
    fields = {"item_name": "spoon"}
    fields.update(codex.get_uuid_field())
    fields.update(codex.get_datetime_fields())
    result = codex.convs.unique_id_with_datetime.format(fields)
    print(result)
    # >>> spoon_2025_11_07_16_43_01_570dab8a1005421bac4091a8eff1a3ae


def example_rule_match():
    # Rule objects also have a couple of useful methods
    rule = codex.rules.asset
    string = "hello world"
    if not rule.match(string):
        print(rule.get_mismatch_message(string))


def example_convention_representations():
    # You can also use Conventions to generate patterns and examples.
    print(codex.convs.asset_maya_file.human_readable_pattern())
    # >>> D:/projects/{project}/library/{type}/{asset}/{asset}_v{version}.ma
    print(codex.convs.asset_maya_file.glob_pattern())
    # >>> D:/projects/*/library/*/*/*_v*.ma
    print(codex.convs.asset_maya_file.human_readable_example_pattern())
    # >>> D:/projects/mySuperProject/library/prp/peach00/peach00_v001.ma
    print(codex.convs.asset_maya_file.generate_examples(num=2))
    # >>> [
    #         'D:/projects/mySuperProject/library/chr/cassie05/cassie05_v003.ma',
    #         'D:/projects/mySuperProject/library/env/redApple01/redApple01_v002.ma'
    #     ]
    print(codex.convs.asset_maya_file.regex_pattern)
    # >>> ^D:/projects/(?P<project_0>[a-zA-Z]+)/library/(?P<type_0>[a-z]+)/(?P<asset_0>([a-z]+)([A-Z][a-z]*)*(\d{2}))/(?P<asset_1>([a-z]+)([A-Z][a-z]*)*(\d{2}))_v(?P<version_0>\d{3}).(?P<extension_0>ma)$


def example_codex_summary():
    print(codex.human_readable)
    # >>>  Lucent Configuration:

    # Rules:
    # - asset    : "([a-z]+)([A-Z][a-z]*)*(\d{2})"
    # - default  : "[a-zA-Z0-9]+"
    # - episode  : "ep\d{3}"
    # - extension: "[a-zA-Z0-9]+"
    # - frame    : "\d{4}|#{4}|%04d"
    # - group    : "[a-z]+"
    # - project  : "[a-zA-Z]+"
    # - season   : "s\d{3}"
    # - sequence : "sq\d{3}"
    # - shot     : "sh\d{4}[A-Z]?"
    # - type     : "[a-z]+"
    # - version  : "\d{3}"

    # Conventions:
    # - project_root           : "D:/projects/{project}"
    # - library_dir            : "D:/projects/{project}/library"
    # - asset_dir              : "D:/projects/{project}/library/{type}/{asset}"
    # - asset_publish_file     : "D:/projects/{project}/library/{type}/{asset}/publish/v{version}/someSubdir/{asset}_v{version}.{extension}"
    # - asset_maya_file        : "D:/projects/{project}/library/{type}/{asset}/{asset}_v{version}.{extension}"
    # - prop_maya_file         : "D:/projects/{project}/library/{type}/{asset}/{asset}_v{version}.{extension}"
    # - user_dir               : "D:/projects/{project}/users/{$USERNAME}"
    # - say_hello              : "Hello {friend}, my name is {$USERNAME}"
    # - api_route              : "https://api.example.com/{project}/{asset}"
    # - unique_id_with_datetime: "{item_name}_{year}_{month}_{day}_{hour}_{min}_{sec}_{uuid}"
    # - database_query         : "{{"asset_name": "asset"}}"
    # - maya_asset_dag_path    : "|assets|{type}|{type}_{asset}"


def main():
    example_format_convention()
    example_fixed_fields()
    example_solve()
    example_solve_conv_and_fields()
    example_transmute()
    example_path_objects()
    example_increment()
    example_file_discovery()
    example_field_generators()
    example_rule_match()
    example_convention_representations()
    example_codex_summary()


if __name__ == "__main__":
    main()
