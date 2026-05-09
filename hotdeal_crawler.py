import pandas as pd
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import nest_asyncio # 로컬 루프 충돌 방지용
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# 1. 이미 실행 중인 루프가 있어도 중첩 실행 가능하게 허용
nest_asyncio.apply()

async def get_hotdeal_df():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 스텔스 로직 주입 (봇 탐지 우회 핵심)
        await stealth_async(page)
        
        try:
            # 타임아웃 방지를 위해 주소를 게시판 직접 링크로 변경 제안
            await page.goto('https://www.fmkorea.com/hotdeal', wait_until='domcontentloaded')
            # 요소가 나타날 때까지 확실히 대기
            await page.wait_for_selector("div.fm_best_widget._bd_pc", timeout=20000)

            content = await page.content()
            bs = BeautifulSoup(content, 'html.parser')
            container = bs.find("div", class_="fm_best_widget _bd_pc")
            
            if not container: return pd.DataFrame()

            data = []
            for elem in container.find_all('li'):
                title_tag = elem.find('h3', class_='title')
                link_tag = elem.find('a')
                vote_tag = elem.find('span', class_='count')
                
                title = title_tag.get_text(strip=True) if title_tag else "N/A"
                link = 'https://fmkorea.com' + link_tag.attrs['href'] if link_tag else "N/A"
                vote = vote_tag.get_text(strip=True).replace('[', '').replace(']', '') if vote_tag else '0'
                
                info = {'Title': title, 'Vote': vote, 'URL': link, 'Shop': '', 'Price': ''}
                metas = elem.find_all('span')
                for meta in metas:
                    txt = meta.get_text(strip=True)
                    if '쇼핑몰:' in txt: info['Shop'] = txt.replace('쇼핑몰:', '').strip()
                    elif '가격:' in txt: info['Price'] = txt.replace('가격:', '').replace('원', '').replace(',', '').strip()
                data.append(info)
            
            await browser.close()
            return pd.DataFrame(data)
        except Exception as e:
            print(f"로컬 실행 중 오류: {e}")
            return pd.DataFrame()

def send_email(df):
    sender = "2joonh2@gmail.com"
    # 윈도우 환경 변수에 EMAIL_PASSWORD가 등록되어 있어야 합니다.
    password = 'wjmrahnuhsesphby'

    msg = MIMEMultipart()
    msg['Subject'] = "[JHLWAREHOUSE] PKG No.1"
    msg['From'], msg['To'] = sender, sender
    msg.attach(MIMEText(df.to_html(escape=False, render_links=True, index=False), 'html'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

# --- 로컬 실행용 메인 로직 수정 ---
if __name__ == "__main__":
    try:
        # 기존 루프가 있으면 가져오고, 없으면 새로 만듭니다.
        loop = asyncio.get_event_loop()
        df = loop.run_until_complete(get_hotdeal_df())
    except RuntimeError:
        # 루프가 없는 환경을 위한 대비
        df = asyncio.run(get_hotdeal_df())

    if not df.empty:
        send_email(df)
        print("이메일 발송 완료!")
