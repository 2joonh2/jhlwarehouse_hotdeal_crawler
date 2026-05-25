import asyncio
import html
import os
import smtplib
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.fmkorea.com"
HOTDEAL_URL = f"{BASE_URL}/hotdeal"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_KEYWORDS = ["MX KEYS"]
DEFAULT_KEYWORD_FILE = "keywords.txt"
KST = timezone(timedelta(hours=9))


@dataclass
class HotdealFrame:
    rows: list[dict[str, str]]

    @property
    def empty(self) -> bool:
        return not self.rows

    def __iter__(self) -> Iterable[dict[str, str]]:
        return iter(self.rows)


def parse_keywords() -> list[str]:
    keyword_file = os.environ.get("HOTDEAL_KEYWORD_FILE", DEFAULT_KEYWORD_FILE)
    if not os.path.isabs(keyword_file):
        keyword_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), keyword_file)

    keywords = []
    if os.path.exists(keyword_file):
        with open(keyword_file, "r", encoding="utf-8") as file:
            keywords.extend(
                line.strip()
                for line in file
                if line.strip() and not line.lstrip().startswith("#")
            )

    raw_keywords = os.environ.get("HOTDEAL_KEYWORDS", "")
    keywords.extend(keyword.strip() for keyword in raw_keywords.split(",") if keyword.strip())

    deduped = []
    seen = set()
    for keyword in keywords:
        key = keyword.casefold()
        if key not in seen:
            deduped.append(keyword)
            seen.add(key)

    return deduped or DEFAULT_KEYWORDS


def find_matching_keyword(row: dict[str, str], keywords: list[str]) -> str:
    haystack = " ".join(
        [
            row.get("Title", ""),
            row.get("Shop", ""),
            row.get("Price", ""),
            row.get("Delivery", ""),
        ]
    ).casefold()

    for keyword in keywords:
        if keyword.casefold() in haystack:
            return keyword
    return ""


def filter_matches(df: HotdealFrame, keywords: list[str]) -> HotdealFrame:
    rows = []
    for row in df.rows:
        matched_keyword = find_matching_keyword(row, keywords)
        if matched_keyword:
            rows.append({**row, "MatchedKeyword": matched_keyword})
    return HotdealFrame(rows)


def _info_values(info) -> dict[str, str]:
    values = []
    for span in info.select("span"):
        text = span.get_text(" ", strip=True)
        values.append(text.split(":", 1)[-1].strip())

    return {
        "Shop": values[0] if len(values) > 0 else "",
        "Price": values[1] if len(values) > 1 else "",
        "Delivery": values[2] if len(values) > 2 else "",
    }


def fetch_hotdeals() -> HotdealFrame:
    response = _request_hotdeal()
    if response.status_code == 430:
        cookies = _solve_fmk_challenge()
        if cookies:
            response = _request_hotdeal(cookies=cookies)
    if response.status_code == 430:
        print("FMK security challenge is still active; skipped this run.")
        return HotdealFrame([])
    response.raise_for_status()

    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")
    if soup.title and "security" in soup.title.get_text(" ", strip=True).casefold():
        return HotdealFrame([])

    container = soup.select_one("div.fm_best_widget._bd_pc")
    if not container:
        return HotdealFrame([])

    rows: list[dict[str, str]] = []
    for item in container.find_all("li"):
        title_link = item.select_one("h3.title a[href]")
        if not title_link:
            continue

        title_target = title_link.select_one(".ellipsis-target")
        title = title_target.get_text(" ", strip=True) if title_target else title_link.get_text(" ", strip=True)
        url = urljoin(BASE_URL, title_link["href"])
        vote_tag = item.select_one(".pc_voted_count .count")
        info = item.select_one(".hotdeal_info")
        info_values = _info_values(info) if info else {"Shop": "", "Price": "", "Delivery": ""}

        rows.append(
            {
                "Title": title,
                "URL": url,
                "Vote": vote_tag.get_text(strip=True) if vote_tag else "0",
                "Shop": info_values["Shop"],
                "Price": info_values["Price"],
                "Delivery": info_values["Delivery"],
                "MatchedKeyword": "",
            }
        )

    return HotdealFrame(rows)


def _request_hotdeal(cookies: dict[str, str] | None = None) -> requests.Response:
    return requests.get(
        HOTDEAL_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        cookies=cookies,
        timeout=30,
    )


def _solve_fmk_challenge() -> dict[str, str]:
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fmk_challenge.mjs")
    if not os.path.exists(script_path):
        return {}

    try:
        result = subprocess.run(
            ["node", script_path, HOTDEAL_URL, USER_AGENT],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return {}

    cookies = {}
    for cookie in result.stdout.strip().split(";"):
        if "=" not in cookie:
            continue
        name, value = cookie.strip().split("=", 1)
        cookies[name] = value
    return cookies


async def get_hotdeal_df() -> HotdealFrame:
    return await asyncio.to_thread(fetch_hotdeals)


def build_subject(df: HotdealFrame, is_alert: bool) -> str:
    if not is_alert:
        hour = datetime.now(KST).strftime("%H")
        return f"[HOTDEAL CRAWLER] {hour}\uc2dc \ud56b\ub51c \uc815\ubcf4"

    first = df.rows[0]
    matched_keyword = first.get("MatchedKeyword") or "keyword"
    return f"[HOTDEAL CRAWLER] {matched_keyword} \uc0c1\ud488 \ud56b\ub51c\uc774 \ubc1c\uacac\ub418\uc5c8\uc2b5\ub2c8\ub2e4"


def render_email_body(df: HotdealFrame, *, is_alert: bool, keywords: list[str] | None = None) -> str:
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    keywords = keywords or []
    title = (
        "\ud0a4\uc6cc\ub4dc \ud56b\ub51c\uc744 \ucc3e\uc558\uc2b5\ub2c8\ub2e4"
        if is_alert
        else "\uc774\ubc88 \uc2dc\uac04 \ud56b\ub51c \uc815\ubcf4"
    )
    subtitle = (
        "\ub4f1\ub85d\ud55c \ud0a4\uc6cc\ub4dc\uc640 \ub9e4\uce6d\ub41c \uc0c1\ud488\ub9cc \ubaa8\uc558\uc2b5\ub2c8\ub2e4."
        if is_alert
        else "FMK \ud56b\ub51c \uac8c\uc2dc\ud310\uc5d0\uc11c \uc218\uc9d1\ud55c \ucd5c\uc2e0 \uc0c1\ud488\uc785\ub2c8\ub2e4."
    )
    accent = "#b42318" if is_alert else "#175cd3"
    chip_background = "#fee4e2" if is_alert else "#d1e9ff"
    chip_text = "#912018" if is_alert else "#1849a9"
    keyword_text = ", ".join(html.escape(keyword) for keyword in keywords) if keywords else "-"

    cards = []
    for index, row in enumerate(df.rows, start=1):
        title_text = html.escape(row.get("Title", ""))
        url = html.escape(row.get("URL", ""), quote=True)
        shop = html.escape(row.get("Shop", "") or "-")
        price = html.escape(row.get("Price", "") or "-")
        delivery = html.escape(row.get("Delivery", "") or "-")
        vote = html.escape(row.get("Vote", "0") or "0")
        matched_keyword = row.get("MatchedKeyword", "")
        keyword_badge = ""
        if matched_keyword:
            keyword_badge = (
                f'<span style="display:inline-block;margin-left:8px;padding:3px 8px;'
                f'border-radius:999px;background:#fff1f3;color:#c01048;font-size:12px;'
                f'font-weight:700;">{html.escape(matched_keyword)}</span>'
            )

        cards.append(
            f"""
            <tr>
              <td style="padding:0 0 12px 0;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e4e7ec;border-radius:10px;background:#ffffff;">
                  <tr>
                    <td style="padding:16px 18px;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                          <td style="vertical-align:top;padding-right:12px;">
                            <div style="font-size:12px;color:#667085;margin-bottom:7px;">#{index}{keyword_badge}</div>
                            <a href="{url}" style="font-size:17px;line-height:1.45;color:#101828;text-decoration:none;font-weight:700;">{title_text}</a>
                          </td>
                          <td style="vertical-align:top;text-align:right;width:150px;">
                            <div style="display:inline-block;padding:7px 11px;border-radius:8px;background:#ecfdf3;color:#027a48;font-size:18px;line-height:1.2;font-weight:800;white-space:nowrap;">{price}</div>
                            <div style="margin-top:7px;display:inline-block;padding:5px 9px;border-radius:8px;background:#fff7ed;color:#c2410c;font-size:15px;line-height:1.2;font-weight:800;white-space:nowrap;">\ucd94\ucc9c {vote}</div>
                          </td>
                        </tr>
                      </table>
                      <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:14px;">
                        <tr>
                          <td style="padding:5px 10px;border-radius:6px;background:#f2f4f7;color:#344054;font-size:13px;">{shop}</td>
                          <td style="width:8px;"></td>
                          <td style="padding:5px 10px;border-radius:6px;background:#f9f5ff;color:#6941c6;font-size:13px;">{delivery}</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            """
        )

    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;color:#101828;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f7fb;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="width:640px;max-width:94%;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e4e7ec;">
            <tr>
              <td style="padding:26px 28px;background:#ffffff;border-top:5px solid {accent};">
                <div style="font-size:12px;font-weight:700;letter-spacing:.08em;color:{accent};">HOTDEAL CRAWLER</div>
                <h1 style="margin:10px 0 8px 0;font-size:24px;line-height:1.35;color:#101828;">{title}</h1>
                <div style="font-size:14px;line-height:1.6;color:#475467;">{subtitle}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 18px 28px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border-radius:10px;">
                  <tr>
                    <td style="padding:14px 16px;font-size:13px;color:#475467;">
                      <span style="display:inline-block;padding:4px 9px;border-radius:999px;background:{chip_background};color:{chip_text};font-weight:700;">{len(df.rows)} items</span>
                      <span style="margin-left:10px;">\uc218\uc9d1 \uc2dc\uac01: {html.escape(now)} KST</span>
                      <div style="margin-top:8px;">\uac10\uc2dc \ud0a4\uc6cc\ub4dc: {keyword_text}</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 22px 28px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  {''.join(cards)}
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 28px;background:#f8fafc;color:#667085;font-size:12px;line-height:1.6;">
                FMK \ud56b\ub51c \uac8c\uc2dc\ud310 \uc790\ub3d9 \uc218\uc9d1 \uba54\uc77c\uc785\ub2c8\ub2e4. \ud0a4\uc6cc\ub4dc\ub294 Termux\uc758 <strong>keyword.sh</strong>\ub85c \uc218\uc815\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def send_email(df: HotdealFrame, *, is_alert: bool = False, keywords: list[str] | None = None) -> None:
    sender = os.environ.get("EMAIL_SENDER", "2joonh2@gmail.com")
    recipient = os.environ.get("EMAIL_TO", sender)
    password = os.environ.get("EMAIL_PASSWORD")
    if not password:
        raise RuntimeError("EMAIL_PASSWORD is not set.")

    msg = MIMEMultipart()
    msg["Subject"] = str(Header(build_subject(df, is_alert), "utf-8"))
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(render_email_body(df, is_alert=is_alert, keywords=keywords), "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)


async def main() -> None:
    df = await get_hotdeal_df()
    if df.empty:
        print("No hotdeal rows found.")
        return

    keywords = parse_keywords()
    matched_df = filter_matches(df, keywords)
    alert_only = os.environ.get("HOTDEAL_ALERT_ONLY", "true").casefold() in {"1", "true", "yes", "y"}

    print(f"Fetched {len(df.rows)} hotdeal rows.")
    print(f"Watching keywords: {', '.join(keywords)}")
    if matched_df.empty:
        print("No keyword matches found.")
        if alert_only:
            return
        email_df = df
        is_alert = False
    else:
        print(f"Matched {len(matched_df.rows)} rows.")
        for row in matched_df.rows[:5]:
            print(f"- [{row['MatchedKeyword']}] {row['Title']} / {row['Price']} / vote {row['Vote']}")
        email_df = matched_df
        is_alert = True

    if os.environ.get("EMAIL_PASSWORD"):
        send_email(email_df, is_alert=is_alert, keywords=keywords)
        print("Email sent.")
    else:
        print("EMAIL_PASSWORD is not set; skipped email.")


if __name__ == "__main__":
    asyncio.run(main())
