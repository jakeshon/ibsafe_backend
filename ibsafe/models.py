from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

# Create your models here.

class SocialAccount(models.Model):
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('apple', 'Apple'),
        ('facebook', 'Facebook'),
        ('kakao', 'Kakao'),
        ('naver', 'Naver'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_id = models.CharField(max_length=100)  # 각 제공업체의 고유 ID
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('provider', 'provider_id')
    
    def __str__(self):
        return f"{self.user.username}의 {self.provider} 계정"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_image = models.URLField(max_length=500, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[
        ('male', '남성'),
        ('female', '여성'),
        ('other', '기타'),
    ], null=True, blank=True)
    
    # 기본 신체 정보
    birth_date = models.DateField(null=True, blank=True, help_text="생년월일")
    height = models.IntegerField(null=True, blank=True, help_text="키 (cm)")
    weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text="몸무게 (kg)")
    
    # 목표 설정 필드들
    step_count = models.IntegerField(default=0, help_text="평소 걸음수")
    sleep_time = models.IntegerField(default=0, help_text="평소 수면시간 (분 단위)")
    water_intake = models.IntegerField(default=0, help_text="평소 물 섭취량 (잔 단위)")
    
    # 식사 패턴
    has_breakfast = models.BooleanField(default=False, help_text="아침 식사 여부")
    has_lunch = models.BooleanField(default=True, help_text="점심 식사 여부")
    has_dinner = models.BooleanField(default=True, help_text="저녁 식사 여부")
    
    # 음식 알러지
    has_gluten_allergy = models.BooleanField(default=False, help_text="글루텐 알러지")
    has_lactose_allergy = models.BooleanField(default=False, help_text="유당 알러지")
    has_nut_allergy = models.BooleanField(default=False, help_text="견과류 알러지")
    has_seafood_allergy = models.BooleanField(default=False, help_text="해산물 알러지")
    has_egg_allergy = models.BooleanField(default=False, help_text="계란 알러지")
    has_soy_allergy = models.BooleanField(default=False, help_text="대두 알러지")
    
    # 유당불내증
    has_lactose_intolerance = models.BooleanField(default=False, help_text="유당불내증")
    
    # 음식 선호도
    food_preference = models.TextField(null=True, blank=True, help_text="음식 선호도 및 특별한 요구사항")
    
    # 첫 로그인 관련
    is_password_changed = models.BooleanField(default=False, help_text="첫 로그인 시 비밀번호 변경 여부")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}의 프로필"
    
    @property
    def primary_social_account(self):
        """주요 소셜 계정 반환 (가장 최근에 생성된 것)"""
        return self.user.social_accounts.order_by('-created_at').first()


class UserMedication(models.Model):
    """사용자 복용약 모델"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medications')
    medication_name = models.CharField(max_length=100, help_text="약 이름")
    has_breakfast = models.BooleanField(default=False, help_text="아침 복용 여부")
    has_lunch = models.BooleanField(default=False, help_text="점심 복용 여부")
    has_dinner = models.BooleanField(default=False, help_text="저녁 복용 여부")
    has_as_needed = models.BooleanField(default=False, help_text="필요 시 복용 여부")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "사용자 복용약"
        verbose_name_plural = "사용자 복용약들"
        ordering = ['-created_at']
    
    def __str__(self):
        timing_parts = []
        if self.has_breakfast:
            timing_parts.append('아침')
        if self.has_lunch:
            timing_parts.append('점심')
        if self.has_dinner:
            timing_parts.append('저녁')
        if self.has_as_needed:
            timing_parts.append('필요 시')
        
        timing_text = ', '.join(timing_parts) if timing_parts else '미정'
        return f"{self.user.username}의 {self.medication_name} ({timing_text})"


class MedicationRecord(models.Model):
    """복용약 기록 모델"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medication_records')
    medication_name = models.CharField(max_length=100, help_text="약 이름")
    has_breakfast = models.BooleanField(default=False, help_text="아침 복용 스케줄")
    has_lunch = models.BooleanField(default=False, help_text="점심 복용 스케줄")
    has_dinner = models.BooleanField(default=False, help_text="저녁 복용 스케줄")
    has_as_needed = models.BooleanField(default=False, help_text="필요 시 복용 스케줄")
    taken_breakfast = models.BooleanField(default=False, help_text="아침 복용 여부")
    taken_lunch = models.BooleanField(default=False, help_text="점심 복용 여부")
    taken_dinner = models.BooleanField(default=False, help_text="저녁 복용 여부")
    taken_as_needed = models.BooleanField(default=False, help_text="필요 시 복용 여부")
    record_date = models.DateField(help_text="기록 날짜")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "복용약 기록"
        verbose_name_plural = "복용약 기록들"
        ordering = ['-record_date', '-created_at']
        # 같은 날짜, 같은 사용자, 같은 약에 대한 중복 방지
        unique_together = ('user', 'medication_name', 'record_date')
    
    def __str__(self):
        return f"{self.user.username}의 {self.record_date} {self.medication_name} 복용 기록"


class FoodCategory(models.Model):
    """음식 분류 모델"""
    main_category_code = models.IntegerField()
    main_category_name = models.CharField(max_length=50)
    middle_category_code = models.IntegerField(null=True, blank=True)
    middle_category_name = models.CharField(max_length=50, null=True, blank=True)
    sub_category_code = models.IntegerField(null=True, blank=True)
    sub_category_name = models.CharField(max_length=50, null=True, blank=True)
    detail_category_code = models.IntegerField(null=True, blank=True)
    detail_category_name = models.CharField(max_length=50, null=True, blank=True)
    
    # 대표식품 정보 추가
    representative_food_code = models.IntegerField(null=True, blank=True)
    representative_food_name = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        verbose_name = "음식 분류"
        verbose_name_plural = "음식 분류들"
        # 복합 unique constraint: 대분류코드 + 대표식품코드로 고유성 보장
        unique_together = ('main_category_code', 'representative_food_code', 'middle_category_code', 'sub_category_code', 'detail_category_code')
    
    def __str__(self):
        return f"{self.main_category_name} - {self.middle_category_name or ''} - {self.sub_category_name or ''} - {self.representative_food_name or ''}"

class Food(models.Model):
    """음식 정보 모델 - 모든 159개 컬럼 포함"""
    
    # === 기본 정보 ===
    food_code = models.CharField(max_length=20, unique=True, help_text="식품 고유 코드")
    food_name = models.CharField(max_length=100, help_text="식품명")
    data_type_code = models.CharField(max_length=1, null=True, blank=True, help_text="데이터구분코드")
    data_type_name = models.CharField(max_length=2, null=True, blank=True, help_text="데이터구분명")
    food_origin_code = models.IntegerField(null=True, blank=True, help_text="식품기원코드")
    food_origin_name = models.CharField(max_length=22, null=True, blank=True, help_text="식품기원명")
    category = models.ForeignKey(FoodCategory, on_delete=models.CASCADE, related_name='foods')
    
    # === 영양성분 기준 ===
    nutrition_standard_amount = models.CharField(max_length=10, null=True, blank=True, help_text="영양성분함량기준량")
    nutrition_standard_unit = models.CharField(max_length=10, null=True, blank=True, help_text="영양성분함량기준단위")
    
    # === 기본 영양성분 (100g 기준) ===
    energy_kcal = models.IntegerField(null=True, blank=True, help_text="에너지 (kcal)")
    water_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="수분 (g)")
    protein_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="단백질 (g)")
    fat_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="지방 (g)")
    ash_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="회분 (g)")
    carbohydrates_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="탄수화물 (g)")
    sugar_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="당류 (g)")
    dietary_fiber_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="식이섬유 (g)")
    
    # === 무기질 ===
    calcium_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="칼슘 (mg)")
    iron_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="철 (mg)")
    phosphorus_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="인 (mg)")
    potassium_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="칼륨 (mg)")
    sodium_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="나트륨 (mg)")
    copper_ug = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="구리 (μg)")
    magnesium_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="마그네슘 (mg)")
    manganese_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="망간 (mg)")
    molybdenum_ug = models.TextField(null=True, blank=True, help_text="몰리브덴 (μg)")
    fluorine_mg = models.TextField(null=True, blank=True, help_text="불소 (mg)")
    selenium_ug = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="셀레늄 (μg)")
    zinc_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="아연 (mg)")
    chlorine_mg = models.TextField(null=True, blank=True, help_text="염소 (mg)")
    iodine_ug = models.TextField(null=True, blank=True, help_text="요오드 (μg)")
    chromium_ug = models.TextField(null=True, blank=True, help_text="크롬 (μg)")
    
    # === 비타민 A ===
    vitamin_a_rae_ug = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="비타민 A (μg RAE)")
    retinol_ug = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="레티놀 (μg)")
    beta_carotene_ug = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="베타카로틴 (μg)")
    
    # === 비타민 B군 ===
    thiamine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="티아민 (mg)")
    riboflavin_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="리보플라빈 (mg)")
    niacin_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="니아신 (mg)")
    nicotinic_acid_mg = models.TextField(null=True, blank=True, help_text="니코틴산 (mg)")
    nicotinamide_mg = models.TextField(null=True, blank=True, help_text="니코틴아마이드 (mg)")
    biotin_ug = models.TextField(null=True, blank=True, help_text="비오틴 / 바이오틴 (μg)")
    vitamin_b6_mg = models.TextField(null=True, blank=True, help_text="비타민 B6 (mg)")
    vitamin_b12_ug = models.CharField(max_length=5, null=True, blank=True, help_text="비타민 B12 (μg)")
    folate_dfe_ug = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="엽산 (μg DFE)")
    choline_mg = models.TextField(null=True, blank=True, help_text="콜린 (mg)")
    pantothenic_acid_mg = models.TextField(null=True, blank=True, help_text="판토텐산 (mg)")
    
    # === 비타민 D ===
    vitamin_d_ug = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="비타민 D (μg)")
    vitamin_d2_ug = models.TextField(null=True, blank=True, help_text="비타민 D2 (μg)")
    vitamin_d3_ug = models.TextField(null=True, blank=True, help_text="비타민 D3 (μg)")
    
    # === 비타민 E ===
    vitamin_e_ate_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="비타민 E (mg α-TE)")
    alpha_tocopherol_mg = models.TextField(null=True, blank=True, help_text="알파 토코페롤 (mg)")
    beta_tocopherol_mg = models.TextField(null=True, blank=True, help_text="베타 토코페롤 (mg)")
    gamma_tocopherol_mg = models.TextField(null=True, blank=True, help_text="감마 토코페롤 (mg)")
    delta_tocopherol_mg = models.TextField(null=True, blank=True, help_text="델타 토코페롤 (mg)")
    alpha_tocotrienol_mg = models.TextField(null=True, blank=True, help_text="알파 토코트리에놀 (mg)")
    beta_tocotrienol_mg = models.TextField(null=True, blank=True, help_text="베타 토코트리에놀 (mg)")
    gamma_tocotrienol_mg = models.TextField(null=True, blank=True, help_text="감마 토코트리에놀 (mg)")
    delta_tocotrienol_mg = models.TextField(null=True, blank=True, help_text="델타 토코트리에놀 (mg)")
    
    # === 비타민 K ===
    vitamin_k_ug = models.TextField(null=True, blank=True, help_text="비타민 K (μg)")
    vitamin_k1_ug = models.TextField(null=True, blank=True, help_text="비타민 K1 (μg)")
    vitamin_k2_ug = models.TextField(null=True, blank=True, help_text="비타민 K2 (μg)")
    
    # === 비타민 C ===
    vitamin_c_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="비타민 C (mg)")
    
    # === 지방 관련 ===
    cholesterol_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="콜레스테롤 (mg)")
    saturated_fatty_acids_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="포화지방산 (g)")
    trans_fatty_acids_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="트랜스지방산 (g)")
    unsaturated_fat_g = models.TextField(null=True, blank=True, help_text="불포화지방 (g)")
    
    # === 당류 ===
    galactose_g = models.TextField(null=True, blank=True, help_text="갈락토오스 (g)")
    fructose_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="과당 (g)")
    sugar_alcohol_g = models.TextField(null=True, blank=True, help_text="당알콜 (g)")
    maltose_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="맥아당 (g)")
    allulose_g = models.TextField(null=True, blank=True, help_text="알룰로오스 (g)")
    erythritol_g = models.TextField(null=True, blank=True, help_text="에리스리톨 (g)")
    lactose_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="유당 (g)")
    sucrose_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="자당 (g)")
    tagatose_g = models.TextField(null=True, blank=True, help_text="타가토스 (g)")
    glucose_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="포도당 (g)")
    
    # === 지방산 상세 ===
    epa_dha_mg = models.TextField(null=True, blank=True, help_text="EPA + DHA (mg)")
    gadoleic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="가돌레산 (20:1 n-11) / 에이코센산 (20:1 n-9) (mg)")
    gamma_linolenic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="감마 리놀렌산 (18:3 n-6) (mg)")
    nervonic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="네르본산 (24:1) (mg)")
    docosadienoic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="도코사디에노산 (22:2) (mg)")
    docosapentaenoic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="도코사펜타에노산 (DPA, 22:5 n-3) (mg)")
    docosahexaenoic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="도코사헥사에노산 (DHA, 22:6 n-3) (mg)")
    dihomo_linolenic_acid_mg = models.TextField(null=True, blank=True, help_text="디호모리놀렌산 (20:3 n-3) (mg)")
    lauric_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="라우르산 (12:0) (mg)")
    lignoceric_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="리그노세르산 (24:0) (mg)")
    linoleic_acid_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="리놀레산 (18:2 n-6) (g)")
    myristoleic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="미리스톨레산 (14:1) (mg)")
    myristic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="미리스트산 (14:0) (mg)")
    vaccenic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="박센산 (18:1 n-7) (mg)")
    behenic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="베헨산 (22:0) (mg)")
    butyric_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="부티르산 (4:0) (mg)")
    stearic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="스테아르산 (18:0) (mg)")
    stearidonic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="스테아리돈산 (18:4 n-3) (mg)")
    arachidonic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="아라키돈산 (20:4 n-6) (mg)")
    arachidic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="아라키드산 (20:0) (mg)")
    alpha_linolenic_acid_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="알파리놀렌산 (18:3 n-3) (g)")
    erucic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="에루크산 (22:1) (mg)")
    eicosadienoic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="에이코사디에노산 (20:2 n-6) (mg)")
    eicosatrienoic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="에이코사트리에노산 (20:3 n-6) (mg)")
    eicosapentaenoic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="에이코사펜타에노산 (EPA, 20:5 n-3) (mg)")
    omega3_fatty_acids_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="오메가3 지방산 (g)")
    omega6_fatty_acids_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="오메가6 지방산 (g)")
    oleic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="올레산 (18:1 n-9) (mg)")
    caproic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="카프로산 (6:0) (mg)")
    capric_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="카프르산 (10:0) (mg)")
    caprylic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="카프릴산 (8:0) (mg)")
    tridecanoic_acid_mg = models.TextField(null=True, blank=True, help_text="트라이데칸산 (13:0) (mg)")
    trans_linoleic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="트랜스 리놀레산 (18:2t) (mg)")
    trans_linolenic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="트랜스 리놀렌산 (18:3t) (mg)")
    trans_oleic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="트랜스 올레산 (18:1 trans n-9) (mg)")
    tricosanoic_acid_mg = models.TextField(null=True, blank=True, help_text="트리코산산 (23:0) (mg)")
    palmitoleic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="팔미톨레산 (16:1) (mg)")
    palmitic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="팔미트산 (16:0) (mg)")
    pentadecanoic_acid_mg = models.TextField(null=True, blank=True, help_text="펜타데칸산 (15:0) (mg)")
    heneicosanoic_acid_mg = models.TextField(null=True, blank=True, help_text="헨에이코산산 (21:0) (mg)")
    heptadecenoic_acid_mg = models.TextField(null=True, blank=True, help_text="헵타데센산 (17:1) (mg)")
    heptadecanoic_acid_mg = models.TextField(null=True, blank=True, help_text="헵타데칸산 (17:0) (mg)")
    
    # === 아미노산 ===
    amino_acids_mg = models.CharField(max_length=8, null=True, blank=True, help_text="아미노산 (mg)")
    essential_amino_acids_mg = models.TextField(null=True, blank=True, help_text="필수아미노산 (mg)")
    non_essential_amino_acids_mg = models.TextField(null=True, blank=True, help_text="비필수아미노산 (mg)")
    glutamic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="글루탐산 (mg)")
    glycine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="글리신 (mg)")
    lysine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="라이신 (mg)")
    leucine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="류신 / 루신 (mg)")
    methionine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="메티오닌 (mg)")
    valine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="발린 (mg)")
    serine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="세린 (mg)")
    cysteine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="시스테인 (mg)")
    arginine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="아르기닌 (mg)")
    aspartic_acid_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="아스파르트산 (mg)")
    alanine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="알라닌 (mg)")
    isoleucine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="이소류신 / 이소루신 (mg)")
    taurine_mg = models.TextField(null=True, blank=True, help_text="타우린 (mg)")
    threonine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="트레오닌 (mg)")
    tryptophan_mg = models.TextField(null=True, blank=True, help_text="트립토판 (mg)")
    tyrosine_mg = models.CharField(max_length=7, null=True, blank=True, help_text="티로신 (mg)")
    phenylalanine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="페닐알라닌 (mg)")
    proline_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="프롤린 (mg)")
    histidine_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="히스티딘 (mg)")
    
    # === 기타 성분 ===
    caffeine_mg = models.CharField(max_length=6, null=True, blank=True, help_text="카페인 (mg)")
    tocopherol_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="토코페롤 (mg)")
    tocotrienol_mg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="토코트리에놀 (mg)")
    
    # === 메타데이터 ===
    source_code = models.IntegerField(null=True, blank=True, help_text="출처코드")
    source_name = models.CharField(max_length=50, null=True, blank=True, help_text="출처명")
    food_weight = models.CharField(max_length=17, null=True, blank=True, help_text="식품중량")
    company_name = models.CharField(max_length=50, null=True, blank=True, help_text="업체명")
    data_generation_method_code = models.IntegerField(null=True, blank=True, help_text="데이터생성방법코드")
    data_generation_method_name = models.CharField(max_length=2, null=True, blank=True, help_text="데이터생성방법명")
    data_generation_date = models.DateField(null=True, blank=True, help_text="데이터생성일자")
    data_reference_date = models.DateField(null=True, blank=True, help_text="데이터기준일자")
    
    # === 추가된 컬럼들 ===
    dietary_fiber_type = models.CharField(max_length=10, null=True, blank=True, help_text="식이섬유종류")
    dietary_fiber_basis = models.TextField(null=True, blank=True, help_text="식이섬유근거")
    fodmap = models.CharField(max_length=50, null=True, blank=True, help_text="포드맵")
    fodmap_basis = models.TextField(null=True, blank=True, help_text="포드맵근거")
    
    # === 시스템 필드 ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "음식"
        verbose_name_plural = "음식들"
        ordering = ['food_name']
    
    def __str__(self):
        return self.food_name
    
    @property
    def calories_per_100g(self):
        """100g당 칼로리"""
        return self.energy_kcal
    
    @property
    def protein_percentage(self):
        """단백질 비율 (%)"""
        if self.energy_kcal and self.protein_g:
            protein_calories = float(self.protein_g) * 4  # 단백질 1g = 4kcal
            return round((protein_calories / self.energy_kcal) * 100, 1)
        return 0
    
    @property
    def fat_percentage(self):
        """지방 비율 (%)"""
        if self.energy_kcal and self.fat_g:
            fat_calories = float(self.fat_g) * 9  # 지방 1g = 9kcal
            return round((fat_calories / self.energy_kcal) * 100, 1)
        return 0
    
    @property
    def carbohydrate_percentage(self):
        """탄수화물 비율 (%)"""
        if self.energy_kcal and self.carbohydrates_g:
            carb_calories = float(self.carbohydrates_g) * 4  # 탄수화물 1g = 4kcal
            return round((carb_calories / self.energy_kcal) * 100, 1)
        return 0


class UserFoodRecord(models.Model):
    """사용자 음식 기록 모델"""
    MEAL_TYPE_CHOICES = [
        ('breakfast', '아침'),
        ('lunch', '점심'),
        ('dinner', '저녁'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='food_records')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='user_records')
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES, help_text="식사 타입")
    amount = models.DecimalField(max_digits=8, decimal_places=2, help_text="섭취량 (g)")
    record_date = models.DateField(help_text="기록 날짜")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "사용자 음식 기록"
        verbose_name_plural = "사용자 음식 기록들"
        ordering = ['-record_date', '-created_at']
        # 같은 날짜, 같은 사용자, 같은 음식, 같은 식사 타입에 대한 중복 방지
        unique_together = ('user', 'food', 'meal_type', 'record_date')
    
    def __str__(self):
        return f"{self.user.username}의 {self.record_date} {self.get_meal_type_display()} - {self.food.food_name}"
    
    @property
    def total_calories(self):
        """총 칼로리 (섭취량 기준)"""
        if self.food.energy_kcal and self.amount:
            return round((self.food.energy_kcal * float(self.amount)) / 100, 1)
        return 0
    
    @property
    def total_protein(self):
        """총 단백질 (섭취량 기준)"""
        if self.food.protein_g and self.amount:
            return round((float(self.food.protein_g) * float(self.amount)) / 100, 1)
        return 0
    
    @property
    def total_fat(self):
        """총 지방 (섭취량 기준)"""
        if self.food.fat_g and self.amount:
            return round((float(self.food.fat_g) * float(self.amount)) / 100, 1)
        return 0
    
    @property
    def total_carbohydrates(self):
        """총 탄수화물 (섭취량 기준)"""
        if self.food.carbohydrates_g and self.amount:
            return round((float(self.food.carbohydrates_g) * float(self.amount)) / 100, 1)
        return 0


class UserSleepRecord(models.Model):
    """사용자 수면 기록 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sleep_records')
    sleep_minutes = models.IntegerField(help_text="수면 시간 (분 단위)")
    record_date = models.DateField(help_text="기록 날짜")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "사용자 수면 기록"
        verbose_name_plural = "사용자 수면 기록들"
        ordering = ['-record_date', '-created_at']
        # 같은 날짜, 같은 사용자에 대한 중복 방지
        unique_together = ('user', 'record_date')
    
    def __str__(self):
        hours = self.sleep_minutes // 60
        minutes = self.sleep_minutes % 60
        return f"{self.user.username}의 {self.record_date} 수면 - {hours}시간 {minutes}분"
    
    @property
    def sleep_hours(self):
        """수면 시간 (시간 단위)"""
        return round(self.sleep_minutes / 60, 1)
    
    @property
    def formatted_sleep_time(self):
        """포맷된 수면 시간 (예: 7시간 30분)"""
        hours = self.sleep_minutes // 60
        minutes = self.sleep_minutes % 60
        if minutes == 0:
            return f"{hours}시간"
        else:
            return f"{hours}시간 {minutes}분"


class IBSSSSPainRecord(models.Model):
    """IBS-SSS 통증 기록 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ibssss_pain_records')
    record_date = models.DateField(help_text="통증 기록 날짜")
    has_pain = models.BooleanField(default=False, help_text="해당 날짜에 통증이 있었는지 여부")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "IBS-SSS 통증 기록"
        verbose_name_plural = "IBS-SSS 통증 기록들"
        ordering = ['-record_date']
        # 같은 날짜, 같은 사용자에 대한 중복 방지
        unique_together = ('user', 'record_date')
    
    def __str__(self):
        pain_status = "있음" if self.has_pain else "없음"
        return f"{self.user.username}의 {self.record_date} 통증 기록 - {pain_status}"


class IBSSSSRecord(models.Model):
    """IBS-SSS 설문 기록 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ibssss_records')
    
    # 7개 설문 항목별 답변
    # 1. 복부 통증 여부
    question_1 = models.BooleanField(null=True, blank=True, help_text="1번: 복부 통증 여부")
    
    # 2. 복부 통증 강도 (0-100)
    question_2 = models.IntegerField(null=True, blank=True, help_text="2번: 복부 통증 강도 (0-100)")
    
    # 3. 복통 일수 (0-10일)
    question_3 = models.IntegerField(null=True, blank=True, help_text="3번: 복통 일수 (0-10일)")
    
    # 4. 복부 팽만감 여부
    question_4 = models.BooleanField(null=True, blank=True, help_text="4번: 복부 팽만감 여부")
    
    # 5. 복부 팽만감 강도 (0-100)
    question_5 = models.IntegerField(null=True, blank=True, help_text="5번: 복부 팽만감 강도 (0-100)")
    
    # 6. 배변 습관 만족도 (0-100)
    question_6 = models.IntegerField(null=True, blank=True, help_text="6번: 배변 습관 만족도 (0-100)")
    
    # 7. 삶의 방해 정도 (0-100)
    question_7 = models.IntegerField(null=True, blank=True, help_text="7번: 삶의 방해 정도 (0-100)")
    
    # 계산된 결과
    total_score = models.IntegerField(null=True, blank=True, help_text="총점 (0-500)")
    severity = models.CharField(max_length=20, null=True, blank=True, choices=[
        ('normal', '정상'),
        ('mild', '경증'),
        ('moderate', '중등도'),
        ('severe', '중증'),
    ], help_text="심각도")
    
    # 메타데이터
    record_date = models.DateField(help_text="기록 날짜")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "IBS-SSS 기록"
        verbose_name_plural = "IBS-SSS 기록들"
        ordering = ['-record_date', '-created_at']
        # 같은 날짜, 같은 사용자에 대한 중복 방지
        unique_together = ('user', 'record_date')
    
    def __str__(self):
        return f"{self.user.username}의 IBS-SSS 기록 ({self.record_date})"
    
    def calculate_total_score(self):
        """IBS-SSS 총점 계산"""
        total_score = 0
        
        # 1. 복부 통증 강도 (0-100점)
        if self.question_1 and self.question_2 is not None:
            total_score += self.question_2
        
        # 2. 복부 팽만감 강도 (0-100점)
        if self.question_4 and self.question_5 is not None:
            total_score += self.question_5
        
        # 3. 배변 습관 불만족도 (0-100점)
        if self.question_6 is not None:
            total_score += self.question_6
        
        # 4. 삶의 방해 정도 (0-100점)
        if self.question_7 is not None:
            total_score += self.question_7
        
        # 5. 복통 일수 (0-100점)
        if self.question_3 is not None:
            total_score += (self.question_3 * 10)
        
        return total_score
    
    def calculate_severity(self):
        """심각도 계산"""
        total_score = self.calculate_total_score()
        
        if total_score <= 75:
            return 'normal'
        elif total_score <= 175:
            return 'mild'
        elif total_score <= 300:
            return 'moderate'
        else:
            return 'severe'
    
    def save(self, *args, **kwargs):
        """저장 시 총점과 심각도 자동 계산"""
        self.total_score = self.calculate_total_score()
        self.severity = self.calculate_severity()
        super().save(*args, **kwargs)


class IBSQOLRecord(models.Model):
    """IBS-QOL 설문 기록 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ibsqol_records')
    
    # 34개 설문 항목별 답변 (1-5점)
    question_1 = models.IntegerField(null=True, blank=True, help_text="1번: 장 문제로 인한 무력감")
    question_2 = models.IntegerField(null=True, blank=True, help_text="2번: 장 문제로 인한 냄새 때문에 난처함")
    question_3 = models.IntegerField(null=True, blank=True, help_text="3번: 변기에 앉아있는 시간 때문에 괴로움")
    question_4 = models.IntegerField(null=True, blank=True, help_text="4번: 장 문제로 인한 다른 병에 걸리기 쉬움")
    question_5 = models.IntegerField(null=True, blank=True, help_text="5번: 장 문제로 인한 배 팽창감")
    question_6 = models.IntegerField(null=True, blank=True, help_text="6번: 장 문제로 인한 생활 조절 불가")
    question_7 = models.IntegerField(null=True, blank=True, help_text="7번: 장 문제로 인한 일상생활 즐거움 감소")
    question_8 = models.IntegerField(null=True, blank=True, help_text="8번: 장 문제에 대한 이야기 시 불편함")
    question_9 = models.IntegerField(null=True, blank=True, help_text="9번: 장 문제로 인한 우울감")
    question_10 = models.IntegerField(null=True, blank=True, help_text="10번: 장 문제로 인한 고립감")
    question_11 = models.IntegerField(null=True, blank=True, help_text="11번: 장 문제로 인한 음식량 조심")
    question_12 = models.IntegerField(null=True, blank=True, help_text="12번: 장 문제로 인한 성생활 어려움")
    question_13 = models.IntegerField(null=True, blank=True, help_text="13번: 장 문제를 가지고 있어서 화남")
    question_14 = models.IntegerField(null=True, blank=True, help_text="14번: 장 문제로 인한 다른 사람들 성가심")
    question_15 = models.IntegerField(null=True, blank=True, help_text="15번: 장 문제 악화에 대한 걱정")
    question_16 = models.IntegerField(null=True, blank=True, help_text="16번: 장 문제로 인한 신경 날카로움")
    question_17 = models.IntegerField(null=True, blank=True, help_text="17번: 장 문제 과장에 대한 걱정")
    question_18 = models.IntegerField(null=True, blank=True, help_text="18번: 장 문제로 인한 할 일 제대로 못함")
    question_19 = models.IntegerField(null=True, blank=True, help_text="19번: 장 문제로 인한 스트레스 상황 회피")
    question_20 = models.IntegerField(null=True, blank=True, help_text="20번: 장 문제로 인한 성적 욕구 감소")
    question_21 = models.IntegerField(null=True, blank=True, help_text="21번: 장 문제로 인한 입을 수 있는 옷 제한")
    question_22 = models.IntegerField(null=True, blank=True, help_text="22번: 장 문제로 인한 격렬한 활동 회피")
    question_23 = models.IntegerField(null=True, blank=True, help_text="23번: 장 문제로 인한 음식 종류 조심")
    question_24 = models.IntegerField(null=True, blank=True, help_text="24번: 장 문제로 인한 모르는 사람들과 어울리기 어려움")
    question_25 = models.IntegerField(null=True, blank=True, help_text="25번: 장 문제로 인한 느리고 둔한 느낌")
    question_26 = models.IntegerField(null=True, blank=True, help_text="26번: 장 문제로 인한 불결함")
    question_27 = models.IntegerField(null=True, blank=True, help_text="27번: 장 문제로 인한 장거리 여행 어려움")
    question_28 = models.IntegerField(null=True, blank=True, help_text="28번: 장 문제로 인한 먹고 싶을 때 못 먹는 실망감")
    question_29 = models.IntegerField(null=True, blank=True, help_text="29번: 장 문제로 인한 화장실 가까이 있는 것의 중요성")
    question_30 = models.IntegerField(null=True, blank=True, help_text="30번: 생활이 장 문제를 중심으로 돌아감")
    question_31 = models.IntegerField(null=True, blank=True, help_text="31번: 배변 조절 못하고 참지 못하는 것에 대한 걱정")
    question_32 = models.IntegerField(null=True, blank=True, help_text="32번: 대변을 보지 못할까 봐 두려움")
    question_33 = models.IntegerField(null=True, blank=True, help_text="33번: 장 문제가 가까운 사람들과의 관계에 영향")
    question_34 = models.IntegerField(null=True, blank=True, help_text="34번: 아무도 장 문제를 이해하지 못한다고 느낌")
    
    # 계산된 결과
    total_score = models.IntegerField(null=True, blank=True, help_text="총점 (34-170)")
    quality_level = models.CharField(max_length=20, null=True, blank=True, choices=[
        ('excellent', '매우 좋음'),
        ('good', '좋음'),
        ('fair', '보통'),
        ('poor', '나쁨'),
        ('very_poor', '매우 나쁨'),
    ], help_text="삶의 질 수준")
    
    # 메타데이터
    record_date = models.DateField(help_text="기록 날짜")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "IBS-QOL 기록"
        verbose_name_plural = "IBS-QOL 기록들"
        ordering = ['-record_date', '-created_at']
        # 같은 날짜, 같은 사용자에 대한 중복 방지
        unique_together = ('user', 'record_date')
    
    def __str__(self):
        return f"{self.user.username}의 IBS-QOL 기록 ({self.record_date})"
    
    def calculate_total_score(self):
        """IBS-QOL 총점 계산 (역산)"""
        total_score = 0
        max_score = 34 * 5  # 34개 질문 × 5점
        
        # 각 답변을 점수로 변환 (1점=5점, 2점=4점, 3점=3점, 4점=2점, 5점=1점)
        questions = [
            self.question_1, self.question_2, self.question_3, self.question_4,
            self.question_5, self.question_6, self.question_7, self.question_8,
            self.question_9, self.question_10, self.question_11, self.question_12,
            self.question_13, self.question_14, self.question_15, self.question_16,
            self.question_17, self.question_18, self.question_19, self.question_20,
            self.question_21, self.question_22, self.question_23, self.question_24,
            self.question_25, self.question_26, self.question_27, self.question_28,
            self.question_29, self.question_30, self.question_31, self.question_32,
            self.question_33, self.question_34
        ]
        
        for answer in questions:
            if answer is not None and 1 <= answer <= 5:
                total_score += (6 - answer)  # 역산
        
        return total_score
    
    def calculate_quality_level(self):
        """삶의 질 수준 계산"""
        total_score = self.calculate_total_score()
        max_score = 34 * 5
        
        # 백분율 계산 (0-100%)
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        if percentage >= 80:
            return 'excellent'
        elif percentage >= 60:
            return 'good'
        elif percentage >= 40:
            return 'fair'
        elif percentage >= 20:
            return 'poor'
        else:
            return 'very_poor'
    
    def save(self, *args, **kwargs):
        """저장 시 총점과 삶의 질 수준 자동 계산"""
        self.total_score = self.calculate_total_score()
        self.quality_level = self.calculate_quality_level()
        super().save(*args, **kwargs)


class PSSStressRecord(models.Model):
    """PSS 스트레스 설문 기록 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pss_stress_records')
    
    # 10개 설문 항목별 답변 (0-4점)
    question_1 = models.IntegerField(null=True, blank=True, help_text="1번: 예상치 못한 일로 속상함")
    question_2 = models.IntegerField(null=True, blank=True, help_text="2번: 중요한 일을 조절할 수 없다고 느낌")
    question_3 = models.IntegerField(null=True, blank=True, help_text="3번: 불안하고 스트레스받음")
    question_4 = models.IntegerField(null=True, blank=True, help_text="4번: 개인적인 문제를 잘 처리할 수 있다고 자신감")
    question_5 = models.IntegerField(null=True, blank=True, help_text="5번: 일이 내 뜻대로 진행되고 있다고 느낌")
    question_6 = models.IntegerField(null=True, blank=True, help_text="6번: 자신이 해야 할 모든 일에 잘 대처할 수 없음")
    question_7 = models.IntegerField(null=True, blank=True, help_text="7번: 일상에서 짜증나는 것을 잘 조절할 수 있음")
    question_8 = models.IntegerField(null=True, blank=True, help_text="8번: 자신이 일을 잘 해냈다고 느낌")
    question_9 = models.IntegerField(null=True, blank=True, help_text="9번: 자신의 능력으로는 어떻게 해 볼 수 없는 일 때문에 화남")
    question_10 = models.IntegerField(null=True, blank=True, help_text="10번: 어려운 일이 너무 많아져서 극복할 수 없다고 느낌")
    
    # 계산된 결과
    total_score = models.IntegerField(null=True, blank=True, help_text="총점 (0-40)")
    stress_level = models.CharField(max_length=20, null=True, blank=True, choices=[
        ('low', '낮음'),
        ('moderate', '보통'),
        ('high', '높음'),
    ], help_text="스트레스 수준")
    
    # 메타데이터
    record_date = models.DateField(help_text="기록 날짜")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "PSS 스트레스 기록"
        verbose_name_plural = "PSS 스트레스 기록들"
        ordering = ['-record_date', '-created_at']
        # 같은 날짜, 같은 사용자에 대한 중복 방지
        unique_together = ('user', 'record_date')
    
    def __str__(self):
        return f"{self.user.username}의 PSS 스트레스 기록 ({self.record_date})"
    
    def calculate_total_score(self):
        """PSS 총점 계산"""
        total_score = 0
        
        # 각 질문별 점수 계산
        questions = [
            self.question_1, self.question_2, self.question_3, self.question_4,
            self.question_5, self.question_6, self.question_7, self.question_8,
            self.question_9, self.question_10
        ]
        
        for i, answer in enumerate(questions):
            if answer is not None and 0 <= answer <= 4:
                question_score = answer
                
                # 역산이 필요한 질문들 (4, 5, 7, 8번)
                if i + 1 in [4, 5, 7, 8]:
                    question_score = 4 - answer  # 0→4, 1→3, 2→2, 3→1, 4→0
                
                total_score += question_score
        
        return total_score
    
    def calculate_stress_level(self):
        """스트레스 수준 계산"""
        total_score = self.calculate_total_score()
        
        if total_score <= 13:
            return 'low'
        elif total_score <= 26:
            return 'moderate'
        else:
            return 'high'
    
    def save(self, *args, **kwargs):
        """저장 시 총점과 스트레스 수준 자동 계산"""
        self.total_score = self.calculate_total_score()
        self.stress_level = self.calculate_stress_level()
        super().save(*args, **kwargs)


class UserWaterRecord(models.Model):
    """사용자 물 섭취량 기록 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='water_records')
    water_intake = models.DecimalField(max_digits=8, decimal_places=2, help_text="물 섭취량 (ml)")
    cup_count = models.IntegerField(help_text="컵 수")
    record_date = models.DateField(help_text="기록 날짜")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "사용자 물 섭취량 기록"
        verbose_name_plural = "사용자 물 섭취량 기록들"
        ordering = ['-record_date', '-created_at']
        # 같은 날짜, 같은 사용자에 대한 중복 방지
        unique_together = ('user', 'record_date')

    def __str__(self):
        return f"{self.user.username}의 {self.record_date} 물 섭취량: {self.water_intake}ml ({self.cup_count}컵)"

    @property
    def water_intake_liters(self):
        """리터 단위로 변환"""
        return float(self.water_intake) / 1000.0

    @property
    def formatted_water_intake(self):
        """포맷된 물 섭취량 문자열"""
        if self.water_intake >= 1000:
            return f"{self.water_intake_liters:.1f}L ({self.cup_count}컵)"
        else:
            return f"{self.water_intake}ml ({self.cup_count}컵)"


class UserExerciseRecord(models.Model):
    """사용자 운동 기록 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_records')
    target_steps = models.IntegerField(help_text="목표 걸음 수")
    current_steps = models.IntegerField(help_text="현재 걸음 수")
    record_date = models.DateField(help_text="기록 날짜")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "사용자 운동 기록"
        verbose_name_plural = "사용자 운동 기록들"
        ordering = ['-record_date', '-created_at']
        # 같은 날짜, 같은 사용자에 대한 중복 방지
        unique_together = ('user', 'record_date')

    def __str__(self):
        return f"{self.user.username}의 {self.record_date} 운동: {self.current_steps}걸음 (목표: {self.target_steps}걸음)"

    @property
    def progress_percentage(self):
        """목표 대비 진행률 (%)"""
        if self.target_steps > 0:
            return min((self.current_steps / self.target_steps) * 100, 100.0)
        return 0.0

    @property
    def is_goal_achieved(self):
        """목표 달성 여부"""
        return self.current_steps >= self.target_steps

    @property
    def formatted_progress(self):
        """포맷된 진행률 문자열"""
        return f"{self.progress_percentage:.1f}%"


class InterventionRecord(models.Model):
    """AI 중재 결과 기록 모델"""
    GUBUN_CHOICES = [
        ('all', '전체 (음식, 운동)'),
        ('sleep', '수면'),
        ('food', '음식'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intervention_records')
    record_date = models.DateField(help_text="중재 대상 날짜")
    target_date = models.DateField(help_text="중재 적용 날짜 (대상 날짜 + 1일)")
    gubun = models.CharField(max_length=10, choices=GUBUN_CHOICES, default='all', help_text="중재 구분")
    
    # 중재 결과 데이터 (JSON 형태로 저장)
    diet_evaluation = models.TextField(help_text="식단 평가")
    diet_target = models.JSONField(default=dict, null=True, blank=True, help_text="식단 권고사항 (Target 객체)")
    
    food_evaluation = models.TextField(null=True, blank=True, help_text="음식 평가")
    input_fodmap_count = models.JSONField(default=dict, null=True, blank=True, help_text="포드맵 음식 수 (전체, 저포드맵, 고포드맵 수)")
    
    sleep_evaluation = models.TextField(null=True, blank=True, help_text="수면 평가")
    sleep_target = models.FloatField(null=True, blank=True, help_text="수면 목표 시간 (시간)")
    
    exercise_evaluation = models.TextField(help_text="운동 평가")
    exercise_target = models.IntegerField(null=True, blank=True, help_text="운동 목표 걸음 수")
    
    processing_time = models.FloatField(help_text="처리 시간 (초)")
    error_message = models.TextField(blank=True, null=True, help_text="오류 메시지 (있는 경우)")
    
    # 입력 파라미터 저장 (input_ 접두어)
    input_allergies = models.JSONField(default=list, null=True, blank=True, help_text="알레르기 정보")
    input_restrictions = models.JSONField(default=list, null=True, blank=True, help_text="식이 제한사항")
    input_recent_3days = models.JSONField(default=list, null=True, blank=True, help_text="최근 3일간 음식 기록")
    input_today_sleep = models.FloatField(null=True, blank=True, help_text="오늘 수면 시간")
    input_week_step = models.JSONField(default=list, null=True, blank=True, help_text="일주일간 걸음 수")
    input_today_diet = models.JSONField(default=list, null=True, blank=True, help_text="오늘 식단")
    input_use_rag = models.BooleanField(default=True, null=True, blank=True, help_text="RAG 사용 여부")
    input_ollama_model = models.CharField(max_length=100, default="gpt-oss:20b", null=True, blank=True, help_text="사용된 Ollama 모델")
    
    # LLM 출력 결과 저장
    outputs = models.JSONField(default=dict, null=True, blank=True, help_text="LLM 원본 출력 결과")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI 중재 결과 기록"
        verbose_name_plural = "AI 중재 결과 기록들"
        ordering = ['-target_date', '-created_at']
        # 같은 기록 날짜, 같은 사용자, 같은 구분에 대한 중복 방지
        unique_together = ('user', 'record_date', 'gubun')

    def __str__(self):
        return f"{self.user.username}의 {self.record_date} 중재 결과 (적용일: {self.target_date})"


class NotificationSchedule(models.Model):
    """알림 스케줄 모델"""
    GUBUN_CHOICES = [
        ('notification', '알림'),
        ('exercise_save', '운동저장'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='스케줄 이름')
    description = models.TextField(blank=True, verbose_name='스케줄 설명')
    cron_expression = models.CharField(max_length=50, verbose_name='Cron 표현식', help_text='예: 0 21 * * * (매일 21시 0분)')
    gubun = models.CharField(max_length=20, choices=GUBUN_CHOICES, default='notification', verbose_name='구분', help_text='알림 또는 액션')
    title = models.CharField(max_length=200, verbose_name='알림 제목', blank=True, help_text='알림인 경우에만 사용')
    body = models.TextField(verbose_name='알림 내용', blank=True, help_text='알림인 경우에만 사용')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '알림 스케줄'
        verbose_name_plural = '알림 스케줄'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.cron_expression}"

    def get_readable_schedule(self):
        """읽기 쉬운 스케줄 표현"""
        try:
            parts = self.cron_expression.split(' ')
            if len(parts) == 5:
                minute, hour = parts[0], parts[1]
                if minute != '*' and hour != '*':
                    return f"매일 {hour}시 {minute}분"
            return self.cron_expression
        except:
            return self.cron_expression


class NotificationHistory(models.Model):
    """알람 이력 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_histories')
    title = models.CharField(max_length=200, verbose_name='알람 제목')
    body = models.TextField(verbose_name='알람 내용')
    payload = models.CharField(max_length=100, null=True, blank=True, verbose_name='페이로드')
    is_read = models.BooleanField(default=False, verbose_name='읽음 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    
    class Meta:
        verbose_name = '알람 이력'
        verbose_name_plural = '알람 이력들'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class SystemProfile(models.Model):
    """시스템 프로필 모델 - 앱 버전 및 다운로드 정보 관리"""
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
    ]
    
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, verbose_name='플랫폼')
    version = models.CharField(max_length=20, verbose_name='최소 지원 버전', help_text='예: 0.1.11+11')
    download_url = models.URLField(max_length=500, verbose_name='다운로드 URL')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '시스템 프로필'
        verbose_name_plural = '시스템 프로필들'
        unique_together = ('platform',)
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_platform_display()} - {self.version}"
    
    def is_version_supported(self, app_version):
        """앱 버전이 지원되는지 확인"""
        try:
            # 버전 비교 로직 (간단한 문자열 비교)
            return app_version >= self.version
        except:
            return False


class BatchSchedule(models.Model):
    """배치 작업 스케줄 설정 모델"""
    FREQUENCY_CHOICES = [
        ('daily', '매일'),
        ('weekly', '매주'),
        ('monthly', '매월'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='스케줄 이름')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, verbose_name='실행 주기')
    hour = models.IntegerField(default=9, verbose_name='실행 시간 (시)', help_text='0-23')
    minute = models.IntegerField(default=0, verbose_name='실행 시간 (분)', help_text='0-59')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '배치 스케줄'
        verbose_name_plural = '배치 스케줄'
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()} {self.hour:02d}:{self.minute:02d}"
    
    @property
    def cron_expression(self):
        """Cron 표현식 반환"""
        if self.frequency == 'daily':
            return f"{self.minute} {self.hour} * * *"
        elif self.frequency == 'weekly':
            return f"{self.minute} {self.hour} * * 0"  # 매주 일요일
        elif self.frequency == 'monthly':
            return f"{self.minute} {self.hour} 1 * *"  # 매월 1일
        return f"{self.minute} {self.hour} * * *"


class UserExerciseHistory(models.Model):
    """사용자 운동 히스토리 모델 - 스케줄 기반 자동 저장"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_histories')
    record_date = models.DateField(help_text="기록 날짜")
    record_time = models.TimeField(help_text="기록 시간")
    target_steps = models.IntegerField(help_text="목표 걸음 수")
    current_steps = models.IntegerField(help_text="현재 걸음 수")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "사용자 운동 히스토리"
        verbose_name_plural = "사용자 운동 히스토리들"
        ordering = ['-record_date', '-record_time']
        # 같은 날짜, 같은 시간, 같은 사용자에 대한 중복 방지
        unique_together = ('user', 'record_date', 'record_time')
        indexes = [
            models.Index(fields=['user', 'record_date']),
            models.Index(fields=['record_date', 'record_time']),
        ]
    
    def __str__(self):
        return f"{self.user.username}의 {self.record_date} {self.record_time} 운동 기록: {self.current_steps}걸음 (목표: {self.target_steps}걸음)"
    
    @property
    def progress_percentage(self):
        """목표 대비 진행률 (%)"""
        if self.target_steps > 0:
            return min((self.current_steps / self.target_steps) * 100, 100.0)
        return 0.0
    
    @property
    def is_goal_achieved(self):
        """목표 달성 여부"""
        return self.current_steps >= self.target_steps
    
    @property
    def formatted_progress(self):
        """포맷된 진행률 문자열"""
        return f"{self.progress_percentage:.1f}%"
    
    @property
    def steps_remaining(self):
        """남은 걸음 수"""
        return max(0, self.target_steps - self.current_steps)


class UserLoginHistory(models.Model):
    """사용자 로그인 이력 모델"""
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]
    
    LOGIN_TYPE_CHOICES = [
        ('auto', '자동 로그인'),
        ('manual', '수동 로그인'),
        ('social', '소셜 로그인'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_histories')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, verbose_name='플랫폼')
    app_version = models.CharField(max_length=20, verbose_name='앱 버전', help_text='예: 0.1.11+11')
    login_type = models.CharField(max_length=10, choices=LOGIN_TYPE_CHOICES, verbose_name='로그인 타입')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 주소')
    user_agent = models.TextField(null=True, blank=True, verbose_name='User Agent')
    device_info = models.JSONField(default=dict, null=True, blank=True, verbose_name='디바이스 정보')
    login_time = models.DateTimeField(auto_now_add=True, verbose_name='로그인 시간')
    
    class Meta:
        verbose_name = '사용자 로그인 이력'
        verbose_name_plural = '사용자 로그인 이력들'
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', 'login_time']),
            models.Index(fields=['platform']),
            models.Index(fields=['login_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username}의 {self.get_platform_display()} 로그인 ({self.login_time.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def formatted_login_time(self):
        """포맷된 로그인 시간"""
        return self.login_time.strftime('%Y-%m-%d %H:%M:%S')
    
    @property
    def is_recent_login(self):
        """최근 로그인 여부 (24시간 이내)"""
        from django.utils import timezone
        from datetime import timedelta
        return self.login_time > timezone.now() - timedelta(hours=24)


