import pandas as pd
import requests # urllib 대신 requests 사용
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import time

def get_hotdeal_df():
    url = 'https://www.fmkorea.com/hotdeal'
    
    # 헤더를 더 정교하게 설정 (브라우저인 척 하기)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.google.com/' # 구글을 통해서 들어온 척 하기
    }

    try:
        # 세션을 사용하여 접속 유지력 강화
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=30)
        
        # 만약 차단(430, 403 등)되었다면 에러 발생
        response.raise_for_status() 
        
        bs = BeautifulSoup(response.text, 'html.parser')
        crawled = bs.find("div", class_="fm_best_widget _bd_pc").find_all('li')

        data = []
        for elem in crawled:
            title_tag = elem.find('h3', class_='title')
            link_tag = elem.find('a')
            vote_tag = elem.find('span', class_='count')
            
            info = {
                'Title': title_tag.get_text(strip=True) if title_tag else "N/A",
                'Vote': vote_tag.get_text(strip=True) if vote_tag else '0',
                'URL': 'https://fmkorea.com' + link_tag.attrs['href'] if link_tag else "N/A",
                'Shop': '', 'Price': '', 'Shipping': '' # 기본값 초기화
            }
            
            metas = elem.find_all('span')
            for meta in metas:
                text = meta.get_text(strip=True)
                if '쇼핑몰:' in text: info['Shop'] = text.replace('쇼핑몰:', '').strip()
                elif '가격:' in text: info['Price'] = text.replace('가격:', '').replace('원', '').replace('₩', '').replace(',', '').strip()
                elif '배송' in text: info['Shipping'] = text.replace('배송:', '').replace('원', '').replace('무료', '0').strip()
            data.append(info)
            
        return pd.DataFrame(data)

    except Exception as e:
        print(f"데이터 수집 중 에러 발생: {e}")
        return pd.DataFrame()

# send_email 함수는 이전과 동일
# ...
