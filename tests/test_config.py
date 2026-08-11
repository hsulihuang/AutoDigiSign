import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.config import (  # noqa: E402
    ConfigurationError,
    load_credentials_settings,
    resolve_project_paths,
)


class ConfigTests(unittest.TestCase):
    def test_resolves_only_documented_input_paths(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_directory = root / 'inputs' / 'configs'
            config_directory.mkdir(parents=True)
            (config_directory / 'credentials.ini').write_text(
                '[credentials]\nusername=u\npassword=p\npincode=1\n',
                encoding='utf-8',
            )
            (root / 'inputs' / 'employee_list.txt').write_text(
                '1 User\n',
                encoding='utf-8',
            )
            # A similarly named nested file must not be selected.
            nested = root / 'storehouse' / 'credentials.ini'
            nested.parent.mkdir()
            nested.write_text('unused', encoding='utf-8')

            paths = resolve_project_paths(root)

            self.assertEqual(
                paths.credentials,
                (config_directory / 'credentials.ini').resolve(),
            )
            self.assertIsNone(paths.email_config)

    def test_missing_required_input_is_reported_before_browser_start(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(FileNotFoundError, 'employee_list.txt'):
                resolve_project_paths(temporary_directory)

    def test_loads_credentials_without_signature_settings(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / 'credentials.ini'
            path.write_text(
                '[credentials]\n'
                'username=user\n'
                'password=secret\n'
                'pincode=1234\n',
                encoding='utf-8',
            )

            settings = load_credentials_settings(path)

            self.assertEqual(settings.username, 'user')
            self.assertEqual(settings.password, 'secret')
            self.assertEqual(settings.pincode, '1234')

    def test_missing_credentials_field_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / 'credentials.ini'
            path.write_text(
                '[credentials]\nusername=user\npassword=secret\n',
                encoding='utf-8',
            )

            with self.assertRaisesRegex(
                ConfigurationError,
                r'credentials\.pincode',
            ):
                load_credentials_settings(path)

if __name__ == '__main__':
    unittest.main()
