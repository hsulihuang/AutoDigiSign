import logging

from autodigisign.logging_config import log_exception
from autodigisign.signing import (
    SignatureDriverStateError,
    SignatureReaderTypeError,
    digital_signature,
)


def process_employees(
    driver,
    employees,
    pincode,
):
    """Process employees and return the number of recoverable failures.

    Reader-type and driver-state errors still stop the batch immediately because
    they affect every remaining employee or make further browser use unsafe.
    """
    failed_employee_count = 0
    for employee in employees:
        employee_id = employee['id']
        employee_name = employee['name']
        try:
            digital_signature(
                employee_id,
                employee_name,
                pincode,
                driver,
            )
            logging.info(
                "Digital signature performed for Employee ID: %s, Name: %s",
                employee_id,
                employee_name,
            )
        except (SignatureReaderTypeError, SignatureDriverStateError):
            # Both conditions affect every remaining employee, so continuing the
            # batch would produce repeated failures or use an incompatible reader.
            raise
        except Exception as error:
            failed_employee_count += 1
            log_exception(
                "Error processing Employee ID: "
                f"{employee_id}, Name: {employee_name}",
                error,
            )
    return failed_employee_count
