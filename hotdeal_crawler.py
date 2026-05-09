import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
def get_hotdeal_df():
    with sync_playwright() as p:
        # 스텔스 모드와 유사한 환경 설정
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            # 1. 대기 전략 변경: 'networkidle' 대신 'domcontentloaded' 사용 (훨씬 빠름)
            # 2. 타임아웃을 30초로 줄이되, 실패 시 재시도 로직 권장
            page.goto('https://www.fmkorea.com/hotdeal', wait_until='domcontentloaded', timeout=30000)
            
            # 페이지가 뜬 후 아주 잠시만(2초) 기다려 데이터 안정화
            page.wait_for_timeout(2000) 
            
            html_content = page.content()
            bs = BeautifulSoup(html_content, 'html.parser')
            
            crawled = bs.find("div", class_="fm_best_widget _bd_pc").find_all('li')
            data = []
            for elem in crawled:
                title_tag = elem.find('h3', class_='title')
                link_tag = elem.find('a')
                vote_tag = elem.find('span', class_='count')
                
                info = {
                    'Title': title_tag.get_text(strip=True) if title_tag else "N/A",
                    'Vote': vote_tag.get_text(strip=True).replace('[', '').replace(']', '') if vote_tag else '0',
                    'URL': 'https://fmkorea.com' + link_tag.attrs['href'] if link_tag else "N/A",
                    'Shop': '', 'Price': '', 'Shipping': ''
                }
                
                metas = elem.find_all('span')
                for meta in metas:
                    text = meta.get_text(strip=True)
                    if '쇼핑몰:' in text: info['Shop'] = text.replace('쇼핑몰:', '').strip()
                    elif '가격:' in text: info['Price'] = text.replace('가격:', '').replace('원', '').replace('₩', '').replace(',', '').strip()
                    elif '배송' in text: info['Shipping'] = text.replace('배송:', '').replace('원', '').replace('무료', '0').strip()
                data.append(info)
            
            browser.close()
            return pd.DataFrame(data)

        except Exception as e:
            print(f"브라우저 구동 중 에러: {e}")
            browser.close()
            return pd.DataFrame()

def send_email(df):
    sender_email = "2joonh2@gmail.com"
    receiver_email = "2joonh2@gmail.com"
    password = os.environ.get('EMAIL_PASSWORD')

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "[실시간 알림] 펨코 핫딜 업데이트 (Playwright)"

    html_body = f"<h2>현재 핫딜 목록</h2>{df.to_html(escape=False, render_links=True, index=False)}"
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)

if __name__ == "__main__":
    df = get_hotdeal_df()
    if not df.empty:
        send_email(df)
