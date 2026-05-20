## Requirements
- Python >= 3.9

Note: The new type annotation syntax was introduced in Python 3.9 (PEP 585), and while there is no plan for removal
at the moment, using modern annotations is more future-proof.

## Installation
Use your preferred package installer:

=== "pip"
    ```pip install lucent-codex```

=== "uv"
    ```uv add lucent-codex```

=== "poetry"
    ```poetry add lucent-codex```

## Quick Start

To try it quickly, Lucent provides an example configuration for testing purposes:

```python
from lucent.lucent_example_config import codex

print(codex.convs.asset_maya_file.human_readable_pattern())
```