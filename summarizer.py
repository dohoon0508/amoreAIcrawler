"""
후기 요약 기능
"""
import os
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class ReviewSummarizer:
    def __init__(self, use_openai: bool = True):
        """
        요약기 초기화
        
        Args:
            use_openai: OpenAI API 사용 여부 (False면 간단한 텍스트 요약 사용)
        """
        self.use_openai = use_openai
        if use_openai:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print("경고: OPENAI_API_KEY가 설정되지 않았습니다. 간단한 요약 방식을 사용합니다.")
                self.use_openai = False
            else:
                self.client = OpenAI(api_key=api_key)
    
    def summarize_reviews(self, reviews: List[Dict], product_name: str = "") -> Dict:
        """
        후기 리스트를 요약
        
        Args:
            reviews: 후기 리스트
            product_name: 제품명
            
        Returns:
            요약 결과 딕셔너리
        """
        if not reviews:
            return {
                'summary': "후기가 없습니다.",
                'key_points': [],
                'average_rating': 0,
                'total_reviews': 0
            }
        
        # 평균 평점 계산
        ratings = []
        for r in reviews:
            rating = r.get('rating')
            if rating is not None and rating > 0:
                ratings.append(rating)
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # 리뷰 텍스트 수집
        review_texts = [r.get('review_text', '') for r in reviews if r.get('review_text')]
        
        if self.use_openai:
            summary = self._summarize_with_openai(review_texts, product_name)
        else:
            summary = self._summarize_simple(review_texts, product_name)
        
        # 주요 키워드 추출
        key_points = self._extract_key_points(reviews)
        
        return {
            'summary': summary,
            'key_points': key_points,
            'average_rating': round(avg_rating, 2),
            'total_reviews': len(reviews),
            'positive_count': len([r for r in reviews if (r.get('rating') or 0) >= 4]),
            'negative_count': len([r for r in reviews if (r.get('rating') or 0) <= 2])
        }
    
    def _summarize_with_openai(self, review_texts: List[str], product_name: str) -> str:
        """OpenAI API를 사용한 요약"""
        try:
            # 리뷰 텍스트를 하나로 합치기 (최대 길이 제한)
            combined_text = "\n\n".join(review_texts[:50])  # 최대 50개 리뷰만 사용
            
            if len(combined_text) > 15000:  # 토큰 제한 고려
                combined_text = combined_text[:15000]
            
            prompt = f"""다음은 {product_name} 제품에 대한 고객 후기들입니다. 
이 후기들을 종합적으로 분석하여 3-5문단으로 요약해주세요.

요약 시 다음 사항을 포함해주세요:
1. 전체적인 평가와 만족도
2. 주요 장점과 특징
3. 단점이나 개선점 (있다면)
4. 추천 대상

후기들:
{combined_text}

요약:"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 제품 리뷰를 분석하고 요약하는 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI 요약 오류: {e}")
            return self._summarize_simple(review_texts, product_name)
    
    def _summarize_simple(self, review_texts: List[str], product_name: str) -> str:
        """간단한 텍스트 기반 요약"""
        if not review_texts:
            return "후기 데이터가 없습니다."
        
        # 키워드 빈도 분석
        keywords = {
            '촉촉': 0, '보습': 0, '수분': 0, '건조': 0,
            '지속력': 0, '지속': 0, '오래': 0,
            '유분': 0, '끈적': 0, '부드러움': 0,
            '향': 0, '냄새': 0, '향기': 0,
            '각질': 0, '입술': 0, '립': 0,
            '만족': 0, '좋아': 0, '추천': 0,
            '별로': 0, '아쉽': 0, '불만': 0
        }
        
        all_text = " ".join(review_texts)
        for keyword in keywords:
            keywords[keyword] = all_text.count(keyword)
        
        # 상위 키워드
        top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 간단한 요약 생성
        summary_parts = []
        summary_parts.append(f"{product_name}에 대한 고객 후기를 분석한 결과, 총 {len(review_texts)}개의 후기가 수집되었습니다.")
        
        if top_keywords:
            summary_parts.append(f"주요 언급 키워드: {', '.join([k[0] for k in top_keywords if k[1] > 0])}")
        
        # 긍정/부정 키워드 분석
        positive_count = sum(keywords[k] for k in ['만족', '좋아', '추천', '촉촉', '보습'])
        negative_count = sum(keywords[k] for k in ['별로', '아쉽', '불만', '건조', '끈적'])
        
        if positive_count > negative_count:
            summary_parts.append("전반적으로 긍정적인 평가가 많습니다.")
        elif negative_count > positive_count:
            summary_parts.append("일부 부정적인 평가가 있습니다.")
        else:
            summary_parts.append("평가가 양분되어 있습니다.")
        
        return " ".join(summary_parts)
    
    def _extract_key_points(self, reviews: List[Dict]) -> List[str]:
        """주요 포인트 추출"""
        key_points = []
        
        # 평점별 분류
        high_rated = [r for r in reviews if (r.get('rating') or 0) >= 4]
        low_rated = [r for r in reviews if (r.get('rating') or 0) <= 2]
        
        if high_rated:
            # 고평점 후기에서 자주 언급되는 내용
            texts = [r.get('review_text', '') for r in high_rated]
            common_words = self._find_common_phrases(texts)
            if common_words:
                key_points.append(f"긍정적 평가: {', '.join(common_words[:3])}")
        
        if low_rated:
            texts = [r.get('review_text', '') for r in low_rated]
            common_words = self._find_common_phrases(texts)
            if common_words:
                key_points.append(f"개선 필요: {', '.join(common_words[:3])}")
        
        # 옵션별 인기도
        options = {}
        for r in reviews:
            option = r.get('option', '')
            if option:
                options[option] = options.get(option, 0) + 1
        
        if options:
            top_option = max(options.items(), key=lambda x: x[1])
            key_points.append(f"인기 옵션: {top_option[0]} ({top_option[1]}개 후기)")
        
        return key_points
    
    def _find_common_phrases(self, texts: List[str]) -> List[str]:
        """공통적으로 언급되는 구문 찾기"""
        # 간단한 구현: 2-3글자 키워드 빈도 계산
        phrases = {}
        for text in texts:
            # 2-3글자 키워드 추출
            words = text.split()
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                if len(phrase) <= 10:  # 너무 긴 구문 제외
                    phrases[phrase] = phrases.get(phrase, 0) + 1
        
        # 빈도순 정렬
        sorted_phrases = sorted(phrases.items(), key=lambda x: x[1], reverse=True)
        return [p[0] for p in sorted_phrases[:5] if p[1] >= 2]


if __name__ == "__main__":
    # 테스트
    reviews = [
        {
            'rating': 5,
            'review_text': '지속력 오래 지속돼요 유분기 유분 적당해요 촉촉함 촉촉해요',
            'option': '베리'
        },
        {
            'rating': 5,
            'review_text': '라네즈 립밤은 단순한 립밤을 넘어선 립 케어의 끝판왕이에요! 특히 건조한 계절에 사용할 때 그 진가를 제대로 느낄 수 있어요.',
            'option': '자몽'
        }
    ]
    
    summarizer = ReviewSummarizer(use_openai=False)
    result = summarizer.summarize_reviews(reviews, "라네즈 립 슬리핑 마스크")
    print(result)

