# Extractor plugins

VeriCorpus exposes an alpha third-party extractor interface so engines do not need to be merged into the core package.

## Interface

Implement an object with a stable `name` and an `extract(page, page_number, *, dpi=300)` method that returns `vericorpus.models.Candidate`.

```python
from vericorpus.models import Candidate

class MyExtractor:
    name = "my_extractor"

    def extract(self, page, page_number, *, dpi=300):
        text = "..."
        return Candidate(engine=self.name, text=text, confidence=0.9)
```

Register it in your package metadata under the `vericorpus.extractors` entry-point group:

```toml
[project.entry-points."vericorpus.extractors"]
my_extractor = "my_package:MyExtractor"
```

VeriCorpus discovers installed entry points at runtime. Plugin failures are converted into local error evidence and do not stop the whole corpus run.

## Compatibility

This plugin interface is alpha in the 0.x line. Breaking changes require an RFC and will be documented before the stable 1.0 API.
