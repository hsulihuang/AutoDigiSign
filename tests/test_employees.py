import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.employees import (  # noqa: E402
    EmployeeListFormatError,
    get_employees,
)


class EmployeeListTests(unittest.TestCase):
    def load(self, contents, effective_month):
        with tempfile.TemporaryDirectory() as temporary_directory:
            employee_list = Path(temporary_directory) / 'employee_list.txt'
            employee_list.write_text(contents, encoding='utf-8')
            return get_employees(employee_list, effective_month=effective_month)

    def test_selects_current_month_and_permanent_employees(self):
        contents = """
[2026-08]
A001 Alice
B001 Bob
[2026-09]
B001 Bob
C001 Carol
D001 David
[2026-10]
E001 Erin
F001 Frank
[permanent]
G001 Grace
H001 Helen
"""

        august = self.load(contents, '202608')
        september = self.load(contents, '2026-09')
        october = self.load(contents, '202610')

        self.assertEqual(
            [item['id'] for item in august],
            ['A001', 'B001', 'G001', 'H001'],
        )
        self.assertEqual(
            [item['id'] for item in september],
            ['B001', 'C001', 'D001', 'G001', 'H001'],
        )
        self.assertEqual(
            [item['id'] for item in october],
            ['E001', 'F001', 'G001', 'H001'],
        )

    def test_unsectioned_legacy_rows_remain_permanent(self):
        contents = """
G001 Grace Hopper
[202609]
C001 Carol Chen
"""

        employees = self.load(contents, '202608')

        self.assertEqual(employees, [{'id': 'G001', 'name': 'Grace Hopper'}])

    def test_compact_yyyymm_section_remains_supported(self):
        employees = self.load('[202608]\nA001 Alice\n', '2026-08')

        self.assertEqual(employees, [{'id': 'A001', 'name': 'Alice'}])

    def test_duplicate_active_employee_is_selected_once(self):
        contents = """
[2026-08]
A001 Alice
[permanent]
A001 Alice
"""

        employees = self.load(contents, '202608')

        self.assertEqual(employees, [{'id': 'A001', 'name': 'Alice'}])

    def test_duplicate_id_with_different_names_reports_error_and_continues(self):
        contents = """
[2026-08]
A001 Alice
[permanent]
A001 Alicia
"""

        with self.assertLogs(level='ERROR') as captured_logs:
            employees = self.load(contents, '202608')

        self.assertEqual(employees, [{'id': 'A001', 'name': 'Alice'}])
        self.assertIn(
            'Employee list configuration error: conflicting names',
            '\n'.join(captured_logs.output),
        )

    def test_same_name_with_different_ids_selects_both_employees(self):
        contents = """
[2026-08]
A001 Alex Chen
[permanent]
A002 Alex Chen
"""

        employees = self.load(contents, '202608')

        self.assertEqual(
            employees,
            [
                {'id': 'A001', 'name': 'Alex Chen'},
                {'id': 'A002', 'name': 'Alex Chen'},
            ],
        )

    def test_invalid_month_section_is_rejected(self):
        with self.assertRaisesRegex(EmployeeListFormatError, 'invalid month'):
            self.load('[2026-13]\nA001 Alice\n', '202608')

    def test_employee_name_is_required(self):
        with self.assertRaisesRegex(EmployeeListFormatError, 'employee row'):
            self.load('[permanent]\nA001\n', '202608')


if __name__ == '__main__':
    unittest.main()
