"""Version information for moff-cli."""

import tomllib
from pathlib import Path


def get_version() -> str:
    """Get the version from pyproject.toml.

    Returns:
        The version string from pyproject.toml, or a fallback version if not found.
    """
    try:
        # Get the path to pyproject.toml
        # __file__ is in src/moff_cli/, so we need to go up two levels
        package_root = Path(__file__).parent.parent.parent
        pyproject_path = package_root / "pyproject.toml"

        # Read and parse the TOML file
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Extract version from [project] section
        return data["project"]["version"]
    except (FileNotFoundError, KeyError, tomllib.TOMLDecodeError) as e:
        # Fallback version if we can't read from pyproject.toml
        # This might happen during development or in unusual installation scenarios
        return "0.0.0+unknown"


__version__ = get_version()
