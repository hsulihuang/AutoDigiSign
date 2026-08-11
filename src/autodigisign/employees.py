import logging
import re
from datetime import datetime


PERMANENT_SECTION = 'permanent'
MONTH_PATTERN = re.compile(r'(?P<year>\d{4})-?(?P<month>\d{2})')


class EmployeeListFormatError(ValueError):
    """The employee list contains an invalid section or employee row."""


def _validate_month(value, description):
    """Return YYYYMM for a validated YYYY-MM or YYYYMM value."""
    match = MONTH_PATTERN.fullmatch(value)
    if match is None:
        raise EmployeeListFormatError(
            f"{description} must use YYYY-MM or YYYYMM format: {value!r}."
        )

    month_number = int(match.group('month'))
    if not 1 <= month_number <= 12:
        raise EmployeeListFormatError(
            f"{description} contains an invalid month: {value!r}."
        )
    return f"{match.group('year')}{match.group('month')}"


def _parse_section(line, line_number):
    """Return a validated section name, or None for an employee row."""
    if not (line.startswith('[') or line.endswith(']')):
        return None
    if not (line.startswith('[') and line.endswith(']')):
        raise EmployeeListFormatError(
            f"Invalid section header on line {line_number}: {line!r}."
        )

    section = line[1:-1].strip()
    if section.lower() == PERMANENT_SECTION:
        return PERMANENT_SECTION
    if MONTH_PATTERN.fullmatch(section):
        return _validate_month(
            section,
            f"Section header on line {line_number}",
        )
    raise EmployeeListFormatError(
        f"Unsupported section header on line {line_number}: {line!r}. "
        f"Use [YYYY-MM], [YYYYMM], or [{PERMANENT_SECTION}]."
    )


def get_employees(employee_list_filepath, effective_month=None):
    """Load permanent and effective-month employees from employee_list.txt.

    Employee rows before the first section are treated as permanent for
    backward compatibility with the original unsectioned file format.
    """
    if not employee_list_filepath:
        raise FileNotFoundError("employee_list.txt was not found.")

    if effective_month is None:
        effective_month = datetime.now().strftime('%Y%m')
    effective_month = _validate_month(
        str(effective_month),
        "Effective month",
    )

    current_section = PERMANENT_SECTION
    employees = []
    selected_names_by_id = {}

    with open(employee_list_filepath, 'r', encoding='utf-8-sig') as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue

            section = _parse_section(line, line_number)
            if section is not None:
                current_section = section
                continue

            employee_fields = line.split(maxsplit=1)
            if len(employee_fields) != 2:
                raise EmployeeListFormatError(
                    f"Invalid employee row on line {line_number}. "
                    "Expected: <employee_id> <employee_name>."
                )
            employee_id, employee_name = employee_fields

            if current_section not in (PERMANENT_SECTION, effective_month):
                continue

            existing_name = selected_names_by_id.get(employee_id)
            if existing_name is not None:
                if existing_name != employee_name:
                    logging.error(
                        "Employee list configuration error: conflicting names "
                        "for active Employee ID: %s on line %d. Retaining the "
                        "first active name and processing this employee once.",
                        employee_id,
                        line_number,
                    )
                else:
                    logging.debug(
                        "Skipped a duplicate active employee entry for "
                        "Employee ID: %s.",
                        employee_id,
                    )
                continue

            selected_names_by_id[employee_id] = employee_name
            employees.append({'id': employee_id, 'name': employee_name})

    logging.info(
        "Employee list selected: effective_month=%s, active_count=%d",
        f"{effective_month[:4]}-{effective_month[4:]}",
        len(employees),
    )
    return employees
