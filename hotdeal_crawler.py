import pandas as pd
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

async def get_hotdeal_df():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 봇 탐지 회피를 위해 실제 브라우저와 유사하게 설정
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # 펨코 핫딜 페이지 접속
            await page.goto('https://www.fmkorea.com/hotdeal', wait_until='domcontentloaded', timeout=30000)
            
            # 데이터 로딩 대기 (10초)
            await page.wait_for_selector("div.fm_best_widget._bd_pc", timeout=10000)
            
            content = await page.content()
            bs = BeautifulSoup(content, 'html.parser')
            container = bs.find("div", class_="fm_best_widget _bd_pc")
            
            if not container: return pd.DataFrame()

            data = []
            for elem in container.find_all('li'):
                title_tag = elem.find('h3', class_='title')
                link_tag = elem.find('a')
                
                if title_tag and link_tag:
                    info = {
                        'Title': title_tag.get_text(strip=True),
                        'URL': 'https://fmkorea.com' + link_tag.attrs['href'],
                        'Vote': '0', 'Shop': '', 'Price': ''
                    }
                    
                    vote_tag = elem.find('span', class_='count')
                    if vote_tag: info['Vote'] = vote_tag.get_text(strip=True).replace('[', '').replace(']', '')
                    
                    metas = elem.find_all('span')
                    for meta in metas:
                        txt = meta.get_text(strip=True)
                        if '쇼핑몰:' in txt: info['Shop'] = txt.replace('쇼핑몰:', '').strip()
                        elif '가격:' in txt: info['Price'] = txt.replace('가격:', '').strip()
                    data.append(info)
            
            await browser.close()
            return pd.DataFrame(data)
        except Exception as e:
            print(f"크롤링 중 오류: {e}")
            return pd.DataFrame()

def send_email(df):
    sender = "2joonh2@gmail.com"
    password = os.environ.get('EMAIL_PASSWORD')

    msg = MIMEMultipart()
    msg['Subject'] = "[자동화 알림] 펨코 핫딜 업데이트"
    msg['From'], msg['To'] = sender, sender
    msg.attach(MIMEText(df.to_html(escape=False, render_links=True, index=False), 'html'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

# --- 로컬/깃허브 공용 실행 로직 ---
if __name__ == "__main__":
    # 실행 중인 루프가 있는지 확인하고 적절한 방식으로 실행
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 로컬 IDE 환경 (이미 루프가 도는 경우)
            import nest_asyncio
            nest_asyncio.apply()
            df = loop.run_until_complete(get_hotdeal_df())
        else:
            # 일반적인 터미널 환경
            df = asyncio.run(get_hotdeal_df())
    except Exception:
        # 그 외 예외 상황
        df = asyncio.run(get_hotdeal_df())

    if not df.empty:
        send_email(df)
        print("작업 완료!")
