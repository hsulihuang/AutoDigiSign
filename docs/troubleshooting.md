# AutoDigiSign 疑難排解

本文件依「症狀 → 檢查 → 處理」整理常見問題。不要把真實帳密、PIN、員工或患者
資料、CAPTCHA、session 值或完整日誌貼到公開 issue。

2.0.0 的正式簽章僅在院方管理的 Windows x64 電腦完成端到端驗證。本文件中的
macOS Python、瀏覽器及 OCR 內容只適用於應用程式層級檢查；部署範圍請參閱
[安裝指南](installation.md#部署與驗證範圍)，元件相容問題請參閱
[「macOS 出現 `61001`」](#macos-出現-61001)。

開始前請確認目前位於 AutoDigiSign 專案根目錄，不可停留在作業系統根目錄或系統
目錄，例如 Windows 的 `C:\Windows\System32` 或 macOS 的 `/`。請優先使用專案的
`.venv`。Windows 範例：

```bat
cd /d C:\Path\To\AutoDigiSign
.venv\Scripts\python.exe --version
```

macOS 範例：

```sh
cd /path/to/AutoDigiSign
.venv/bin/python --version
```

## 一、Python 與 `.venv`

### `AutoDigiSign requires Python 3.14.x`

程式只接受 Python 3.14.x。Windows 使用 `py -V:3.14` 建立 `.venv`；macOS 使用
`python3.14`。不要使用 3.13、3.15 或系統中另一套 Python。

### 建立 `.venv` 時出現 `[WinError 5] 存取被拒`

若錯誤路徑是 `C:\Windows\System32\.venv`，代表命令提示字元停留在系統目錄。
先切換至專案根目錄，再建立環境：

```bat
cd /d C:\Path\To\AutoDigiSign
py -V:3.14 -m venv .venv
```

不要在 `C:\Windows\System32` 建立專案環境，也不應用系統管理員權限繞過此問題。

### `ModuleNotFoundError: autodigisign` 或其他套件遺失

重新安裝專案與固定版本相依套件：

```bat
.venv\Scripts\python.exe -m pip install --editable .
.venv\Scripts\python.exe -m pip check
```

macOS 將 Python 路徑換成 `.venv/bin/python`。若是排程發生，另確認排程使用的確實
是目前專案 `.venv`，而不是系統 Python。

### macOS 無法雙擊 `launcher_macos.command`

若終端機顯示 `Permission denied`，請進入專案根目錄並設定一次執行權限：

```sh
chmod +x launcher_macos.command
```

若啟動檔顯示找不到 `.venv`，請依安裝指南重新建立專案虛擬環境；不要改用系統
Python，也不要以系統管理員權限執行啟動檔。

### OpenCV 顯示 `ImportError: DLL load failed`

Windows 應安裝 Microsoft 官方 Visual C++ Redistributable x64，並確認 Python
也是 x64。完成後重建 `.venv`；不要從另一台電腦複製 `.venv`。

## 二、Tesseract 與 CAPTCHA

### `Tesseract was not found`

`pytesseract` 只是 Python 介面，仍需安裝 Tesseract 應用程式。先執行：

```text
tesseract --version
```

若 Tesseract 位於非標準位置，設定 `TESSERACT_CMD` 為可執行檔的完整絕對路徑。
Windows 只套用於目前命令提示字元的設定方式：

```bat
set "TESSERACT_CMD=C:\Path\To\Tesseract-OCR\tesseract.exe"
launcher_win64.bat
```

需要讓之後的手動執行及同一使用者的工作排程持續使用時，執行 `setx`，再重新登入
Windows：

```bat
setx TESSERACT_CMD "C:\Path\To\Tesseract-OCR\tesseract.exe"
```

macOS 終端機可只針對一次手動執行指定：

```sh
TESSERACT_CMD="/absolute/path/to/tesseract" ./launcher_macos.command
```

macOS LaunchAgent 則必須在 plist 既有的 `EnvironmentVariables` `<dict>` 中加入：

```xml
<key>TESSERACT_CMD</key>
<string>/absolute/path/to/tesseract</string>
```

上述路徑都必須換成實際可執行檔位置。Windows 可執行
`"%TESSERACT_CMD%" --version`，macOS 可執行 `"$TESSERACT_CMD" --version`；再執行
AutoDigiSign，並從 INFO 確認實際選用的版本、來源與檔名。

### `CERTIFICATE_VERIFY_FAILED` 或 `Missing Subject Key Identifier`

目前版本直接由 Selenium 擷取瀏覽器已載入的 CAPTCHA，不再用第二個 HTTPS 連線
下載，因此不應再由 CAPTCHA 下載流程觸發這個憑證鏈錯誤。若仍看到舊訊息，先確認
執行的是目前專案與 `.venv`，並檢查 DEBUG traceback 的模組路徑。

### CAPTCHA 持續辨識失敗

正式環境 CAPTCHA 必須恰為六碼，且只含 `0-9`、`A-Z`。程式會依序嘗試多種
二值化及 Tesseract 分頁策略，格式不符才換下一個方法或要求新圖。

請確認：

- 瀏覽器中 CAPTCHA 圖片可正常完整顯示。
- Tesseract 可由相同使用者及排程環境執行。
- DEBUG 有 `CAPTCHA OCR strategy completed`，並檢查耗時、候選長度與
  `format_valid`；日誌不會記錄圖片或答案。
- 沒有公司端點防護軟體阻擋瀏覽器截圖或 Tesseract。

CAPTCHA 原圖與中間影像只存在記憶體，不會寫入本機，因此不會有新的
`outputs/captcha/` 可供檢查。

## 三、瀏覽器與 WebDriver

### Edge 或 Chrome 無法啟動

依序檢查：

1. 瀏覽器本身可以由目前使用者正常開啟。
2. DEBUG 中的瀏覽器版本、Driver 版本、平台與來源。
3. `webdrivers/` 是否可寫入，官方 Microsoft／Google 服務是否被網路政策封鎖。
4. 院方管理的 Edge 即使不是最新版本也可使用；程式會尋找相同 build 的歷史
   Driver。Chrome 備援須為 115 以上；不應為了配合程式自行更新資訊室管理的瀏覽器。

若網路無法下載，可從官方來源預先取得相容 Driver 放入 `webdrivers/`；程式會
遞迴檢查其實際 `--version`。不要只依資料夾名稱判定版本。

### Edge 失敗後改用 Chrome

這是預期備援行為。INFO／DEBUG 會記錄 Edge 失敗原因與最後選用的瀏覽器。若
Chrome 115 以上成功，工作可繼續；仍應在維護時段檢查 Edge 失敗原因。

## 四、HCAServiSign、卡片與讀卡機

### Windows 出現 `61001` 或 `ServiSign主程式-未安裝完成`

確認這是院方管理且獲授權的電腦，院方配置、與現行 NTUH 簽章頁面相容的
HCAServiSign 已安裝，而且本機服務正在執行。HCAServiSign 不是 Python 套件，
執行 `pip install` 不會安裝或修復它。若元件遺失或版本不符，請洽院方資訊室；
AutoDigiSign 不附帶也不會下載 HCAServiSign。

### macOS 出現 `61001`

本次針對 `HCAServiSignMacSetup_1.3.25.0827.pkg` 的診斷顯示，網頁呈現的 `61001`
可能包住底層 `61009`：舊版 macOS HCAServiSign 的 Path table 沒有院方現行簽章
頁面所使用的 Path ID。使用該套件自己的 Path ID 測試時，本機服務可以正常回應，
因此問題不是單純「主程式未安裝」、瀏覽器選錯或讀卡機未連線，而是院方頁面與
元件版本不相容。

重新安裝同一套舊版元件、改用 Edge／Chrome 或更換讀卡機，都不會補上缺少的配對
資料。請勿修改院方網頁 JavaScript 或 Path ID、重簽元件、以代理改寫要求、使用
Wine，或改裝 `MBGWServiSignSetup.exe`、其他 NTUH 服務或其他機構的 ServiSign
套件。這些做法不受支援，也可能破壞簽章信任鏈。

目前處理方式是改在已配置相容 HCAServiSign 的院方 Windows 電腦執行。日後若要
重新評估 macOS，必須由院方或元件廠商提供與當時簽章頁面相容的正式 macOS 安裝
套件，並先在同一台 Mac 完成人工及 AutoDigiSign 實際 PCSC 簽章。

### `[-1]查無錯誤代碼定義。`

AutoDigiSign 固定使用 PCSC 晶片讀卡機（無數字按鍵）與
`NTUHWeb1_btnDoSignatureByPCSC`。此訊息表示 PCSC 要求遭拒，可能接上了不支援的
HCIC 健保讀卡機（有數字按鍵），也可能是讀卡機型號、驅動或院方元件不相容。

程式會立即停止整批，避免所有員工重複失敗。請先以同一張卡、同一台讀卡機在網站
完成人工 PCSC 簽章，再恢復自動化。

### PIN 或卡片錯誤

確認 `credentials.ini` 的持卡人、入口網站帳號、目前插入的卡片與 PIN 相符。
不要反覆嘗試不確定的 PIN，以免卡片被鎖定；必要時依院方程序請資訊服務台協助。

## 五、簽章逾時或個別員工失敗

- 簽章彈出視窗最多等待 30 秒。
- 第一次收到「批次電子簽章作業中」後，處理最多等待 180 秒。
- 重複的作業中訊息不會延長 180 秒期限。
- 成功或錯誤等終止訊息會立即結束等待。

一般員工錯誤會記錄後繼續處理其餘名冊，但只要有一人失敗，程式最後就回傳非零
結束碼，郵件主旨也可能出現 `[Alert]`。讀卡機類型或無法恢復瀏覽器主視窗等全域
錯誤會立即停止整批。

若網站顯示完成但程式逾時，請保留已遮蔽的 DEBUG 診斷資訊，確認終止訊息文字及
實際完成時間是否與目前判讀規則不同。

## 六、設定檔與名冊

### 找不到 `credentials.ini` 或 `employee_list.txt`

全新 clone 不包含 `inputs/`。檔案只能從下列固定位置載入，不會遞迴搜尋其他地方：

```text
inputs/configs/credentials.ini
inputs/employee_list.txt
inputs/configs/email_config.ini  # 選用
```

請從 `examples/` 複製範例並替換所有預留值；不要把真實設定寫入 `examples/`。

### 名冊格式錯誤或同員編不同姓名

月份使用 `[YYYY-MM]`，永久員工使用 `[permanent]`，每列為 `<員編> <姓名>`。
同員編不同姓名會記錄設定錯誤、保留第一個有效姓名並處理一次；不同員編即使同名
仍分別處理。

## 七、日誌與郵件

### 沒有產生日誌

正常執行會在 `outputs/logs/<西元年>/<月份>/` 建立 INFO 與 DEBUG。若兩者都沒有，
檢查專案路徑及 `outputs/` 寫入權限；日誌初始化本身失敗時可能無法留下檔案。

### 沒有收到郵件

郵件是選用功能。先確認 `inputs/configs/email_config.ini` 存在且格式正確，再檢查：

- SMTP 主機、連接埠與收件者。
- Gmail 使用兩步驟驗證及 App Password，而不是一般密碼。
- Google 帳號密碼變更後，舊 App Password 是否已失效。
- 網路或防火牆是否允許 SMTP。
- INFO／DEBUG 中的寄送錯誤。

沒有 `email_config.ini` 時，程式只記錄 INFO 並跳過寄信，不影響本機兩份日誌。

## 八、仍無法解決時

先以一位獲授權測試員工進行受控手動執行，記錄發生時間、作業系統、瀏覽器版本、
Tesseract 版本、Driver 來源與已遮蔽的錯誤類型。公開回報只能提供去識別化摘要；
原始日誌若需傳送，必須使用院方核可管道及獲授權收件者。
