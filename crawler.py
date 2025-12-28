"""
아모레몰 제품 후기 크롤러
"""
import time
import json
import os
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re


class AmoreMallCrawler:
    def __init__(self, headless: bool = False, debug: bool = False):
        """
        크롤러 초기화
        
        Args:
            headless: 브라우저를 백그라운드에서 실행할지 여부
            debug: 디버깅 모드 (HTML 저장 등)
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        self.debug = debug
    
    def _close_popups(self):
        """팝업 창 닫기"""
        try:
            # 다양한 팝업 닫기 버튼 셀렉터
            close_selectors = [
                (By.CSS_SELECTOR, ".popup .close, .modal .close, [class*='popup'] [class*='close']"),
                (By.CSS_SELECTOR, "button.close, a.close, .close-button"),
                (By.XPATH, "//button[contains(@class, 'close')]"),
                (By.XPATH, "//a[contains(@class, 'close')]"),
                (By.XPATH, "//*[contains(@class, 'popup')]//*[contains(@class, 'close')]"),
                (By.XPATH, "//*[contains(@class, 'modal')]//*[contains(@class, 'close')]"),
                (By.XPATH, "//button[contains(text(), '닫기')]"),
                (By.XPATH, "//button[contains(text(), '취소')]"),
                (By.XPATH, "//*[@aria-label='닫기' or @aria-label='close']"),
                # X 버튼 (일반적인 닫기 아이콘)
                (By.XPATH, "//button[contains(@class, 'btn-close')]"),
                (By.XPATH, "//span[contains(@class, 'close')]"),
                # ESC 키로 닫을 수 있는 팝업도 처리
            ]
            
            for by, selector in close_selectors:
                try:
                    close_buttons = self.driver.find_elements(by, selector)
                    for btn in close_buttons:
                        if btn.is_displayed():
                            # JavaScript로 클릭 (더 안정적)
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(0.5)
                            print("  ✓ 팝업 닫기 버튼 클릭")
                            break
                except:
                    continue
            
            # ESC 키로 팝업 닫기 시도
            try:
                from selenium.webdriver.common.keys import Keys
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.5)
            except:
                pass
                
        except Exception as e:
            if self.debug:
                print(f"  [디버깅] 팝업 닫기 시도 중 오류: {e}")
    
    def _get_product_info_from_notice(self, url: str) -> Dict:
        """
        상품정보제공 고시 보기를 통해서 상품 정보 수집
        (리뷰 수집 후 호출)
        
        Args:
            url: 제품 페이지 URL
            
        Returns:
            제품 정보 딕셔너리 (성분, 사용방법, 주의사항 포함)
        """
        product_info = {
            'product_url': url,
            'product_name': '',
            'product_code': '',
            'category': '',
            'sub_category': '',
            'price': '',  # 원래 가격 (예: "135,000")
            'current_price': '',  # 현재 가격 (할인된 가격, 예: "126,000")
            'price_range': '',
            'discount_rate': '',  # 할인률 (예: "10%")
            'rating': '',  # 평균 별점 (예: "4.9")
            'review_count': '',
            'usage_method': '',
            'ingredients': '',
            'precautions': ''
        }
        
        # 제품 코드는 URL에서 추출
        try:
            if 'onlineProdCode=' in url:
                product_info['product_code'] = url.split('onlineProdCode=')[1].split('&')[0]
            elif 'onlineProdSn=' in url:
                product_info['product_code'] = url.split('onlineProdSn=')[1].split('&')[0]
        except:
            pass
        
        # 상품정보제공 고시 정보 추출
        usage_method = ""
        ingredients = ""
        precautions = ""
        
        try:
            # "상품정보제공 고시 보기" 버튼 찾기 및 클릭
            notice_button_selectors = [
                (By.XPATH, "//*[contains(text(), '상품정보제공 고시')]"),
                (By.XPATH, "//*[contains(text(), '상품정보제공')]"),
                (By.XPATH, "//*[contains(text(), '고시 보기')]"),
                (By.CSS_SELECTOR, "[class*='notice'][class*='button']"),
            ]
            
            notice_button_found = False
            
            for by, selector in notice_button_selectors:
                try:
                    notice_button = self.driver.find_element(by, selector)
                    if notice_button and notice_button.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", notice_button)
                        time.sleep(1)
                        before_url = self.driver.current_url
                        self.driver.execute_script("arguments[0].click();", notice_button)
                        time.sleep(3)
                        after_url = self.driver.current_url
                        
                        if before_url != after_url:
                            print(f"  ✓ 상품정보제공 고시 열기 (페이지 이동)")
                        else:
                            print(f"  ✓ 상품정보제공 고시 열기 (같은 페이지)")
                            time.sleep(3)
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(2)
                            self.driver.execute_script("window.scrollTo(0, 0);")
                            time.sleep(1)
                        
                        notice_button_found = True
                        break
                except:
                    continue
            
            if not notice_button_found:
                print(f"  ⚠ '상품정보제공 고시 보기' 버튼을 찾을 수 없습니다.")
            else:
                # 버튼을 찾았지만 정보를 추출하지 못한 경우 확인
                pass
            
            if notice_button_found:
                time.sleep(2)
                notice_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                if self.debug:
                    print(f"  [디버깅] 상품정보제공 고시 페이지 파싱 시작")
                
                # 사용 방법 추출 (더 포괄적으로)
                usage_keywords = ['사용방법', '사용 방법', '사용법', 'How to Use', '용법']
                
                # 방법 1: dt/dd 구조에서 찾기
                dt_elements = notice_soup.find_all('dt')
                for dt in dt_elements:
                    dt_text = dt.get_text(strip=True)
                    if any(keyword in dt_text for keyword in usage_keywords):
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            usage_method = dd.get_text(separator='\n', strip=True)
                            if len(usage_method) > 10:
                                if self.debug:
                                    print(f"  [디버깅] dt/dd 구조에서 사용 방법 추출: {len(usage_method)}자")
                                break
                
                # 방법 2: 테이블 구조에서 찾기
                if not usage_method:
                    tables = notice_soup.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            th = row.find('th')
                            td = row.find('td')
                            if th and td:
                                th_text = th.get_text(strip=True)
                                if any(keyword in th_text for keyword in usage_keywords):
                                    usage_method = td.get_text(separator='\n', strip=True)
                                    if len(usage_method) > 10:
                                        if self.debug:
                                            print(f"  [디버깅] 테이블 구조에서 사용 방법 추출: {len(usage_method)}자")
                                        break
                        if usage_method:
                            break
                
                # 방법 3: 텍스트 기반 검색 (개선)
                if not usage_method:
                    for keyword in usage_keywords:
                        # 정확한 키워드 매칭
                        usage_elem = notice_soup.find(string=re.compile(keyword, re.I))
                        if usage_elem:
                            parent = usage_elem.find_parent()
                            if parent:
                                # 부모 요소의 모든 텍스트 가져오기
                                usage_text = parent.get_text(separator='\n', strip=True)
                                # 키워드 다음의 텍스트 추출
                                keyword_pos = usage_text.find(keyword)
                                if keyword_pos >= 0:
                                    after_keyword = usage_text[keyword_pos + len(keyword):].strip()
                                    # 줄바꿈이나 특수문자 제거 후 추출
                                    usage_method = re.sub(r'^[:\s\n]+', '', after_keyword)
                                    usage_method = usage_method.split('\n')[0].strip()[:1000]
                                    if len(usage_method) > 10:
                                        if self.debug:
                                            print(f"  [디버깅] 텍스트 기반에서 사용 방법 추출: {len(usage_method)}자")
                                        break
                        
                        # h4, h3, h2 태그에서 찾기
                        if not usage_method:
                            headings = notice_soup.find_all(['h2', 'h3', 'h4'])
                            for heading in headings:
                                heading_text = heading.get_text(strip=True)
                                if keyword in heading_text:
                                    # 다음 형제 요소나 부모의 다음 형제에서 내용 찾기
                                    next_elem = heading.find_next_sibling()
                                    if next_elem:
                                        usage_method = next_elem.get_text(separator='\n', strip=True)
                                        if len(usage_method) > 10:
                                            if self.debug:
                                                print(f"  [디버깅] 헤딩 구조에서 사용 방법 추출: {len(usage_method)}자")
                                            break
                                    else:
                                        # 부모의 다음 형제 찾기
                                        parent = heading.find_parent()
                                        if parent:
                                            parent_next = parent.find_next_sibling()
                                            if parent_next:
                                                usage_method = parent_next.get_text(separator='\n', strip=True)
                                                if len(usage_method) > 10:
                                                    if self.debug:
                                                        print(f"  [디버깅] 부모 형제에서 사용 방법 추출: {len(usage_method)}자")
                                                    break
                        if usage_method:
                            break
                
                # 성분 추출
                h4_elems = notice_soup.find_all('h4')
                if self.debug:
                    print(f"  [디버깅] h4 요소 {len(h4_elems)}개 발견")
                for h4 in h4_elems:
                    h4_text = h4.get_text(strip=True)
                    if self.debug and ('화장품법' in h4_text or '성분' in h4_text):
                        print(f"  [디버깅] 성분 관련 h4 발견: {h4_text[:80]}")
                    if '화장품법' in h4_text and '성분' in h4_text:
                        next_sibling = h4.find_next_sibling()
                        if next_sibling:
                            ingredients = next_sibling.get_text(separator=' ', strip=True)
                            if self.debug:
                                print(f"  [디버깅] next_sibling에서 성분 추출: {len(ingredients)}자")
                            if len(ingredients) > 20:
                                if self.debug:
                                    print(f"  [디버깅] ✓ 성분 추출 성공! (방법1)")
                                break
                        parent = h4.find_parent()
                        if parent and (not ingredients or len(ingredients) <= 20):
                            for sibling in parent.find_next_siblings():
                                text = sibling.get_text(separator=' ', strip=True)
                                if len(text) > 50:
                                    ingredients = text
                                    break
                            if not ingredients:
                                parent_text = parent.get_text(separator=' ', strip=True)
                                h4_pos = parent_text.find(h4_text)
                                if h4_pos >= 0:
                                    after_h4 = parent_text[h4_pos + len(h4_text):].strip()
                                    if len(after_h4) > 20:
                                        ingredients = after_h4
                        break
                
                # 주의사항 추출 (더 포괄적으로)
                precautions_keywords = ['주의사항', '주의 사항', '주의', 'precaution', '경고', '주의사항', '사용시 주의사항']
                
                # 방법 1: dt/dd 구조에서 찾기
                dt_elements = notice_soup.find_all('dt')
                for dt in dt_elements:
                    dt_text = dt.get_text(strip=True)
                    if any(keyword in dt_text for keyword in precautions_keywords):
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            precautions = dd.get_text(separator='\n', strip=True)
                            if len(precautions) > 10:
                                if self.debug:
                                    print(f"  [디버깅] dt/dd 구조에서 주의사항 추출: {len(precautions)}자")
                                break
                
                # 방법 2: 테이블 구조에서 찾기
                if not precautions:
                    tables = notice_soup.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            th = row.find('th')
                            td = row.find('td')
                            if th and td:
                                th_text = th.get_text(strip=True)
                                if any(keyword in th_text for keyword in precautions_keywords):
                                    precautions = td.get_text(separator='\n', strip=True)
                                    if len(precautions) > 10:
                                        if self.debug:
                                            print(f"  [디버깅] 테이블 구조에서 주의사항 추출: {len(precautions)}자")
                                        break
                        if precautions:
                            break
                
                # 방법 3: 텍스트 기반 검색 (개선)
                if not precautions:
                    for keyword in precautions_keywords:
                        # 정확한 키워드 매칭
                        precautions_elem = notice_soup.find(string=re.compile(keyword, re.I))
                        if precautions_elem:
                            parent = precautions_elem.find_parent()
                            if parent:
                                # 부모 요소의 모든 텍스트 가져오기
                                precautions_text = parent.get_text(separator='\n', strip=True)
                                # 키워드 다음의 텍스트 추출
                                keyword_pos = precautions_text.find(keyword)
                                if keyword_pos >= 0:
                                    after_keyword = precautions_text[keyword_pos + len(keyword):].strip()
                                    # 줄바꿈이나 특수문자 제거 후 추출
                                    precautions = re.sub(r'^[:\s\n]+', '', after_keyword)
                                    precautions = precautions.split('\n')[0].strip()[:1000]
                                    if len(precautions) > 10:
                                        if self.debug:
                                            print(f"  [디버깅] 텍스트 기반에서 주의사항 추출: {len(precautions)}자")
                                        break
                        
                        # h4, h3, h2 태그에서 찾기
                        if not precautions:
                            headings = notice_soup.find_all(['h2', 'h3', 'h4'])
                            for heading in headings:
                                heading_text = heading.get_text(strip=True)
                                if keyword in heading_text:
                                    # 다음 형제 요소나 부모의 다음 형제에서 내용 찾기
                                    next_elem = heading.find_next_sibling()
                                    if next_elem:
                                        precautions = next_elem.get_text(separator='\n', strip=True)
                                        if len(precautions) > 10:
                                            if self.debug:
                                                print(f"  [디버깅] 헤딩 구조에서 주의사항 추출: {len(precautions)}자")
                                            break
                                    else:
                                        # 부모의 다음 형제 찾기
                                        parent = heading.find_parent()
                                        if parent:
                                            parent_next = parent.find_next_sibling()
                                            if parent_next:
                                                precautions = parent_next.get_text(separator='\n', strip=True)
                                                if len(precautions) > 10:
                                                    if self.debug:
                                                        print(f"  [디버깅] 부모 형제에서 주의사항 추출: {len(precautions)}자")
                                                    break
                        if precautions:
                            break
                
                # 사용 방법과 주의사항 텍스트 정리
                if usage_method:
                    usage_method = usage_method.strip()[:1000]
                    if len(usage_method) < 10:
                        usage_method = ""
                
                if precautions:
                    precautions = precautions.strip()[:1000]
                    if len(precautions) < 10:
                        precautions = ""
                
                # 성분 텍스트 정리
                if ingredients:
                    ingredients = re.sub(r'^\d+\.\s*\w+', '', ingredients)
                    if len(ingredients) < 20:
                        ingredients = ""
                    else:
                        ingredients = ingredients[:2000].strip()
                
        except Exception as e:
            if self.debug:
                print(f"  [디버깅] 상품정보제공 고시 추출 오류: {e}")
        
        product_info['usage_method'] = usage_method
        product_info['ingredients'] = ingredients
        product_info['precautions'] = precautions
        
        return product_info
    
    def get_product_info(self, url: str) -> Dict:
        """
        제품 기본 정보 추출
        
        Args:
            url: 제품 페이지 URL
            
        Returns:
            제품 정보 딕셔너리
        """
        self.driver.get(url)
        time.sleep(3)  # 페이지 로딩 대기
        
        # 팝업 닫기
        self._close_popups()
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 제품명 추출 (첫 화면에서) - h1 태그 사용
            product_name_raw = ""
            try:
                # h1 태그로 제품명 찾기
                name_elem = soup.find('h1')
                if name_elem:
                    product_name_raw = name_elem.get_text(strip=True)
                    if self.debug:
                        print(f"  [디버깅] 제품명 찾음 (h1): {product_name_raw}")
                
                # Selenium으로도 시도
                if not product_name_raw:
                    try:
                        name_element = self.driver.find_element(By.TAG_NAME, "h1")
                        if name_element:
                            product_name_raw = name_element.text.strip()
                    except:
                        pass
            except Exception as e:
                if self.debug:
                    print(f"  [디버깅] 제품명 추출 오류: {e}")
            
            # 제품명 파싱: "10%135,000원자음2종 세트 (150ml+125ml)4.9(4,374)좋아요"
            # -> 할인율, 가격, 제품명, 평점, 리뷰 개수 분리
            discount_rate = ""
            price_from_name = ""  # 원래 가격 (예: "135,000원")
            current_price = ""  # 현재 가격 (할인된 가격, 예: "126,000원")
            product_name = product_name_raw
            rating_from_name = ""
            review_count_from_name = ""
            
            if product_name_raw:
                # 할인율 추출 (예: "10%")
                discount_match = re.search(r'(\d+)%', product_name_raw)
                if discount_match:
                    discount_rate = discount_match.group(1) + "%"
                
                # 가격 추출 (예: "135,000원") - 원래 가격
                price_match = re.search(r'(\d{1,3}(?:,\d{3})*)원', product_name_raw)
                if price_match:
                    price_from_name = price_match.group(1) + "원"
                    # 할인율이 있으면 현재 가격 계산
                    if discount_rate:
                        try:
                            original_price = int(price_match.group(1).replace(',', ''))
                            discount_percent = int(discount_match.group(1))
                            discounted_price = original_price * (100 - discount_percent) // 100
                            current_price = f"{discounted_price:,}원"
                        except:
                            current_price = price_from_name
                    else:
                        current_price = price_from_name
                
                # 평점 추출 (예: "4.9")
                rating_match = re.search(r'(\d+\.?\d*)', product_name_raw)
                if rating_match:
                    # 가격 다음에 나오는 평점 찾기
                    price_end = product_name_raw.find('원')
                    if price_end > 0:
                        after_price = product_name_raw[price_end:]
                        rating_match = re.search(r'(\d+\.?\d*)', after_price)
                        if rating_match:
                            rating_from_name = rating_match.group(1)
                
                # 리뷰 개수 추출 (예: "(4,374)")
                review_match = re.search(r'\((\d{1,3}(?:,\d{3})*)\)', product_name_raw)
                if review_match:
                    review_count_from_name = review_match.group(1)
                
                # 제품명 추출: 가격과 평점 사이의 텍스트
                # 패턴: [할인율][가격][제품명][평점](리뷰수)[기타]
                if price_from_name and rating_from_name:
                    price_pos = product_name_raw.find(price_from_name)
                    rating_pos = product_name_raw.find(rating_from_name, price_pos + len(price_from_name))
                    if price_pos >= 0 and rating_pos > price_pos:
                        product_name = product_name_raw[price_pos + len(price_from_name):rating_pos].strip()
                elif price_from_name:
                    # 가격만 있는 경우
                    price_pos = product_name_raw.find(price_from_name)
                    if price_pos >= 0:
                        # 평점이나 리뷰 개수 패턴 찾기
                        remaining = product_name_raw[price_pos + len(price_from_name):]
                        rating_match = re.search(r'(\d+\.?\d*)', remaining)
                        if rating_match:
                            rating_pos = remaining.find(rating_match.group(1))
                            product_name = remaining[:rating_pos].strip()
                        else:
                            product_name = remaining.strip()
                
                # 제품명 정리 (불필요한 문자 제거)
                product_name = re.sub(r'^\d+%', '', product_name)  # 앞의 할인율 제거
                product_name = re.sub(r'^\d{1,3}(?:,\d{3})*원', '', product_name)  # 앞의 가격 제거
                # 평점과 리뷰 수 제거 (예: "4.9(4,375)" 패턴) - 여러 번 시도
                product_name = re.sub(r'\d+\.?\d*\(\d{1,3}(?:,\d{3})*\)', '', product_name)  # "4.9(4,375)" 패턴 제거
                product_name = re.sub(r'\d+\.\d+\(\d{1,3}(?:,\d{3})*\)', '', product_name)  # "4.9(4,375)" 패턴 제거 (더 정확)
                product_name = re.sub(r'\d+\.\d+', '', product_name)  # 평점 제거 (예: "4.9")
                product_name = re.sub(r'\(\d{1,3}(?:,\d{3})*\)', '', product_name)  # 리뷰 개수 제거 (예: "(4,375)")
                product_name = re.sub(r'\d+\.?\d*$', '', product_name)  # 뒤의 평점 제거
                product_name = re.sub(r'좋아요$', '', product_name)  # "좋아요" 제거
                product_name = product_name.strip()
            
            # 제품 코드 추출 (URL에서 먼저 시도)
            product_code = ""
            if 'onlineProdCode=' in url:
                product_code = url.split('onlineProdCode=')[1].split('&')[0]
            
            # URL에 없으면 페이지에서 추출 시도
            if not product_code:
                # 메타 정보에서 추출
                meta_code = soup.find('meta', {'property': re.compile('product.*code|code', re.I)})
                if meta_code:
                    product_code = meta_code.get('content', '')
                
                # 페이지의 스크립트나 데이터 속성에서 추출
                if not product_code:
                    # data-product-code, data-code 등의 속성 찾기
                    code_elem = soup.find(attrs={'data-product-code': True}) or \
                               soup.find(attrs={'data-code': True}) or \
                               soup.find(attrs={'data-prod-code': True})
                    if code_elem:
                        product_code = (code_elem.get('data-product-code') or 
                                       code_elem.get('data-code') or 
                                       code_elem.get('data-prod-code') or '')
                
                # URL 파라미터에서 onlineProdSn 추출 후 페이지에서 변환 시도
                if not product_code and 'onlineProdSn=' in url:
                    prod_sn = url.split('onlineProdSn=')[1].split('&')[0]
                    # 페이지의 JavaScript나 숨겨진 요소에서 product_code 찾기
                    script_tags = soup.find_all('script')
                    for script in script_tags:
                        if script.string:
                            # onlineProdCode 패턴 찾기
                            code_match = re.search(r'onlineProdCode["\']?\s*[:=]\s*["\']?(\d+)', script.string)
                            if code_match:
                                product_code = code_match.group(1)
                                break
                
                # 여전히 없으면 onlineProdSn을 product_code로 사용 (최후의 수단)
                if not product_code and 'onlineProdSn=' in url:
                    product_code = url.split('onlineProdSn=')[1].split('&')[0]
            
            # 카테고리 추출
            category = ""
            sub_category = ""
            try:
                # 브레드크럼 또는 카테고리 링크 찾기
                breadcrumb = soup.find(class_=re.compile('breadcrumb|category|nav', re.I))
                if breadcrumb:
                    links = breadcrumb.find_all('a')
                    categories = [link.get_text(strip=True) for link in links if link.get_text(strip=True)]
                    if len(categories) >= 2:
                        # 마지막에서 두 번째가 메인 카테고리, 마지막이 세부 카테고리일 수 있음
                        category = categories[-2] if len(categories) >= 2 else ""
                        sub_category = categories[-1] if len(categories) >= 1 else ""
                
                # 또는 메타 정보에서 추출
                if not category:
                    meta_category = soup.find('meta', {'property': re.compile('category', re.I)})
                    if meta_category:
                        category = meta_category.get('content', '')
            except:
                pass
            
            # 가격 추출 (페이지에서 직접 추출)
            price = ""  # 원래 가격
            original_price = ""  # 취소선이 있는 원래 가격
            price_range = ""
            page_discount_rate = ""  # 페이지에서 추출한 할인률
            page_rating = ""  # 페이지에서 추출한 평점
            page_review_count = ""  # 페이지에서 추출한 리뷰 수
            
            try:
                # 페이지가 완전히 로드될 때까지 대기
                time.sleep(2)
                
                # Selenium으로 직접 요소 찾기
                page_text = self.driver.page_source
                
                # 1. 취소선이 있는 원래 가격 찾기 (정가, 예: "150,000원")
                try:
                    strike_selectors = [
                        (By.CSS_SELECTOR, "s, strike, del"),
                        (By.XPATH, "//s | //strike | //del"),
                        (By.CSS_SELECTOR, "[style*='line-through'], [style*='text-decoration: line-through']"),
                        (By.XPATH, "//*[contains(@class, 'original') or contains(@class, 'old') or contains(@class, 'strike')]"),
                    ]
                    for by, selector in strike_selectors:
                        try:
                            strike_elems = self.driver.find_elements(by, selector)
                            for elem in strike_elems:
                                if elem.is_displayed():
                                    strike_text = elem.text.strip()
                                    original_price_match = re.search(r'(\d{1,3}(?:,\d{3})*)원', strike_text)
                                    if original_price_match:
                                        original_price = original_price_match.group(1) + "원"
                                        price = original_price.replace('원', '')
                                        if self.debug:
                                            print(f"  [디버깅] 취소선 가격 찾음: {original_price}")
                                        break
                            if original_price:
                                break
                        except:
                            continue
                except Exception as e:
                    if self.debug:
                        print(f"  [디버깅] 취소선 가격 찾기 오류: {e}")
                
                # BeautifulSoup으로도 시도
                if not original_price:
                    strike_elem = soup.find(['s', 'strike', 'del']) or soup.find(class_=re.compile('strike|del|original|old', re.I))
                    if strike_elem:
                        strike_text = strike_elem.get_text(strip=True)
                        original_price_match = re.search(r'(\d{1,3}(?:,\d{3})*)원', strike_text)
                        if original_price_match:
                            original_price = original_price_match.group(1) + "원"
                            price = original_price.replace('원', '')
                
                # 2. 할인률 추출 - priceBox__rate 클래스 사용
                discount_rate_elem = soup.find(class_=re.compile('priceBox__rate|discountRate|discount.*rate', re.I))
                if discount_rate_elem:
                    rate_text = discount_rate_elem.get_text(strip=True)
                    rate_match = re.search(r'(\d+)%', rate_text)
                    if rate_match:
                        page_discount_rate = rate_match.group(1) + "%"
                        if self.debug:
                            print(f"  [디버깅] 할인률 찾음 (클래스): {page_discount_rate}")
                
                # Selenium으로도 시도
                if not page_discount_rate:
                    try:
                        rate_elem = self.driver.find_element(By.CSS_SELECTOR, ".priceBox__rate, [class*='discountRate']")
                        if rate_elem and rate_elem.is_displayed():
                            rate_text = rate_elem.text.strip()
                            rate_match = re.search(r'(\d+)%', rate_text)
                            if rate_match:
                                page_discount_rate = rate_match.group(1) + "%"
                                if self.debug:
                                    print(f"  [디버깅] 할인률 찾음 (Selenium): {page_discount_rate}")
                    except:
                        pass
                
                # 3. 할인가 추출 - priceBox__price 클래스 사용
                current_price_elem = soup.find(class_=re.compile('priceBox__price|currentPrice|salePrice', re.I))
                if current_price_elem:
                    price_text = current_price_elem.get_text(strip=True)
                    price_match = re.search(r'(\d{1,3}(?:,\d{3})*)', price_text)
                    if price_match:
                        current_price = price_match.group(1)  # 숫자만 (예: "135,000")
                        if self.debug:
                            print(f"  [디버깅] 할인가 찾음 (클래스): {current_price}")
                
                # Selenium으로도 시도
                if not current_price:
                    try:
                        price_elem = self.driver.find_element(By.CSS_SELECTOR, ".priceBox__price, [class*='currentPrice']")
                        if price_elem and price_elem.is_displayed():
                            price_text = price_elem.text.strip()
                            price_match = re.search(r'(\d{1,3}(?:,\d{3})*)', price_text)
                            if price_match:
                                current_price = price_match.group(1)  # 숫자만
                                if self.debug:
                                    print(f"  [디버깅] 할인가 찾음 (Selenium): {current_price}")
                    except:
                        pass
                
                # 원래 가격이 없으면 할인률과 할인가로 계산
                if not original_price and page_discount_rate and current_price:
                    try:
                        discount_percent = int(page_discount_rate.replace('%', ''))
                        current_price_num = int(current_price.replace(',', ''))
                        original_price_num = int(current_price_num * 100 / (100 - discount_percent))
                        original_price = f"{original_price_num:,}원"
                        price = f"{original_price_num:,}"
                        if self.debug:
                            print(f"  [디버깅] 정가 계산됨: {original_price}")
                    except:
                        pass
                
                # Selenium으로도 시도 (요소의 부모나 형제 요소 포함)
                if not page_discount_rate:
                    try:
                        discount_price_selectors = [
                            (By.XPATH, "//*[contains(text(), '%')]"),
                            (By.CSS_SELECTOR, "[class*='discount'], [class*='sale'], [class*='price']"),
                        ]
                        for by, selector in discount_price_selectors:
                            try:
                                discount_elems = self.driver.find_elements(by, selector)
                                for elem in discount_elems:
                                    if elem.is_displayed():
                                        # 요소 자체의 텍스트
                                        discount_text = elem.text.strip()
                                        # 부모 요소의 텍스트도 확인
                                        try:
                                            parent = elem.find_element(By.XPATH, "..")
                                            parent_text = parent.text.strip()
                                            if len(parent_text) > len(discount_text):
                                                discount_text = parent_text
                                        except:
                                            pass
                                        
                                        if self.debug and len(discount_text) < 200:
                                            print(f"  [디버깅] 할인 텍스트 확인: {discount_text[:100]}")
                                        
                                        # "10% 135,000원" 또는 "10%135,000원" 패턴 찾기
                                        discount_price_match = re.search(r'(\d+)%\s*(\d{1,3}(?:,\d{3})*)원', discount_text)
                                        if not discount_price_match:
                                            discount_price_match = re.search(r'(\d+)%(\d{1,3}(?:,\d{3})*)원', discount_text)
                                        if discount_price_match:
                                            page_discount_rate = discount_price_match.group(1) + "%"
                                            current_price_num = int(discount_price_match.group(2).replace(',', ''))
                                            current_price = f"{current_price_num:,}"
                                            
                                            # 원래 가격이 없으면 할인률로 계산
                                            if not original_price:
                                                discount_percent = int(discount_price_match.group(1))
                                                original_price_num = int(current_price_num * 100 / (100 - discount_percent))
                                                original_price = f"{original_price_num:,}원"
                                                price = f"{original_price_num:,}"
                                            
                                            if self.debug:
                                                print(f"  [디버깅] 할인 정보 찾음 (Selenium): {page_discount_rate}, {current_price}, 정가: {price}")
                                            break
                                if page_discount_rate:
                                    break
                            except:
                                continue
                    except Exception as e:
                        if self.debug:
                            print(f"  [디버깅] 할인 정보 찾기 오류: {e}")
                
                
                # 3. 평점 추출 (예: "★4.9" 또는 "4.9")
                try:
                    # Selenium으로 평점 찾기
                    rating_selectors = [
                        (By.XPATH, "//*[contains(text(), '★') or contains(text(), '☆')]"),
                        (By.XPATH, "//*[contains(@class, 'rating') or contains(@class, 'star') or contains(@class, 'score')]"),
                    ]
                    for by, selector in rating_selectors:
                        try:
                            rating_elems = self.driver.find_elements(by, selector)
                            for elem in rating_elems:
                                if elem.is_displayed():
                                    rating_text = elem.text.strip()
                                    rating_match = re.search(r'(\d+\.\d+)', rating_text)
                                    if rating_match:
                                        page_rating = rating_match.group(1)
                                        if self.debug:
                                            print(f"  [디버깅] 평점 찾음: {page_rating}")
                                        break
                            if page_rating:
                                break
                        except:
                            continue
                except Exception as e:
                    if self.debug:
                        print(f"  [디버깅] 평점 찾기 오류: {e}")
                
                # 정규식으로도 시도
                if not page_rating:
                    rating_patterns = [
                        r'[★☆]\s*(\d+\.\d+)',  # "★4.9"
                        r'평점[:\s]*(\d+\.\d+)',  # "평점: 4.9"
                        r'(\d+\.\d+)\s*점',
                    ]
                    for pattern in rating_patterns:
                        rating_match = re.search(pattern, page_text)
                        if rating_match:
                            page_rating = rating_match.group(1)
                            break
                
                # BeautifulSoup으로도 시도
                if not page_rating:
                    rating_elem = soup.find(string=re.compile(r'[★☆]\s*\d+\.\d+|\d+\.\d+\s*점'))
                    if rating_elem:
                        rating_match = re.search(r'(\d+\.\d+)', rating_elem)
                        if rating_match:
                            page_rating = rating_match.group(1)
                
                # 4. 리뷰 수 추출 (예: "리뷰 4,375" 또는 "4,375")
                try:
                    # Selenium으로 리뷰 수 찾기
                    review_selectors = [
                        (By.XPATH, "//*[contains(text(), '리뷰')]"),
                        (By.XPATH, "//*[contains(text(), '후기')]"),
                    ]
                    for by, selector in review_selectors:
                        try:
                            review_elems = self.driver.find_elements(by, selector)
                            for elem in review_elems:
                                if elem.is_displayed():
                                    review_text = elem.text.strip()
                                    review_match = re.search(r'리뷰\s*(\d{1,3}(?:,\d{3})*)', review_text)
                                    if not review_match:
                                        review_match = re.search(r'후기\s*(\d{1,3}(?:,\d{3})*)', review_text)
                                    if review_match:
                                        page_review_count = review_match.group(1)
                                        if self.debug:
                                            print(f"  [디버깅] 리뷰 수 찾음: {page_review_count}")
                                        break
                            if page_review_count:
                                break
                        except:
                            continue
                except Exception as e:
                    if self.debug:
                        print(f"  [디버깅] 리뷰 수 찾기 오류: {e}")
                
                # 정규식으로도 시도
                if not page_review_count:
                    review_patterns = [
                        r'리뷰\s*(\d{1,3}(?:,\d{3})*)',  # "리뷰 4,375"
                        r'후기\s*(\d{1,3}(?:,\d{3})*)',  # "후기 4,375"
                        r'\((\d{1,3}(?:,\d{3})*)\)',  # "(4,375)"
                    ]
                    for pattern in review_patterns:
                        review_match = re.search(pattern, page_text)
                        if review_match:
                            page_review_count = review_match.group(1)
                            break
                
                # 가격대 분류
                if price:
                    price_num = int(price.replace(',', ''))
                    if price_num < 10000:
                        price_range = "1만원 미만"
                    elif price_num < 30000:
                        price_range = "1-3만원"
                    elif price_num < 50000:
                        price_range = "3-5만원"
                    elif price_num < 100000:
                        price_range = "5-10만원"
                    elif price_num < 200000:
                        price_range = "10-20만원"
                    else:
                        price_range = "20만원 이상"
            except Exception as e:
                if self.debug:
                    print(f"  [디버깅] 가격 추출 오류: {e}")
                pass
            
            # 상품정보제공 고시 정보 추출
            usage_method = ""  # 사용 방법
            ingredients = ""  # 성분
            precautions = ""  # 주의사항
            
            try:
                # "상품정보제공 고시 보기" 버튼 찾기 및 클릭
                notice_button_selectors = [
                    (By.XPATH, "//*[contains(text(), '상품정보제공 고시')]"),
                    (By.XPATH, "//*[contains(text(), '상품정보제공')]"),
                    (By.XPATH, "//*[contains(text(), '고시 보기')]"),
                    (By.CSS_SELECTOR, "[class*='notice'][class*='button']"),
                ]
                
                notice_button_found = False
                current_url = self.driver.current_url  # 현재 URL 저장
                
                for by, selector in notice_button_selectors:
                    try:
                        notice_button = self.driver.find_element(by, selector)
                        if notice_button and notice_button.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", notice_button)
                            time.sleep(1)
                            before_url = self.driver.current_url
                            self.driver.execute_script("arguments[0].click();", notice_button)
                            time.sleep(3)  # 페이지 이동 또는 콘텐츠 로드 대기
                            after_url = self.driver.current_url
                            
                            # URL이 변경되었는지 확인
                            if before_url != after_url:
                                print(f"  ✓ 상품정보제공 고시 열기 (페이지 이동)")
                            else:
                                # URL이 변경되지 않았으면 같은 페이지에서 섹션이 표시됨
                                print(f"  ✓ 상품정보제공 고시 열기 (같은 페이지)")
                                # 추가 대기 (동적 콘텐츠 로드)
                                time.sleep(3)
                                # 페이지 스크롤하여 모든 콘텐츠 로드
                                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(2)
                                self.driver.execute_script("window.scrollTo(0, 0);")
                                time.sleep(1)
                            
                            notice_button_found = True
                            break
                    except:
                        continue
                
                if notice_button_found:
                    # 페이지 이동 후 정보 추출
                    # 페이지 소스 다시 가져오기 (동적 콘텐츠 반영)
                    # 추가 대기 (동적 콘텐츠가 완전히 로드될 때까지)
                    time.sleep(2)
                    # 페이지 소스 다시 가져오기
                    notice_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    
                    # 변수 초기화는 함수 스코프에서 이미 했으므로 여기서는 하지 않음
                    # (함수 스코프의 변수에 직접 할당됨)
                    
                    if self.debug:
                        print(f"  [디버깅] 상품정보제공 고시 페이지 파싱 시작")
                    
                    # 사용 방법 추출
                    usage_keywords = ['사용방법', '사용 방법', 'How to Use']
                    for keyword in usage_keywords:
                        usage_elem = notice_soup.find(string=re.compile(keyword, re.I))
                        if usage_elem:
                            parent = usage_elem.find_parent()
                            if parent:
                                # 다음 형제 요소나 부모의 텍스트에서 사용 방법 찾기
                                usage_text = parent.get_text(separator='\n', strip=True)
                                # "사용방법" 다음 텍스트 추출
                                usage_match = re.search(rf'{keyword}[^\n]*\n([^\n]+)', usage_text, re.I)
                                if usage_match:
                                    usage_method = usage_match.group(1).strip()
                                else:
                                    # 부모 요소의 전체 텍스트에서 추출
                                    usage_method = usage_text.split(keyword)[-1].strip()[:500]
                                break
                    
                    # 성분 추출 (더 강화된 방법)
                    # 방법 1: h4 태그에서 "화장품법" 또는 "성분" 키워드 찾기 (가장 정확)
                    h4_elems = notice_soup.find_all('h4')
                    if self.debug:
                        print(f"  [디버깅] h4 요소 {len(h4_elems)}개 발견")
                    for h4 in h4_elems:
                        h4_text = h4.get_text(strip=True)
                        if self.debug and ('화장품법' in h4_text or '성분' in h4_text):
                            print(f"  [디버깅] 성분 관련 h4 발견: {h4_text[:80]}")
                        if '화장품법' in h4_text and '성분' in h4_text:
                            # h4 다음 형제 요소에서 성분 찾기
                            next_sibling = h4.find_next_sibling()
                            if next_sibling:
                                ingredients = next_sibling.get_text(separator=' ', strip=True)
                                if self.debug:
                                    print(f"  [디버깅] next_sibling에서 성분 추출: {len(ingredients)}자")
                                if len(ingredients) > 20:
                                    if self.debug:
                                        print(f"  [디버깅] ✓ 성분 추출 성공! (방법1)")
                                    break
                            # h4의 부모 요소에서 찾기
                            if self.debug and (not ingredients or len(ingredients) <= 20):
                                print(f"  [디버깅] next_sibling에서 성분 추출 실패, 부모 요소 확인 중...")
                            parent = h4.find_parent()
                            if parent and (not ingredients or len(ingredients) <= 20):
                                # 부모의 다음 형제나 자식 요소에서 찾기
                                for sibling in parent.find_next_siblings():
                                    text = sibling.get_text(separator=' ', strip=True)
                                    if len(text) > 50:
                                        ingredients = text
                                        break
                                if not ingredients:
                                    # 부모의 모든 텍스트에서 h4 다음 부분만 추출
                                    parent_text = parent.get_text(separator=' ', strip=True)
                                    h4_pos = parent_text.find(h4_text)
                                    if h4_pos >= 0:
                                        after_h4 = parent_text[h4_pos + len(h4_text):].strip()
                                        if len(after_h4) > 20:
                                            ingredients = after_h4
                            break
                    
                    # 방법 2: dt/dd 구조에서 찾기
                    if not ingredients or len(ingredients) < 10:
                        ingredients_keywords = ['성분', '화장품법', 'ingredient', '성분명']
                        for keyword in ingredients_keywords:
                            dt_elem = notice_soup.find('dt', string=re.compile(keyword, re.I))
                            if dt_elem:
                                next_dd = dt_elem.find_next_sibling('dd')
                                if next_dd:
                                    ingredients = next_dd.get_text(separator=' ', strip=True)
                                    if len(ingredients) > 10:
                                        break
                    
                    # 방법 3: div.dSection 구조에서 찾기 (이미지에서 확인된 구조)
                    if not ingredients or len(ingredients) < 10:
                        d_sections = notice_soup.find_all('div', class_=re.compile('dSection|section', re.I))
                        for section in d_sections:
                            section_text = section.get_text(strip=True)
                            if '화장품법' in section_text and '성분' in section_text:
                                # h4 다음의 텍스트 추출
                                h4_in_section = section.find('h4')
                                if h4_in_section:
                                    # h4 다음의 모든 텍스트
                                    h4_text = h4_in_section.get_text(strip=True)
                                    full_text = section.get_text(separator=' ', strip=True)
                                    h4_pos = full_text.find(h4_text)
                                    if h4_pos >= 0:
                                        after_h4 = full_text[h4_pos + len(h4_text):].strip()
                                        if len(after_h4) > 20:
                                            ingredients = after_h4
                                            break
                    
                    # 방법 4: 텍스트 패턴으로 찾기
                    if not ingredients or len(ingredients) < 10:
                        notice_text = notice_soup.get_text(separator=' ')
                        # "화장품법...성분" 다음의 긴 텍스트 찾기
                        pattern = r'화장품법[^성]*성분[^\\n]*([^\\n]{50,})'
                        match = re.search(pattern, notice_text)
                        if match:
                            ingredients = match.group(1).strip()
                    
                    # 성분 텍스트 정리 (최대 2000자)
                    if ingredients:
                        # 불필요한 텍스트 제거
                        ingredients = re.sub(r'^\d+\.\s*\w+', '', ingredients)
                        # 너무 짧은 경우 제외
                        if len(ingredients) < 20:
                            ingredients = ""
                        else:
                            ingredients = ingredients[:2000].strip()
                    
                    # 주의사항 추출
                    precautions_keywords = ['주의사항', '주의 사항', '주의', 'precaution', '경고']
                    for keyword in precautions_keywords:
                        precautions_elem = notice_soup.find(string=re.compile(keyword, re.I))
                        if precautions_elem:
                            parent = precautions_elem.find_parent()
                            if parent:
                                precautions_text = parent.get_text(separator='\n', strip=True)
                                precautions_match = re.search(rf'{keyword}[^\n]*\n([^\n]+)', precautions_text, re.I)
                                if precautions_match:
                                    precautions = precautions_match.group(1).strip()
                                else:
                                    precautions = precautions_text.split(keyword)[-1].strip()[:500]
                                break
                    
                    # 상품정보제공 고시 페이지에서 제품 페이지로 돌아가기
                    try:
                        # 뒤로가기 버튼 찾기
                        back_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".back, .btnBack, [class*='back'], [class*='prev'], button[aria-label*='뒤'], a[aria-label*='뒤']")
                        back_found = False
                        for back_button in back_buttons:
                            if back_button.is_displayed():
                                self.driver.execute_script("arguments[0].click();", back_button)
                                time.sleep(2)
                                back_found = True
                                break
                        
                        if not back_found:
                            # 뒤로가기 버튼이 없으면 브라우저 뒤로가기
                            self.driver.back()
                            time.sleep(2)
                    except:
                        # 뒤로가기 버튼이 없으면 브라우저 뒤로가기
                        try:
                            self.driver.back()
                            time.sleep(2)
                        except:
                            pass
                        
            except Exception as e:
                if self.debug:
                    print(f"  [디버깅] 상품정보제공 고시 추출 오류: {e}")
            
            # 가격 정보 우선순위: 페이지에서 추출한 정보 > 제품명에서 추출한 정보
            # 원래 가격 (취소선이 있는 가격, 정가)
            final_original_price = price if price else ""
            if not final_original_price and original_price:
                final_original_price = original_price.replace('원', '').replace(',', '')
                final_original_price = f"{int(final_original_price):,}" if final_original_price else ""
            if not final_original_price and price_from_name:
                price_num = int(re.sub(r'[^\d]', '', price_from_name))
                if price_num > 1000:  # 1000원 이상인 경우만 사용
                    final_original_price = re.sub(r'[^\d,]', '', price_from_name)
            
            # 현재 가격 (할인된 가격) - "원" 제거
            final_current_price = current_price if current_price else ""
            if final_current_price and '원' in final_current_price:
                final_current_price = final_current_price.replace('원', '').strip()
            if not final_current_price and price_from_name:
                # 제품명에서 추출한 가격 사용
                price_num = int(re.sub(r'[^\d]', '', price_from_name))
                if price_num > 1000:
                    final_current_price = re.sub(r'[^\d,]', '', price_from_name)
            
            # 할인률 우선순위: 페이지 > 제품명
            final_discount_rate = page_discount_rate if page_discount_rate else discount_rate
            
            # 평점 우선순위: 페이지 > 제품명
            final_rating = page_rating if page_rating else rating_from_name
            
            # 리뷰 수 우선순위: 페이지 > 제품명
            final_review_count = page_review_count if page_review_count else review_count_from_name
            
            if self.debug:
                print(f"  [디버깅] 최종 가격 정보:")
                print(f"    price 변수: {price}")
                print(f"    original_price 변수: {original_price}")
                print(f"    current_price 변수: {current_price}")
                print(f"    page_discount_rate 변수: {page_discount_rate}")
                print(f"    page_rating 변수: {page_rating}")
                print(f"    page_review_count 변수: {page_review_count}")
                print(f"    정가: {final_original_price}")
                print(f"    할인가: {final_current_price}")
                print(f"    할인률: {final_discount_rate}")
                print(f"    평점: {final_rating}")
                print(f"    리뷰 수: {final_review_count}")
            
            return {
                'product_name': product_name,  # 정리된 제품명 (예: "자음2종 세트 (150ml+125ml)")
                'product_code': product_code,
                'product_url': url,
                'category': category,
                'sub_category': sub_category,
                'price': final_original_price if final_original_price else '',  # 원래 가격 (숫자만, 예: "150,000")
                'current_price': final_current_price if final_current_price else '',  # 현재 가격 (할인된 가격, 예: "135,000")
                'price_range': price_range,
                'discount_rate': final_discount_rate if final_discount_rate else '',  # 할인률 (예: "10%")
                'rating': final_rating if final_rating else '',  # 평균 별점 (예: "4.9")
                'review_count': final_review_count if final_review_count else '',
                'usage_method': usage_method,
                'ingredients': ingredients,
                'precautions': precautions
            }
        except Exception as e:
            print(f"제품 정보 추출 오류: {e}")
            return {}
    
    def _save_debug_html(self, html_content: str, filename: str):
        """디버깅용 HTML 저장"""
        if self.debug:
            debug_dir = "debug_html"
            os.makedirs(debug_dir, exist_ok=True)
            filepath = os.path.join(debug_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"  [디버깅] HTML 저장: {filepath}")
    
    def extract_reviews(self, max_pages: int = 10, max_reviews: int = None, test_mode: bool = False, max_more_clicks: int = None) -> List[Dict]:
        """
        후기 데이터 추출
        
        Args:
            max_pages: 최대 페이지 수 (None이면 모든 페이지)
            max_reviews: 최대 리뷰 수 (None이면 제한 없음)
            test_mode: 테스트 모드 (더 보기 버튼 1번만 클릭)
            max_more_clicks: 더 보기 버튼 최대 클릭 횟수 (None이면 test_mode에 따라 자동 설정)
            
        Returns:
            후기 리스트
        """
        reviews = []
        
        try:
            # 팝업 닫기
            self._close_popups()
            
            # 페이지 하단으로 스크롤하여 후기 섹션 로드
            print("후기 섹션 찾는 중...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # 스크롤 후 다시 팝업 닫기 (스크롤로 인해 팝업이 다시 나타날 수 있음)
            self._close_popups()
            
            # 여러 방법으로 후기 탭/섹션 찾기
            review_tab_found = False
            
            # 방법 1: CSS 셀렉터로 탭 찾기 (우선순위: 리뷰 숫자가 포함된 탭)
            tab_css_selectors = [
                "[class*='tab'] a",
                "[class*='tab'] button",
                ".tab a",
                ".tab button",
                "a[href*='review']",
                "a[href*='후기']",
                "button[class*='tab']",
                "[class*='tab'][class*='review']",
                "[class*='tab'][class*='후기']",
            ]
            
            for selector in tab_css_selectors:
                try:
                    tabs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for tab in tabs:
                        tab_text = tab.text.strip()
                        # "리뷰" 또는 "후기"가 포함되고, 숫자도 포함된 탭 우선 선택 (예: "리뷰 2,010")
                        if ('리뷰' in tab_text or '후기' in tab_text) and tab.is_displayed():
                            # 숫자가 포함된 탭이면 우선 선택
                            if any(char.isdigit() for char in tab_text):
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", tab)
                                time.sleep(3)
                                review_tab_found = True
                                print(f"✓ 후기/리뷰 탭 클릭 완료: {tab_text[:30]} (CSS 셀렉터)")
                                break
                    if review_tab_found:
                        break
                    
                    # 숫자가 없는 탭도 시도
                    if not review_tab_found:
                        for tab in tabs:
                            tab_text = tab.text.strip()
                            if ('리뷰' in tab_text or '후기' in tab_text) and tab.is_displayed():
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", tab)
                                time.sleep(3)
                                review_tab_found = True
                                print(f"✓ 후기/리뷰 탭 클릭 완료: {tab_text[:30]} (CSS 셀렉터)")
                                break
                        if review_tab_found:
                            break
                except:
                    continue
            
            # 방법 2: XPath로 탭 찾기 (숫자가 포함된 리뷰 탭 우선)
            if not review_tab_found:
                tab_selectors = [
                    # 숫자가 포함된 리뷰 탭 우선 (예: "리뷰 2,010")
                    "//*[contains(text(), '리뷰') and contains(text(), ',') and (contains(@class, 'tab') or name()='a' or name()='button')]",
                    "//*[contains(text(), '리뷰') and (contains(@class, 'tab') or name()='a' or name()='button')]",
                    "//*[contains(text(), '후기') and (contains(@class, 'tab') or name()='a' or name()='button')]",
                    "//a[contains(text(), '리뷰')]",
                    "//a[contains(text(), '후기')]",
                    "//button[contains(text(), '리뷰')]",
                    "//button[contains(text(), '후기')]",
                    "//*[contains(@class, 'tab')]//*[contains(text(), '리뷰')]",
                    "//*[contains(@class, 'tab')]//*[contains(text(), '후기')]",
                ]
                
                for selector in tab_selectors:
                    try:
                        tabs = self.driver.find_elements(By.XPATH, selector)
                        for tab in tabs:
                            if tab.is_displayed() and tab.is_enabled():
                                tab_text = tab.text.strip()
                                # 숫자가 포함된 리뷰 탭 찾기 (예: "리뷰 2,010")
                                if ('후기' in tab_text or '리뷰' in tab_text) and len(tab_text) > 0:
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
                                    time.sleep(1)
                                    self.driver.execute_script("arguments[0].click();", tab)
                                    time.sleep(3)
                                    review_tab_found = True
                                    print(f"✓ 후기/리뷰 탭 클릭 완료: {tab_text[:30]} (XPath)")
                                    break
                        if review_tab_found:
                            break
                    except:
                        continue
            
            # 방법 3: URL에 리뷰가 포함된 링크 찾기
            if not review_tab_found:
                try:
                    review_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='review'], a[href*='후기']")
                    for link in review_links:
                        if link.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                            time.sleep(1)
                            self.driver.execute_script("arguments[0].click();", link)
                            time.sleep(3)
                            review_tab_found = True
                            print("✓ 후기/리뷰 탭 클릭 완료 (링크 클릭)")
                            break
                except:
                    pass
            
            if not review_tab_found:
                print("⚠ 후기 탭을 찾지 못했습니다. 페이지 전체에서 후기 검색을 시도합니다.")
                # 후기 섹션으로 스크롤
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # 중복 체크를 위한 리뷰 ID 저장
            seen_review_ids = set()
            
            page = 1
            no_new_reviews_count = 0  # 새로운 리뷰가 없는 연속 횟수
            more_button_click_count = 0  # "더 보기" 버튼 클릭 횟수
            # max_more_clicks가 지정되면 사용, 아니면 test_mode에 따라 자동 설정
            if max_more_clicks is not None:
                MAX_MORE_BUTTON_CLICKS = max_more_clicks
            else:
                MAX_MORE_BUTTON_CLICKS = 3 if test_mode else 15  # 테스트 모드면 3번, 아니면 15번
            
            if test_mode:
                print(f"  [테스트 모드] '더 보기' 버튼을 {MAX_MORE_BUTTON_CLICKS}번만 클릭합니다.")
            elif max_more_clicks is not None:
                print(f"  [사용자 지정] '더 보기' 버튼을 {MAX_MORE_BUTTON_CLICKS}번 클릭합니다.")
            
            while (max_pages is None or page <= max_pages):
                print(f"\n[페이지 {page}] 후기 크롤링 중... (현재 누적: {len(reviews)}개)")
                
                # 디버깅: 페이지 HTML 저장
                if self.debug and page == 1:
                    self._save_debug_html(self.driver.page_source, f"page_{page}_source.html")
                
                # 현재 페이지의 리뷰 수 저장
                reviews_before = len(reviews)
                
                # 방법 1: Selenium으로 직접 리뷰 요소 찾기 (정확한 셀렉터 우선)
                selenium_reviews = []
                selenium_selectors = [
                    (By.CSS_SELECTOR, ".reviewCard"),  # 아모레몰의 개별 리뷰 카드
                    (By.CSS_SELECTOR, "div.reviewCard"),
                    (By.CSS_SELECTOR, "[class*='reviewCard']"),
                    (By.CSS_SELECTOR, "[class*='review']"),
                    (By.CSS_SELECTOR, "[class*='리뷰']"),
                    (By.CSS_SELECTOR, "[class*='comment']"),
                    (By.CSS_SELECTOR, "[data-review]"),
                    (By.CSS_SELECTOR, "[id*='review']"),
                    (By.XPATH, "//div[contains(@class, 'reviewCard')]"),
                    (By.XPATH, "//div[contains(@class, 'review')]"),
                    (By.XPATH, "//li[contains(@class, 'review')]"),
                    (By.XPATH, "//article[contains(@class, 'review')]"),
                ]
                
                for by, selector in selenium_selectors:
                    try:
                        elements = self.driver.find_elements(by, selector)
                        if elements:
                            selenium_reviews = elements
                            print(f"  ✓ Selenium으로 {len(elements)}개의 리뷰 요소 발견: {selector}")
                            break
                    except:
                        continue
                
                # 방법 2: BeautifulSoup으로 파싱
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # 다양한 방법으로 후기 요소 찾기
                review_elements = []
                
                # 정확한 셀렉터 우선 (아모레몰 구조에 맞춤)
                selectors = [
                    {'class': 'reviewCard'},  # 아모레몰의 개별 리뷰 카드
                    {'class': lambda x: x and 'reviewCard' in x},
                    {'class': re.compile('reviewCard', re.I)},
                    {'class': re.compile('review.*item|item.*review', re.I)},
                    {'class': re.compile('review|comment|후기|리뷰', re.I)},
                    {'class': lambda x: x and any(kw in x.lower() for kw in ['review', 'comment', '후기', '리뷰'])},
                    {'data-review': True},
                    {'id': re.compile('review|comment|리뷰|후기', re.I)},
                ]
                
                for selector in selectors:
                    elements = soup.find_all(['div', 'li', 'article', 'section', 'tr'], selector)
                    if elements:
                        # reviewArea는 제외 (전체 영역이므로)
                        elements = [e for e in elements if 'reviewArea' not in ' '.join(e.get('class', []))]
                        if elements:
                            review_elements = elements
                            print(f"  ✓ BeautifulSoup으로 {len(elements)}개의 후기 요소 발견 (방법: {selector})")
                            break
                
                # 방법 3: 텍스트 패턴으로 찾기 (사용자명, 평점 등이 있는 요소)
                if not review_elements:
                    all_divs = soup.find_all(['div', 'li', 'article'])
                    for div in all_divs:
                        text = div.get_text()
                        # 사용자명 패턴 (예: smle******) 또는 평점 패턴 찾기
                        if (re.search(r'\w+\*+|\d+대|여성|남성|지성|건성|수분', text) and 
                            len(text) > 50 and 
                            (re.search(r'지속력|촉촉|유분|향|각질', text) or len(text) > 100)):
                            review_elements.append(div)
                    if review_elements:
                        print(f"  ✓ {len(review_elements)}개의 후기 요소 발견 (텍스트 패턴)")
                
                # Selenium으로 찾은 요소를 BeautifulSoup 요소로 변환
                if selenium_reviews and not review_elements:
                    for selenium_elem in selenium_reviews[:20]:  # 최대 20개만
                        try:
                            html = selenium_elem.get_attribute('outerHTML')
                            if html:
                                soup_elem = BeautifulSoup(html, 'html.parser')
                                review_elements.append(soup_elem)
                        except:
                            continue
                    if review_elements:
                        print(f"  ✓ Selenium 요소를 BeautifulSoup으로 변환: {len(review_elements)}개")
                
                if not review_elements:
                    print("  ⚠ 후기 요소를 찾을 수 없습니다.")
                    # 디버깅: 페이지 구조 일부 출력
                    if page == 1:
                        print("  [디버깅] 페이지의 주요 클래스명:")
                        classes = set()
                        for tag in soup.find_all(class_=True)[:30]:
                            classes.update(tag.get('class', []))
                        print(f"    {', '.join(list(classes)[:15])}")
                        
                        # 디버깅: 리뷰 관련 텍스트가 있는 요소 찾기
                        review_text_elements = soup.find_all(string=re.compile('리뷰|후기|review', re.I))
                        if review_text_elements:
                            print(f"  [디버깅] '리뷰' 텍스트를 포함한 요소 {len(review_text_elements)}개 발견")
                            for i, elem in enumerate(review_text_elements[:3]):
                                parent = elem.parent if elem.parent else None
                                if parent:
                                    print(f"    예시 {i+1}: {parent.name} - {str(parent)[:200]}")
                    break
                
                # 디버깅: 첫 번째 요소의 HTML 샘플 저장
                if self.debug and page == 1 and review_elements:
                    sample_html = str(review_elements[0])[:2000]
                    self._save_debug_html(sample_html, f"review_element_sample.html")
                    print(f"  [디버깅] 첫 번째 후기 요소 샘플 저장")
                
                page_reviews = []
                for idx, element in enumerate(review_elements):
                    review_data = self._parse_review_element(element, idx)
                    if review_data:
                        # 중복 체크 (사용자명 + 리뷰 텍스트 일부로 고유 ID 생성)
                        review_id = f"{review_data.get('username', '')}_{review_data.get('review_text', '')[:50]}"
                        if review_id not in seen_review_ids:
                            seen_review_ids.add(review_id)
                            page_reviews.append(review_data)
                
                if not page_reviews:
                    print(f"  ⚠ 페이지 {page}에서 새로운 후기를 찾을 수 없습니다.")
                    no_new_reviews_count += 1
                    if no_new_reviews_count >= 3:
                        print(f"  ⚠ 연속 3회 새로운 후기가 없습니다. 크롤링 종료.")
                        break
                else:
                    no_new_reviews_count = 0  # 새로운 후기가 있으면 카운터 리셋
                
                reviews.extend(page_reviews)
                new_reviews_count = len(reviews) - reviews_before
                print(f"✓ 페이지 {page}에서 {new_reviews_count}개의 새로운 후기 추출 (누적: {len(reviews)}개)")
                
                # 최대 리뷰 수 제한 확인
                if max_reviews and len(reviews) >= max_reviews:
                    print(f"  ✓ 최대 리뷰 수({max_reviews}개)에 도달했습니다. 크롤링 종료.")
                    break
                
                # "더 보기" 버튼 찾기 및 클릭 (최대 20번 제한)
                more_button_found = False
                
                if more_button_click_count < MAX_MORE_BUTTON_CLICKS:
                    more_button_selectors = [
                        # CSS 셀렉터 (우선순위 높음)
                        (By.CSS_SELECTOR, "button.btnIr.more"),
                        (By.CSS_SELECTOR, ".btnIr.more"),
                        (By.CSS_SELECTOR, "button[class*='more']"),
                        (By.CSS_SELECTOR, "[class*='more'][class*='btn']"),
                        (By.CSS_SELECTOR, "a[class*='more']"),
                        (By.CSS_SELECTOR, "[class*='more']"),
                        # XPath 셀렉터
                        (By.XPATH, "//button[contains(text(), '더 보기')]"),
                        (By.XPATH, "//button[contains(text(), '더보기')]"),
                        (By.XPATH, "//*[contains(text(), '더 보기')]"),
                        (By.XPATH, "//*[contains(text(), '더보기')]"),
                        (By.XPATH, "//*[contains(text(), '더 많은 리뷰')]"),
                        (By.XPATH, "//*[contains(text(), '더 많은 후기')]"),
                        (By.XPATH, "//button[contains(@class, 'more')]"),
                        (By.XPATH, "//*[contains(@class, 'more') and contains(@class, 'btn')]"),
                        (By.XPATH, "//a[contains(text(), '더 보기')]"),
                        (By.XPATH, "//a[contains(text(), '더보기')]"),
                    ]
                    
                    for by, selector in more_button_selectors:
                        try:
                            # find_elements로 여러 버튼 찾기
                            more_buttons = self.driver.find_elements(by, selector)
                            for more_button in more_buttons:
                                if more_button and more_button.is_displayed():
                                    # 버튼이 비활성화되어 있지 않은지 확인
                                    is_disabled = (
                                        more_button.get_attribute('disabled') is not None or
                                        'disabled' in (more_button.get_attribute('class') or '') or
                                        'disabled' in (more_button.get_attribute('aria-disabled') or '')
                                    )
                                    
                                    # 버튼 텍스트 확인
                                    button_text = more_button.text.strip()
                                    if not button_text:
                                        button_text = more_button.get_attribute('textContent') or ''
                                    
                                    # "더 많은 리뷰 보기" 또는 "더 보기" 관련 텍스트가 있는지 확인
                                    if ('더' in button_text and ('보기' in button_text or '많은' in button_text or '리뷰' in button_text)) or (not button_text and 'more' in (more_button.get_attribute('class') or '').lower()):
                                        if not is_disabled:
                                            # 버튼이 보이도록 스크롤
                                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", more_button)
                                            time.sleep(1)
                                            # 버튼 클릭
                                            self.driver.execute_script("arguments[0].click();", more_button)
                                            time.sleep(3)  # 새로운 리뷰 로딩 대기
                                            # 추가로 아래로 스크롤하여 더 많은 리뷰 로드
                                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                            time.sleep(2)
                                            # 점진적 스크롤 (더 많은 리뷰 로드)
                                            for i in range(3):
                                                scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                                                scroll_pos = (i + 1) * (scroll_height // 4)
                                                self.driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                                                time.sleep(0.5)
                                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                            time.sleep(2)
                                            more_button_click_count += 1
                                            more_button_found = True
                                            print(f"  → '더 보기' 버튼 클릭 ({more_button_click_count}/{MAX_MORE_BUTTON_CLICKS}) - 추가 리뷰 로딩 중...")
                                            break
                            if more_button_found:
                                break
                        except:
                            continue
                else:
                    print(f"  ⚠ '더 보기' 버튼 최대 클릭 횟수({MAX_MORE_BUTTON_CLICKS}회)에 도달했습니다.")
                
                # "더 보기" 버튼이 없으면 다음 페이지 버튼 찾기
                if not more_button_found:
                    next_page_found = False
                    next_button_selectors = [
                        # 아모레몰 특정 셀렉터
                        (By.CSS_SELECTOR, ".pagination .next, .pagination .btnNext"),
                        (By.CSS_SELECTOR, "[class*='next']:not([disabled])"),
                        (By.CSS_SELECTOR, "button[class*='next'], a[class*='next']"),
                        # XPath 셀렉터
                        (By.XPATH, "//*[contains(@class, 'next') and not(contains(@class, 'disabled'))]"),
                        (By.XPATH, "//*[contains(@class, 'pagination')]//*[contains(text(), '다음')]"),
                        (By.XPATH, "//*[contains(@class, 'pagination')]//*[contains(text(), '>')]"),
                        (By.XPATH, "//button[contains(text(), '다음')]"),
                        (By.XPATH, "//a[contains(text(), '다음')]"),
                        # 숫자로 된 다음 페이지 버튼
                        (By.XPATH, f"//*[contains(@class, 'pagination')]//*[text()='{page + 1}']"),
                        (By.XPATH, f"//*[contains(@class, 'pagination')]//*[@data-page='{page + 1}']"),
                    ]
                    
                    for by, selector in next_button_selectors:
                        try:
                            next_button = self.driver.find_element(by, selector)
                            if next_button and next_button.is_displayed():
                                # 버튼이 비활성화되어 있지 않은지 확인
                                is_disabled = (
                                    next_button.get_attribute('disabled') is not None or
                                    'disabled' in (next_button.get_attribute('class') or '') or
                                    'disabled' in (next_button.get_attribute('aria-disabled') or '')
                                )
                                
                                if not is_disabled:
                                    # 스크롤하여 버튼이 보이도록
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                                    time.sleep(1)
                                    self.driver.execute_script("arguments[0].click();", next_button)
                                    time.sleep(3)  # 페이지 로딩 대기
                                    next_page_found = True
                                    print(f"  → 다음 페이지로 이동 (페이지 {page + 1})")
                                    break
                        except:
                            continue
                    
                    if next_page_found:
                        page += 1
                    else:
                        # "더 보기" 버튼도 없고 다음 페이지 버튼도 없으면 무한 스크롤 시도
                        print(f"  → 페이지네이션 버튼이 없습니다. 스크롤하여 추가 리뷰 로드 시도...")
                        # 페이지 하단으로 스크롤
                        last_height = self.driver.execute_script("return document.body.scrollHeight")
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        new_height = self.driver.execute_script("return document.body.scrollHeight")
                        
                        if new_height == last_height:
                            print(f"  ⚠ 더 이상 새로운 콘텐츠가 로드되지 않습니다. 크롤링 종료.")
                            break
                        else:
                            print(f"  → 스크롤로 추가 콘텐츠 로드됨. 계속 크롤링...")
                            page += 1
                else:
                    # "더 보기" 버튼을 클릭했으면 같은 페이지에서 계속
                    pass
            
        except Exception as e:
            print(f"후기 추출 오류: {e}")
            import traceback
            traceback.print_exc()
        
        return reviews
    
    def _parse_review_element(self, element, index: int = 0) -> Optional[Dict]:
        """
        개별 후기 요소 파싱
        
        Args:
            element: BeautifulSoup 요소
            index: 요소 인덱스 (디버깅용)
            
        Returns:
            파싱된 후기 데이터
        """
        try:
            # 요소의 전체 텍스트 가져오기
            all_text = element.get_text(separator='\n', strip=True)
            text_lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            # 최소한의 텍스트가 없으면 스킵
            if not all_text or len(all_text) < 20:
                return None
            
            review_data = {}
            
            # 사용자명 추출 - 아모레몰 구조에 맞춤
            username = ""
            # 아모레몰: span.profileCard__userTitle
            username_elem = (
                element.find('span', class_=re.compile('profileCard__userTitle|userTitle', re.I)) or
                element.find(class_=re.compile('profileCard__userTitle|userTitle', re.I)) or
                element.find('span', class_=lambda x: x and 'userTitle' in x) or
                element.find(class_=re.compile('user|name|nick|id', re.I))
            )
            if username_elem:
                username = username_elem.get_text(strip=True)
            
            # 텍스트에서 사용자명 패턴 직접 찾기
            if not username:
                username_match = re.search(r'([a-zA-Z0-9]+\*+)', all_text)
                if username_match:
                    username = username_match.group(1)
            
            # 사용자 정보 (나이/성별/피부타입 등) - 아모레몰 구조에 맞춤
            user_info = ""
            # 아모레몰: span.profileCard__userDesc
            info_elem = (
                element.find('span', class_=re.compile('profileCard__userDesc|userDesc', re.I)) or
                element.find(class_=re.compile('profileCard__userDesc|userDesc', re.I)) or
                element.find('span', class_=lambda x: x and 'userDesc' in x) or
                element.find(class_=re.compile('info|demographic|user-info', re.I))
            )
            if info_elem:
                user_info = info_elem.get_text(strip=True)
            
            # 텍스트에서 직접 추출 (백업)
            if not user_info:
                info_patterns = [
                    r'(\d+대[^\n]*여성|남성[^\n]*)',
                    r'(\d+대[^\n]*지성|건성|수분[^\n]*)',
                    r'(\d+대[^\n]*)',
                    r'(여성|남성[^\n]*지성|건성[^\n]*)'
                ]
                for pattern in info_patterns:
                    info_match = re.search(pattern, all_text)
                    if info_match:
                        user_info = info_match.group(1).strip()
                        break
            
            # user_info를 세분화하여 파싱
            age = ""
            gender = ""
            skin_type_1 = ""
            skin_type_2 = ""
            
            if user_info:
                # "/" 구분자가 있는 경우와 없는 경우 모두 처리
                if '/' in user_info:
                    # "20대/여성/지성/트러블" 형식 파싱
                    parts = [p.strip() for p in user_info.split('/') if p.strip()]
                    
                    if len(parts) >= 1:
                        # 나이 추출 (예: "20대", "30대")
                        age_match = re.search(r'(\d+대)', parts[0])
                        if age_match:
                            age = age_match.group(1)
                    
                    if len(parts) >= 2:
                        # 성별 추출
                        if '여성' in parts[1] or '여' in parts[1]:
                            gender = '여성'
                        elif '남성' in parts[1] or '남' in parts[1]:
                            gender = '남성'
                    
                    if len(parts) >= 3:
                        # 피부타입1 추출
                        skin_type_1 = parts[2]
                    
                    if len(parts) >= 4:
                        # 피부타입2 추출
                        skin_type_2 = parts[3]
                else:
                    # "/" 구분자가 없는 경우 (예: "40대여성복합성주름")
                    # 정규식으로 패턴 매칭하여 추출
                    
                    # 나이 추출 (예: "20대", "30대", "40대", "50대 이상")
                    age_match = re.search(r'(\d+대(?:\s*이상)?)', user_info)
                    if age_match:
                        age = age_match.group(1).strip()
                    
                    # 성별 추출
                    if '여성' in user_info or '여' in user_info:
                        gender = '여성'
                    elif '남성' in user_info or '남' in user_info:
                        gender = '남성'
                    
                    # 피부타입 패턴 정의 (더 포괄적으로)
                    # 주요 피부타입 (skin_type_1)
                    main_skin_types = [
                        '지성', '건성', '수분부족지성', '수분부족', '복합성', 
                        '민감성', '중성', '수분'
                    ]
                    
                    # 부가 정보 (skin_type_2)
                    additional_info = [
                        '트러블', '모공', '주름', '칙칙함', '건조함', 
                        '탄력없음', '수분부족', '민감성'
                    ]
                    
                    # 피부타입 추출 (긴 패턴부터 매칭)
                    found_main = None
                    found_additional = []
                    
                    # 주요 피부타입 찾기 (긴 것부터)
                    for st in sorted(main_skin_types, key=len, reverse=True):
                        if st in user_info:
                            found_main = st
                            break
                    
                    # 부가 정보 찾기
                    for info in sorted(additional_info, key=len, reverse=True):
                        if info in user_info and info != found_main:
                            found_additional.append(info)
                    
                    # 중복 제거
                    found_additional = list(dict.fromkeys(found_additional))  # 순서 유지하며 중복 제거
                    
                    # 피부타입 할당
                    if found_main:
                        skin_type_1 = found_main
                    
                    # 부가 정보 할당 (주요 피부타입과 중복되지 않는 것만)
                    if found_additional:
                        # 첫 번째 부가 정보를 skin_type_2에 할당
                        # 단, 이미 skin_type_1에 할당된 것은 제외
                        for info in found_additional:
                            if info != skin_type_1:
                                skin_type_2 = info
                                break
                        
                        # 두 번째 부가 정보가 있으면 skin_type_2에 추가 (또는 별도 처리)
                        if len(found_additional) > 1 and not skin_type_2:
                            for info in found_additional[1:]:
                                if info != skin_type_1:
                                    skin_type_2 = info
                                    break
                    
                    # 나이가 없고 피부타입만 있는 경우 (예: "건성건조함")
                    if not age and (skin_type_1 or skin_type_2):
                        # 이미 파싱된 상태이므로 그대로 사용
                        pass
            
            # 평점 추출 - 아모레몰 구조에 맞춤
            rating = 0
            
            # 방법 1: 아모레몰 구조 - div.icoStarWrap.star5 (star5 = 5점)
            star_wrap = element.find('div', class_=re.compile('icoStarWrap|starWrap', re.I))
            if star_wrap:
                star_class = ' '.join(star_wrap.get('class', []))
                # star5, star4 등의 패턴 찾기
                star_match = re.search(r'star(\d+)', star_class)
                if star_match:
                    rating = int(star_match.group(1))
                else:
                    # 별 개수 세기
                    stars = star_wrap.find_all('i', class_=re.compile('icoStar|star', re.I))
                    rating = len(stars) if stars else 0
            
            # 방법 2: 별 요소 직접 찾기
            if rating == 0:
                star_elements = element.find_all('i', class_=re.compile('icoStar|star', re.I))
                if star_elements:
                    rating = len(star_elements)
            
            # 방법 3: 텍스트에서 평점 숫자 찾기
            if rating == 0:
                rating_match = re.search(r'(\d+)\s*점|평점[:\s]*(\d+)|(\d+)\s*/\s*5', all_text)
                if rating_match:
                    rating = int(rating_match.group(1) or rating_match.group(2) or rating_match.group(3))
            
            # 방법 4: 클래스에서 평점 찾기
            if rating == 0:
                rating_elem = element.find(class_=re.compile('rating|score|point', re.I))
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    rating_match = re.search(r'(\d+)', rating_text)
                    if rating_match:
                        rating = int(rating_match.group(1))
            
            # 옵션 정보 (예: "옵션: 베리")
            option = ""
            option_patterns = [
                r'옵션[:\s]*([^\n]+)',
                r'option[:\s]*([^\n]+)',
                r'선택[:\s]*([^\n]+)'
            ]
            
            for pattern in option_patterns:
                option_match = re.search(pattern, all_text, re.I)
                if option_match:
                    option = option_match.group(1).strip()
                    break
            
            # 리뷰 텍스트 추출 - 아모레몰 구조에 맞춤
            review_text = ""
            
            # 방법 1: 아모레몰 구조 - p.txt 또는 div.txt
            text_elem = (
                element.find('p', class_='txt') or
                element.find('p', class_=lambda x: x and 'txt' in x) or
                element.find('div', class_='txt') or
                element.find(['p', 'div'], class_=re.compile('txt|text|content', re.I))
            )
            if text_elem:
                review_text = text_elem.get_text(strip=True)
                # 불필요한 텍스트 제거 (신고 버튼 등)
                review_text = re.sub(r'신고내용.*?차단하기', '', review_text, flags=re.DOTALL)
                review_text = re.sub(r'작성자:.*?글내용:', '', review_text)
                review_text = review_text.strip()
            
            # 방법 2: 모든 텍스트 라인 중 가장 긴 것 찾기
            if not review_text or len(review_text) < 20:
                # 리뷰 관련 키워드가 포함된 긴 텍스트 찾기
                review_keywords = ['지속력', '촉촉', '유분', '향', '각질', '입술', '립', '보습', '수분', '건조', '사용', '후기']
                candidate_texts = []
                
                for line in text_lines:
                    if len(line) > 30:  # 최소 길이
                        # 리뷰 키워드가 있거나 매우 긴 텍스트
                        if any(kw in line for kw in review_keywords) or len(line) > 100:
                            candidate_texts.append(line)
                
                if candidate_texts:
                    # 가장 긴 텍스트 선택
                    review_text = max(candidate_texts, key=len)
                    # 불필요한 텍스트 제거
                    review_text = re.sub(r'신고내용.*?차단하기', '', review_text, flags=re.DOTALL)
                    review_text = review_text.strip()
                elif text_lines:
                    # 키워드가 없어도 가장 긴 텍스트 선택
                    review_text = max(text_lines, key=len)
            
            # 리뷰 타입 (예: "한달 사용 리뷰")
            review_type = ""
            type_patterns = [
                r'(\d+\s*[일개월주년]+?\s*사용\s*리뷰)',
                r'(한달|한\s*달|1개월)\s*사용',
                r'사용\s*리뷰'
            ]
            
            for pattern in type_patterns:
                type_match = re.search(pattern, all_text, re.I)
                if type_match:
                    review_type = type_match.group(0).strip()
                    break
            
            # 특이사항 추출 (prdStyle 구조: dt/dd)
            special_note_1 = ""
            special_note_2 = ""
            special_note_3 = ""
            
            prd_style = element.find('div', class_=re.compile('prdStyle', re.I))
            if prd_style:
                # dt/dd 구조로 된 특이사항 추출
                dts = prd_style.find_all('dt')
                dds = prd_style.find_all('dd')
                
                special_notes = []
                for i, dt in enumerate(dts):
                    if i < len(dds):
                        label = dt.get_text(strip=True)
                        value = dds[i].get_text(strip=True)
                        special_notes.append(f"{label}: {value}")
                
                if len(special_notes) >= 1:
                    special_note_1 = special_notes[0]
                if len(special_notes) >= 2:
                    special_note_2 = special_notes[1]
                if len(special_notes) >= 3:
                    special_note_3 = special_notes[2]
            
            # 특이사항이 없으면 텍스트에서 키워드 기반으로 추출
            if not special_note_1:
                # 발색감, 지속력, 사용감, 향, 민감성, 보습감 등 키워드 찾기
                special_keywords = {
                    '지속력': ['지속', '오래', '오랫동안', '지속력'],
                    '발색감': ['발색', '색상', '컬러', '톤'],
                    '사용감': ['사용감', '발림', '밀착', '부드러움', '끈적'],
                    '향': ['향', '냄새', '향기', '아로마'],
                    '민감성': ['민감', '순함', '자극', '알레르기'],
                    '보습감': ['보습', '촉촉', '수분', '건조'],
                    '유분기': ['유분', '기름', '번들', '윤기'],
                    '광택감': ['광택', '글로시', '윤기', '번들']
                }
                
                found_notes = []
                for keyword, patterns in special_keywords.items():
                    for pattern in patterns:
                        if pattern in review_text or pattern in all_text:
                            # 해당 키워드 주변 텍스트 추출
                            text_to_search = review_text if review_text else all_text
                            match = re.search(f'{pattern}[^\n]*', text_to_search, re.I)
                            if match:
                                note_text = match.group(0).strip()[:50]  # 최대 50자
                                if note_text and note_text not in found_notes:
                                    found_notes.append(f"{keyword}: {note_text}")
                                    break
                
                if len(found_notes) >= 1:
                    special_note_1 = found_notes[0]
                if len(found_notes) >= 2:
                    special_note_2 = found_notes[1]
                if len(found_notes) >= 3:
                    special_note_3 = found_notes[2]
            
            # 최소한 리뷰 텍스트가 있어야 유효한 후기로 간주
            if review_text and len(review_text) > 10:
                review_data = {
                    'username': username,
                    'user_info': user_info,  # 원본 정보
                    'age': age,
                    'gender': gender,
                    'skin_type_1': skin_type_1,
                    'skin_type_2': skin_type_2,
                    'rating': rating if rating > 0 else None,
                    'option': option,
                    'review_type': review_type,
                    'special_note_1': special_note_1,  # 특이사항1 (예: "지속력: 오래 지속돼요")
                    'special_note_2': special_note_2,  # 특이사항2 (예: "유분기: 유분 적당해요")
                    'special_note_3': special_note_3,  # 특이사항3 (예: "촉촉함: 촉촉해요")
                    'review_text': review_text,
                }
                
                # 디버깅 모드일 때만 raw_html 저장
                if self.debug:
                    review_data['raw_html'] = str(element)[:1000]
                
                return review_data
            else:
                # 디버깅: 파싱 실패 원인 출력
                if self.debug and index < 3:
                    print(f"    [디버깅] 요소 {index} 파싱 실패 - 텍스트 길이: {len(review_text) if review_text else 0}")
                    print(f"      전체 텍스트 샘플: {all_text[:200]}")
            
        except Exception as e:
            if self.debug:
                print(f"후기 파싱 오류 (요소 {index}): {e}")
        
        return None
    
    def crawl_product_reviews(self, url: str, max_pages: int = 10, max_reviews: int = None, test_mode: bool = False, max_more_clicks: int = None) -> Dict:
        """
        제품 후기 전체 크롤링
        
        프로세스:
        1. 제품 페이지 접속
        2. 리뷰 수집 (더 많은 리뷰 보기 버튼 클릭)
        3. 리뷰 수집 후 상품정보제공 고시 보기로 상품 정보 수집
        4. 뒤로가기로 전체 제품 페이지로 복귀
        
        Args:
            url: 제품 페이지 URL
            max_pages: 최대 페이지 수 (None이면 모든 페이지)
            max_reviews: 최대 리뷰 수 (None이면 제한 없음)
            test_mode: 테스트 모드 (더 보기 버튼 3번만 클릭)
            
        Returns:
            제품 정보와 후기 리스트를 포함한 딕셔너리
        """
        # 1. 제품 페이지 접속 및 기본 정보 수집
        self.driver.get(url)
        time.sleep(3)
        self._close_popups()
        
        # 제품 기본 정보 먼저 수집 (가격, 평점, 제품명 등)
        basic_info = self.get_product_info(url)
        
        # 2. 리뷰 수집
        reviews = self.extract_reviews(max_pages, max_reviews, test_mode)
        
        # 3. 리뷰 수집 후 "상품상세" 탭 클릭
        print("  → '상품상세' 탭 클릭 중...")
        try:
            # "상품상세" 탭 찾기 및 클릭
            detail_tab_selectors = [
                (By.XPATH, "//*[contains(text(), '상품상세')]"),
                (By.XPATH, "//*[contains(text(), '상품 상세')]"),
                (By.XPATH, "//*[contains(text(), '상세')]"),
                (By.CSS_SELECTOR, "[class*='tab'][class*='detail']"),
                (By.CSS_SELECTOR, "[class*='tab'][class*='상세']"),
            ]
            
            detail_tab_found = False
            for by, selector in detail_tab_selectors:
                try:
                    detail_tab = self.driver.find_element(by, selector)
                    if detail_tab and detail_tab.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", detail_tab)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", detail_tab)
                        time.sleep(2)
                        print("  ✓ '상품상세' 탭 클릭 완료")
                        detail_tab_found = True
                        break
                except:
                    continue
            
            if not detail_tab_found:
                print("  ⚠ '상품상세' 탭을 찾을 수 없습니다. 상품 페이지로 다시 이동합니다.")
                self.driver.get(url)
                time.sleep(3)
                self._close_popups()
        except Exception as e:
            if self.debug:
                print(f"  [디버깅] '상품상세' 탭 클릭 오류: {e}")
            # 오류 발생 시 상품 페이지로 다시 이동
            self.driver.get(url)
            time.sleep(3)
            self._close_popups()
        
        # 4. 상품정보제공 고시 보기로 상품 정보 수집
        print("  → 상품정보제공 고시에서 상품 정보 수집 중...")
        notice_info = self._get_product_info_from_notice(url)
        
        # 기본 정보와 고시 정보 병합
        # notice_info는 usage_method, ingredients, precautions만 포함
        # 나머지는 모두 basic_info에서 가져오기
        product_info = {**basic_info}  # basic_info를 기본으로
        # notice_info에서 usage_method, ingredients, precautions만 추가
        if notice_info.get('usage_method'):
            product_info['usage_method'] = notice_info['usage_method']
        if notice_info.get('ingredients'):
            product_info['ingredients'] = notice_info['ingredients']
        if notice_info.get('precautions'):
            product_info['precautions'] = notice_info['precautions']
        
        # 상품 정보 수집 결과 로그 출력
        if product_info.get('ingredients'):
            print(f"  ✓ 성분 정보 수집 완료 ({len(product_info['ingredients'])}자)")
        else:
            print(f"  ⚠ 성분 정보를 찾을 수 없습니다.")
        
        if product_info.get('usage_method'):
            print(f"  ✓ 사용 방법 수집 완료 ({len(product_info['usage_method'])}자)")
        
        if product_info.get('precautions'):
            print(f"  ✓ 주의사항 수집 완료 ({len(product_info['precautions'])}자)")
        
        # 5. 뒤로가기로 전체 제품 페이지로 복귀 (한번만)
        try:
            self.driver.back()
            time.sleep(2)
            # 만약 상품정보제공 고시 페이지에 있다면 한 번 더 뒤로가기
            if 'notice' in self.driver.current_url.lower() or '고시' in self.driver.current_url.lower():
                self.driver.back()
                time.sleep(2)
            print("  ✓ 뒤로가기로 전체 제품 페이지로 복귀")
        except:
            pass
        
        return {
            'product_info': product_info,
            'reviews': reviews,
            'total_reviews': len(reviews)
        }
    
    def get_brand_products(self, brand_url: str, max_products: int = None) -> tuple[List[Dict], str]:
        """
        브랜드 페이지 또는 카테고리 페이지에서 모든 제품 링크 추출
        
        Args:
            brand_url: 브랜드 페이지 URL 또는 카테고리 페이지 URL
            max_products: 최대 제품 수 (None이면 모든 제품)
            
        Returns:
            (제품 정보 리스트, 브랜드명) 튜플
        """
        # URL 타입 확인
        if 'displayCategorySn' in brand_url:
            page_type = "카테고리"
        elif 'brandSn' in brand_url:
            page_type = "브랜드"
        else:
            page_type = "제품 목록"
        
        print(f"\n{page_type} 페이지에서 제품 목록 추출 중: {brand_url}")
        self.driver.get(brand_url)
        time.sleep(3)
        
        # 팝업 닫기
        self._close_popups()
        
        # 브랜드명 추출
        brand_name = ""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            # 브랜드명 찾기 (h1, 브랜드 로고 alt, 페이지 타이틀 등)
            brand_elem = (
                soup.find('h1') or
                soup.find(class_=re.compile('brand.*name|brand.*title', re.I)) or
                soup.find('img', alt=re.compile('로고|brand', re.I))
            )
            if brand_elem:
                if brand_elem.name == 'img':
                    brand_name = brand_elem.get('alt', '')
                else:
                    brand_name = brand_elem.get_text(strip=True)
                # "설화수 로고" -> "설화수", "설화수 브랜드관" -> "설화수"
                brand_name = re.sub(r'\s*로고.*', '', brand_name).strip()
                brand_name = re.sub(r'\s*브랜드관.*', '', brand_name).strip()
                if not brand_name and brand_elem.name != 'img':
                    brand_name = brand_elem.get('title', '')
                    brand_name = re.sub(r'\s*로고.*', '', brand_name).strip()
                    brand_name = re.sub(r'\s*브랜드관.*', '', brand_name).strip()
            
            # 페이지 타이틀에서 추출 시도
            if not brand_name:
                title = soup.find('title')
                if title:
                    title_text = title.get_text(strip=True)
                    # "설화수 - 아모레몰" -> "설화수"
                    brand_name = title_text.split('-')[0].split('|')[0].strip()
                    brand_name = re.sub(r'\s*브랜드관.*', '', brand_name).strip()
            
            # URL에서 브랜드 번호로 기본값 설정
            if not brand_name:
                if 'brandSn=18' in brand_url:
                    brand_name = "sulwhasoo"
                elif 'brandSn=' in brand_url:
                    brand_sn = brand_url.split('brandSn=')[1].split('&')[0]
                    brand_name = f"brand_{brand_sn}"
                elif 'displayCategorySn=' in brand_url:
                    cat_sn = brand_url.split('displayCategorySn=')[1].split('&')[0]
                    brand_name = f"category_{cat_sn}"
                else:
                    brand_name = "unknown"
        except:
            brand_name = "unknown"
        
        products = []
        seen_urls = set()
        page = 1
        max_products_target = None  # 목표 제품 수 (77개 등)
        
        # 브랜드 페이지인 경우 목표 제품 수 확인
        if 'brandSn=' in brand_url or 'displayCategorySn=' in brand_url:
            try:
                # 페이지에서 "87개" 같은 텍스트 찾기 (다양한 패턴 시도)
                page_text = self.driver.page_source
                count_patterns = [
                    r'(\d+)\s*개의?\s*상품',
                    r'(\d+)\s*개의?\s*제품',
                    r'상품.*?(\d+)\s*개',
                    r'제품.*?(\d+)\s*개',
                ]
                
                for pattern in count_patterns:
                    count_match = re.search(pattern, page_text)
                    if count_match:
                        max_products_target = int(count_match.group(1))
                        print(f"  → 목표 제품 수: {max_products_target}개")
                        break
                
                # Selenium으로도 시도
                if not max_products_target:
                    try:
                        count_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '개의 상품') or contains(text(), '개의 제품')]")
                        for elem in count_elements:
                            text = elem.text.strip()
                            count_match = re.search(r'(\d+)\s*개의?\s*(?:상품|제품)', text)
                            if count_match:
                                max_products_target = int(count_match.group(1))
                                print(f"  → 목표 제품 수: {max_products_target}개 (Selenium)")
                                break
                    except:
                        pass
            except:
                pass
        
        while True:
            print(f"  [페이지 {page}] 제품 링크 찾는 중...")
            
            # 페이지가 완전히 로드될 때까지 대기
            time.sleep(2)
            
            # 첫 페이지에서 목표 제품 수에 도달할 때까지 스크롤 반복
            if page == 1:
                if max_products_target:
                    print(f"    → 목표 제품 수({max_products_target}개)에 도달할 때까지 스크롤 중...")
                else:
                    print(f"    → 모든 제품을 로드하기 위해 스크롤 중...")
                
                scroll_count = 0
                max_scrolls = 15  # 최대 15번 스크롤
                last_count = 0
                no_change_count = 0
                
                while scroll_count < max_scrolls:
                    # 부드러운 점진적 스크롤
                    last_height = self.driver.execute_script("return document.body.scrollHeight")
                    scroll_steps = 8
                    for i in range(scroll_steps):
                        scroll_position = int((i + 1) * (last_height / scroll_steps))
                        self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                        time.sleep(0.3)
                    
                    # 끝까지 스크롤
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)  # 제품 로드 대기 (시간 증가)
                    
                    # "더 보기" 버튼 클릭 시도
                    try:
                        more_button_selectors = [
                            (By.XPATH, "//*[contains(text(), '더 보기')]"),
                            (By.XPATH, "//*[contains(text(), '더보기')]"),
                            (By.XPATH, "//*[contains(text(), '더 많은')]"),
                            (By.XPATH, "//button[contains(@class, 'more')]"),
                            (By.XPATH, "//a[contains(@class, 'more')]"),
                            (By.CSS_SELECTOR, "[class*='more'][class*='button']"),
                            (By.CSS_SELECTOR, "[class*='load'][class*='more']"),
                        ]
                        
                        for by, selector in more_button_selectors:
                            try:
                                more_buttons = self.driver.find_elements(by, selector)
                                for btn in more_buttons:
                                    if btn.is_displayed() and btn.is_enabled():
                                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                        time.sleep(0.5)
                                        self.driver.execute_script("arguments[0].click();", btn)
                                        time.sleep(3)  # 클릭 후 제품 로드 대기
                                        print(f"    → '더 보기' 버튼 클릭")
                                        # 버튼 클릭 후 다시 스크롤
                                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                        time.sleep(2)
                                        break
                            except:
                                continue
                    except:
                        pass
                    
                    # 현재 제품 개수 확인 (스크롤 및 버튼 클릭 후)
                    current_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/detail']")
                    seen_hrefs = set()
                    for link in current_links:
                        href = link.get_attribute('href')
                        if href and '/product/detail' in href:
                            if href.startswith('/'):
                                href = 'https://www.amoremall.com' + href
                            seen_hrefs.add(href)
                    current_count = len(seen_hrefs)
                    
                    # 목표 제품 수에 도달했는지 확인
                    if max_products_target and current_count >= max_products_target:
                        print(f"    ✓ 목표 제품 수({max_products_target}개)에 도달! (현재: {current_count}개)")
                        break
                    
                    # 제품 개수가 변하지 않으면 종료
                    if current_count == last_count:
                        no_change_count += 1
                        if no_change_count >= 2:  # 2번 연속 변하지 않으면 종료
                            print(f"    → 제품 개수가 더 이상 증가하지 않습니다. (현재: {current_count}개)")
                            break
                    else:
                        no_change_count = 0
                        print(f"    → 제품 개수 증가: {last_count}개 → {current_count}개")
                    
                    last_count = current_count
                    scroll_count += 1
                    
                    if scroll_count % 2 == 0:
                        print(f"    → 스크롤 {scroll_count}회 진행 중... (현재 발견: {current_count}개{f' / 목표: {max_products_target}개' if max_products_target else ''})")
                
                # 다시 맨 위로 스크롤 (파싱을 위해)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            
            # 페이지 소스 파싱
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 제품 링크 찾기 (더 포괄적으로)
            product_links = []
            
            # 방법 1: Selenium으로 직접 찾기 (더 정확함)
            try:
                selenium_links = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "a[href*='/product/detail']"
                )
                if selenium_links:
                    product_links = selenium_links
                    print(f"    ✓ Selenium으로 {len(selenium_links)}개의 링크 발견")
            except:
                pass
            
            # 방법 2: BeautifulSoup으로 찾기 (Selenium이 실패한 경우)
            if not product_links:
                link_selectors = [
                    {'href': re.compile(r'/product/detail.*onlineProdCode=')},
                    {'href': re.compile(r'/product/detail')},
                    {'class': re.compile('product|item|goods', re.I)},
                ]
                
                for selector in link_selectors:
                    links = soup.find_all('a', selector)
                    if links:
                        product_links = links
                        print(f"    ✓ BeautifulSoup으로 {len(links)}개의 링크 발견")
                        break
            
            # 제품 정보 추출
            new_products_count = 0
            for link in product_links:
                try:
                    if hasattr(link, 'get'):
                        # BeautifulSoup 요소
                        href = link.get('href', '')
                    else:
                        # Selenium 요소
                        href = link.get_attribute('href')
                    
                    if not href:
                        continue
                    
                    # 상대 경로를 절대 경로로 변환
                    if href.startswith('/'):
                        href = 'https://www.amoremall.com' + href
                    elif not href.startswith('http'):
                        continue
                    
                    # 제품 상세 페이지 URL인지 확인
                    if '/product/detail' not in href:
                        continue
                    
                    # 전체 상품 목록 페이지로 이동하는 링크는 제외
                    # 예: "전체 상품", "전체보기" 등의 링크는 제외
                    if 'display/category' in href or 'display/brand' in href:
                        # 브랜드/카테고리 페이지 링크는 제외 (제품 상세 페이지만)
                        if '/product/detail' not in href:
                            continue
                    
                    # 중복 체크
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    # 제품 코드 추출
                    product_code = ""
                    if 'onlineProdCode=' in href:
                        product_code = href.split('onlineProdCode=')[1].split('&')[0]
                    elif 'onlineProdSn=' in href:
                        # onlineProdSn만 있는 경우 onlineProdSn을 제품 코드로 사용
                        product_code = href.split('onlineProdSn=')[1].split('&')[0]
                    
                    # 제품명 추출 (가능한 경우)
                    product_name_raw = ""
                    if hasattr(link, 'get_text'):
                        product_name_raw = link.get_text(strip=True)
                    else:
                        product_name_raw = link.text.strip()
                    
                    # 제품명 파싱: "10%135,000원자음2종 세트 (150ml+125ml)4.9(4,374)좋아요"
                    product_name = product_name_raw
                    if product_name_raw and len(product_name_raw) > 10:
                        # 가격과 평점 사이의 제품명 추출
                        price_match = re.search(r'(\d{1,3}(?:,\d{3})*)원', product_name_raw)
                        rating_match = re.search(r'(\d+\.?\d*)', product_name_raw)
                        
                        if price_match and rating_match:
                            price_pos = product_name_raw.find(price_match.group(0))
                            rating_pos = product_name_raw.find(rating_match.group(0), price_pos + len(price_match.group(0)))
                            if price_pos >= 0 and rating_pos > price_pos:
                                product_name = product_name_raw[price_pos + len(price_match.group(0)):rating_pos].strip()
                        elif price_match:
                            # 가격만 있는 경우
                            price_pos = product_name_raw.find(price_match.group(0))
                            if price_pos >= 0:
                                remaining = product_name_raw[price_pos + len(price_match.group(0)):]
                                # 평점이나 리뷰 개수 패턴 찾기
                                rating_match = re.search(r'(\d+\.?\d*)', remaining)
                                if rating_match:
                                    rating_pos = remaining.find(rating_match.group(1))
                                    product_name = remaining[:rating_pos].strip()
                                else:
                                    product_name = remaining.strip()
                        
                        # 제품명 정리 (가격, 할인율, 평점, 리뷰 수 제거)
                        product_name = re.sub(r'^\d+%', '', product_name)  # 앞의 할인율 제거
                        product_name = re.sub(r'^\d{1,3}(?:,\d{3})*원', '', product_name)  # 앞의 가격 제거
                        # 평점과 리뷰 수 제거 (예: "4.9(4,375)" 패턴) - 여러 번 시도
                        product_name = re.sub(r'\d+\.\d+\(\d{1,3}(?:,\d{3})*\)', '', product_name)  # "4.9(4,375)" 패턴 제거
                        product_name = re.sub(r'\d+\.\d+', '', product_name)  # 평점 제거 (예: "4.9")
                        product_name = re.sub(r'\(\d{1,3}(?:,\d{3})*\)', '', product_name)  # 리뷰 개수 제거 (예: "(4,375)")
                        product_name = re.sub(r'\d+\.?\d*$', '', product_name)  # 뒤의 평점 제거
                        product_name = re.sub(r'좋아요$', '', product_name)  # "좋아요" 제거
                        product_name = product_name.strip()
                    
                    # 너무 짧은 텍스트는 제품명이 아닐 수 있음
                    if len(product_name) < 3:
                        product_name = ""
                    
                    products.append({
                        'product_url': href,
                        'product_name': product_name,
                        'product_code': product_code
                    })
                    new_products_count += 1
                    
                    if max_products and len(products) >= max_products:
                        break
                        
                except Exception as e:
                    if self.debug:
                        print(f"    [디버깅] 링크 처리 오류: {e}")
                    continue
            
            print(f"    → {new_products_count}개의 새로운 제품 발견 (누적: {len(products)}개)")
            
            if max_products and len(products) >= max_products:
                break
            
            # 브랜드/카테고리 페이지에서는 페이지네이션을 사용하지 않고 스크롤만 사용
            # (전체 상품 목록 페이지로 이동하지 않도록)
            next_page_found = False
            if 'brandSn=' not in brand_url and 'displayCategorySn=' not in brand_url:
                # 브랜드/카테고리가 아닌 경우에만 페이지네이션 시도
                next_selectors = [
                    (By.XPATH, "//*[contains(@class, 'next') and not(contains(@class, 'disabled'))]"),
                    (By.XPATH, "//*[contains(@class, 'pagination')]//*[contains(text(), '다음')]"),
                    (By.XPATH, "//button[contains(text(), '다음')]"),
                    (By.XPATH, "//a[contains(text(), '다음')]"),
                    (By.CSS_SELECTOR, ".pagination .next:not(.disabled)"),
                ]
                
                for by, selector in next_selectors:
                    try:
                        next_button = self.driver.find_element(by, selector)
                        if next_button and next_button.is_displayed():
                            is_disabled = (
                                next_button.get_attribute('disabled') is not None or
                                'disabled' in (next_button.get_attribute('class') or '')
                            )
                            if not is_disabled:
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", next_button)
                                time.sleep(3)
                                next_page_found = True
                                print(f"    → 다음 페이지로 이동")
                                break
                    except:
                        continue
            
            # 첫 페이지에서 목표 제품 수를 모두 찾았으면 스크롤 불필요
            if page == 1 and max_products_target and len(products) >= max_products_target:
                print(f"    ✓ 첫 페이지에서 목표 제품 수({max_products_target}개)를 모두 찾았습니다!")
                break
            
            # 첫 페이지에서 목표 제품 수를 모두 찾았으면 추가 스크롤 불필요
            if page == 1 and max_products_target and len(products) >= max_products_target:
                print(f"    ✓ 첫 페이지에서 목표 제품 수({max_products_target}개)를 모두 찾았습니다!")
                break
            
            # 브랜드/카테고리 페이지이거나 페이지네이션이 없으면 스크롤 방식으로 전환
            # 하지만 첫 페이지에서 이미 스크롤했으므로 추가 스크롤은 최소화
            if not next_page_found or new_products_count == 0:
                # 첫 페이지가 아니거나 목표 제품 수를 못 찾은 경우에만 추가 시도 (1번만)
                if page == 1 and max_products_target and len(products) < max_products_target:
                    print(f"    → 목표 제품 수({max_products_target}개) 미달, 한 번만 추가 시도... (현재: {len(products)}개)")
                    # 한 번만 끝까지 스크롤
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)
                    
                    # 페이지 소스 다시 파싱
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    selenium_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/detail']")
                    
                    # 새로운 제품 추가
                    for link in selenium_links:
                        try:
                            href = link.get_attribute('href')
                            if not href or href in seen_urls:
                                continue
                            if href.startswith('/'):
                                href = 'https://www.amoremall.com' + href
                            if '/product/detail' not in href:
                                continue
                            
                            seen_urls.add(href)
                            product_code = ""
                            if 'onlineProdCode=' in href:
                                product_code = href.split('onlineProdCode=')[1].split('&')[0]
                            elif 'onlineProdSn=' in href:
                                product_code = href.split('onlineProdSn=')[1].split('&')[0]
                            
                            product_name = link.text.strip() if link.text else ""
                            if product_name and len(product_name) > 10:
                                # 제품명 정리
                                product_name = re.sub(r'^\d+%', '', product_name)
                                product_name = re.sub(r'^\d{1,3}(?:,\d{3})*원', '', product_name)
                                product_name = re.sub(r'\d+\.?\d*\(\d{1,3}(?:,\d{3})*\)', '', product_name)
                                product_name = re.sub(r'\d+\.\d+', '', product_name)
                                product_name = re.sub(r'\(\d{1,3}(?:,\d{3})*\)', '', product_name)
                                product_name = re.sub(r'\d+\.?\d*$', '', product_name)
                                product_name = re.sub(r'좋아요$', '', product_name)
                                product_name = product_name.strip()
                            
                            if len(product_name) < 3:
                                product_name = ""
                            
                            products.append({
                                'product_url': href,
                                'product_name': product_name,
                                'product_code': product_code
                            })
                            
                            if max_products_target and len(products) >= max_products_target:
                                break
                        except:
                            continue
                    
                    if max_products_target and len(products) >= max_products_target:
                        print(f"    ✓ 목표 제품 수({max_products_target}개)에 도달했습니다!")
                        break
                
                # 추가 스크롤 루프 제거 (한 번만 시도했으므로 종료)
                break
                
                if consecutive_no_new >= 10 or (max_products and len(products) >= max_products):
                    break
                else:
                    page += 1
            else:
                page += 1
        
        print(f"\n✓ 총 {len(products)}개의 제품 발견")
        if brand_name:
            print(f"  브랜드명: {brand_name}")
        
        return products, brand_name
    
    def crawl_brand_products(self, brand_url: str, max_products: int = None, max_pages_per_product: int = 10, max_reviews_per_product: int = None, test_mode: bool = False, max_more_clicks: int = None, resume: bool = True) -> tuple[List[Dict], str]:
        """
        브랜드의 모든 제품 리뷰 크롤링
        
        Args:
            brand_url: 브랜드 페이지 URL
            max_products: 최대 제품 수 (None이면 모든 제품)
            max_pages_per_product: 제품당 최대 페이지 수
            max_reviews_per_product: 제품당 최대 리뷰 수
            test_mode: 테스트 모드 (더 보기 버튼 3번만 클릭)
            max_more_clicks: 더 보기 버튼 최대 클릭 횟수
            resume: 중단 후 재개 모드 (기존 JSON 파일에서 이미 크롤링된 제품 건너뛰기)
            
        Returns:
            (각 제품의 크롤링 결과 리스트, 브랜드명) 튜플
        """
        # 1. 브랜드 페이지에서 모든 제품 링크 추출
        products, brand_name = self.get_brand_products(brand_url, max_products)
        
        if not products:
            print("⚠ 제품을 찾을 수 없습니다.")
            return [], brand_name
        
        # 2. 중단 후 재개: 기존 JSON 파일에서 이미 크롤링된 제품 확인
        crawled_product_codes = set()
        if resume:
            info_file = f"info_{brand_name}.json"
            if os.path.exists(info_file):
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        for product in existing_data.get('products', []):
                            if product.get('product_code'):
                                crawled_product_codes.add(product['product_code'])
                    if crawled_product_codes:
                        print(f"\n✓ 기존 크롤링 데이터 발견: {len(crawled_product_codes)}개 제품 이미 크롤링됨")
                        print(f"  → 중단된 지점부터 재개합니다.")
                except Exception as e:
                    if self.debug:
                        print(f"  [디버깅] 기존 파일 읽기 오류: {e}")
        
        # 3. 각 제품의 리뷰 크롤링
        results = []
        total_products = len(products)
        skipped_count = 0
        
        print(f"\n{'='*60}")
        print(f"총 {total_products}개 제품의 리뷰 크롤링 시작")
        if crawled_product_codes:
            print(f"  (이미 크롤링된 {len(crawled_product_codes)}개 제품 건너뛰기)")
        print(f"{'='*60}")
        
        for idx, product in enumerate(products, 1):
            product_code = product.get('product_code', '')
            product_name = product.get('product_name', '제품명 없음')
            
            # 이미 크롤링된 제품은 건너뛰기
            if resume and product_code and product_code in crawled_product_codes:
                print(f"\n[{idx}/{total_products}] {product_name}")
                print(f"  ⏭ 이미 크롤링된 제품입니다. 건너뜁니다.")
                skipped_count += 1
                continue
            
            print(f"\n[{idx}/{total_products}] {product_name}")
            print(f"  URL: {product['product_url']}")
            
            try:
                result = self.crawl_product_reviews(
                    product['product_url'],
                    max_pages=max_pages_per_product,
                    max_reviews=max_reviews_per_product,
                    test_mode=test_mode,
                    max_more_clicks=max_more_clicks
                )
                
                # 제품 정보 업데이트 (크롤링한 정보와 브랜드 페이지 정보 병합)
                # 브랜드 페이지에서 가져온 정보로 업데이트 (제품명은 크롤링한 것이 우선)
                if product.get('product_code') and not result['product_info'].get('product_code'):
                    result['product_info']['product_code'] = product['product_code']
                if product.get('product_url'):
                    result['product_info']['product_url'] = product['product_url']
                # 브랜드 페이지의 제품명이 더 정리되어 있으면 사용 (크롤링한 제품명이 비어있는 경우)
                if not result['product_info'].get('product_name') and product.get('product_name'):
                    result['product_info']['product_name'] = product['product_name']
                results.append(result)
                
                print(f"  ✓ {len(result['reviews'])}개의 후기 추출 완료")
                
            except Exception as e:
                print(f"  ✗ 오류 발생: {e}")
                import traceback
                if self.debug:
                    traceback.print_exc()
                continue
        
        print(f"\n{'='*60}")
        print(f"크롤링 완료: {len(results)}개 제품 (건너뛴 제품: {skipped_count}개)")
        print(f"{'='*60}")
        
        return results, brand_name
    
    def close(self):
        """브라우저 종료"""
        self.driver.quit()


if __name__ == "__main__":
    # 테스트
    url = "https://www.amoremall.com/kr/ko/product/detail?onlineProdSn=63063&clickUrl=pc%3D1766379469907&cust=null&recommendId=3505e7fb-8916-41fa-bcc0-507c55948275&dp=MOB_CAT_ORD_RANK&planId=RP-230807-095421&scenarioId=scenario_1&itemSetId=IS-201022-091405&targetGroupId=ALL&channelId=channel_2&abTestKey=0&ITEM_VALUE=CTG002_111970001785&onlineProdCode=111970001785"
    
    crawler = AmoreMallCrawler(headless=False)
    try:
        result = crawler.crawl_product_reviews(url, max_pages=5)
        print(f"\n총 {result['total_reviews']}개의 후기 추출")
        print(f"\n제품 정보: {result['product_info']}")
        print(f"\n첫 번째 후기 예시:")
        if result['reviews']:
            print(json.dumps(result['reviews'][0], ensure_ascii=False, indent=2))
    finally:
        crawler.close()

