---
project: moff-cli
feature: settings
linked_features: [feature_settings.md]
---

# Technical Details

The settings feature provides configuration management for `moff-cli`, handling JSON schema validation, default settings, and configuration merging.

## Dependencies

- `pydantic` - for settings schema validation, data models, and JSON serialization
- `pathlib` (standard library) - for path operations
- `typing` - for type hints and data structures
- `json` (standard library) - for additional JSON operations if needed

# Implementation Details

## Settings Loading Pipeline

```python
from pydantic import ValidationError

def load_settings(root_directory: Path) -> Settings:
    """
    Load settings with pydantic validation and automatic merging.
    """
    settings_path = root_directory / "settings.json"

    # 1. Get defaults
    default_settings = get_default_settings()

    # 2. Check if user settings exist
    if not settings_path.exists():
        # Create default settings.json on first run
        write_settings_file(settings_path, default_settings)
        return default_settings

    # 3. Load user settings with pydantic validation
    try:
        user_data = read_settings_file(settings_path)

        # Merge with defaults
        effective_settings = merge_settings(default_settings, user_data)

        # Additional business logic validation if needed
        validate_settings_business_logic(effective_settings)

        return effective_settings

    except ValidationError as e:
        # Pydantic provides detailed, structured error messages
        raise ValueError(f"Invalid settings in {settings_path}:\n{format_validation_errors(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to load settings: {e}")

def format_validation_errors(error: ValidationError) -> str:
    """Format pydantic validation errors for user-friendly display"""
    errors = []
    for err in error.errors():
        loc = " -> ".join(str(l) for l in err['loc'])
        msg = err['msg']
        errors.append(f"  - {loc}: {msg}")
    return "\n".join(errors)
```

## Data Models

```python
from pydantic import BaseModel, Field, validator, ValidationError
from typing import Dict, List, Optional, Literal, Any
from pathlib import Path

class RootDetection(BaseModel):
    method: Literal["project_file"] = "project_file"
    pattern: str = "project_*.md"

class RootConfig(BaseModel):
    detect: RootDetection = Field(default_factory=lambda: RootDetection())
    override_path: Optional[Path] = None
    ignore: List[str] = Field(default_factory=lambda: ["**/.git/**", "**/.venv/**", "**/node_modules/**"])

class HeaderRule(BaseModel):
    level: int = Field(ge=1, le=6)  # Markdown headers are 1-6
    text: str
    match: Literal["exact", "regex"] = "exact"

    @validator('text')
    def validate_regex_if_needed(cls, v, values):
        if values.get('match') == 'regex':
            import re
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v

class HeaderConfig(BaseModel):
    required: List[HeaderRule] = Field(default_factory=list)
    optional: List[HeaderRule] = Field(default_factory=list)
    order: Literal["strict", "in-order", "any"] = "in-order"

class FrontmatterConfig(BaseModel):
    required: Dict[str, Literal["string", "number", "boolean", "list", "object"]] = Field(default_factory=dict)
    optional: Dict[str, Literal["string", "number", "boolean", "list", "object"]] = Field(default_factory=dict)

class FilenameConfig(BaseModel):
    pattern: str  # e.g., "feature_*.md"

    @validator('pattern')
    def validate_pattern(cls, v):
        if not v.endswith('.md'):
            raise ValueError("Filename pattern must end with .md")
        return v

class PrefixConfig(BaseModel):
    filename: FilenameConfig
    location: Literal["any", "root_only", "subdirs_only"] = "any"
    frontmatter: FrontmatterConfig
    headers: HeaderConfig

class Settings(BaseModel):
    version: int = 1
    root: RootConfig
    prefixes: Dict[str, PrefixConfig]

    @validator('version')
    def validate_version(cls, v):
        if v != 1:
            raise ValueError(f"Unsupported settings version: {v}")
        return v

    class Config:
        # Allow Path objects to be serialized
        json_encoders = {
            Path: str
        }
```

## Default Settings Factory

```python
def get_default_settings() -> Settings:
    """Returns the built-in default settings"""
    return Settings(
        version=1,
        root=RootConfig(
            detect=RootDetection(method="project_file", pattern="project_*.md"),
            override_path=None,
            ignore=["**/.git/**", "**/.venv/**", "**/node_modules/**"]
        ),
        prefixes={
            "project": PrefixConfig(
                filename=FilenameConfig(pattern="project_*.md"),
                location="root_only",
                frontmatter=FrontmatterConfig(
                    required={"project": "string"},
                    optional={}
                ),
                headers=HeaderConfig(
                    required=[
                        HeaderRule(level=1, text="Overview", match="exact")
                    ],
                    optional=[
                        HeaderRule(level=2, text="Requirements", match="exact")
                    ],
                    order="in-order"
                )
            ),
            "feature": PrefixConfig(
                filename=FilenameConfig(pattern="feature_*.md"),
                location="any",
                frontmatter=FrontmatterConfig(
                    required={"project": "string", "feature": "string"},
                    optional={"linked_features": "list"}
                ),
                headers=HeaderConfig(
                    required=[
                        HeaderRule(level=1, text="Overview", match="exact"),
                        HeaderRule(level=2, text="Requirements", match="exact")
                    ],
                    optional=[],
                    order="strict"
                )
            ),
            "tech": PrefixConfig(
                filename=FilenameConfig(pattern="tech_*.md"),
                location="subdirs_only",
                frontmatter=FrontmatterConfig(
                    required={"project": "string"},
                    optional={"feature": "string", "linked_features": "list"}
                ),
                headers=HeaderConfig(
                    required=[
                        HeaderRule(level=1, text="Technical Details", match="exact"),
                        HeaderRule(level=1, text="Implementation Details", match="exact")
                    ],
                    optional=[],
                    order="in-order"
                )
            )
        }
    )
```

## Settings Merging with Pydantic

```python
def merge_settings(defaults: Settings, user_dict: Dict[str, Any]) -> Settings:
    """
    Deep merge user settings with defaults using pydantic's built-in validation.

    Pydantic handles the merging automatically through its parsing.
    Missing fields in user_dict will use the defaults from the model.
    """
    # Convert defaults to dict
    defaults_dict = defaults.dict()

    # Deep merge the dictionaries
    merged_dict = deep_merge(defaults_dict, user_dict)

    # Let pydantic validate and create the merged settings
    try:
        return Settings(**merged_dict)
    except ValidationError as e:
        # Pydantic provides detailed error messages
        raise ValueError(f"Invalid settings: {e}")

def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Recursively merge two dictionaries.

    Args:
        base: The base dictionary (defaults)
        override: The dictionary to merge in (user settings)

    Returns:
        Merged dictionary
    """
    import copy
    result = copy.deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result

# Alternative: Use pydantic's parse_obj with defaults
def load_user_settings(user_dict: Dict[str, Any], defaults: Settings) -> Settings:
    """
    Load user settings with defaults fallback.

    This approach uses pydantic's schema to handle missing fields.
    """
    # Get defaults as dict
    defaults_dict = defaults.dict()

    # Update with user settings (shallow merge for simplicity)
    # For deep merge, use the deep_merge function above
    merged = {**defaults_dict, **user_dict}

    # Parse and validate
    return Settings.parse_obj(merged)
```

## Validation with Pydantic

```python
# With pydantic, most validation is automatic through the model definitions.
# The validators in the models handle validation at parse time.
# Additional business logic validation can be added as needed:

def validate_settings_business_logic(settings: Settings) -> None:
    """
    Additional business logic validation beyond pydantic's type checking.

    Pydantic handles:
    - Type validation (automatic)
    - Enum/Literal validation (automatic)
    - Field constraints (through Field() definitions)
    - Custom validators (through @validator decorators)

    This function adds domain-specific rules if needed.
    """
    # Example: Ensure at least one prefix is defined
    if not settings.prefixes:
        raise ValueError("At least one prefix must be defined")

    # Example: Ensure 'project' prefix exists and is root_only
    if 'project' in settings.prefixes:
        if settings.prefixes['project'].location != 'root_only':
            raise ValueError("Project prefix should be root_only")

    # Most validation is already handled by pydantic's type system
    # and the validators defined in the models
```

## File I/O with Pydantic

```python
import json
from pathlib import Path
from pydantic import ValidationError

def read_settings_file(path: Path) -> Dict[str, Any]:
    """Read and parse settings.json"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in settings file: {e}")
    except IOError as e:
        raise IOError(f"Cannot read settings file: {e}")

def write_settings_file(path: Path, settings: Settings) -> None:
    """Write settings to JSON file using pydantic's JSON serialization"""
    try:
        # Pydantic's json() method handles serialization properly
        json_content = settings.json(indent=2, ensure_ascii=False)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_content)
    except IOError as e:
        raise IOError(f"Cannot write settings file: {e}")

def load_settings_from_file(path: Path) -> Settings:
    """
    Load and validate settings from JSON file using pydantic.

    This combines reading and parsing with validation.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Pydantic validates during parsing
        return Settings.parse_obj(data)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in settings file: {e}")
    except ValidationError as e:
        # Pydantic provides detailed validation errors
        raise ValueError(f"Invalid settings configuration:\n{e}")
    except IOError as e:
        raise IOError(f"Cannot read settings file: {e}")

# Alternative: Use pydantic's parse_file directly
def load_settings_direct(path: Path) -> Settings:
    """Load settings using pydantic's built-in file parsing"""
    try:
        return Settings.parse_file(path)
    except ValidationError as e:
        raise ValueError(f"Invalid settings:\n{e}")
    except Exception as e:
        raise IOError(f"Cannot load settings: {e}")
```

## Integration Points

### With Collector

The collector feature receives the effective Settings object:
```python
def collect_documentation(settings: Settings) -> CollectorOutput:
    # Use settings.root for root detection
    # Use settings.prefixes for file matching
    # Use settings.root.ignore for exclusion patterns
    pass
```

### With Check

The check feature receives the effective Settings object:
```python
def check_documentation(collector_output: CollectorOutput, settings: Settings) -> List[Diagnostic]:
    # Use settings.prefixes for validation rules
    # Match against location, frontmatter, headers
    pass
```

## Error Handling

- **Missing settings.json**: Create with defaults on first run
- **Invalid JSON**: Raise clear error with line/column information
- **Schema violations**: Validate and report specific fields that are invalid
- **Permission errors**: Handle read/write permission issues gracefully
- **Path resolution**: Resolve relative paths relative to root directory

## Performance Considerations

- Cache parsed settings for the duration of the CLI invocation
- Lazy loading: Only parse settings when needed
- Minimal file I/O: Read settings once per invocation
