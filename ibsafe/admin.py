from django.contrib import admin
from .models import (
    SocialAccount, UserProfile, UserMedication, FoodCategory, Food, 
    UserFoodRecord, UserSleepRecord, IBSSSSPainRecord, IBSSSSRecord, 
    IBSQOLRecord, PSSStressRecord, UserWaterRecord, BatchSchedule
)

@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'provider_id', 'created_at']
    list_filter = ['provider', 'created_at']
    search_fields = ['user__username', 'provider_id']
    ordering = ['-created_at']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'birth_date', 'gender', 'created_at']
    list_filter = ['gender', 'created_at']
    search_fields = ['user__username', 'phone_number']
    ordering = ['-created_at']

@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ['main_category_code', 'main_category_name', 'middle_category_name', 'sub_category_name', 'representative_food_name']
    list_filter = ['main_category_name']
    search_fields = ['main_category_name', 'middle_category_name', 'sub_category_name', 'representative_food_name']
    ordering = ['main_category_code']
    
    fieldsets = (
        ('대분류', {
            'fields': ('main_category_code', 'main_category_name')
        }),
        ('중분류', {
            'fields': ('middle_category_code', 'middle_category_name')
        }),
        ('소분류', {
            'fields': ('sub_category_code', 'sub_category_name')
        }),
        ('세분류', {
            'fields': ('detail_category_code', 'detail_category_name')
        }),
        ('대표식품', {
            'fields': ('representative_food_code', 'representative_food_name')
        }),
    )

@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ['food_name', 'food_code', 'category', 'energy_kcal', 'protein_g', 'fat_g', 'carbohydrates_g']
    list_filter = ['category__main_category_name', 'data_generation_date', 'data_type_name']
    search_fields = ['food_name', 'food_code', 'category__main_category_name']
    ordering = ['food_name']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('food_code', 'food_name', 'data_type_code', 'data_type_name', 'food_origin_code', 'food_origin_name', 'category', 'nutrition_standard_amount', 'nutrition_standard_unit')
        }),
        ('기본 영양성분', {
            'fields': ('energy_kcal', 'water_g', 'protein_g', 'fat_g', 'ash_g', 'carbohydrates_g', 'sugar_g', 'dietary_fiber_g')
        }),
        ('무기질', {
            'fields': ('calcium_mg', 'iron_mg', 'phosphorus_mg', 'potassium_mg', 'sodium_mg', 'copper_ug', 'magnesium_mg', 'manganese_mg', 'molybdenum_ug', 'fluorine_mg', 'selenium_ug', 'zinc_mg', 'chlorine_mg', 'iodine_ug', 'chromium_ug')
        }),
        ('비타민 A', {
            'fields': ('vitamin_a_rae_ug', 'retinol_ug', 'beta_carotene_ug')
        }),
        ('비타민 B군', {
            'fields': ('thiamine_mg', 'riboflavin_mg', 'niacin_mg', 'nicotinic_acid_mg', 'nicotinamide_mg', 'biotin_ug', 'vitamin_b6_mg', 'vitamin_b12_ug', 'folate_dfe_ug', 'choline_mg', 'pantothenic_acid_mg')
        }),
        ('비타민 D', {
            'fields': ('vitamin_d_ug', 'vitamin_d2_ug', 'vitamin_d3_ug')
        }),
        ('비타민 E', {
            'fields': ('vitamin_e_ate_mg', 'alpha_tocopherol_mg', 'beta_tocopherol_mg', 'gamma_tocopherol_mg', 'delta_tocopherol_mg', 'alpha_tocotrienol_mg', 'beta_tocotrienol_mg', 'gamma_tocotrienol_mg', 'delta_tocotrienol_mg')
        }),
        ('비타민 K', {
            'fields': ('vitamin_k_ug', 'vitamin_k1_ug', 'vitamin_k2_ug')
        }),
        ('비타민 C', {
            'fields': ('vitamin_c_mg',)
        }),
        ('지방 관련', {
            'fields': ('cholesterol_mg', 'saturated_fatty_acids_g', 'trans_fatty_acids_g', 'unsaturated_fat_g')
        }),
        ('당류', {
            'fields': ('galactose_g', 'fructose_g', 'sugar_alcohol_g', 'maltose_g', 'allulose_g', 'erythritol_g', 'lactose_g', 'sucrose_g', 'tagatose_g', 'glucose_g')
        }),
        ('지방산 상세 (1)', {
            'fields': ('epa_dha_mg', 'gadoleic_acid_mg', 'gamma_linolenic_acid_mg', 'nervonic_acid_mg', 'docosadienoic_acid_mg', 'docosapentaenoic_acid_mg', 'docosahexaenoic_acid_mg', 'dihomo_linolenic_acid_mg', 'lauric_acid_mg', 'lignoceric_acid_mg', 'linoleic_acid_g', 'myristoleic_acid_mg', 'myristic_acid_mg', 'vaccenic_acid_mg', 'behenic_acid_mg')
        }),
        ('지방산 상세 (2)', {
            'fields': ('butyric_acid_mg', 'stearic_acid_mg', 'stearidonic_acid_mg', 'arachidonic_acid_mg', 'arachidic_acid_mg', 'alpha_linolenic_acid_g', 'erucic_acid_mg', 'eicosadienoic_acid_mg', 'eicosatrienoic_acid_mg', 'eicosapentaenoic_acid_mg', 'omega3_fatty_acids_g', 'omega6_fatty_acids_g', 'oleic_acid_mg')
        }),
        ('지방산 상세 (3)', {
            'fields': ('caproic_acid_mg', 'capric_acid_mg', 'caprylic_acid_mg', 'tridecanoic_acid_mg', 'trans_linoleic_acid_mg', 'trans_linolenic_acid_mg', 'trans_oleic_acid_mg', 'tricosanoic_acid_mg', 'palmitoleic_acid_mg', 'palmitic_acid_mg', 'pentadecanoic_acid_mg', 'heneicosanoic_acid_mg', 'heptadecenoic_acid_mg', 'heptadecanoic_acid_mg')
        }),
        ('아미노산 (1)', {
            'fields': ('amino_acids_mg', 'essential_amino_acids_mg', 'non_essential_amino_acids_mg', 'glutamic_acid_mg', 'glycine_mg', 'lysine_mg', 'leucine_mg', 'methionine_mg', 'valine_mg', 'serine_mg', 'cysteine_mg')
        }),
        ('아미노산 (2)', {
            'fields': ('arginine_mg', 'aspartic_acid_mg', 'alanine_mg', 'isoleucine_mg', 'taurine_mg', 'threonine_mg', 'tryptophan_mg', 'tyrosine_mg', 'phenylalanine_mg', 'proline_mg', 'histidine_mg')
        }),
        ('기타 성분', {
            'fields': ('caffeine_mg', 'tocopherol_mg', 'tocotrienol_mg')
        }),
        ('메타데이터', {
            'fields': ('source_code', 'source_name', 'food_weight', 'company_name', 'data_generation_method_code', 'data_generation_method_name', 'data_generation_date', 'data_reference_date')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    # 필터 옵션 추가
    list_per_page = 50  # 한 페이지당 표시할 항목 수


@admin.register(UserFoodRecord)
class UserFoodRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'food', 'meal_type', 'amount', 'record_date', 'total_calories', 'created_at']
    list_filter = ['meal_type', 'record_date', 'created_at']
    search_fields = ['user__username', 'food__food_name']
    ordering = ['-record_date', '-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'food', 'meal_type', 'amount', 'record_date')
        }),
        ('영양 정보', {
            'fields': ('total_calories', 'total_protein', 'total_fat', 'total_carbohydrates')
        }),
    )
    
    readonly_fields = ['total_calories', 'total_protein', 'total_fat', 'total_carbohydrates', 'created_at', 'updated_at']


@admin.register(UserSleepRecord)
class UserSleepRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'sleep_minutes', 'sleep_hours', 'record_date', 'created_at']
    list_filter = ['record_date', 'created_at']
    search_fields = ['user__username']
    ordering = ['-record_date', '-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'sleep_minutes', 'record_date')
        }),
        ('계산된 정보', {
            'fields': ('sleep_hours', 'formatted_sleep_time')
        }),
    )
    
    readonly_fields = ['sleep_hours', 'formatted_sleep_time', 'created_at', 'updated_at']


@admin.register(IBSSSSRecord)
class IBSSSSRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'record_date', 'total_score', 'severity', 'question_1', 'question_4', 'created_at']
    list_filter = ['severity', 'question_1', 'question_4', 'record_date', 'created_at']
    search_fields = ['user__username']
    ordering = ['-record_date', '-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'record_date')
        }),
        ('설문 답변', {
            'fields': ('question_1', 'question_2', 'question_3', 'question_4', 'question_5', 'question_6', 'question_7')
        }),
        ('계산된 결과', {
            'fields': ('total_score', 'severity')
        }),
    )
    
    readonly_fields = ['total_score', 'severity', 'created_at', 'updated_at']


@admin.register(IBSSSSPainRecord)
class IBSSSSPainRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'record_date', 'has_pain', 'created_at']
    list_filter = ['has_pain', 'record_date', 'created_at']
    search_fields = ['user__username']
    ordering = ['-record_date', '-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'record_date', 'has_pain')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserWaterRecord)
class UserWaterRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'water_intake', 'cup_count', 'record_date', 'water_intake_liters', 'created_at']
    list_filter = ['record_date', 'created_at']
    search_fields = ['user__username']
    ordering = ['-record_date', '-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'water_intake', 'cup_count', 'record_date')
        }),
        ('계산된 정보', {
            'fields': ('water_intake_liters', 'formatted_water_intake')
        }),
    )
    
    readonly_fields = ['water_intake_liters', 'formatted_water_intake', 'created_at', 'updated_at']


@admin.register(BatchSchedule)
class BatchScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'frequency', 'hour', 'minute', 'is_active', 'created_at']
    list_filter = ['frequency', 'is_active', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'frequency', 'is_active')
        }),
        ('실행 시간', {
            'fields': ('hour', 'minute'),
            'description': '매일/매주/매월 실행할 시간을 설정합니다.'
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # 편집 중인 경우
            return ['created_at', 'updated_at']
        return ['created_at', 'updated_at']
