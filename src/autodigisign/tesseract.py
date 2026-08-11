import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


TESSERACT_VERSION_PATTERN = re.compile(r'\d+(?:\.\d+){1,3}')


class TesseractConfigurationError(RuntimeError):
    """Raised when an installed, working Tesseract executable cannot be found."""


@dataclass(frozen=True)
class TesseractSelection:
    executable_path: Path
    version: str
    source: str


def _subprocess_options(operating_system):
    if operating_system == 'windows':
        return {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)}
    return {}


def get_tesseract_version(executable_path, operating_system):
    """Run Tesseract and return the version reported by the executable."""
    completed = subprocess.run(
        [str(executable_path), '--version'],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
        **_subprocess_options(operating_system),
    )
    version_output = f"{completed.stdout}\n{completed.stderr}"
    first_line = next(
        (line.strip() for line in version_output.splitlines() if line.strip()),
        '',
    )
    if 'tesseract' not in first_line.lower():
        raise TesseractConfigurationError(
            f"Unexpected Tesseract version output: {first_line or '[empty]'}"
        )
    version_match = TESSERACT_VERSION_PATTERN.search(first_line)
    if not version_match:
        raise TesseractConfigurationError(
            f"Tesseract did not report a recognizable version: {first_line}"
        )
    return version_match.group(0)


def _normalize_override(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    return value


def _environment_value(environment, name, operating_system):
    value = environment.get(name)
    if value is not None or operating_system != 'windows':
        return value
    normalized_name = name.casefold()
    for environment_name, environment_value in environment.items():
        if environment_name.casefold() == normalized_name:
            return environment_value
    return None


def _resolve_override(value, environment, operating_system):
    normalized_value = _normalize_override(value)
    if not normalized_value:
        return None
    override_path = Path(normalized_value).expanduser()
    if override_path.is_file():
        return override_path.resolve()
    discovered_path = shutil.which(
        normalized_value,
        path=_environment_value(environment, 'PATH', operating_system),
    )
    if discovered_path:
        return Path(discovered_path).resolve()
    return None


def _known_tesseract_paths(operating_system, environment):
    if operating_system == 'macos':
        return (
            Path('/opt/homebrew/bin/tesseract'),
            Path('/usr/local/bin/tesseract'),
            Path('/opt/local/bin/tesseract'),
        )
    if operating_system == 'windows':
        candidates = []
        local_app_data = _environment_value(
            environment,
            'LOCALAPPDATA',
            operating_system,
        )
        if local_app_data:
            candidates.append(
                Path(local_app_data)
                / 'Programs'
                / 'Tesseract-OCR'
                / 'tesseract.exe'
            )
        for variable_name in ('PROGRAMFILES', 'PROGRAMFILES(X86)'):
            program_files = _environment_value(
                environment,
                variable_name,
                operating_system,
            )
            if program_files:
                candidates.append(
                    Path(program_files) / 'Tesseract-OCR' / 'tesseract.exe'
                )
        return tuple(candidates)
    raise TesseractConfigurationError(
        f"Unsupported operating system for Tesseract detection: {operating_system}"
    )


def _candidate_key(candidate_path, operating_system):
    candidate_text = str(candidate_path)
    if operating_system == 'windows':
        return candidate_text.casefold()
    return candidate_text


def resolve_tesseract(operating_system, environment=None):
    """Find and validate Tesseract using override, PATH, then known locations."""
    environment = dict(os.environ if environment is None else environment)
    configured_command = _environment_value(
        environment,
        'TESSERACT_CMD',
        operating_system,
    )
    if configured_command is not None:
        configured_path = _resolve_override(
            configured_command,
            environment,
            operating_system,
        )
        if configured_path is None:
            raise TesseractConfigurationError(
                "TESSERACT_CMD is set but does not identify an existing "
                f"Tesseract executable: {configured_command}"
            )
        try:
            configured_version = get_tesseract_version(
                configured_path,
                operating_system,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise TesseractConfigurationError(
                "TESSERACT_CMD identifies a file that could not be executed: "
                f"{configured_path}: {type(error).__name__}: {error}"
            ) from error
        return TesseractSelection(
            configured_path,
            configured_version,
            'TESSERACT_CMD',
        )

    candidates = []
    path_candidate = shutil.which(
        'tesseract',
        path=_environment_value(environment, 'PATH', operating_system),
    )
    if path_candidate:
        candidates.append((Path(path_candidate).resolve(), 'PATH'))
    candidates.extend(
        (candidate_path, 'known-location')
        for candidate_path in _known_tesseract_paths(
            operating_system,
            environment,
        )
    )

    checked_candidates = set()
    validation_errors = []
    for candidate_path, source in candidates:
        candidate_key = _candidate_key(candidate_path, operating_system)
        if candidate_key in checked_candidates:
            continue
        checked_candidates.add(candidate_key)
        if not candidate_path.is_file():
            continue
        try:
            version = get_tesseract_version(candidate_path, operating_system)
        except (
            OSError,
            subprocess.SubprocessError,
            TesseractConfigurationError,
        ) as error:
            validation_errors.append(
                f"{candidate_path}: {type(error).__name__}: {error}"
            )
            continue
        return TesseractSelection(
            candidate_path.resolve(),
            version,
            source,
        )

    error_details = ''
    if validation_errors:
        error_details = ' Invalid candidates: ' + ' | '.join(validation_errors)
    raise TesseractConfigurationError(
        "Tesseract was not found or could not be executed. Install Tesseract, "
        "add it to PATH, or set TESSERACT_CMD to its executable path."
        + error_details
    )


def configure_pytesseract(operating_system, environment=None):
    """Resolve Tesseract and configure pytesseract in one explicit step."""
    import pytesseract

    selection = resolve_tesseract(
        operating_system,
        environment=environment,
    )
    pytesseract.pytesseract.tesseract_cmd = str(selection.executable_path)
    return selection
