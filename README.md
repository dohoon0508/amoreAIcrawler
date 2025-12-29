# 아모레몰 제품 후기 크롤링 및 데이터베이스화 시스템

아모레몰 제품 페이지에서 고객 후기와 제품 정보를 크롤링하고, 데이터베이스에 저장하는 시스템입니다.

## 주요 기능

### ✅ 제품 정보 크롤링
- 제품명, 제품 코드, URL
- 카테고리, 세부 카테고리
- 가격 정보 (정가, 할인가, 할인률)
- 평균 평점, 리뷰 개수
- 사용 방법, 성분, 주의사항 (상품정보제공 고시에서 추출)

### ✅ 리뷰 크롤링
- 사용자 정보 (사용자명, 나이, 성별, 피부타입1, 피부타입2)
- 평점, 제품 옵션, 리뷰 타입
- 리뷰 텍스트
- 특이사항 (발색감, 지속력, 사용감, 향, 민감성 등)
- "더 보기" 버튼 자동 클릭으로 대량 리뷰 수집

### ✅ 브랜드 전체 크롤링
- 브랜드 페이지에서 모든 제품 자동 탐색
- 각 제품별 정보 및 리뷰 수집
- JSON 파일 자동 분리 저장 (제품 정보 / 리뷰)
- **재개 기능**: 중단된 크롤링을 자동으로 이어서 진행
- **중복 리뷰 제거**: 동일한 리뷰 자동 감지 및 제거

## 설치

### 1. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

또는 개별 설치:

```bash
pip install selenium beautifulsoup4 requests sqlalchemy lxml webdriver-manager python-dotenv
```

### 2. Chrome 브라우저 확인

Chrome 브라우저가 설치되어 있어야 합니다. ChromeDriver는 자동으로 다운로드됩니다.

### 3. (선택사항) OpenAI API 사용

OpenAI API를 사용한 요약 기능을 사용하려면:

```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

## 사용 방법

### 1. 단일 제품 크롤링

```bash
python main.py "제품_URL"
```

**예시:**
```bash
python main.py "https://www.amoremall.com/kr/ko/product/detail?onlineProdSn=63063&onlineProdCode=111970001785"
```

### 2. 브랜드 전체 제품 크롤링

```bash
python main.py "브랜드_URL" --brand
```

**예시:**
```bash
# 설화수 전체 제품 크롤링 (더보기 10번)
python main.py "https://www.amoremall.com/kr/ko/display/brand/detail/all?brandSn=18" --brand --max-more-clicks 10
```

### 3. 크롤링 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--brand` | 브랜드 페이지 모드 (모든 제품 크롤링) | False |
| `--max-products N` | 브랜드 모드에서 최대 제품 수 | 모든 제품 |
| `--max-pages N` | 최대 페이지 수 (0이면 모든 페이지) | 10 |
| `--max-reviews N` | 최대 리뷰 수 | 제한 없음 |
| `--max-more-clicks N` | "더 보기" 버튼 최대 클릭 횟수 | test_mode: 3, 일반: 15 |
| `--test` | 테스트 모드 (더보기 3번만) | False |
| `--headless` | 브라우저를 백그라운드에서 실행 | False |
| `--debug` | 디버깅 모드 (HTML 저장 등) | False |
| `--use-openai` | OpenAI API를 사용한 요약 | False |
| `--db-path PATH` | 데이터베이스 파일 경로 | amoremall_reviews.db |
| `--output PATH` | JSON 파일 저장 경로 (단일 제품 모드) | - |

**참고**: 브랜드 크롤링 모드에서는 재개 기능이 기본적으로 활성화되어 있습니다. 같은 브랜드 URL로 다시 실행하면 중단된 지점부터 자동으로 이어서 진행됩니다.

### 4. 사용 예시

```bash
# 기본 실행 (단일 제품)
python main.py "https://www.amoremall.com/kr/ko/product/detail?onlineProdSn=63063"

# 브랜드 전체 크롤링 (더보기 10번)
python main.py "https://www.amoremall.com/kr/ko/display/brand/detail/all?brandSn=18" --brand --max-more-clicks 10

# 테스트 모드 (더보기 3번, 제품 5개만)
python main.py "https://www.amoremall.com/kr/ko/display/brand/detail/all?brandSn=18" --brand --test --max-products 5

# 백그라운드 실행
python main.py "https://www.amoremall.com/kr/ko/display/brand/detail/all?brandSn=18" --brand --headless --max-more-clicks 10
```

## 출력 파일

### 브랜드 크롤링 모드

브랜드 크롤링 시 자동으로 두 개의 JSON 파일이 생성됩니다:

1. **`info_{브랜드명}.json`** - 제품 정보
   - 제품명, 제품 코드, URL
   - 카테고리, 가격 정보
   - 평점, 리뷰 개수
   - 사용 방법, 성분, 주의사항

2. **`review_{브랜드명}.json`** - 모든 리뷰
   - 각 리뷰에 제품 코드와 제품명 포함
   - 사용자 정보, 평점, 리뷰 텍스트

**예시:**
- `info_설화수.json` - 77개 제품 정보
- `review_설화수.json` - 10,105개 리뷰

### 단일 제품 모드

`--output` 옵션을 사용하면:
- `info_{output}.json` - 제품 정보
- `review_{output}.json` - 리뷰

## 수집되는 데이터 구조

### 제품 정보 (Product Info)

```json
{
  "product_name": "자음2종 세트 (150ml+125ml)",
  "product_code": "111970001785",
  "product_url": "https://...",
  "category": "스킨케어",
  "sub_category": "세트",
  "price": "150,000",
  "current_price": "135,000",
  "discount_rate": "10%",
  "rating": "4.9",
  "review_count": "4,375",
  "usage_method": "사용 방법...",
  "ingredients": "성분 목록...",
  "precautions": "주의사항..."
}
```

### 리뷰 정보 (Review)

```json
{
  "product_code": "111970001785",
  "product_name": "자음2종 세트 (150ml+125ml)",
  "username": "사용자명",
  "age": "20대",
  "gender": "여성",
  "skin_type_1": "지성",
  "skin_type_2": "트러블",
  "rating": 5,
  "option": "옵션명",
  "review_type": "포토리뷰",
  "review_text": "리뷰 내용...",
  "prd_style_features": {
    "발색감": "좋음",
    "지속력": "보통",
    "사용감": "부드러움"
  }
}
```

## 데이터베이스 구조

### Products (제품)
- `id`: 제품 ID
- `product_code`: 제품 코드 (고유)
- `product_name`: 제품명
- `product_url`: 제품 URL
- `category`, `sub_category`: 카테고리
- `price`, `current_price`, `discount_rate`: 가격 정보
- `rating`, `review_count`: 평점 및 리뷰 수
- `usage_method`, `ingredients`, `precautions`: 상세 정보
- `created_at`, `updated_at`: 생성/수정 시간

### Reviews (후기)
- `id`: 후기 ID
- `product_id`: 제품 ID (외래키)
- `username`: 사용자명
- `age`, `gender`, `skin_type_1`, `skin_type_2`: 사용자 정보
- `rating`: 평점
- `option`: 제품 옵션
- `review_type`: 리뷰 타입
- `review_text`: 리뷰 텍스트
- `prd_style_features`: 특이사항 (JSON)
- `created_at`: 생성 시간

### ProductSummaries (제품 요약)
- `id`: 요약 ID
- `product_id`: 제품 ID (외래키, 고유)
- `summary`: 요약 텍스트
- `key_points`: 주요 포인트 (JSON)
- `average_rating`: 평균 평점
- `total_reviews`: 총 후기 수
- `positive_count`: 긍정적 후기 수
- `negative_count`: 부정적 후기 수
- `created_at`, `updated_at`: 생성/수정 시간

## 모듈 설명

### `crawler.py`
- `AmoreMallCrawler`: 아모레몰 웹사이트 크롤링 클래스
- Selenium을 사용한 동적 콘텐츠 크롤링
- 제품 정보 및 리뷰 데이터 추출
- 브랜드 페이지에서 모든 제품 자동 탐색
- "더 보기" 버튼 자동 클릭으로 대량 리뷰 수집

**주요 메서드:**
- `get_product_info()`: 제품 기본 정보 수집
- `extract_reviews()`: 리뷰 수집 (더보기 버튼 자동 클릭, 중복 제거)
- `_get_product_info_from_notice()`: 상품정보제공 고시에서 상세 정보 수집
- `get_brand_products()`: 브랜드 페이지에서 모든 제품 링크 추출 (목표 제품 수까지 자동 스크롤)
- `crawl_brand_products()`: 브랜드 전체 제품 크롤링 (재개 기능 포함)

### `summarizer.py`
- `ReviewSummarizer`: 후기 요약 클래스
- OpenAI API 또는 간단한 텍스트 요약 지원
- 주요 키워드 및 포인트 추출

### `database.py`
- `DatabaseManager`: 데이터베이스 관리 클래스
- SQLAlchemy를 사용한 ORM
- 제품, 후기, 요약 데이터 CRUD 작업

### `main.py`
- 메인 실행 스크립트
- 전체 워크플로우 관리
- 브랜드 모드 및 단일 제품 모드 지원

## 크롤링 프로세스

### 브랜드 크롤링 프로세스

1. **제품 목록 수집**
   - 브랜드 페이지 접속
   - 스크롤하여 모든 제품 로드 (목표 제품 수까지 자동 스크롤)
   - 제품 링크 추출

2. **재개 기능 확인** (자동)
   - 기존 `info_{브랜드명}.json` 파일 확인
   - 이미 크롤링된 제품은 자동으로 건너뜀
   - 누락된 제품만 크롤링 진행

3. **각 제품별 크롤링**
   - 제품 페이지 접속
   - 기본 제품 정보 수집 (가격, 평점 등)
   - 리뷰 탭 클릭
   - "더 보기" 버튼 클릭하여 리뷰 수집
   - "상품상세" 탭 클릭
   - "상품정보제공 고시 보기"에서 상세 정보 수집
   - 뒤로가기로 브랜드 페이지로 복귀

4. **데이터 저장 및 병합**
   - 제품 정보: `info_{브랜드명}.json` (기존 데이터와 병합)
   - 리뷰: `review_{브랜드명}.json` (기존 데이터와 병합)
   - 중복 리뷰 자동 제거 (제품코드 + 사용자명 + 리뷰텍스트 기준)
   - (선택) 데이터베이스 저장

## 주요 기능 상세

### 재개 기능 (Resume)

브랜드 크롤링 중 중단되더라도 같은 브랜드 URL로 다시 실행하면 자동으로 이어서 진행됩니다.

**작동 방식:**
- 기존 `info_{브랜드명}.json` 파일을 읽어서 이미 크롤링된 제품 확인
- `onlineProdSn`과 `product_code` 기준으로 매칭
- 이미 크롤링된 제품은 자동으로 건너뛰고 누락된 제품만 크롤링
- 새로 크롤링한 데이터를 기존 데이터와 자동 병합

**예시:**
```bash
# 첫 실행 (77개 제품 크롤링 시작)
python main.py "https://www.amoremall.com/kr/ko/display/brand/detail/all?brandSn=18" --brand --max-more-clicks 10

# 중단 후 재개 (이미 크롤링된 제품은 건너뛰고 나머지만 진행)
python main.py "https://www.amoremall.com/kr/ko/display/brand/detail/all?brandSn=18" --brand --max-more-clicks 10
```

### 중복 리뷰 제거

크롤링 과정에서 중복으로 수집된 리뷰를 자동으로 제거합니다.

**제거 기준:**
- 제품코드 + 사용자명 + 리뷰텍스트 조합이 동일한 경우
- 저장 시 자동으로 중복 제거되어 고유 리뷰만 저장됩니다

**수동 중복 제거:**
```python
# Python 스크립트로 중복 제거 (예시)
import json
from collections import defaultdict

with open('review_LANEIGE.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

reviews = data.get('reviews', [])
seen = set()
unique_reviews = []

for r in reviews:
    sig = f"{r.get('product_code')}|{r.get('username')}|{r.get('review_text', '').strip()}"
    if sig not in seen:
        seen.add(sig)
        unique_reviews.append(r)

data['reviews'] = unique_reviews
data['total_reviews'] = len(unique_reviews)

with open('review_LANEIGE.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

## 주의사항

1. **웹 크롤링 윤리**
   - 웹사이트의 이용약관을 확인하세요
   - 과도한 요청은 IP 차단을 유발할 수 있으므로 적절한 딜레이를 두세요
   - 크롤링 속도를 조절하여 서버에 부담을 주지 마세요

2. **성능 고려사항**
   - 브랜드 전체 크롤링은 시간이 오래 걸릴 수 있습니다 (77개 제품 기준 약 1-2시간)
   - `--test` 모드로 먼저 테스트하는 것을 권장합니다
   - `--headless` 모드를 사용하면 더 빠르게 실행됩니다
   - 재개 기능을 활용하면 중단된 크롤링을 효율적으로 완료할 수 있습니다

3. **데이터 저장**
   - 대량의 리뷰를 수집하면 JSON 파일 크기가 커질 수 있습니다 (10,000개 리뷰 ≈ 10MB)
   - 데이터베이스 저장 시 디스크 공간을 확인하세요
   - 중복 리뷰는 자동으로 제거되지만, 백업 파일을 생성하는 것을 권장합니다

4. **OpenAI API**
   - OpenAI API 사용 시 API 키가 필요하며, 사용량에 따라 비용이 발생할 수 있습니다

## 문제 해결

### ChromeDriver 오류
```bash
# ChromeDriver를 수동으로 업데이트
pip install --upgrade webdriver-manager
```

### 팝업 문제
- 크롤러가 자동으로 팝업을 닫습니다
- 팝업이 계속 나타나면 `_close_popups()` 메서드를 확인하세요

### 리뷰를 찾을 수 없음
- 제품 페이지에 리뷰가 실제로 있는지 확인하세요
- `--debug` 모드를 사용하여 HTML을 저장하고 확인하세요

### 제품 개수가 맞지 않음
- 브랜드 페이지에서 스크롤이 완전히 로드되지 않았을 수 있습니다
- `get_brand_products()` 메서드의 스크롤 로직이 개선되어 목표 제품 수까지 자동으로 스크롤합니다
- 목표 제품 수가 표시되지 않는 경우 수동으로 확인하세요

### 중복 리뷰 문제
- 크롤링 과정에서 중복 리뷰가 수집될 수 있습니다
- 저장 시 자동으로 중복 제거되지만, 수동으로도 확인 가능합니다
- 중복 제거 기준: 제품코드 + 사용자명 + 리뷰텍스트 조합

## 라이선스

이 프로젝트는 교육 및 연구 목적으로 제공됩니다.

## 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.
