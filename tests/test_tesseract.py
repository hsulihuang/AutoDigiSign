import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.tesseract import (  # noqa: E402
    TesseractConfigurationError,
    resolve_tesseract,
)


class TesseractTests(unittest.TestCase):
    def test_environment_override_has_priority(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            executable = Path(temporary_directory) / 'tesseract'
            executable.write_text('', encoding='utf-8')
            with patch(
                'autodigisign.tesseract.get_tesseract_version',
                return_value='5.5.2',
            ):
                selection = resolve_tesseract(
                    'macos',
                    environment={
                        'TESSERACT_CMD': str(executable),
                        'PATH': '',
                    },
                )

        self.assertEqual(selection.version, '5.5.2')
        self.assertEqual(selection.source, 'TESSERACT_CMD')

    def test_invalid_override_fails_instead_of_silently_ignoring_it(self):
        with self.assertRaisesRegex(TesseractConfigurationError, 'TESSERACT_CMD'):
            resolve_tesseract(
                'macos',
                environment={
                    'TESSERACT_CMD': '/does/not/exist',
                    'PATH': '',
                },
            )


if __name__ == '__main__':
    unittest.main()
