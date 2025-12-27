"""
데이터베이스에서 크롤링된 정보 조회 스크립트
"""
import argparse
import json
from database import DatabaseManager


def print_product_info(product, summary=None):
    """제품 정보 출력"""
    print("\n" + "=" * 70)
    print("제품 정보")
    print("=" * 70)
    print(f"제품명: {product.product_name}")
    print(f"제품 코드: {product.product_code}")
    print(f"URL: {product.product_url}")
    print(f"생성일: {product.created_at}")
    print(f"수정일: {product.updated_at}")
    
    if summary:
        print(f"\n평균 평점: {summary.average_rating}/5.0")
        print(f"총 후기 수: {summary.total_reviews}개")
        print(f"긍정적 후기: {summary.positive_count}개")
        print(f"부정적 후기: {summary.negative_count}개")


def print_reviews(reviews, limit=None):
    """후기 목록 출력"""
    if not reviews:
        print("\n후기가 없습니다.")
        return
    
    display_reviews = reviews[:limit] if limit else reviews
    
    print("\n" + "=" * 70)
    print(f"후기 목록 (총 {len(reviews)}개 중 {len(display_reviews)}개 표시)")
    print("=" * 70)
    
    for i, review in enumerate(display_reviews, 1):
        print(f"\n{'─' * 70}")
        print(f"후기 #{i} (ID: {review.id})")
        print(f"{'─' * 70}")
        
        if review.username:
            print(f"👤 사용자: {review.username}")
        if review.user_info:
            print(f"📋 정보: {review.user_info}")
        if review.rating:
            stars = '⭐' * review.rating + '☆' * (5 - review.rating)
            print(f"⭐ 평점: {stars} ({review.rating}/5)")
        if review.option:
            print(f"🎨 옵션: {review.option}")
        if review.review_type:
            print(f"🏷️  타입: {review.review_type}")
        print(f"📅 작성일: {review.created_at}")
        
        print(f"\n💬 후기 내용:")
        review_text = review.review_text
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
    
    if limit and len(reviews) > limit:
        print(f"\n... 외 {len(reviews) - limit}개의 후기가 더 있습니다.")


def print_summary(summary):
    """요약 정보 출력"""
    if not summary:
        print("\n요약 정보가 없습니다.")
        return
    
    print("\n" + "=" * 70)
    print("요약 정보")
    print("=" * 70)
    
    print(f"\n📊 평균 평점: {summary.average_rating}/5.0")
    print(f"📝 총 후기 수: {summary.total_reviews}개")
    print(f"👍 긍정적 후기: {summary.positive_count}개")
    print(f"👎 부정적 후기: {summary.negative_count}개")
    
    if summary.key_points:
        import json
        try:
            key_points = json.loads(summary.key_points)
            if key_points:
                print(f"\n🔑 주요 포인트:")
                for point in key_points:
                    print(f"   • {point}")
        except:
            pass
    
    print(f"\n📄 종합 요약:")
    summary_text = summary.summary
    if len(summary_text) > 100:
        sentences = summary_text.split('. ')
        for sentence in sentences:
            if sentence.strip():
                print(f"   {sentence.strip()}{'.' if not sentence.endswith('.') else ''}")
    else:
        print(f"   {summary_text}")
    
    print(f"\n📅 생성일: {summary.created_at}")
    print(f"📅 수정일: {summary.updated_at}")


def main():
    parser = argparse.ArgumentParser(description='크롤링된 데이터 조회')
    parser.add_argument('--product-code', help='제품 코드로 조회')
    parser.add_argument('--list-products', action='store_true', help='모든 제품 목록 보기')
    parser.add_argument('--limit', type=int, help='표시할 후기 수 제한')
    parser.add_argument('--db-path', default='amoremall_reviews.db', help='데이터베이스 파일 경로')
    parser.add_argument('--export', help='JSON 파일로 내보내기')
    
    args = parser.parse_args()
    
    db = DatabaseManager(db_path=args.db_path)
    
    try:
        if args.list_products:
            # 모든 제품 목록
            products = db.get_all_products()
            print("\n" + "=" * 70)
            print(f"저장된 제품 목록 (총 {len(products)}개)")
            print("=" * 70)
            
            for i, product in enumerate(products, 1):
                print(f"\n{i}. {product.product_name}")
                print(f"   코드: {product.product_code}")
                print(f"   후기 수: {len(product.reviews)}개")
                if product.summary:
                    print(f"   평균 평점: {product.summary.average_rating}/5.0")
        
        elif args.product_code:
            # 특정 제품 조회
            product = db.get_product(args.product_code)
            if not product:
                print(f"제품 코드 '{args.product_code}'를 찾을 수 없습니다.")
                return
            
            print_product_info(product, product.summary)
            
            # 후기 조회
            reviews = product.reviews
            print_reviews(reviews, limit=args.limit)
            
            # 요약 조회
            if product.summary:
                print_summary(product.summary)
            
            # JSON 내보내기
            if args.export:
                export_data = {
                    'product_info': {
                        'product_name': product.product_name,
                        'product_code': product.product_code,
                        'product_url': product.product_url,
                        'created_at': product.created_at.isoformat() if product.created_at else None,
                        'updated_at': product.updated_at.isoformat() if product.updated_at else None
                    },
                    'reviews': [
                        {
                            'id': r.id,
                            'username': r.username,
                            'user_info': r.user_info,
                            'rating': r.rating,
                            'option': r.option,
                            'review_type': r.review_type,
                            'review_text': r.review_text,
                            'created_at': r.created_at.isoformat() if r.created_at else None
                        }
                        for r in reviews
                    ],
                    'summary': {
                        'summary': product.summary.summary if product.summary else None,
                        'key_points': json.loads(product.summary.key_points) if product.summary and product.summary.key_points else [],
                        'average_rating': product.summary.average_rating if product.summary else None,
                        'total_reviews': product.summary.total_reviews if product.summary else 0,
                        'positive_count': product.summary.positive_count if product.summary else 0,
                        'negative_count': product.summary.negative_count if product.summary else 0
                    } if product.summary else None
                }
                
                with open(args.export, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                print(f"\n✓ 데이터를 {args.export}에 저장했습니다.")
        
        else:
            print("사용법:")
            print("  모든 제품 목록: python view_data.py --list-products")
            print("  특정 제품 조회: python view_data.py --product-code <제품코드>")
            print("  후기 수 제한: python view_data.py --product-code <제품코드> --limit 5")
            print("  JSON 내보내기: python view_data.py --product-code <제품코드> --export output.json")
    
    finally:
        db.close()


if __name__ == "__main__":
    main()

