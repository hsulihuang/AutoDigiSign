# AutoDigiSign 安裝指南

## 部署與驗證範圍

2.0.0 的正式部署限於已獲授權、由院方管理且已配置相容 HCAServiSign 的 Windows
10／11 x64 電腦；此環境已完成包含實際 PCSC 簽章的端到端驗證。macOS 內容僅供
應用程式技術準備與未來相容性參考，不代表正式簽章已通過驗證。完整發佈狀態請參閱
[README.md](../README.md#release-status--發佈狀態)。

疑難排解請參閱 [troubleshooting.md](troubleshooting.md)；專案概述與安全摘要請參閱
[README.md](../README.md)。

本文件提供 Windows 正式安裝、受控執行及自動排程手續，並保留 macOS 應用程式
技術準備與條件式 LaunchAgent 參考；日常換卡、更新帳密或名冊、立即執行及排程
維護，請參閱 [日常維護指南](maintenance.md)。

`.venv` 是這台電腦及此專案專用的隔離 Python 環境，不可從另一台電腦或不同
作業系統複製；換機時必須重新建立。`pip install --editable .` 會依
`pyproject.toml` 安裝 AutoDigiSign，並從 `requirements.txt` 讀取固定版本相依
套件。程式、啟動檔及排程都應使用專案 `.venv`，不要使用系統中的其他 Python。

本指南中的所有命令都必須在 AutoDigiSign 專案根目錄執行，不可停留在作業系統
根目錄或系統目錄，例如 Windows 的 `C:\Windows\System32` 或 macOS 的 `/`。


## 一、Windows 首次安裝

1. 請使用日後實際執行程式與工作排程的同一個獲授權 Windows 帳號。

2. 安裝下列軟硬體，並確認皆可正常使用：

   - Python 3.14.x
   - Microsoft Visual C++ Redistributable x64
   - Microsoft Edge（優先）或 Chrome 115 以上（備援），至少一個可正常使用
   - Tesseract OCR
   - 院方已在該電腦配置、且與現行 NTUH 簽章頁面相容的 HCAServiSign
   - PCSC 晶片讀卡機（無數字按鍵）及製造商驅動
   - 有效的醫事人員卡

   Python 請使用 Python.org 或 Microsoft Store 提供的官方 Python Install Manager，
   開啟新的命令提示字元後執行：

   ```bat
   py install 3.14
   py -V:3.14 --version
   ```

   結果必須是 `Python 3.14.x`。若 Store、MSIX 或下載被院內政策封鎖，請由
   資訊室部署官方 Python 3.14 x64，不要使用非官方重新封裝版本。

   Microsoft Visual C++ Redistributable 請使用 [Microsoft 官方頁面](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)
   提供的 x64 套件；
   缺少此元件時 OpenCV 可能發生 DLL 載入錯誤。Tesseract、HCAServiSign 與
   讀卡機驅動都不是 Python 套件，無法透過 `pip` 或 WebDriver 自動安裝。
   HCAServiSign 必須使用院方在目標電腦配置、且與現行簽章頁面配對的版本；
   AutoDigiSign 不附帶也不會下載該元件。若院方電腦尚未配置，請洽資訊室處理，
   不要自行安裝舊版、一般用途或其他服務的 ServiSign 套件。資訊室管理的稍舊 Edge
   版本可以使用，不必自行更新。

   Tesseract 若安裝在非標準位置，可先在目前的命令提示字元指定完整路徑：

   ```bat
   set "TESSERACT_CMD=C:\Path\To\Tesseract-OCR\tesseract.exe"
   ```

   如需讓同一位使用者之後開啟的命令提示字元與工作排程都能取得此設定，可執行：

   ```bat
   setx TESSERACT_CMD "C:\Path\To\Tesseract-OCR\tesseract.exe"
   ```

   `setx` 不會改變目前已開啟的程序；完成後請重新登入 Windows，再進行手動測試及
   建立工作排程。請將範例路徑換成實際的 `tesseract.exe`，不要將引號寫入變數值。

3. 啟用自動簽章前，請先在同一台電腦完成人工簽章。請勿反覆輸入錯誤 PIN，
   以免醫事人員卡被鎖定。

4. 透過 Git clone 或 GitHub 的 **Code > Download ZIP** 取得專案，存放在獲授權
   使用者的本機資料夾，不要放在共用或雲端同步位置。開啟「命令提示字元」並進入
   專案根目錄：

   ```bat
   cd /d C:\Path\To\AutoDigiSign
   ```

5. 建立專案專用 Python 環境並安裝套件：

   ```bat
   py -V:3.14 -m venv .venv
   .venv\Scripts\python.exe -m pip install --upgrade pip
   .venv\Scripts\python.exe -m pip install --editable .
   ```

6. 透過 Git clone 或下載 ZIP 取得的新專案不包含本機資料目錄，請自行建立：

   ```bat
   if not exist inputs\configs mkdir inputs\configs
   if not exist outputs\logs mkdir outputs\logs
   if not exist webdrivers mkdir webdrivers
   ```

   程式會依目前的瀏覽器版本檢查 WebDriver；若本機沒有相容版本，會自動下載，
   並保留既有的舊版本。

7. 從不含真實資料的範例建立必要輸入檔：

   ```bat
   copy examples\credentials.ini.example inputs\configs\credentials.ini
   copy examples\employee_list.txt.example inputs\employee_list.txt
   ```

   只有需要寄送郵件時才另外執行：

   ```bat
   copy examples\email_config.ini.example inputs\configs\email_config.ini
   ```


## 二、macOS 技術準備（僅供技術檢查）

本節只準備 AutoDigiSign 的 Python、瀏覽器／WebDriver 與 OCR 環境，不會安裝或
取代 HCAServiSign，也不構成正式簽章部署；限制請見[部署與驗證範圍](#部署與驗證範圍)。

1. 請使用進行技術檢查的獲授權 macOS 帳號。若未來符合正式部署條件，必須由同一
   帳號執行程式與 LaunchAgent。不要將專案放在共用或雲端同步資料夾。

2. 安裝下列應用程式，並確認皆可正常使用：

   - Python 3.14.x
   - Microsoft Edge（優先）或 Chrome 115 以上（備援），至少一個可正常使用
   - Tesseract OCR

   若院方允許使用 Homebrew，可安裝 Python 及 Tesseract：

   ```sh
   brew install python@3.14 tesseract
   ```

   若無法使用 Homebrew，請從院方或官方核可來源安裝，並確認下列命令可執行：

   ```sh
   python3.14 --version
   tesseract --version
   ```

3. 請勿以舊版或一般用途的 macOS HCAServiSign、其他 NTUH 服務使用的 ServiSign、
   Windows 的 `MBGWServiSignSetup.exe`，或其他機構的安裝套件替代。修改網頁
   JavaScript／Path ID、重簽元件、透過代理改寫要求或使用 Wine，也不是受支援的
   解決方式。技術原因請參閱[疑難排解](troubleshooting.md#macos-出現-61001)；只有
   符合本指南開頭所列條件後，才能重新評估正式部署。

4. 透過 Git clone 或下載 ZIP 取得專案，開啟「終端機」並進入專案根目錄：

   ```sh
   cd /path/to/AutoDigiSign
   ```

   確認 macOS 啟動檔可執行；Git clone 通常會保留此權限，但下載 ZIP 後可能需要
   手動設定一次：

   ```sh
   chmod +x launcher_macos.command
   ```

5. 建立專案專用 Python 環境並安裝套件：

   ```sh
   python3.14 -m venv .venv
   .venv/bin/python -m pip install --upgrade pip
   .venv/bin/python -m pip install --editable .
   ```

6. 建立本機資料目錄：

   ```sh
   mkdir -p inputs/configs outputs/logs webdrivers
   ```

   程式會依目前的瀏覽器版本檢查 WebDriver；若本機沒有相容版本，會自動下載，
   並保留既有的舊版本。Homebrew 安裝的 Tesseract 通常可自動找到；若安裝於
   非標準位置，可在終端機以完整絕對路徑執行：

   ```sh
   TESSERACT_CMD="/absolute/path/to/tesseract" ./launcher_macos.command
   ```

   此設定只套用於這次手動技術檢查；LaunchAgent 的條件式設定方式請參閱第九節。

7. 從範例建立必要輸入檔；只有需要寄送郵件時才複製郵件範例：

   ```sh
   cp examples/credentials.ini.example inputs/configs/credentials.ini
   cp examples/employee_list.txt.example inputs/employee_list.txt
   # Optional:
   cp examples/email_config.ini.example inputs/configs/email_config.ini
   ```


## 三、建立員工名冊

編輯由 `examples/employee_list.txt.example` 複製而來的
`inputs/employee_list.txt`，並將檔案儲存為 UTF-8。

臨時員工使用 [YYYY-MM] 區段，永久員工使用 [permanent] 區段：

```text
[2026-08]
012345 Y1測試員工
142857 Y2測試員工

[2026-09]
142857 Y2測試員工
114514 Y1測試員工

[permanent]
009487 永久員工
```

注意：

- 每列格式為「員編 姓名」。
- 同一臨時員工若跨多個月份有效，必須列在每個有效月份。
- PGY1 姓名前加上 Y1，PGY2 姓名前加上 Y2。
- 員編與姓名皆相同時，只處理一次。
- 同一員編出現不同姓名時，程式會記錄設定錯誤，保留第一個有效姓名，並只簽章一次。
- 不同員編即使姓名相同，仍會分別處理。


## 四、建立帳密設定

編輯由 `examples/credentials.ini.example` 複製而來的
`inputs/configs/credentials.ini`，替換全部預留值並以 UTF-8 儲存：

```ini
[credentials]
username = <入口網站員工編號>
password = <入口網站密碼>
pincode = <醫事人員卡 PIN>
```

AutoDigiSign 一律使用 PCSC 晶片讀卡機（無數字按鍵），不使用 HCIC 健保讀卡機
（有數字按鍵），並一律點擊 `NTUHWeb1_btnDoSignatureByPCSC`。
彈出視窗必須在 30 秒內出現；網頁第一次回傳「批次電子簽章作業中」後，
另開始計算 180 秒處理期限，重複出現作業中訊息不會重設期限。收到成功或錯誤等
終止訊息時會立即結束等待。

若個別員工發生可復原的錯誤，程式會記錄錯誤並繼續處理其餘員工；只要有一位以上
失敗，程式最後就會回傳非零結束碼，避免工作排程器誤報成功。

網頁若回傳「[-1]查無錯誤代碼定義。」，程式會立即回報錯誤並停止批次，
提示可能誤接了本程式不支援的 HCIC 健保讀卡機（有數字按鍵），而不是必要的
PCSC 晶片讀卡機（無數字按鍵）。


## 五、郵件設定（選用）

如需寄送執行結果，從 `examples/email_config.ini.example` 複製並建立
`inputs/configs/email_config.ini`：

```ini
[email]
smtp_server = smtp.gmail.com
smtp_port = 587
sender_email = <寄件帳號>
sender_password = <應用程式密碼>
recipients = <收件者一>, <收件者二>
```

未建立此檔案時，程式會在 INFO 日誌中記錄跳過寄信的訊息，並略過寄信；
本機仍會照常產生 INFO 與 DEBUG 日誌。

Gmail 必須啟用兩步驟驗證並使用 App Password，不可填入一般帳號密碼；若管理型
帳號禁止 App Password，請改用院方核可的 SMTP 服務。

可由 [Google 帳戶安全性設定](https://myaccount.google.com/security)啟用兩步驟
驗證，並在 [Google App Passwords](https://myaccount.google.com/apppasswords)
建立專用密碼。Google 帳號密碼變更後，舊 App Password 會失效。

請勿使用一般電子郵件傳送 `credentials.ini`、入口網站密碼或卡片 PIN。


## 六、程式環境驗證

Windows 在專案根目錄執行：

```bat
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import autodigisign"
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

macOS 在專案根目錄執行：

```sh
.venv/bin/python --version
.venv/bin/python -c "import autodigisign"
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v
```

確認：

- Python 顯示 3.14.x。
- pip check 顯示 No broken requirements found。
- 2.0.0 應顯示 `Ran 67 tests`，且最後顯示 `OK`。
- Edge（優先）或 Chrome 115 以上（備援）至少一個可正常使用，且 Tesseract 可正常使用。
- `inputs/employee_list.txt` 與 `inputs/configs/credentials.ini` 內容正確。

上述命令只驗證 Python 套件與程式測試，不會呼叫 HCAServiSign，也不等於電子病歷
簽章驗證。Windows 正式部署還必須確認院方配置的相容 HCAServiSign、PCSC 晶片
讀卡機及醫事人員卡均可使用，並依下一節完成一筆實際簽章；macOS 測試全部通過，
也只代表應用程式層級驗證。


## 七、Windows 第一次受控正式執行

1. 先用相同帳號、卡片及 PCSC 讀卡機在同一台院方 Windows 電腦完成人工簽章。
2. 名冊暫時只保留一位獲授權且已確認有待簽章資料的測試員工。
3. 雙擊專案根目錄的 `launcher_win64.bat`。
4. 確認 AutoDigiSign 實際完成 PCSC 簽章，並核對網站結果。
5. 檢查 `outputs/logs/<西元年>/<月份>/` 內的 INFO 與 DEBUG 日誌。
6. 若已設定郵件，確認收到 INFO 與 DEBUG 兩個附件。
7. 測試成功後，再恢復正式名冊並建立工作排程。

院方網頁會先檢查有無待簽章病歷；若沒有，便直接回傳「查無待簽章電子病歷資料」，
不會呼叫 HCAServiSign。這種結果只能驗證登入與查詢流程，不能作為簽章元件或實際
簽章成功的證明。

`launcher_macos.command` 目前僅供應用程式層級技術檢查，不得據此認定正式驗證
完成或建立正式排程。


## 八、Windows 工作排程器

只有受控實機測試成功後才建立排程。以實際執行 AutoDigiSign 的同一獲授權帳號開啟命令提示字元，進入專案根目錄後執行：

```bat
powershell.exe -NoProfile -File .\scheduling\windows\register-autodigisign-task.ps1
```

腳本會建立名為 `AutoDigiSign` 的工作，每日於 **06:30、13:00、16:50、20:00、23:30** 觸發。它會自動使用目前的專案路徑及登入帳號、執行 `launcher_win64.bat --scheduled`、只在使用者登入時執行、防止工作重疊，並設定四小時執行上限。腳本不會保存 Windows 密碼、入口網站密碼或卡片 PIN。

上述五個時間是腳本預設值，並非程式固定值，可依需求使用逗號分隔的 24 小時制
`HH:mm` 自行指定。例如，第一次建立時只安排 06:30 與 13:00：

```bat
powershell.exe -NoProfile -File .\scheduling\windows\register-autodigisign-task.ps1 -DailyTimes "06:30,13:00"
```

工作已存在時，先檢查目前設定，再加入 `-Force` 更新：

```bat
powershell.exe -NoProfile -File .\scheduling\windows\register-autodigisign-task.ps1 -Force
```

更新既有工作並同時修改時間時，將 `-DailyTimes "HH:mm,HH:mm"` 與 `-Force` 一併加入。

若院方 PowerShell 政策禁止執行本機腳本，不要降低安全政策；改用「建立工作」手動設定：

- 使用者帳戶：與實際操作瀏覽器、HCAServiSign 及讀卡機的帳號相同。
- 安全性：選擇「僅在使用者登入時執行」。
- 觸發程序：每日 06:30、13:00、16:50、20:00、23:30。
- Program/script：`C:\Windows\System32\cmd.exe`
- Add arguments：`/d /c ""C:\Path\To\AutoDigiSign\launcher_win64.bat" --scheduled"`
- Start in：`C:\Path\To\AutoDigiSign`
- 若工作已在執行中：選擇「不啟動新的執行個體」。
- 錯過開始時間：選擇「排定的開始時間過後，立即啟動工作」。
- 執行上限：四小時。

Start in 只能填目錄，不要加引號。所有路徑必須改成這台電腦的實際絕對路徑。
電腦必須保持喚醒、使用者已登入，且讀卡機與醫事人員卡已接妥。

建立後先手動按一次「執行」，確認 Last Run Result，並檢查
`outputs\logs\<西元年>\<月份>` 內的 INFO 與 DEBUG 日誌。排程的最大執行時間至少須涵蓋
「當月有效員工數 × 每人約 213 秒」的最壞情況；每人包含彈出視窗 30 秒、
簽章處理 180 秒及最多 3 秒的視窗清理，並須額外預留登入、CAPTCHA 辨識與
頁面操作時間。

若要移除工作，執行下列腳本並確認；專案、設定、名冊及日誌都會保留：

```bat
powershell.exe -NoProfile -File .\scheduling\windows\unregister-autodigisign-task.ps1
```


## 九、macOS LaunchAgent（未來相容性參考）

2.0.0 目前尚無法使用 macOS LaunchAgent 建立正式簽章排程。以下內容僅供未來參考，
且只有符合[部署與驗證範圍](#部署與驗證範圍)所列條件後才可使用。不要建立系統
LaunchDaemon。在專案根目錄執行：

```sh
mkdir -p "$HOME/Library/LaunchAgents"
cp scheduling/macos/com.autodigisign.agent.plist.example \
  "$HOME/Library/LaunchAgents/com.autodigisign.agent.plist"
chmod 600 "$HOME/Library/LaunchAgents/com.autodigisign.agent.plist"
```

編輯已複製的 plist，將所有 `/ABSOLUTE/PATH/TO/AutoDigiSign` 換成這台 Mac
實際的專案根目錄。範本中的完整路徑分別用於：

- `launcher_macos.command`（以 `--scheduled` 模式執行）
- `WorkingDirectory` 指向 AutoDigiSign 專案根目錄

啟動檔會自行使用專案 `.venv/bin/python` 並設定 `PYTHONPATH`，行為與 Windows
工作排程呼叫 `launcher_win64.bat --scheduled` 一致；排程模式不會倒數或等待按鍵。

範本已設定每日 **06:30、13:00、16:50、20:00、23:30** 五個觸發時間，且
`RunAtLoad=false`。只有核定時間不同時才修改 `StartCalendarInterval` 內的
`Hour` 與 `Minute`。Tesseract 位於非標準位置時，在 `EnvironmentVariables`
既有的 `<dict>` 中加入 `TESSERACT_CMD` 與完整路徑：

```xml
<key>TESSERACT_CMD</key>
<string>/absolute/path/to/tesseract</string>
```

不要建立第二個 `EnvironmentVariables`；修改後必須依下列步驟重新驗證與載入。

驗證、載入並確認狀態：

```sh
plutil -lint "$HOME/Library/LaunchAgents/com.autodigisign.agent.plist"
launchctl bootstrap "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.autodigisign.agent.plist"
launchctl print "gui/$(id -u)/com.autodigisign.agent"
```

符合上述前置條件後，立即進行一次受控測試：

```sh
launchctl kickstart "gui/$(id -u)/com.autodigisign.agent"
```

LaunchAgent 必須以獲授權使用者登入，且執行時 Mac 保持喚醒；院方提供且與現行
頁面相容的 HCAServiSign、PCSC 晶片讀卡機（無數字按鍵）及醫事人員卡均須就緒。
測試後檢查
`launchctl print`，並確認 `outputs/logs/<西元年>/<月份>/` 內新產生的 INFO 與
DEBUG 日誌。

修改已載入的 plist 前，先卸載；修改後重新執行 `plutil -lint` 與
`launchctl bootstrap`：

```sh
launchctl bootout "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.autodigisign.agent.plist"
```


## 十、受限或離線環境

若醫院電腦無法連線公共 Python 套件服務，請在另一台可上網且同為 Windows x64、
Python 3.14 的電腦準備套件，不要在 macOS 下載 Windows 套件：

```bat
py -V:3.14 -m pip download --dest wheelhouse -r requirements.txt "setuptools>=77"
```

透過院方核可方式移轉專案與 `wheelhouse/`，在目標電腦建立 `.venv` 後執行：

```bat
.venv\Scripts\python.exe -m pip install --no-index --find-links=wheelhouse "setuptools>=77"
.venv\Scripts\python.exe -m pip install --no-index --find-links=wheelhouse -r requirements.txt
.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps --editable .
```

若 Microsoft 或 Google 官方 WebDriver 服務也被封鎖，第一次執行前將經官方來源
取得、且與瀏覽器相容的 Driver 放入 `webdrivers/`。程式會遞迴執行 `--version`
確認版本，不依賴固定檔名以外的舊資料夾名稱。


## 十一、移轉既有安裝

換電腦時只需透過核可方式移轉下列本機輸入：

```text
inputs/configs/credentials.ini
inputs/configs/email_config.ini  # 啟用郵件時才需要
inputs/employee_list.txt
```

請在新電腦重新建立 `.venv`、取得與該電腦瀏覽器相容的 WebDriver，並在通過實際
簽章驗證後重新建立 Windows 工作排程。macOS LaunchAgent 亦須符合本指南開頭的
部署與驗證條件才可建立。不要跨作業系統複製 `.venv`；舊日誌及舊 CAPTCHA 圖片
不是安裝必要資料，應依院方政策另行封存或處理。

若既有安裝仍使用舊名稱 `WebDriver/`，更新程式後請保留其內容並將資料夾改名為
`webdrivers/`；否則程式不會在新位置找到舊 Driver，可能需要重新下載。


## 十二、資料安全

- `inputs`、`outputs`、`webdrivers` 與 `.venv` 均為本機檔案或目錄，不應提交至 Git。
- INFO 日誌保留員編、姓名及簽章結果，DEBUG 日誌包含較詳細的除錯資訊。
- 程式會遮蔽密碼、PIN、CAPTCHA、工作階段（session）權杖等敏感內容；
  日誌仍只能透過院方核可的方式保存與傳送。
- CAPTCHA 圖片與影像處理過程只存在記憶體，不會寫入磁碟；DEBUG 只記錄耗時、
  辨識策略、候選長度與六碼格式驗證結果，不會記錄圖片或辨識值。
- 本專案不會自動刪除日誌；請依院方政策保存、封存或清理。
