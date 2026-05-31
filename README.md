# JHL Warehouse Hotdeal Crawler

FMK hotdeal crawler that runs on an Android phone through Termux. It fetches the FMK hotdeal list, sends an hourly HTML email digest, and sends a special subject when a configured keyword is found.

## What It Does

- Runs directly on an Android phone, avoiding GitHub Actions IP blocking.
- Crawls `https://www.fmkorea.com/hotdeal`.
- Sends an HTML email digest once per hour at the configured minute.
- Watches configurable keywords such as `MX KEYS`.
- Uses a card-style email body with title, price, vote count, shop, and delivery.
- Skips temporary FMK security challenge responses instead of crashing.

## Email Subjects

Normal hourly digest:

```text
[HOTDEAL CRAWLER] 19시 핫딜 정보
```

Keyword alert:

```text
[HOTDEAL CRAWLER] MX KEYS 상품 핫딜이 발견되었습니다
```

## Repository Files

- `hotdeal_crawler.py`: crawler, keyword matching, HTML email rendering, and SMTP sending.
- `phone_deploy.sh`: Termux deployment script. It installs packages and writes phone-side helper scripts.
- `fmk_challenge.mjs`: lightweight helper used when FMK returns its security challenge.
- `.gitattributes`: keeps shell and Node helper scripts as LF so Termux can execute them.
- `.gitignore`: excludes local Android SDK/APK artifacts such as `platform-tools/` and `termux.apk`.

## Phone Setup

The current deployment target is a rooted Android device with USB debugging enabled.

1. Connect the phone to the PC by USB.
2. Confirm ADB can see it:

```powershell
.\platform-tools\adb.exe devices -l
```

3. Install Termux if needed:

```powershell
.\platform-tools\adb.exe install -r .\termux.apk
```

4. Open Termux once so its filesystem is initialized:

```powershell
.\platform-tools\adb.exe shell monkey -p com.termux -c android.intent.category.LAUNCHER 1
```

## Deploy Or Rebuild From PC

Use this after initial setup, after a phone reboot, or whenever repo files changed.

From this repository on Windows PowerShell:

```powershell
.\platform-tools\adb.exe push .\hotdeal_crawler.py /data/local/tmp/hotdeal_crawler.py
.\platform-tools\adb.exe push .\phone_deploy.sh /data/local/tmp/phone_deploy.sh
.\platform-tools\adb.exe push .\fmk_challenge.mjs /data/local/tmp/fmk_challenge.mjs
.\platform-tools\adb.exe shell run-as com.termux /data/data/com.termux/files/usr/bin/bash /data/local/tmp/phone_deploy.sh
```

The app is installed on the phone at:

```text
/data/data/com.termux/files/home/jhlwarehouse_hotdeal_crawler
```

The deploy script also performs one immediate test run. Successful output usually looks like:

```text
Fetched 20 hotdeal rows.
Watching keywords: MX KEYS
No keyword matches found.
Email sent.
```

## Phone Configuration

The phone-side `.env` file lives here:

```text
~/jhlwarehouse_hotdeal_crawler/.env
```

Expected values:

```sh
EMAIL_PASSWORD="your gmail app password"
EMAIL_SENDER=2joonh2@gmail.com
EMAIL_TO=2joonh2@gmail.com
HOTDEAL_INTERVAL_SECONDS=3600
HOTDEAL_RUN_MINUTE=3
HOTDEAL_KEYWORD_FILE=keywords.txt
HOTDEAL_ALERT_ONLY=false
```

`HOTDEAL_ALERT_ONLY=false` means the crawler sends the normal hourly digest even when no keyword matches. Set it to `true` to send only keyword alert emails.

`HOTDEAL_RUN_MINUTE=3` means the background loop runs once every hour at minute `03`, for example `10:03`, `11:03`, and `12:03`.

`HOTDEAL_INTERVAL_SECONDS` is kept only for backward compatibility. The current scheduler uses `HOTDEAL_RUN_MINUTE`.

## Start The Hourly Scheduler

The deploy script does not keep the background scheduler running forever by itself. Start it explicitly:

```sh
cd ~/jhlwarehouse_hotdeal_crawler
nohup ./run_loop.sh > logs/loop.stdout 2>&1 &
```

Check if it is running:

```sh
pgrep -af run_loop
```

Check the next scheduled run:

```sh
tail -10 logs/loop.out
```

Example:

```text
Next hotdeal run: 2026-05-31 14:03:00 +0900 (sleep 1343s)
```

Stop it:

```sh
pkill -f run_loop.sh
```

## Manual Run On Phone

Open Termux and run:

```sh
cd ~/jhlwarehouse_hotdeal_crawler
./run_once.sh
```

Use this to send a test email immediately without waiting for the next `HH:03`.

## Keyword Management On Phone

Keywords are stored in:

```text
~/jhlwarehouse_hotdeal_crawler/keywords.txt
```

Use the helper script:

```sh
cd ~/jhlwarehouse_hotdeal_crawler
./keyword.sh list
./keyword.sh add "MX KEYS"
./keyword.sh add "로지텍"
./keyword.sh remove "MX KEYS"
```

Keyword matching is case-insensitive and checks title, shop, price, and delivery text.

## Logs

Crawler result logs:

```sh
tail -40 ~/jhlwarehouse_hotdeal_crawler/logs/hotdeal.log
```

Scheduler logs:

```sh
tail -40 ~/jhlwarehouse_hotdeal_crawler/logs/loop.out
```

Startup stdout/stderr:

```sh
tail -40 ~/jhlwarehouse_hotdeal_crawler/logs/loop.stdout
```

## Reboot Recovery

If the phone powers off or reboots, the Termux process is gone. Rebuild/check the environment from PC, then start the scheduler again.

1. Confirm ADB sees the phone:

```powershell
.\platform-tools\adb.exe devices -l
```

2. Re-run deployment from PC:

```powershell
.\platform-tools\adb.exe push .\hotdeal_crawler.py /data/local/tmp/hotdeal_crawler.py
.\platform-tools\adb.exe push .\phone_deploy.sh /data/local/tmp/phone_deploy.sh
.\platform-tools\adb.exe push .\fmk_challenge.mjs /data/local/tmp/fmk_challenge.mjs
.\platform-tools\adb.exe shell run-as com.termux /data/data/com.termux/files/usr/bin/bash /data/local/tmp/phone_deploy.sh
```

3. Start the scheduler:

```powershell
.\platform-tools\adb.exe shell "run-as com.termux /data/data/com.termux/files/usr/bin/bash -lc 'nohup /data/data/com.termux/files/home/jhlwarehouse_hotdeal_crawler/run_loop.sh >/data/data/com.termux/files/home/jhlwarehouse_hotdeal_crawler/logs/loop.stdout 2>&1 &'"
```

4. Verify:

```powershell
.\platform-tools\adb.exe shell run-as com.termux /data/data/com.termux/files/usr/bin/pgrep -af run_loop.sh
.\platform-tools\adb.exe shell run-as com.termux /data/data/com.termux/files/usr/bin/tail -5 /data/data/com.termux/files/home/jhlwarehouse_hotdeal_crawler/logs/loop.out
```

## Android Reliability Notes

Termux does not need to stay open on screen, but Android may kill background work if battery optimization is enabled.

Recommended phone setting:

```text
Settings -> Apps -> Termux -> Battery -> Unrestricted / Not optimized
```

The loop calls `termux-wake-lock`, but battery optimization should still be disabled for reliability.

For automatic start after reboot, install and configure Termux:Boot.

## CRLF / LF Note

Termux shell scripts must use LF line endings. If `phone_deploy.sh` is uploaded with CRLF, Termux may fail with:

```text
set: pipefail: invalid option name
```

This repo includes `.gitattributes` to keep `.sh` and `.mjs` files LF-normalized. If a local copy still breaks, normalize before running:

```powershell
((Get-Content .\phone_deploy.sh -Raw) -replace "`r", "") | .\platform-tools\adb.exe shell run-as com.termux /data/data/com.termux/files/usr/bin/tee /data/data/com.termux/files/home/phone_deploy.sh > $null
.\platform-tools\adb.exe shell run-as com.termux /data/data/com.termux/files/usr/bin/bash /data/data/com.termux/files/home/phone_deploy.sh
```

## FMK Security Page

FMK sometimes returns a security challenge page or HTTP 430. The crawler handles this by skipping that run instead of crashing:

```text
FMK security challenge is still active; skipped this run.
```

The next scheduled run will retry automatically.
