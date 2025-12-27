"""
아모레몰 제품 후기 크롤링 및 데이터베이스화 메인 스크립트
"""
import argparse
import json
import os
import time
from crawler import AmoreMallCrawler
from summarizer import ReviewSummarizer
from database import DatabaseManager


def main():
    parser = argparse.ArgumentParser(description='아모레몰 제품 후기 크롤링 및 요약')
    parser.add_argument('url', help='제품 페이지 URL 또는 브랜드 페이지 URL')
    parser.add_argument('--max-pages', type=int, default=10, help='최대 페이지 수 (기본값: 10, 0이면 모든 페이지)')
    parser.add_argument('--max-reviews', type=int, help='최대 리뷰 수 (지정하지 않으면 제한 없음)')
    parser.add_argument('--brand', action='store_true', help='브랜드 페이지 모드 (모든 제품 크롤링)')
    parser.add_argument('--max-products', type=int, help='브랜드 모드에서 최대 제품 수')
    parser.add_argument('--headless', action='store_true', help='브라우저를 백그라운드에서 실행')
    parser.add_argument('--use-openai', action='store_true', help='OpenAI API를 사용한 요약 (기본값: False)')
    parser.add_argument('--db-path', default='amoremall_reviews.db', help='데이터베이스 파일 경로')
    parser.add_argument('--output', help='결과를 JSON 파일로 저장할 경로')
    parser.add_argument('--debug', action='store_true', help='디버깅 모드 (HTML 저장 등)')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (더 보기 버튼 3번만 클릭)')
    parser.add_argument('--max-more-clicks', type=int, help='더 보기 버튼 최대 클릭 횟수 (지정하지 않으면 test_mode에 따라 자동 설정)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("아모레몰 제품 후기 크롤링 시작")
    print("=" * 60)
    
    # 크롤러 초기화
    crawler = AmoreMallCrawler(headless=args.headless, debug=args.debug)
    db = DatabaseManager(db_path=args.db_path)
    summarizer = ReviewSummarizer(use_openai=args.use_openai)
    
    try:
        if args.brand:
            # 브랜드 페이지 모드: 모든 제품 크롤링
            print("\n[브랜드 모드] 브랜드의 모든 제품 리뷰 크롤링 중...")
            max_pages = None if args.max_pages == 0 else args.max_pages
            results, brand_name = crawler.crawl_brand_products(
                args.url,
                max_products=args.max_products,
                max_pages_per_product=max_pages,
                max_reviews_per_product=args.max_reviews,
                test_mode=args.test,
                max_more_clicks=args.max_more_clicks
            )
            
            if not results:
                print("오류: 제품을 찾을 수 없거나 크롤링에 실패했습니다.")
                return
            
            # 모든 제품의 결과를 저장
            all_reviews_data = []
            total_reviews = 0
            
            for result in results:
                product_info = result['product_info']
                reviews = result['reviews']
                total_reviews += len(reviews)
                
                if reviews:
                    # 데이터베이스에 저장
                    product = db.add_product(product_info)
                    db.add_reviews(product.id, reviews)
                    
                    # 요약 생성
                    summary_data = summarizer.summarize_reviews(
                        reviews,
                        product_info.get('product_name', '')
                    )
                    db.add_summary(product.id, summary_data)
                    
                    all_reviews_data.append({
                        'product_info': product_info,
                        'reviews': reviews,
                        'summary': summary_data
                    })
            
            print(f"\n{'='*60}")
            print(f"브랜드 크롤링 완료")
            print(f"{'='*60}")
            print(f"총 제품 수: {len(results)}개")
            print(f"총 후기 수: {total_reviews}개")
            
            # 파일명 기본값 생성 (브랜드명 사용)
            if args.output:
                # 출력 파일명에서 브랜드명 추출 (예: "20251227_sulwhasoo" -> "sulwhasoo")
                base_name = args.output.replace('.json', '').split('_')[-1] if '_' in args.output else args.output.replace('.json', '')
            else:
                # 크롤러에서 추출한 브랜드명 사용
                base_name = brand_name if brand_name else f"brand_{time.strftime('%Y%m%d')}"
            
            # 제품 정보만 저장
            info_file = f"info_{base_name}.json"
            all_products_info = []
            for result in results:
                product_info = result['product_info']
                all_products_info.append(product_info)
            
            info_data = {
                'brand_url': args.url,
                'crawled_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_products': len(results),
                'products': all_products_info
            }
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info_data, f, ensure_ascii=False, indent=2)
            
            # 리뷰만 저장
            review_file = f"review_{base_name}.json"
            all_reviews_list = []
            for result in results:
                product_info = result['product_info']
                reviews = result['reviews']
                for review in reviews:
                    # 각 리뷰에 제품 코드 추가 (참조용)
                    review_with_product = review.copy()
                    review_with_product['product_code'] = product_info.get('product_code', '')
                    review_with_product['product_name'] = product_info.get('product_name', '')
                    all_reviews_list.append(review_with_product)
            
            review_data = {
                'brand_url': args.url,
                'crawled_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_reviews': total_reviews,
                'reviews': all_reviews_list
            }
            
            with open(review_file, 'w', encoding='utf-8') as f:
                json.dump(review_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ JSON 파일 저장 완료:")
            print(f"  - 제품 정보: {info_file}")
            print(f"    - 총 {len(results)}개 제품")
            print(f"    - 파일 크기: {os.path.getsize(info_file) / 1024 / 1024:.2f} MB")
            print(f"  - 리뷰: {review_file}")
            print(f"    - 총 {total_reviews}개 후기")
            print(f"    - 파일 크기: {os.path.getsize(review_file) / 1024 / 1024:.2f} MB")
            return
        
        else:
            # 단일 제품 모드
            print("\n[1단계] 제품 후기 크롤링 중...")
            max_pages = None if args.max_pages == 0 else args.max_pages
            result = crawler.crawl_product_reviews(args.url, max_pages=max_pages, max_reviews=args.max_reviews, test_mode=args.test)
            
            if not result['product_info']:
                print("오류: 제품 정보를 가져올 수 없습니다.")
                return
            
            product_info = result['product_info']
            reviews = result['reviews']
            
            print(f"\n✓ 제품명: {product_info.get('product_name', 'N/A')}")
            print(f"✓ 제품 코드: {product_info.get('product_code', 'N/A')}")
            print(f"✓ 추출된 후기 수: {len(reviews)}")
            
            if not reviews:
                print("경고: 후기를 찾을 수 없습니다.")
                return
            
            # 2. 데이터베이스에 저장
            print("\n[2단계] 데이터베이스에 저장 중...")
            product = db.add_product(product_info)
            print(f"✓ 제품 저장 완료 (ID: {product.id})")
            
            db.add_reviews(product.id, reviews)
            print(f"✓ 후기 저장 완료 ({len(reviews)}개)")
            
            # 3. 후기 요약
            print("\n[3단계] 후기 요약 중...")
            summary_data = summarizer.summarize_reviews(
                reviews, 
                product_info.get('product_name', '')
            )
            
            db.add_summary(product.id, summary_data)
            print("✓ 요약 저장 완료")
            
            # 4. 크롤링된 후기 상세 출력
            print("\n" + "=" * 60)
            print("크롤링된 후기 목록")
            print("=" * 60)
            
            # 처음 10개 후기 상세 출력
            display_count = min(10, len(reviews))
            print(f"\n[총 {len(reviews)}개 후기 중 처음 {display_count}개 미리보기]\n")
            
            for i, review in enumerate(reviews[:display_count], 1):
                print(f"\n{'─' * 60}")
                print(f"후기 #{i}")
                print(f"{'─' * 60}")
                
                if review.get('username'):
                    print(f"👤 사용자: {review['username']}")
                if review.get('user_info'):
                    print(f"📋 정보: {review['user_info']}")
                if review.get('rating'):
                    stars = '⭐' * review['rating'] + '☆' * (5 - review['rating'])
                    print(f"⭐ 평점: {stars} ({review['rating']}/5)")
                if review.get('option'):
                    print(f"🎨 옵션: {review['option']}")
                if review.get('review_type'):
                    print(f"🏷️  타입: {review['review_type']}")
                
                print(f"\n💬 후기 내용:")
                review_text = review.get('review_text', '')
                # 긴 텍스트는 줄바꿈 처리
                if len(review_text) > 100:
                    words = review_text.split()
                    lines = []
                    current_line = []
                    current_length = 0
                    for word in words:
                        if current_length + len(word) + 1 > 80:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                            current_length = len(word)
                        else:
                            current_line.append(word)
                            current_length += len(word) + 1
                    if current_line:
                        lines.append(' '.join(current_line))
                    print('\n'.join(f"   {line}" for line in lines))
                else:
                    print(f"   {review_text}")
            
            if len(reviews) > display_count:
                print(f"\n... 외 {len(reviews) - display_count}개의 후기가 더 있습니다.")
            
            # 5. 요약 결과 출력
            print("\n" + "=" * 60)
            print("요약 결과")
            print("=" * 60)
            print(f"\n📊 평균 평점: {summary_data['average_rating']}/5.0")
            print(f"📝 총 후기 수: {summary_data['total_reviews']}개")
            print(f"👍 긍정적 후기: {summary_data['positive_count']}개")
            print(f"👎 부정적 후기: {summary_data['negative_count']}개")
            
            if summary_data['key_points']:
                print(f"\n🔑 주요 포인트:")
                for point in summary_data['key_points']:
                    print(f"   • {point}")
            
            print(f"\n📄 종합 요약:")
            summary_text = summary_data['summary']
            # 요약 텍스트도 줄바꿈 처리
            if len(summary_text) > 100:
                sentences = summary_text.split('. ')
                for sentence in sentences:
                    if sentence.strip():
                        print(f"   {sentence.strip()}{'.' if not sentence.endswith('.') else ''}")
            else:
                print(f"   {summary_text}")
            
            # 6. JSON 파일로 저장 (제품 정보와 리뷰 분리)
            product_code = product_info.get('product_code', 'unknown')
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            
            if args.output:
                base_name = args.output.replace('.json', '')
            else:
                base_name = f"{product_code}_{timestamp}"
            
            # 제품 정보만 저장
            info_file = f"info_{base_name}.json"
            info_data = {
                'product_info': {
                    'product_name': product_info.get('product_name', ''),
                    'product_code': product_info.get('product_code', ''),
                    'product_url': product_info.get('product_url', ''),
                    'category': product_info.get('category', ''),
                    'sub_category': product_info.get('sub_category', ''),
                    'price': product_info.get('price', ''),
                    'current_price': product_info.get('current_price', ''),
                    'discount_rate': product_info.get('discount_rate', ''),
                    'rating': product_info.get('rating', ''),
                    'review_count': product_info.get('review_count', ''),
                    'price_range': product_info.get('price_range', ''),
                    'usage_method': product_info.get('usage_method', ''),
                    'ingredients': product_info.get('ingredients', ''),
                    'precautions': product_info.get('precautions', ''),
                    'crawled_at': time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'statistics': {
                    'total_reviews': len(reviews),
                    'average_rating': summary_data.get('average_rating', 0),
                    'positive_count': summary_data.get('positive_count', 0),
                    'negative_count': summary_data.get('negative_count', 0)
                },
                'summary': {
                    'summary_text': summary_data.get('summary', ''),
                    'key_points': summary_data.get('key_points', [])
                }
            }
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info_data, f, ensure_ascii=False, indent=2)
            
            # 리뷰만 저장
            review_file = f"review_{base_name}.json"
            reviews_data = []
            for review in reviews:
                review_data = {
                    'product_code': product_code,
                    'product_name': product_info.get('product_name', ''),
                    'username': review.get('username', ''),
                    'user_info': review.get('user_info', ''),
                    'age': review.get('age', ''),
                    'gender': review.get('gender', ''),
                    'skin_type_1': review.get('skin_type_1', ''),
                    'skin_type_2': review.get('skin_type_2', ''),
                    'rating': review.get('rating'),
                    'option': review.get('option', ''),
                    'review_type': review.get('review_type', ''),
                    'special_note_1': review.get('special_note_1', ''),
                    'special_note_2': review.get('special_note_2', ''),
                    'special_note_3': review.get('special_note_3', ''),
                    'review_text': review.get('review_text', '')
                }
                reviews_data.append(review_data)
            
            review_output = {
                'product_code': product_code,
                'product_name': product_info.get('product_name', ''),
                'total_reviews': len(reviews),
                'reviews': reviews_data,
                'crawled_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(review_file, 'w', encoding='utf-8') as f:
                json.dump(review_output, f, ensure_ascii=False, indent=2)
            
            print("\n" + "=" * 60)
            print("JSON 파일 저장 완료")
            print("=" * 60)
            print(f"📁 제품 정보: {info_file}")
            print(f"   - 파일 크기: {os.path.getsize(info_file) / 1024:.2f} KB")
            print(f"📁 리뷰: {review_file}")
            print(f"   - 총 {len(reviews)}개 후기")
            print(f"   - 파일 크기: {os.path.getsize(review_file) / 1024:.2f} KB")
            print("=" * 60)
            print("완료!")
            print("=" * 60)
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        crawler.close()
        db.close()


if __name__ == "__main__":
    main()

