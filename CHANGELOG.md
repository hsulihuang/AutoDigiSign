# Changelog / 更新紀錄

All notable changes to AutoDigiSign are documented in this file.

本文件記錄 AutoDigiSign 各版本的重要變更。

## [2.0.0] - 2026-08-11

**Release validation:** Version 2.0.0 was validated end to end, including an actual PCSC signature, on an authorized, NTUH-managed Windows 10/11 x64 computer using an institution-provided HCAServiSign component compatible with the current signing page. macOS production signing remains unvalidated because a compatible institution-provided HCAServiSign installer is currently unavailable; the macOS code and deployment assets are retained for technical preparation and future compatibility.

**發佈驗證：**2.0.0 已在院方管理且獲授權的 Windows 10／11 x64 電腦上，搭配院方提供並與現行簽章頁面相容的 HCAServiSign 元件，完成包含實際 PCSC 簽章的端到端驗證。macOS 因目前無法取得院方提供的相容 HCAServiSign 安裝套件，尚未完成正式簽章驗證；macOS 程式碼與部署資源僅保留供技術準備及未來相容性使用。

### Breaking Changes / 重大變更

- Python 3.14.x is now the only supported runtime and is validated at startup; existing installations must recreate the project-local `.venv` and install the project from the new `pyproject.toml`. / 執行環境改為僅支援 Python 3.14.x，啟動時會明確檢查版本；既有安裝必須重新建立專案本機 `.venv`，並透過新的 `pyproject.toml` 安裝專案。

### Security / 安全性

- Application logs no longer emit full CAPTCHA URLs, recognized CAPTCHA values, portal-session details, raw third-party request diagnostics, or popup HTML. DEBUG logs retain only non-sensitive CAPTCHA recognition strategy, timing, candidate-length, and format-validation metadata, while verbose Selenium, urllib3, PIL, and pytesseract logging is suppressed. / 應用程式日誌不再輸出完整 CAPTCHA URL、CAPTCHA 辨識值、入口網站 session 詳情、第三方原始請求診斷資訊或彈出視窗 HTML。DEBUG 日誌只保留不具敏感性的 CAPTCHA 辨識策略、耗時、候選長度與格式驗證資訊，並停用 Selenium、urllib3、PIL 與 pytesseract 的詳細日誌。
- Added post-format log redaction for passwords, PINs, sessions, and verification values, including values that appear in exception tracebacks. / 新增格式化後的日誌遮蔽，移除密碼、PIN、session 及驗證資訊，包括出現在例外 traceback 中的敏感值。
- CAPTCHA source and intermediate images are now processed only in memory and are no longer written to disk. / CAPTCHA 原圖及中間處理影像現在只在記憶體內處理，不再寫入磁碟。
- Restricted WebDriver downloads to allow-listed official HTTPS hosts and bounded download sizes, with ZIP archive validation before extraction. Source metadata and ZIP SHA-256 digests are recorded, and extracted executable versions are verified before use. / WebDriver 下載僅允許白名單內的官方 HTTPS 主機並限制檔案大小，且會在解壓前驗證 ZIP 格式。程式會記錄來源資訊與 ZIP SHA-256 摘要，並在使用前確認解壓後的可執行檔版本。

### Added / 新增

- Added month-specific `[YYYY-MM]`, compatible `[YYYYMM]`, and permanent `[permanent]` employee-list sections, including validation, multi-month entries, and employee-ID-based deduplication. Conflicting active names for the same ID are logged as configuration errors; the employee is processed once using the first active name. / 員工名冊新增月份區段 `[YYYY-MM]`、相容格式 `[YYYYMM]` 與永久區段 `[permanent]`，並加入內容驗證、跨月資料及依員編去重。同一有效員編若出現不同姓名，程式會記錄設定錯誤，並只以第一個有效姓名處理一次。
- Added automatic WebDriver management that detects installed browser versions, reuses compatible local drivers, or downloads matching historical versions from official Microsoft and Google catalogs. Drivers are stored under `webdrivers/` by browser, platform, and version, while older versions are retained. / 新增 WebDriver 自動管理：偵測已安裝的瀏覽器版本、重用相容的本機 Driver，或從 Microsoft 與 Google 官方目錄下載相符的歷史版本。Driver 會依瀏覽器、平台及版本保存在 `webdrivers/`，並保留舊版本。
- Added cross-platform Tesseract discovery through `TESSERACT_CMD`, `PATH`, and standard macOS and Windows installation locations. The selected executable is verified by reading its reported version. / 新增跨平台 Tesseract 探測，依序支援 `TESSERACT_CMD`、`PATH` 與 macOS／Windows 標準安裝位置，並透過讀取回報版本確認所選執行檔可正常執行。
- Added strict production CAPTCHA validation requiring exactly six characters from `0-9` and `A-Z`, with alternate preprocessing and Tesseract page-segmentation strategies before a new CAPTCHA is requested. / 新增正式環境 CAPTCHA 格式驗證，辨識結果必須恰為六碼 `0-9`／`A-Z`；格式不符時會先嘗試其他影像處理與 Tesseract 分頁策略，再要求新的 CAPTCHA。
- Added preflight validation for required input files, credentials, and any present email settings before WebDriver download or browser startup. / 新增執行前驗證，在下載 WebDriver 或啟動瀏覽器前檢查必要輸入檔、帳密及存在的郵件設定。
- Added `pyproject.toml` project metadata and an installable `autodigisign` console command. / 新增 `pyproject.toml` 專案中繼資料及可安裝的 `autodigisign` 命令。
- Added sanitized example files for required credentials, optional email settings, and employee rosters. / 新增不含真實資料的帳密、選用郵件設定及員工名冊範例檔。
- Added `launcher_macos.command` for direct Finder double-click execution. Like the Windows launcher, it resolves the project directory from its own location, returns the application's actual exit code, waits 10 seconds after interactive success, and waits for a key after interactive failure. / 新增可直接從 Finder 雙擊執行的 `launcher_macos.command`；其行為與 Windows 啟動檔一致，會依自身位置定位專案目錄、回傳程式實際結束碼，並在手動執行成功後等待 10 秒、失敗後等待按鍵。
- Added per-user scheduling assets: Windows PowerShell registration and removal scripts for production deployment, plus a macOS LaunchAgent template retained for future compatibility. Both default to daily runs at 06:30, 13:00, 16:50, 20:00, and 23:30, and the times can be customized as needed. The scheduling assets invoke the platform launchers in non-interactive `--scheduled` mode. / 新增使用者層級的排程資源：供正式部署使用的 Windows PowerShell 註冊與移除腳本，以及為未來相容性保留的 macOS LaunchAgent 範本。兩者均預設每日於 06:30、13:00、16:50、20:00、23:30 執行，時間可依需求自行調整，並以非互動式 `--scheduled` 模式呼叫各平台啟動檔。
- Added 67 automated tests covering orchestration, year/month log paths, collision-safe log filenames, configuration, browser fallback, CAPTCHA capture and recognition fallbacks, resilient signing-page input, staged signing deadlines, concise INFO exception summaries, log redaction, signing-window recovery, Tesseract, and WebDriver management. / 新增 67 項自動測試，涵蓋主要流程、日誌年月路徑、防止碰撞的日誌檔名、設定、瀏覽器備援、CAPTCHA 擷取與辨識備援、簽章頁輸入復原、分階段簽章期限、精簡 INFO 例外摘要、日誌遮蔽、簽章視窗復原、Tesseract 與 WebDriver 管理。
- Added `.gitattributes` rules that enforce CRLF for Windows batch and PowerShell files and LF for other cross-platform text files. / 新增 `.gitattributes` 規則，強制 Windows 批次檔與 PowerShell 檔使用 CRLF，其餘跨平台文字檔使用 LF。

### Changes / 變更

- Reorganized the source modules under the installable `src/autodigisign/` package, changed module execution to `python -m autodigisign`, and placed WebDriver management in the dedicated `autodigisign.webdriver` subpackage. / 將原始碼模組重整至可安裝的 `src/autodigisign/` 套件，改用 `python -m autodigisign` 執行模組，並由專用的 `autodigisign.webdriver` 子套件負責 WebDriver 管理。
- Configuration and data files are now loaded only from their documented paths under `inputs/` instead of being discovered recursively. Installations already following the documented directory structure require no changes; custom file placements must be moved to the documented paths. / 設定檔與資料檔現在只會從 `inputs/` 下的文件指定路徑載入，不再遞迴搜尋其他位置。已遵循文件目錄結構的安裝不受影響；自行將檔案放在其他位置者，必須將檔案移至文件指定路徑。
- The Windows launcher now requires the project-local `.venv`, matching the newly added macOS launcher. Both launchers display platform-specific setup commands and exit with a nonzero status when the environment is absent; neither falls back to another Python installation. / Windows 啟動檔現在必須使用專案本機 `.venv`，與本版新增的 macOS 啟動檔一致。任一平台找不到該環境時，啟動檔都會顯示對應的建立指令並以非零狀態結束，不會改用其他 Python 安裝。
- Renamed the local WebDriver directory from `WebDriver/` to `webdrivers/`, which now serves as the versioned driver cache. Existing installations may rename the old directory to reuse cached drivers; otherwise, compatible drivers will be downloaded again when needed. / 本機 WebDriver 資料夾由 `WebDriver/` 改名為 `webdrivers/`，新資料夾現在作為版本化 Driver 快取。既有安裝可將舊資料夾改名以沿用快取；若未改名，程式會在需要時重新下載相容的 Driver。
- Both macOS and Windows now prefer Edge, with Chrome as a fallback. / macOS 與 Windows 均改為優先使用 Edge，並以 Chrome 作為備援。
- `email_config.ini` is now optional. When the file is absent, the application logs an INFO message and skips delivery without changing an otherwise successful signing result. / `email_config.ini` 現在為選用設定。檔案不存在時，程式只會記錄 INFO 並跳過寄信，不會改變原本成功的簽章結果。
- Updated OpenCV-Python from 4.10.0.84 to 4.14.0.94, Requests from 2.32.3 to 2.34.2, and Selenium from 4.25.0 to 4.46.0, and added direct pins for NumPy 2.5.2 and Pillow 12.3.0. / 將 OpenCV-Python 由 4.10.0.84 更新至 4.14.0.94、Requests 由 2.32.3 更新至 2.34.2、Selenium 由 4.25.0 更新至 4.46.0，並新增 NumPy 2.5.2 與 Pillow 12.3.0 的直接版本固定。
- Successful terminal signing results now record elapsed time. / 成功取得簽章終止結果時，現在會記錄實際耗時。
- INFO and DEBUG logs are now grouped under `outputs/logs/<YYYY>/<MM>/` and use timestamp-first names such as `autodigisign_20260810T201352_info.log`. Same-second runs receive a shared numeric suffix for both files, and existing logs are never overwritten. / INFO 與 DEBUG 日誌現在依 `outputs/logs/<YYYY>/<MM>/` 分類，並採用時間在前的檔名，例如 `autodigisign_20260810T201352_info.log`。同一秒啟動的不同執行會讓兩個檔案共用數字後綴，且不覆寫既有日誌。
- Exception reporting now keeps only the first nonempty, length-bounded error line in INFO, preventing multiline Selenium driver stacks from expanding the summary log; sanitized complete messages and tracebacks remain in DEBUG. / 例外回報現在只在 INFO 保留第一個非空白且有長度上限的錯誤行，避免 Selenium 多行 Driver stack 膨脹摘要日誌；經遮蔽的完整訊息與 traceback 仍保留在 DEBUG。
- Updated `.gitignore` for the renamed `/webdrivers/` directory, project-local `.venv/`, standalone `employee_list.txt` files, offline `/wheelhouse/` directories, and `*.whl` packages, and anchored project build and data directory rules at the repository root so similarly named source directories remain visible. / 更新 `.gitignore`，納入改名後的 `/webdrivers/`、專案本機 `.venv/`、獨立的 `employee_list.txt`、離線 `/wheelhouse/` 目錄及 `*.whl` 套件，並將專案建置與資料目錄規則限定於版本庫根目錄，避免誤忽略同名的原始碼目錄。
- Renamed `LICENSE.md` to the conventional root filename `LICENSE` without changing the license terms. / 將 `LICENSE.md` 改為較慣用的根目錄檔名 `LICENSE`，授權條款內容不變。

### Fixed / 修正

- Project-root detection no longer switches to account-specific macOS or Windows directories. The Windows launcher resolves the project directory relative to its own location and enters it before execution. / 專案根目錄偵測不再切換至帳號專屬的 macOS 或 Windows 路徑；Windows 啟動檔會依自身位置定位專案目錄，並在執行前切換至該目錄。
- CAPTCHA acquisition now waits for and captures the fully loaded browser-rendered element instead of opening a second HTTPS connection, avoiding certificate-chain failures and ensuring OCR uses the image displayed by the portal. Expected capture and recognition failures remain retryable, explicitly rejected logins advance immediately, and unexpected programming or driver errors are no longer hidden. / CAPTCHA 取得流程現在會等待瀏覽器元素完整載入後直接擷取，不再另建第二個 HTTPS 連線，藉此避開憑證鏈驗證失敗，並確保 OCR 使用入口網站當下顯示的圖片。預期的擷取與辨識失敗仍可重試；登入頁明確拒絕時會立即進入下一次，未預期的程式或驅動錯誤也不再被隱藏。
- Replaced the obsolete `NTUHWeb1_btnDoSignatureByCrossBroswer` selector with the PCSC-only button `NTUHWeb1_btnDoSignatureByPCSC`; AutoDigiSign uses a PCSC chip-card reader without a numeric keypad and does not use an HCIC health-insurance card reader with a numeric keypad. / 將已失效的 `NTUHWeb1_btnDoSignatureByCrossBroswer` 選擇器改為僅支援 PCSC 的按鈕 `NTUHWeb1_btnDoSignatureByPCSC`；AutoDigiSign 使用 PCSC 晶片讀卡機（無數字按鍵），不使用 HCIC 健保讀卡機（有數字按鍵）。
- Employee ID and PIN entry now re-find fields after clear-triggered postbacks and retry stale DOM references up to three times before the PCSC signing button is clicked, preventing alternating employee failures without risking duplicate signature submission. / 員編與 PIN 輸入現在會在清除欄位觸發 postback 後重新尋找元素，並在點擊 PCSC 簽章按鈕前最多重試三次失效的 DOM 參照，避免員工交錯失敗且不會造成重複送出簽章。
- Edge's specific `Node with given id does not belong to the document` response is now treated as a completed employee-field postback only while waiting for that field to become stale; unrelated WebDriver errors are still raised. / Edge 在等待員編欄位失效時回傳的特定 `Node with given id does not belong to the document` 訊息，現在會視為欄位 postback 已完成；其他 WebDriver 錯誤仍會照常拋出。
- Signing attempts now use stage-specific deadlines: 30 seconds for the popup and, after the first in-progress result, 180 seconds for processing without renewal from repeated progress messages. / 簽章作業現在採用分階段期限：彈出視窗最多等待 30 秒，第一次收到作業中結果後最多處理 180 秒，重複的作業中訊息不會延長期限。
- Signing-result handling no longer treats missing popups, missing result elements, or known signing-component errors as success. Terminal success or error messages end the wait immediately; `[-1]查無錯誤代碼定義。` is reported as possibly using an unsupported HCIC reader instead of the required PCSC reader. / 簽章結果判讀不再將缺少彈出視窗、缺少結果元素或已知簽章元件錯誤誤認為成功。成功或錯誤等終止訊息會立即結束等待；收到 `[-1]查無錯誤代碼定義。` 時，程式會提示可能誤接了不支援的 HCIC 健保讀卡機，而不是必要的 PCSC 晶片讀卡機。
- Signing-popup cleanup now verifies that the popup closed and the main window remains usable, stopping the batch when the browser state cannot be restored safely. / 簽章彈出視窗清理流程現在會確認視窗已關閉且主視窗仍可使用；若無法安全恢復瀏覽器狀態，便停止整批作業。
- A recoverable employee failure now produces a nonzero final exit code after the remaining roster has been processed, and the Windows launcher propagates the application's actual exit code to Task Scheduler, preventing false success reports. / 單一員工發生可復原錯誤時，程式會在處理完其餘名冊後回傳非零結束碼，Windows 啟動檔也會將程式的實際結束碼傳回工作排程器，避免誤報成功。
- Repeated logging initialization no longer creates duplicate handlers. / 重複初始化日誌時不再建立重複的 handler。

### Removed / 移除

- Removed the former `src/main.py` script entry point; use `python -m autodigisign`, the installed `autodigisign` command, or the platform launchers instead. / 移除原本的 `src/main.py` 腳本入口；請改用 `python -m autodigisign`、安裝後的 `autodigisign` 命令或各平台啟動檔。
- Removed the former `src/utils/` module set—`autodigisign_utils.py`, `email_utils.py`, `item_locator.py`, and `logging_utils.py`—after migrating active responsibilities into the `autodigisign` package. / 將有效功能移入 `autodigisign` 套件後，移除原本位於 `src/utils/` 的 `autodigisign_utils.py`、`email_utils.py`、`item_locator.py` 與 `logging_utils.py`。
- Removed the separate Console log file and its email attachment; INFO and DEBUG logs remain available locally and through optional email delivery. / 移除獨立 Console 日誌檔及其郵件附件；INFO 與 DEBUG 日誌仍會保存在本機，並可透過選用郵件功能寄送。
- Removed the legacy Windows reboot batch file. / 移除舊版 Windows reboot 批次檔。
- Removed the disabled legacy delay-sign helper and its obsolete selectors. / 移除已停用的舊版延遲簽章輔助流程及其過時選擇器。

### Documentation / 文件

- Reworked the former English-only README as an English-first bilingual project entry point and added `docs/installation.md` as the authoritative Chinese guide for first-time Windows production deployment and macOS technical preparation. / 將原本僅有英文的 README 重整為英文在前的雙語專案入口，並新增 `docs/installation.md`，作為 Windows 首次正式部署與 macOS 技術準備的完整中文指南。
- Documented the validated Windows production scope and the current macOS HCAServiSign deployment limitation throughout the README and user guides. / 在 README 與使用指南中明確記錄已驗證的 Windows 正式部署範圍，以及目前 macOS HCAServiSign 的部署限制。
- Replaced the former root-level Windows text quick guide with the Chinese daily maintenance guide at `docs/maintenance.md`, covering authorized cardholder and credential changes, roster updates, on-demand runs, schedule maintenance, and result review. / 以 `docs/maintenance.md` 的中文日常維護指南取代原本位於根目錄的 Windows 純文字簡易指南，涵蓋更換獲授權持卡人與帳密、更新名冊、立即執行、維護排程及檢查結果。
- Added the Chinese troubleshooting guide at `docs/troubleshooting.md`, covering Python environments, Tesseract and CAPTCHA, browsers and WebDriver, HCAServiSign and PCSC signing, configuration, logs, and email delivery. / 新增 `docs/troubleshooting.md` 中文疑難排解指南，涵蓋 Python 環境、Tesseract 與 CAPTCHA、瀏覽器與 WebDriver、HCAServiSign 與 PCSC 簽章、設定、日誌及郵件寄送。
- Removed the unsubstantiated recommendation for periodic computer restarts from the documentation. / 從文件中移除缺乏依據的定期重新啟動電腦建議。

## [1.6.1] - 2025-11-20

### Fixed / 修正

- Prevented Selenium from remaining on the `ShowInfo` popup and causing all subsequent employees to fail because `NTUHWeb1_txbEmpNO` could not be found, by adding fallback popup closure and an unconditional attempt to return to the main signing window. / 新增彈出視窗備援關閉，並無條件嘗試切回簽章主視窗，避免 Selenium 停留在 `ShowInfo` 視窗，導致後續員工因找不到 `NTUHWeb1_txbEmpNO` 而全部失敗。

## [1.6.0] - 2025-05-02

### Added / 新增

- Added `safe_find()` with retry handling for missing and stale DOM elements. / 新增 `safe_find()`，可重試找不到或已失效的 DOM 元素。

### Changes / 變更

- Moved delay-sign dialog handling into a dedicated helper and left it disabled in the primary signing workflow. / 將延遲簽章對話框處理移至專用函式，主要簽章流程仍維持停用。
- Updated the hard-coded WebDriver paths to target ChromeDriver 136.0.7103.49 and Microsoft Edge WebDriver 134.0.3124.119. / 更新寫死的 WebDriver 路徑，使其分別指向 ChromeDriver 136.0.7103.49 與 Microsoft Edge WebDriver 134.0.3124.119。

## [1.5.1] - 2024-11-28

### Fixed / 修正

- Replaced the fragile absolute XPath used for the delay-sign confirmation button with a text-based selector. / 將容易失效的延遲簽章確認按鈕絕對 XPath 改為文字選擇器。
- Handled missing or hidden delay-sign dialogs without interrupting the workflow and resubmitted the signature after confirmation. / 找不到或無法顯示延遲簽章對話框時不再中斷流程，並會在確認後重新送出簽章。

## [1.5.0] - 2024-11-14

### Added / 新增

- Added initial detection and confirmation of the delay-sign dialog using the preselected default reason. / 新增延遲簽章對話框的初步偵測與確認，使用預先選定的預設理由。

## [1.4.1] - 2024-10-28

### Added / 新增

- Added alert-aware email subjects when warning, error, or critical log entries are detected. / 日誌出現 warning、error 或 critical 時，郵件主旨會加入警示資訊。

### Fixed / 修正

- Passed the CAPTCHA output directory to the login retry routine, restoring CAPTCHA handling during automated runs. / 將 CAPTCHA 輸出目錄傳入登入重試流程，恢復自動執行時的 CAPTCHA 處理。
- Read employee lists as UTF-8 to support names containing non-ASCII characters. / 以 UTF-8 讀取員工名冊，以支援包含非 ASCII 字元的姓名。

### Changes / 變更

- Included employee names in signing logs and generated more concise completion-email summaries. / 簽章日誌加入員工姓名，並精簡完成郵件摘要。
- Moved the Windows reboot batch file into `src/batch/`. / 將 Windows 重新啟動批次檔移至 `src/batch/`。

## [1.4.0] - 2024-10-27

### Added / 新增

- Added `item_locator.py` for locating required files and directories within the project. / 新增 `item_locator.py`，用於在專案內尋找必要檔案與目錄。

### Changes / 變更

- Reorganized application code under `src/` and renamed `auto_reboot.bat` to `reboot_win64.bat`. / 將應用程式程式碼重整至 `src/`，並將 `auto_reboot.bat` 重新命名為 `reboot_win64.bat`。

## [1.3.0] - 2024-10-26

### Changes / 變更

- Split the monolithic application into dedicated signing, email, and logging utility modules. / 將單一大型程式拆分為簽章、郵件及日誌工具模組。
- Simplified the main script so it coordinates the extracted utility functions. / 簡化主程式，使其負責協調已拆出的工具函式。

## [1.2.2] - 2024-10-24

### Changes / 變更

- Replaced the full-log email body with a concise summary containing AutoDigiSign and employee-related entries. / 將完整日誌郵件內文改為只包含 AutoDigiSign 與員工相關資訊的精簡摘要。

## [1.2.1] - 2024-10-23

### Added / 新增

- Added separate DEBUG and INFO log files to completion emails. / 完成郵件新增獨立的 DEBUG 與 INFO 日誌附件。
- Added support for multiple configured email recipients. / 新增多個郵件收件者設定。

### Changes / 變更

- Logged email-delivery success or failure and updated the Windows launcher to keep the console open when the process reports a failure. / 記錄郵件寄送成功或失敗，並在程式回報失敗時讓 Windows 啟動檔保持視窗開啟。

## [1.2.0] - 2024-10-23

### Added / 新增

- Added automatic completion emails with the generated log file attached. / 新增執行完成後自動寄送郵件並附加日誌檔案。

## [1.1.0] - 2024-10-23

### Changes / 變更

- Increased file and console logging verbosity from INFO to DEBUG. / 將檔案及主控台日誌層級由 INFO 提高為 DEBUG。
- Routed login-attempt status messages through the logging system instead of direct console output. / 將登入嘗試的狀態訊息由直接輸出至主控台改為透過日誌系統記錄。

## [1.0.0] - 2024-10-22

### Added / 新增

- Released the initial automated workflow for login, CAPTCHA recognition, employee processing, and digital signatures. / 發布初始自動化流程，包含登入、CAPTCHA 辨識、員工處理及數位簽章。
