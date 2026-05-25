# JHL Warehouse Hotdeal Crawler

FMK hotdeal crawler that runs on an Android phone through Termux. It fetches the FMK hotdeal list, sends an hourly email digest, and sends a special email subject when a configured keyword is found.

## What It Does

- Runs directly on an Android phone, avoiding GitHub Actions IP blocking.
- Crawls `https://www.fmkorea.com/hotdeal`.
- Sends an HTML email digest every hour.
- Watches configurable keywords such as `MX KEYS`.
- Uses a richer card-style email body with title, price, vote count, shop, and delivery.

## Email Subjects

Normal hourly digest:

```text
[HOTDEAL CRAWLER] 19시 핫딜 정보
```

Keyword alert:

```text
[HOTDEAL CRAWLER] MX KEYS 상품 핫딜이 발견되었습니다
```

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

## Deploy From PC

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
HOTDEAL_KEYWORD_FILE=keywords.txt
HOTDEAL_ALERT_ONLY=false
```

`HOTDEAL_ALERT_ONLY=false` means the crawler sends the normal hourly digest even when no keyword matches. Set it to `true` to send only keyword alert emails.

## Manual Run On Phone

Open Termux and run:

```sh
cd ~/jhlwarehouse_hotdeal_crawler
./run_once.sh
```

Expected successful output:

```text
Fetched 20 hotdeal rows.
Watching keywords: MX KEYS
No keyword matches found.
Email sent.
```

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

## Background Loop

Start the hourly loop:

```sh
cd ~/jhlwarehouse_hotdeal_crawler
nohup ./run_loop.sh > logs/loop.out 2>&1 &
```

Check if it is running:

```sh
pgrep -af run_loop
```

Check logs:

```sh
tail -40 logs/hotdeal.log
```

Stop it:

```sh
pkill -f run_loop.sh
```

## Android Reliability Notes

Termux does not need to stay open on screen, but Android may kill background work if battery optimization is enabled.

Recommended phone setting:

```text
Settings -> Apps -> Termux -> Battery -> Unrestricted / Not optimized
```

After phone reboot, start the loop again manually:

```sh
cd ~/jhlwarehouse_hotdeal_crawler
nohup ./run_loop.sh > logs/loop.out 2>&1 &
```

For automatic start after reboot, install and configure Termux:Boot.

## FMK Security Page

FMK sometimes returns a security challenge page or HTTP 430. The crawler handles this by skipping that run instead of crashing:

```text
FMK security challenge is still active; skipped this run.
```

The next scheduled run will retry automatically.
