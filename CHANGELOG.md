### Changelog

- **v1.6.0** (2025-05-02)
  - **Added**: Updated autodigisign_utils.py to handle stale and missing elements in Document Object Model.
  - **Changed**: Deactivated the function for checking whether there is a dialog-form for delay-sign.
  - **Changed**: Updated ChromeDriver to version 136.0.7103.49 and Microsoft Edge WebDriver to version 134.0.3124.119.

- **v1.5.1** (2024-11-28)
  - **Fixed**: Updated delay-sign handling logic to avoid any interruptions in automated signing.

- **v1.5.0** (2024-11-14)
  - **Added**: Functionality to detect and handle the delay-sign dialog during the signing process. This includes selecting a reason and confirming the action if the dialog appears.

- **v1.4.1** (2024-10-28)
  - **Fixed**: Bug causing failure to perform digital signature for automated script execution.

- **v1.4.0** (2024-10-27)
  - **Added**: item_locator.py for finding items (files or folders) in the directory structure.
  - **Changed**: Reorganized project folders for improved clarity and separation of concerns.

- **v1.3.0** (2024-10-26)
  - **Added**: Encapsulated new functions.
  - **Changed**: Refactored functions into separate modules for better code organization.

- **v1.2.2** (2024-10-24)
  - **Changed**: Updated email body summary to improve clarity.

- **v1.2.1** (2024-10-23)
  - **Changed**: Updated the process to verify successful email sending before closing the script.

- **v1.2.0** (2024-10-23)
  - **Added**: Automatic email sending of the log file after script completion.

- **v1.1.0** (2024-10-23)
  - **Added**: Updated logging settings for improved debugging and reporting.

- **v1.0.0** (2024-10-22)
  - **Initial Release**: Automated login, CAPTCHA solving, and digital signature functionality.
