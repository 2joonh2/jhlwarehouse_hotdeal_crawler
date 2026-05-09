import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright # 다시 동기 API 사용
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
def get_hotdeal_df():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 1. 주소를 '위젯'이 아닌 '게시판 목록'으로 변경
            target_url = 'https://www.fmkorea.com/index.php?mid=hotdeal&category=1255812032' 
            page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
            
            # 2. 게시판 목록의 테이블 요소가 뜰 때까지 대기
            # 게시판 목록은 보통 'bd_lst' 클래스를 사용합니다.
            page.wait_for_selector("ul.fm_best_widget", timeout=15000)
            
            content = page.content()
            bs = BeautifulSoup(content, 'html.parser')
        
            
            # 4. 컨테이너 추출 및 안전성 검사
            container = bs.find("div", class_="fm_best_widget _bd_pc")
            if not container:
                print("컨테이너가 HTML 내에 존재하지 않습니다.")
                browser.close()
                return pd.DataFrame()

            crawled = container.find_all('li')
            data = []
            
            for elem in crawled:
                title_tag = elem.find('h3', class_='title')
                link_tag = elem.find('a')
                vote_tag = elem.find('span', class_='count')
                
                # 데이터 정제
                title = title_tag.get_text(strip=True) if title_tag else "N/A"
                link = 'https://fmkorea.com' + link_tag.attrs['href'] if link_tag else "N/A"
                vote = vote_tag.get_text(strip=True).replace('[', '').replace(']', '') if vote_tag else '0'
                
                info = {'Title': title, 'Vote': vote, 'URL': link, 'Shop': '', 'Price': '', 'Shipping': ''}
                
                # 메타 정보 추출
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
            print(f"브라우저 실행 중 에러 발생: {e}")
            if 'browser' in locals(): browser.close()
            return pd.DataFrame()

def send_email(df):
    sender_email = "2joonh2@gmail.com"
    receiver_email = "2joonh2@gmail.com"
    password = os.environ.get('EMAIL_PASSWORD')

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "[실시간 알림] 펨코 핫딜 업데이트"

    # DF를 HTML 표로 변환
    html_body = f"<h2>현재 핫딜 목록</h2>{df.to_html(escape=False, render_links=True, index=False)}"
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)

if __name__ == "__main__":
    hotdeal_df = get_hotdeal_df()
    if not hotdeal_df.empty:
        send_email(hotdeal_df)
    else:
        print("수집된 데이터가 없습니다.")
