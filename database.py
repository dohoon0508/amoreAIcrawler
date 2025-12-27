"""
데이터베이스 관리 모듈
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import List, Dict, Optional
import json

Base = declarative_base()


class Product(Base):
    """제품 테이블"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(100), unique=True, nullable=False)
    product_name = Column(String(500), nullable=False)
    product_url = Column(String(1000))
    category = Column(String(100))  # 카테고리 (스킨케어, 메이크업, 클렌징 등)
    sub_category = Column(String(100))  # 세부 카테고리
    price = Column(String(100))  # 가격
    price_range = Column(String(50))  # 가격대 (1-3만원 등)
    usage_method = Column(Text)  # 사용 방법
    ingredients = Column(Text)  # 성분
    precautions = Column(Text)  # 주의사항
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 관계
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    summary = relationship("ProductSummary", back_populates="product", uselist=False, cascade="all, delete-orphan")


class Review(Base):
    """후기 테이블"""
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    username = Column(String(100))
    user_info = Column(String(200))  # 나이/성별/피부타입 등 (원본)
    age = Column(String(50))  # 나이 (예: "20대")
    gender = Column(String(50))  # 성별 (예: "여성", "남성")
    skin_type_1 = Column(String(50))  # 피부타입1 (예: "지성", "건성")
    skin_type_2 = Column(String(50))  # 피부타입2 (예: "트러블", "모공")
    rating = Column(Integer)
    option = Column(String(100))  # 제품 옵션
    review_type = Column(String(100))  # 리뷰 타입 (예: "한달 사용 리뷰")
    special_note_1 = Column(String(200))  # 특이사항1 (예: "지속력: 오래 지속돼요")
    special_note_2 = Column(String(200))  # 특이사항2 (예: "유분기: 유분 적당해요")
    special_note_3 = Column(String(200))  # 특이사항3 (예: "촉촉함: 촉촉해요")
    review_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 관계
    product = relationship("Product", back_populates="reviews")


class ProductSummary(Base):
    """제품 요약 테이블"""
    __tablename__ = 'product_summaries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), unique=True, nullable=False)
    summary = Column(Text, nullable=False)
    key_points = Column(Text)  # JSON 형태로 저장
    average_rating = Column(Float)
    total_reviews = Column(Integer)
    positive_count = Column(Integer)
    negative_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 관계
    product = relationship("Product", back_populates="summary")


class DatabaseManager:
    """데이터베이스 관리 클래스"""
    
    def __init__(self, db_path: str = "amoremall_reviews.db"):
        """
        데이터베이스 초기화
        
        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def add_product(self, product_info: Dict) -> Product:
        """
        제품 추가 또는 업데이트
        
        Args:
            product_info: 제품 정보 딕셔너리
            
        Returns:
            Product 객체
        """
        product_code = product_info.get('product_code')
        if not product_code:
            raise ValueError("product_code는 필수입니다.")
        
        # 기존 제품 확인
        product = self.session.query(Product).filter_by(product_code=product_code).first()
        
        if product:
            # 업데이트
            product.product_name = product_info.get('product_name', product.product_name)
            product.product_url = product_info.get('product_url', product.product_url)
            product.category = product_info.get('category', product.category)
            product.sub_category = product_info.get('sub_category', product.sub_category)
            product.price = product_info.get('price', product.price)
            product.price_range = product_info.get('price_range', product.price_range)
            product.usage_method = product_info.get('usage_method', product.usage_method)
            product.ingredients = product_info.get('ingredients', product.ingredients)
            product.precautions = product_info.get('precautions', product.precautions)
            product.updated_at = datetime.now()
        else:
            # 새로 생성
            product = Product(
                product_code=product_code,
                product_name=product_info.get('product_name', ''),
                product_url=product_info.get('product_url', ''),
                category=product_info.get('category', ''),
                sub_category=product_info.get('sub_category', ''),
                price=product_info.get('price', ''),
                price_range=product_info.get('price_range', ''),
                usage_method=product_info.get('usage_method', ''),
                ingredients=product_info.get('ingredients', ''),
                precautions=product_info.get('precautions', '')
            )
            self.session.add(product)
        
        self.session.commit()
        self.session.refresh(product)
        return product
    
    def add_reviews(self, product_id: int, reviews: List[Dict]) -> List[Review]:
        """
        후기 추가
        
        Args:
            product_id: 제품 ID
            reviews: 후기 리스트
            
        Returns:
            Review 객체 리스트
        """
        review_objects = []
        for review_data in reviews:
            review = Review(
                product_id=product_id,
                username=review_data.get('username'),
                user_info=review_data.get('user_info'),  # 원본 정보
                age=review_data.get('age'),
                gender=review_data.get('gender'),
                skin_type_1=review_data.get('skin_type_1'),
                skin_type_2=review_data.get('skin_type_2'),
                rating=review_data.get('rating'),
                option=review_data.get('option'),
                review_type=review_data.get('review_type'),
                special_note_1=review_data.get('special_note_1'),
                special_note_2=review_data.get('special_note_2'),
                special_note_3=review_data.get('special_note_3'),
                review_text=review_data.get('review_text', '')
            )
            review_objects.append(review)
            self.session.add(review)
        
        self.session.commit()
        return review_objects
    
    def add_summary(self, product_id: int, summary_data: Dict) -> ProductSummary:
        """
        제품 요약 추가 또는 업데이트
        
        Args:
            product_id: 제품 ID
            summary_data: 요약 데이터 딕셔너리
            
        Returns:
            ProductSummary 객체
        """
        # 기존 요약 확인
        summary = self.session.query(ProductSummary).filter_by(product_id=product_id).first()
        
        if summary:
            # 업데이트
            summary.summary = summary_data.get('summary', '')
            summary.key_points = json.dumps(summary_data.get('key_points', []), ensure_ascii=False)
            summary.average_rating = summary_data.get('average_rating')
            summary.total_reviews = summary_data.get('total_reviews', 0)
            summary.positive_count = summary_data.get('positive_count', 0)
            summary.negative_count = summary_data.get('negative_count', 0)
            summary.updated_at = datetime.now()
        else:
            # 새로 생성
            summary = ProductSummary(
                product_id=product_id,
                summary=summary_data.get('summary', ''),
                key_points=json.dumps(summary_data.get('key_points', []), ensure_ascii=False),
                average_rating=summary_data.get('average_rating'),
                total_reviews=summary_data.get('total_reviews', 0),
                positive_count=summary_data.get('positive_count', 0),
                negative_count=summary_data.get('negative_count', 0)
            )
            self.session.add(summary)
        
        self.session.commit()
        self.session.refresh(summary)
        return summary
    
    def get_product(self, product_code: str) -> Optional[Product]:
        """제품 코드로 제품 조회"""
        return self.session.query(Product).filter_by(product_code=product_code).first()
    
    def get_product_reviews(self, product_code: str) -> List[Review]:
        """제품의 모든 후기 조회"""
        product = self.get_product(product_code)
        if product:
            return product.reviews
        return []
    
    def get_product_summary(self, product_code: str) -> Optional[ProductSummary]:
        """제품 요약 조회"""
        product = self.get_product(product_code)
        if product:
            return product.summary
        return None
    
    def get_all_products(self) -> List[Product]:
        """모든 제품 조회"""
        return self.session.query(Product).all()
    
    def close(self):
        """세션 종료"""
        self.session.close()


if __name__ == "__main__":
    # 테스트
    db = DatabaseManager("test.db")
    
    # 제품 추가
    product_info = {
        'product_code': '111970001785',
        'product_name': '라네즈 립 슬리핑 마스크',
        'product_url': 'https://www.amoremall.com/kr/ko/product/detail?onlineProdCode=111970001785'
    }
    product = db.add_product(product_info)
    print(f"제품 추가: {product.product_name}")
    
    # 후기 추가
    reviews = [
        {
            'username': 'test_user',
            'rating': 5,
            'review_text': '테스트 후기입니다.',
            'option': '베리'
        }
    ]
    db.add_reviews(product.id, reviews)
    print(f"후기 추가 완료")
    
    # 요약 추가
    summary_data = {
        'summary': '테스트 요약입니다.',
        'key_points': ['키포인트1', '키포인트2'],
        'average_rating': 4.5,
        'total_reviews': 1,
        'positive_count': 1,
        'negative_count': 0
    }
    db.add_summary(product.id, summary_data)
    print(f"요약 추가 완료")
    
    db.close()

