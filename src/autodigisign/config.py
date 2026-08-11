import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ConfigurationError(ValueError):
    """Raised when an AutoDigiSign configuration file is incomplete or invalid."""


@dataclass(frozen=True)
class ProjectPaths:
    credentials: Path
    employee_list: Path
    email_config: Optional[Path]


@dataclass(frozen=True)
class CredentialsSettings:
    username: str
    password: str
    pincode: str


def resolve_project_paths(project_root):
    """Resolve the documented project paths without recursively guessing files."""
    project_root = Path(project_root).resolve()
    credentials = project_root / 'inputs' / 'configs' / 'credentials.ini'
    employee_list = project_root / 'inputs' / 'employee_list.txt'
    email_config = project_root / 'inputs' / 'configs' / 'email_config.ini'

    missing_paths = [
        path for path in (credentials, employee_list) if not path.is_file()
    ]
    if missing_paths:
        missing_display = ', '.join(str(path) for path in missing_paths)
        raise FileNotFoundError(
            f"Required AutoDigiSign input file was not found: {missing_display}"
        )

    if email_config.exists() and not email_config.is_file():
        raise ConfigurationError(
            f"Optional email configuration path is not a file: {email_config}"
        )

    return ProjectPaths(
        credentials=credentials,
        employee_list=employee_list,
        email_config=email_config if email_config.is_file() else None,
    )


def _read_config(config_path):
    config_path = Path(config_path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file was not found: {config_path}")

    config = configparser.ConfigParser()
    try:
        loaded_files = config.read(config_path, encoding='utf-8-sig')
    except (configparser.Error, OSError) as error:
        raise ConfigurationError(
            f"Could not read configuration file {config_path}: {error}"
        ) from error
    if not loaded_files:
        raise ConfigurationError(
            f"Could not read configuration file: {config_path}"
        )
    return config


def _required_value(config, section, option, config_path, strip=True):
    if not config.has_section(section):
        raise ConfigurationError(
            f"Missing [{section}] section in {config_path}."
        )
    if not config.has_option(section, option):
        raise ConfigurationError(
            f"Missing {section}.{option} in {config_path}."
        )

    value = config.get(section, option)
    normalized_value = value.strip() if strip else value
    if not normalized_value:
        raise ConfigurationError(
            f"Configuration value {section}.{option} is empty in {config_path}."
        )
    return normalized_value


def load_credentials_settings(credentials_path):
    """Load and validate portal credentials and the medical-card PIN."""
    credentials_path = Path(credentials_path)
    config = _read_config(credentials_path)

    username = _required_value(
        config,
        'credentials',
        'username',
        credentials_path,
    )
    password = _required_value(
        config,
        'credentials',
        'password',
        credentials_path,
        strip=False,
    )
    pincode = _required_value(
        config,
        'credentials',
        'pincode',
        credentials_path,
    )

    return CredentialsSettings(
        username=username,
        password=password,
        pincode=pincode,
    )
