import pandas as pd
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

def get_hotdeal_df():
    url = 'https://www.fmkorea.com/hotdeal'
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urlopen(req)
    bs = BeautifulSoup(html, 'html.parser')
    crawled = bs.find("div", class_="fm_best_widget _bd_pc").find_all('li')

    data = []
    for elem in crawled:
        title_tag = elem.find('h3', class_='title')
        link_tag = elem.find('a')
        vote_tag = elem.find('span', class_='count')
        
        info = {
            'Title': title_tag.get_text(strip=True) if title_tag else "N/A",
            'Vote': vote_tag.get_text(strip=True) if vote_tag else '0',
            'URL': 'https://fmkorea.com' + link_tag.attrs['href'] if link_tag else "N/A"
        }
        
        metas = elem.find_all('span')
        for meta in metas:
            text = meta.get_text(strip=True)
            if '쇼핑몰:' in text: info['Shop'] = text.replace('쇼핑몰:', '').strip()
            elif '가격:' in text: info['Price'] = text.replace('가격:', '').replace('원', '').replace('₩', '').replace(',', '').strip()
            elif '배송' in text: info['Shipping'] = text.replace('배송:', '').replace('원', '').strip()
        data.append(info)
    return pd.DataFrame(data)

def send_email(df):
    sender_email = "2joonh2@gmail.com" # 준희님 이메일
    receiver_email = "2joonh2@gmail.com"
    password = os.environ.get('EMAIL_PASSWORD') # 깃허브에서 주입될 비밀번호

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "[JHLWAREHOUSE] Package No. 1"

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
