# AutoDigiSign

Author / 作者: [hsulihuang](https://github.com/hsulihuang)

## Overview / 專案概述

AutoDigiSign is a Python automation tool for the National Taiwan University Hospital (NTUH) electronic medical-record signing page. It recognizes the portal CAPTCHA, selects employees from a month-aware roster, performs PCSC signatures, writes INFO and DEBUG logs, and can optionally email both logs.

AutoDigiSign 是用於臺大醫院（NTUH）電子病歷簽章頁面的 Python 自動化工具，可辨識入口網站 CAPTCHA、依月份名冊選取員工、執行 PCSC 簽章、建立 INFO 與 DEBUG 日誌，並可選擇寄送兩份日誌。

## Release Status / 發佈狀態

Version 2.0.0 was validated end to end—including an actual PCSC signature—on an authorized, NTUH-managed Windows 10/11 x64 computer using the institution-provided HCAServiSign component compatible with the current signing page. The macOS application path and automated tests are retained, with no known blocking code defect, but production signing on macOS has not been validated because a compatible institution-provided HCAServiSign installer is currently unavailable. A new macOS production signing environment therefore cannot currently be completed. Do not substitute an older, generic, or unrelated ServiSign package.

2.0.0 已在院方管理且獲授權的 Windows 10／11 x64 電腦上，搭配院方提供並與現行簽章頁面相容的 HCAServiSign 元件，完成包含實際 PCSC 簽章的端到端驗證。專案仍保留 macOS 應用程式路徑與自動測試，且目前沒有已知的阻斷性程式問題；但因無法取得院方提供的相容 HCAServiSign 安裝套件，尚未完成 macOS 正式簽章驗證，也無法從零建立新的 macOS 正式簽章環境。請勿以舊版、一般用途或其他服務的 ServiSign 套件替代。

## Documentation / 文件導覽

- [Installation guide](docs/installation.md): Authoritative Chinese instructions for Windows production deployment, plus macOS technical preparation retained for future compatibility. / Windows 正式部署，以及為未來相容性保留之 macOS 技術準備的中文完整說明。
- [Maintenance guide](docs/maintenance.md): Chinese instructions for changing credentials or cardholders, updating the roster, running on demand, maintaining schedules, and reviewing logs. / 更換帳密或持卡人、更新名冊、立即執行、維護排程及檢查日誌的中文說明。
- [Troubleshooting guide](docs/troubleshooting.md): Chinese diagnosis for Python, CAPTCHA, Tesseract, browser, WebDriver, PCSC, signing, logging, and email problems. / Python、CAPTCHA、Tesseract、瀏覽器、WebDriver、PCSC、簽章、日誌及郵件問題的中文排解說明。
- [Changelog](CHANGELOG.md): English-first bilingual version history. / 英文在前的雙語版本紀錄。

## Authorization and Sensitive Data / 授權與敏感資料

AutoDigiSign is an independent project. It is not an official NTUH product and is not affiliated with or endorsed by NTUH. The MIT License applies only to the source code; it does not grant permission to access NTUH systems, process personnel data, or perform electronic signatures. Use this software only when explicitly authorized and in accordance with institutional policies.

AutoDigiSign 是獨立專案，不是臺大醫院官方產品，也未受臺大醫院認可或背書。MIT License 只授權原始碼，不代表取得存取院內系統、處理人員資料或執行電子簽章的權限。只有獲得明確授權的人員可以使用本程式，並須遵守院方政策。

The local installation may contain portal credentials, a medical personnel card PIN, employee IDs and names, SMTP credentials, and execution results. `inputs/`, `outputs/`, `webdrivers/`, and `.venv/` are excluded from Git. Restrict their access and transfer them only through institution-approved methods. AutoDigiSign does not automatically delete logs or impose a retention period.

本機安裝可能包含入口網站帳密、醫事人員卡 PIN、員編與姓名、SMTP 帳密及執行結果。`inputs/`、`outputs/`、`webdrivers/` 與 `.venv/` 均被 Git 忽略，必須限制存取，且只能透過院方核可方式移轉。本程式不會自動刪除日誌，也不設定保存期限。

CAPTCHA source and intermediate images are processed only in memory and are not written to disk. Logs do not record passwords, PINs, CAPTCHA values, session tokens, popup HTML, or raw Selenium traffic. When email is enabled, both the INFO and DEBUG logs are sent to the configured recipients.

CAPTCHA 原圖及中間處理影像只在記憶體內處理，不會寫入磁碟。日誌不記錄密碼、PIN、CAPTCHA 值、session token、彈出視窗 HTML 或 Selenium 原始傳輸內容。啟用郵件時，INFO 與 DEBUG 日誌都會寄給設定的收件者。

## Project Structure / 專案結構

```text
docs/
 ├── installation.md
 ├── maintenance.md
 └── troubleshooting.md
examples/
 ├── credentials.ini.example
 ├── email_config.ini.example
 └── employee_list.txt.example
inputs/                    # Local, Git-ignored / 本機、Git 忽略
 ├── configs/
 │   ├── credentials.ini
 │   └── email_config.ini  # Optional / 選用
 └── employee_list.txt
outputs/                   # Local, Git-ignored / 本機、Git 忽略
 └── logs/<YYYY>/<MM>/
scheduling/
 ├── macos/com.autodigisign.agent.plist.example
 └── windows/
     ├── register-autodigisign-task.ps1
     └── unregister-autodigisign-task.ps1
src/autodigisign/
 ├── __init__.py
 ├── __main__.py
 ├── browser.py
 ├── captcha.py
 ├── config.py
 ├── email_delivery.py
 ├── employees.py
 ├── logging_config.py
 ├── portal.py
 ├── selenium_helpers.py
 ├── signing.py
 ├── signing_workflow.py
 ├── tesseract.py
 └── webdriver/
     ├── catalog.py
     ├── detection.py
     ├── installer.py
     └── manager.py
tests/
webdrivers/                # Local versioned driver cache / 本機版本化 Driver 快取
.venv/                     # Local Python environment / 本機 Python 環境
CHANGELOG.md
LICENSE
README.md
launcher_macos.command
launcher_win64.bat
pyproject.toml
requirements.txt
```

## Requirements / 系統需求

- **Production platform / 正式部署平台**: An authorized, NTUH-managed Windows 10/11 x64 computer with an institution-provided HCAServiSign component compatible with the current signing page. Native Windows ARM64 and 32-bit deployments have not been validated end to end. / 院方管理且獲授權，並已配置與現行簽章頁面相容之 HCAServiSign 元件的 Windows 10／11 x64 電腦；原生 Windows ARM64 與 32 位元尚未完成端到端驗證。
- **macOS status / macOS 狀態**: Technical preparation is documented, but macOS is not a production-validated signing platform for 2.0.0; see Release Status above. / 文件保留 macOS 技術準備，但 macOS 並非 2.0.0 已完成正式簽章驗證的平台；詳見上方「發佈狀態」。
- **Python**: Python 3.14.x only. / 僅支援 Python 3.14.x。
- **Browser / 瀏覽器**: Edge is preferred on both platforms; Chrome 115 or newer is the fallback. / 兩個平台都優先使用 Edge，Chrome 115 以上為備援。
- **Tesseract OCR**: The external Tesseract application is required; `pytesseract` alone is insufficient. / 必須另外安裝 Tesseract，只有 `pytesseract` Python 套件並不足夠。
- **NTUH access / NTUH 存取**: A valid account and hospital network or another authorized connection. / 有效帳號及院內網路或其他獲授權連線。
- **Signing components / 簽章元件**: An institution-provided HCAServiSign component compatible with the current signing page, a valid medical personnel card, and its PIN. AutoDigiSign does not include or download HCAServiSign. / 院方提供且與現行簽章頁面相容的 HCAServiSign、有效醫事人員卡及 PIN。AutoDigiSign 不附帶也不會下載 HCAServiSign。
- **Reader / 讀卡機**: A PCSC chip-card reader without a numeric keypad and its approved driver. AutoDigiSign does not use an HCIC health-insurance card reader with a numeric keypad. / PCSC 晶片讀卡機（無數字按鍵）及核可驅動；本程式不使用 HCIC 健保讀卡機（有數字按鍵）。

See the [installation guide](docs/installation.md) before setting up a new computer. / 新電腦請先閱讀[安裝指南](docs/installation.md)。

## Quick Start / 快速開始

The commands below are only a summary. Follow the installation guide for external applications, hardware, permissions, offline deployment, and controlled first-run procedures. Run all commands from the AutoDigiSign project root, not from an operating-system root or system directory such as `C:\Windows\System32` or `/`.

下列命令只是摘要；外部程式、硬體、權限、離線部署及第一次受控執行，請依安裝指南操作。所有命令都必須在 AutoDigiSign 專案根目錄執行，而非停留在作業系統根目錄或系統目錄，例如 `C:\Windows\System32` 或 `/`。

Both the Windows and macOS launchers require the project-local `.venv`. If it is missing, the launcher displays the platform-specific setup commands and exits; it does not fall back to a system or global Python installation.

Windows 與 macOS 啟動檔都必須使用專案本機 `.venv`。若找不到該環境，啟動檔會顯示對應平台的建立指令後結束，不會改用系統或全域 Python。

### Windows

```bat
py -V:3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install --editable .
if not exist inputs\configs mkdir inputs\configs
if not exist outputs\logs mkdir outputs\logs
if not exist webdrivers mkdir webdrivers
copy examples\credentials.ini.example inputs\configs\credentials.ini
copy examples\employee_list.txt.example inputs\employee_list.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Edit the copied input files, complete the controlled preflight, and then run `launcher_win64.bat`. / 編輯複製出的輸入檔，完成受控執行前檢查後，再執行 `launcher_win64.bat`。

### macOS Technical Preparation / macOS 技術準備

These commands prepare only Python, browser/WebDriver, and OCR for application-level checks; they do not create a production signing environment. See Release Status above and the installation guide. / 下列命令只準備供應用程式層級檢查使用的 Python、瀏覽器／WebDriver 與 OCR，不能建立正式簽章環境；詳見上方「發佈狀態」與安裝指南。

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --editable .
mkdir -p inputs/configs outputs/logs webdrivers
cp examples/credentials.ini.example inputs/configs/credentials.ini
cp examples/employee_list.txt.example inputs/employee_list.txt
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v
```

Use the launcher only for application-level checks; it does not validate macOS production signing and must not be scheduled for production in 2.0.0. See Signing Behavior below and the installation guide for validation requirements. If macOS reports that the file is not executable, run `chmod +x launcher_macos.command` once from the project root. / 此啟動檔僅供應用程式層級檢查，不代表 macOS 正式簽章已通過驗證，2.0.0 也尚無法用於 macOS 正式排程。驗證條件請參閱下方「簽章行為」與安裝指南。若 macOS 顯示檔案不可執行，請先在專案根目錄執行一次 `chmod +x launcher_macos.command`。

### Automated Tests / 自動測試

On version 2.0.0, the final test command shown for each platform discovers and runs all 67 automated tests. A successful run reports `Ran 67 tests` and ends with `OK`; these tests do not perform an actual portal signature.

在 2.0.0 中，各平台最後一行測試指令會找出並執行全部 67 項自動測試。成功時會顯示 `Ran 67 tests`，並以 `OK` 結束；這些測試不會在入口網站執行實際簽章。

## Configuration Summary / 設定摘要

- `inputs/configs/credentials.ini` is required and stores the portal username, password, and card PIN. / 必要；保存入口網站帳號、密碼及卡片 PIN。
- `inputs/employee_list.txt` is required. `[YYYY-MM]` sections are month-specific and `[permanent]` is always active. Duplicate active employee IDs are processed once; conflicting names are reported while the first active name is retained. / 必要；`[YYYY-MM]` 是指定月份，`[permanent]` 永久有效。重複的有效員編只處理一次；姓名衝突會回報並保留第一個有效姓名。
- `inputs/configs/email_config.ini` is optional. When absent, local logs are still created and email is skipped. / 選用；不存在時仍會建立本機日誌，只跳過寄信。

Copy the corresponding file from `examples/` and replace every placeholder. Never place real credentials in `examples/` or Git. Complete formats and rules are maintained in the [installation guide](docs/installation.md).

請從 `examples/` 複製對應檔案並替換所有預留值。不得將真實帳密寫回 `examples/` 或 Git；完整格式與規則以[安裝指南](docs/installation.md)為準。

## Signing Behavior / 簽章行為

AutoDigiSign always clicks `NTUHWeb1_btnDoSignatureByPCSC`. The popup must appear within 30 seconds. After the first `批次電子簽章作業中` message, processing may continue for up to 180 seconds; repeated progress messages do not extend that deadline. Terminal success or error messages end the wait immediately.

AutoDigiSign 一律點擊 `NTUHWeb1_btnDoSignatureByPCSC`。彈出視窗必須在 30 秒內出現；第一次收到「批次電子簽章作業中」後，處理最多可持續 180 秒，重複進度訊息不會延長期限；成功或錯誤等終止訊息會立即結束等待。

The NTUH page checks for pending records before invoking HCAServiSign. A `查無待簽章電子病歷資料` result validates only login and record lookup; it does not validate the signing component or an actual signature. / NTUH 頁面會先查詢是否有待簽章病歷，只有查到資料後才會呼叫 HCAServiSign；「查無待簽章電子病歷資料」只驗證登入與查詢流程，不代表簽章元件或實際簽章已通過驗證。

Recoverable employee-specific failures are logged while remaining employees continue. Any employee failure produces a nonzero final exit code. Reader-type or unsafe browser-state errors stop the batch. / 個別可復原錯誤會記錄後繼續處理其他員工；只要有人失敗，最終即回傳非零結束碼。讀卡機類型或瀏覽器狀態不安全時會停止整批。

## Browser, OCR, and Local Drivers / 瀏覽器、OCR 與本機 Driver

Tesseract is located through `TESSERACT_CMD`, `PATH`, and standard macOS or Windows locations. WebDriver management detects the installed browser version, recursively checks compatible local drivers under `webdrivers/`, and downloads a matching version from allow-listed official Microsoft or Google services only when needed. Older version-labelled drivers are retained.

程式依序透過 `TESSERACT_CMD`、`PATH` 及 macOS／Windows 標準位置尋找 Tesseract。WebDriver 管理會偵測瀏覽器版本、遞迴檢查 `webdrivers/` 內的相容版本，只在必要時由白名單內的 Microsoft 或 Google 官方服務下載，並保留具版本標示的舊 Driver。

The production CAPTCHA is validated as exactly six characters containing only `0-9` and `A-Z`. Alternate preprocessing and Tesseract page-segmentation strategies are tried before a new CAPTCHA is requested. / 正式環境 CAPTCHA 必須恰為六碼 `0-9`／`A-Z`；格式不符時會先嘗試其他影像處理及 Tesseract 分頁策略，再要求新的 CAPTCHA。

## Scheduling / 排程

For 2.0.0, production scheduling is limited to the validated Windows deployment. The supplied Windows scripts default to daily runs at **06:30, 13:00, 16:50, 20:00, and 23:30**, and the times can be changed with `-DailyTimes`. Create a task only after a controlled run completes an actual signature for an employee with pending records. The desktop must remain signed in and awake, with compatible HCAServiSign, the card, and the PCSC reader ready.

2.0.0 的正式排程僅限已驗證的 Windows 部署。Windows 腳本預設每日於 **06:30、13:00、16:50、20:00、23:30** 執行，可透過 `-DailyTimes` 修改。只有在受控執行已對確有待簽資料的員工完成實際簽章後，才能建立排程；執行時桌面必須保持登入與喚醒，且相容 HCAServiSign、卡片及 PCSC 讀卡機均已就緒。

The macOS LaunchAgent template is retained only as a future compatibility reference and must not be used for 2.0.0 production scheduling. Its `StartCalendarInterval` values may be customized only if macOS later meets the documented production-validation requirements. / macOS LaunchAgent 範本僅作為未來相容性參考，尚無法用於 2.0.0 正式排程；只有日後符合文件所列正式部署驗證條件時，才可修改其中的 `StartCalendarInterval`。

Initial setup belongs in the [installation guide](docs/installation.md); later changes belong in the [maintenance guide](docs/maintenance.md). / 初次建立請依[安裝指南](docs/installation.md)，後續修改請依[維護指南](docs/maintenance.md)。

## Logs / 日誌

Each run creates the following under `outputs/logs/<YYYY>/<MM>/`: / 每次執行會在 `outputs/logs/<YYYY>/<MM>/` 建立：

```text
autodigisign_YYYYMMDDTHHMMSS_info.log
autodigisign_YYYYMMDDTHHMMSS_debug.log
```

The timestamp identifies the local start time to the nearest second. If another run starts in the same second, both files receive a shared suffix such as `_02`; existing files are never overwritten. Historical logs retain their original filenames. / 時間戳記以本機開始時間記錄至秒；若同一秒啟動另一個執行個體，該次 INFO 與 DEBUG 會共用 `_02` 等後綴，既有檔案不會被覆寫。歷史日誌維持原檔名。

- **INFO**: Lifecycle, login status, warning/error summaries, and every employee's ID, name, and signing result. / 執行流程、登入狀態、警告／錯誤摘要，以及每位員工的員編、姓名與簽章結果。
- **DEBUG**: INFO plus sanitized application diagnostics and unexpected-error tracebacks. / 包含 INFO，以及經遮蔽的診斷資訊與未預期錯誤 traceback。
- No separate Console log is created. / 不建立獨立 Console 日誌。

## License and Contributions / 授權與貢獻

The source code is licensed under the MIT License; see [LICENSE](LICENSE). This license does not authorize use of NTUH systems or data. Use the [GitHub repository](https://github.com/hsulihuang/AutoDigiSign) for issues and pull requests, but never include credentials, PINs, employee or patient data, CAPTCHA images, session values, or execution logs.

本專案原始碼採 MIT License，詳見 [LICENSE](LICENSE)；此授權不代表取得 NTUH 系統或資料的使用權。請透過 [GitHub 專案頁](https://github.com/hsulihuang/AutoDigiSign)提出 issue 或 pull request，但不得附上帳密、PIN、員工或患者資料、CAPTCHA 圖片、session 值或執行日誌。
