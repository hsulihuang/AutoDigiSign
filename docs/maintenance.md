# AutoDigiSign 日常維護指南

本指南的正式維護流程適用於已在院方管理的 Windows x64 電腦完成實際 PCSC 簽章
驗證的 AutoDigiSign。macOS 內容只供應用程式層級技術檢查與未來相容性參考。
第一次安裝與初次建立排程請依[安裝指南](installation.md)；發生錯誤時請參閱
[疑難排解](troubleshooting.md)。

除非另列完整路徑，下列路徑都以專案根目錄為基準。請將
`C:\Path\To\AutoDigiSign` 或 `/path/to/AutoDigiSign` 換成實際安裝位置。

## 一、維護原則

- 只能使用獲授權的作業系統帳號進行維護。
- 編輯設定或手動執行前，先確認沒有排程或其他手動執行中的 AutoDigiSign。
- 正式執行期間必須保持院方管理的 Windows 電腦喚醒、使用者登入，並備妥院方配置
  且與現行簽章頁面相容的 HCAServiSign、PCSC 晶片讀卡機（無數字按鍵）及
  醫事人員卡。
- 設定檔與名冊使用 UTF-8；不得將 `inputs/`、`outputs/`、`webdrivers/` 或
  `.venv/` 提交至 Git。
- 維護後先進行受控手動測試，確認實際結果及 INFO／DEBUG 日誌，再恢復排程。

## 二、快速索引

| 維護事項 | 檔案或位置 |
| --- | --- |
| 入口網站帳號、密碼或卡片 PIN | `inputs/configs/credentials.ini` |
| 員工名冊 | `inputs/employee_list.txt` |
| 選用郵件設定 | `inputs/configs/email_config.ini` |
| Windows 手動執行 | `launcher_win64.bat` |
| Windows 排程 | `scheduling/windows/`、Windows 工作排程器 |
| macOS 技術檢查（非正式簽章） | `launcher_macos.command` |
| macOS 未來排程參考 | `~/Library/LaunchAgents/com.autodigisign.agent.plist` |
| 執行結果 | `outputs/logs/<西元年>/<月份>/` |

## 三、更換醫事人員卡持有者或帳密

入口網站帳號、密碼、實體醫事人員卡或 PIN 變更時：

1. 暫停排程並確認程式沒有執行中。
2. 編輯 `inputs/configs/credentials.ini`：

   ```ini
   [credentials]
   username = <獲授權入口網站帳號>
   password = <入口網站密碼>
   pincode = <目前插入的醫事人員卡 PIN>
   ```

3. 確認帳號、卡片與 PIN 屬於同一名獲授權持卡人。
4. 先在院內網站完成人工簽章，再用一位測試員工進行受控執行。
5. 確認結果後恢復正式名冊與排程。

不要反覆嘗試不確定的 PIN，以免卡片被鎖定；也不可使用一般電子郵件或通訊軟體
傳送 `credentials.ini`、密碼或 PIN。

## 四、更新員工名冊

編輯 `inputs/employee_list.txt`。臨時員工使用 `[YYYY-MM]`，永久員工使用
`[permanent]`，每列為 `<員編> <姓名>`：

```text
[2026-08]
012345 Y1測試員工
142857 Y2測試員工

[2026-09]
142857 Y2測試員工
271828 Y1測試員工

[permanent]
161803 永久員工
```

- 跨月有效的臨時員工必須列在每個有效月份。
- PGY1、PGY2 姓名分別使用 `Y1`、`Y2` 前綴。
- 同員編同姓名只處理一次。
- 同員編不同姓名會回報設定錯誤、保留第一個有效姓名，並繼續簽章一次。
- 不同員編即使同名仍分別處理。

儲存後先以文字編輯器重新開啟，確認 UTF-8、區段括號與員編沒有被試算表軟體
改寫，再進行受控手動測試。

## 五、手動立即執行

### Windows

進入專案根目錄後雙擊 `launcher_win64.bat`，或執行：

```bat
cd /d C:\Path\To\AutoDigiSign
launcher_win64.bat
```

### macOS 技術檢查（非正式簽章）

本節僅供應用程式層級技術檢查，不能作為正式簽章使用；限制請參閱
[安裝指南](installation.md#部署與驗證範圍)。可在 Finder 雙擊專案根目錄的
`launcher_macos.command`，或在終端機執行：

```sh
cd /path/to/AutoDigiSign
./launcher_macos.command
```

若顯示 `Permission denied`，請在專案根目錄執行一次
`chmod +x launcher_macos.command`，再重新雙擊。

若網站回傳「查無待簽章電子病歷資料」，代表當次未呼叫 HCAServiSign，只能確認
登入及查詢流程，不能證明 macOS 簽章元件或實際簽章可用。

### 確認結果

每次執行會在 `outputs/logs/<西元年>/<月份>/` 產生有時間戳記的 INFO 與 DEBUG
日誌。INFO 保留執行流程及每位員工的員編、姓名與簽章結果；DEBUG 包含較詳細且
已遮蔽敏感值的診斷資訊。若啟用郵件，另確認獲授權收件者收到兩個附件。

程式結束碼為非零、郵件主旨出現 `[Alert]`，或日誌含 WARNING／ERROR 時，都應先
查明原因，不可只因後續員工成功就視為整批成功。

## 六、修改或停用自動排程

Windows 正式排程的第一次建立步驟以[安裝指南](installation.md)為準。

### Windows

下列時間只是預設值，並非程式固定值，可依需求自行修改。預設每日於 **06:30、
13:00、16:50、20:00、23:30** 執行。更新現有工作：

```bat
powershell.exe -NoProfile -File .\scheduling\windows\register-autodigisign-task.ps1 -Force
```

使用不同時間時，以 24 小時制 `HH:mm` 指定並覆寫舊工作：

```bat
powershell.exe -NoProfile -File .\scheduling\windows\register-autodigisign-task.ps1 -DailyTimes "06:30,13:00" -Force
```

移除排程但保留專案、設定、名冊及日誌：

```bat
powershell.exe -NoProfile -File .\scheduling\windows\unregister-autodigisign-task.ps1
```

更新後在工作排程器手動執行一次，確認 Last Run Result 與新日誌。工作必須設定為
只在獲授權使用者登入時執行，且前次尚未完成時不可啟動第二個執行個體。

### macOS（未來相容性參考）

只有符合[安裝指南的部署與驗證條件](installation.md#部署與驗證範圍)後，才可建立
或維護 LaunchAgent；目前不要建立正式 macOS 排程。範本預設每日於 **06:30、
13:00、16:50、20:00、23:30** 執行；日後修改已安裝的 plist 前先卸載：

```sh
launchctl bootout "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.autodigisign.agent.plist"
```

依需要修改 `StartCalendarInterval` 的 `Hour`、`Minute`，然後驗證、載入並立即測試：

```sh
plutil -lint "$HOME/Library/LaunchAgents/com.autodigisign.agent.plist"
launchctl bootstrap "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.autodigisign.agent.plist"
launchctl kickstart "gui/$(id -u)/com.autodigisign.agent"
launchctl print "gui/$(id -u)/com.autodigisign.agent"
```

若專案或 Tesseract 路徑變更，須同步更新 plist 中的 `launcher_macos.command`、
`WorkingDirectory` 或 `TESSERACT_CMD` 完整路徑。`.venv` 必須維持在專案根目錄，
由啟動檔自行尋找。

### 執行時間上限

每位有效員工的最壞情況約為 213 秒：彈出視窗 30 秒、第一次收到作業中訊息後
處理 180 秒，以及最多 3 秒視窗清理；另須預留登入、CAPTCHA 與頁面操作時間。

## 七、其他例行維護

### 選用郵件

SMTP 帳號、App Password 或收件者變更時，更新
`inputs/configs/email_config.ini` 並以手動執行確認。若不再需要郵件，可移除此
檔案；本機 INFO、DEBUG 日誌仍會產生。

### 瀏覽器與 WebDriver

Edge（優先）或 Chrome 115 以上（備援）更新後，下次執行會重用或下載相容 Driver。
舊版 Driver 依版本保留在 `webdrivers/`；除非院方儲存政策另有要求，不需要手動
刪除。下載失敗請查閱[疑難排解](troubleshooting.md)。

### Python 與相依套件

升級應安排在受控維護時段。專案更新後，在根目錄執行：

```bat
.venv\Scripts\python.exe -m pip install --editable .
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

macOS 將 `.venv\Scripts\python.exe` 換成 `.venv/bin/python`，但用途仍限於本指南
開頭所述的應用程式層級技術檢查。Windows 正式部署在測試通過後，仍須對確有待簽
資料的單一員工完成受控實際簽章，不要直接恢復無人值守排程。

### 日誌與本機資料

AutoDigiSign 不會自動刪除日誌，也未設定保存期限。請依院方政策保存、限制存取、
封存或處理 `outputs/logs/`、名冊及設定檔。CAPTCHA 圖片只在記憶體內處理，不會
寫入磁碟；舊版本留下的 `outputs/captcha/` 不再供目前版本使用。

## 八、維護完成檢查表

- [ ] 沒有重複的手動或排程執行個體。
- [ ] 帳號、密碼、卡片及 PIN 屬於同一名獲授權持卡人。
- [ ] 當月與永久名冊內容正確。
- [ ] 目標是已獲授權且由院方管理的 Windows 10／11 x64 電腦。
- [ ] Edge（優先）或 Chrome 115 以上（備援）至少一個可使用，且 Tesseract、院方配置
      的相容 HCAServiSign、PCSC 讀卡機及卡片均已就緒。
- [ ] 已對確有待簽資料的員工完成受控手動執行，並確認實際簽章結果；「查無待簽章
      電子病歷資料」不列為簽章驗證成功。
- [ ] 已檢查新產生的 INFO 與 DEBUG 日誌。
- [ ] 已確認選用郵件寄送結果。
- [ ] 已恢復排程，且立即測試成功。
