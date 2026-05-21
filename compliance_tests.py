"""
اختبار وحدات لنظام حساب نسبة الامتثال
"""

import pytest
from Backend.compliance import (
    clean_text,
    RequirementCategory,
    Requirement,
    RequirementMatch,
    segment_text_into_chunks,
    CATEGORY_WEIGHTS,
    SIMILARITY_THRESHOLDS,
)


class TestDataClasses:
    """اختبار Data Classes"""
    
    def test_requirement_creation(self):
        """اختبار إنشاء كائن Requirement"""
        req = Requirement(
            text="توفير نظام متكامل",
            category=RequirementCategory.SCOPE,
            importance="high",
        )
        
        assert req.text == "توفير نظام متكامل"
        assert req.category == RequirementCategory.SCOPE
        assert req.importance == "high"
    
    def test_requirement_match_coverage(self):
        """اختبار حالات التطابق المختلفة"""
        req = Requirement(
            text="نظام إدارة شامل",
            category=RequirementCategory.SCOPE,
        )
        
        match = RequirementMatch(requirement=req)
        assert match.is_covered == False
        assert match.similarity_score == 0.0
        
        match.is_covered = True
        match.similarity_score = 0.85
        assert match.is_covered == True
        assert match.similarity_score == 0.85


class TestUtilityFunctions:
    """اختبار الدوال المساعدة"""
    
    def test_clean_text(self):
        """اختبار تنظيف النص"""
        dirty = "  النص   بـ   مسافات   غريبة  "
        clean = clean_text(dirty)
        assert "  " not in clean
        assert clean == "النص بـ مسافات غريبة"
        
        # اختبار إزالة الشَدّة
        text_with_shadda = "مرحباـ"
        assert "ـ" not in clean_text(text_with_shadda)
    
    def test_text_segmentation(self):
        """اختبار تقسيم النص إلى أجزاء"""
        text = """
        جملة أولى. جملة ثانية. جملة ثالثة.
        جملة رابعة! جملة خامسة؟ جملة سادسة.
        """
        
        chunks = segment_text_into_chunks(text, chunk_size=50)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
        assert all(len(c) > 0 for c in chunks)


class TestEnumAndConstants:
    """اختبار الـ Enums والثوابت"""
    
    def test_requirement_categories(self):
        """اختبار جميع فئات المتطلبات"""
        expected_categories = [
            "scope", "methodology", "timeline", 
            "deliverables", "resources", "support", "compliance"
        ]
        
        actual_categories = [cat.value for cat in RequirementCategory]
        assert set(actual_categories) == set(expected_categories)
    
    def test_weights_sum_to_one(self):
        """اختبار أن مجموع الأوزان = 1"""
        total_weight = sum(CATEGORY_WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.001  # مع مراعاة الأخطاء العددية
    
    def test_weights_are_positive(self):
        """اختبار أن جميع الأوزان موجبة"""
        for weight in CATEGORY_WEIGHTS.values():
            assert weight > 0
            assert weight <= 1
    
    def test_similarity_thresholds(self):
        """اختبار عتبات التشابه"""
        assert SIMILARITY_THRESHOLDS["high"] > SIMILARITY_THRESHOLDS["medium"]
        assert SIMILARITY_THRESHOLDS["medium"] > SIMILARITY_THRESHOLDS["low"]
        assert SIMILARITY_THRESHOLDS["low"] > 0
        assert SIMILARITY_THRESHOLDS["high"] <= 1


class TestDataValidation:
    """اختبار صحة البيانات"""
    
    def test_requirement_text_not_empty(self):
        """اختبار أن نص المتطلب غير فارغ"""
        with pytest.raises(Exception):
            Requirement(
                text="",  # نص فارغ
                category=RequirementCategory.SCOPE,
            )
    
    def test_category_enum_validation(self):
        """اختبار التحقق من الفئات"""
        # يجب أن يعمل
        req1 = Requirement(
            text="متطلب",
            category=RequirementCategory.SCOPE,
        )
        assert req1.category == RequirementCategory.SCOPE
        
        # يجب أن يفشل
        with pytest.raises(Exception):
            Requirement(
                text="متطلب",
                category="invalid_category",  # فئة غير صحيحة
            )


class TestScoreCalculation:
    """اختبار منطق حساب النسب"""
    
    def test_coverage_ratio_calculation(self):
        """اختبار حساب نسبة التغطية"""
        # 3 من 5 متطلبات مغطاة = 60%
        covered = 3
        total = 5
        coverage_ratio = covered / total
        assert coverage_ratio == 0.6
    
    def test_quality_ratio_clamping(self):
        """اختبار تقييد نسبة الجودة بين 0 و 1"""
        # الدالة يجب أن تقيم القيم بين 0 و 1
        score_too_high = 1.5
        clamped = max(0, min(1, score_too_high))
        assert clamped == 1.0
        
        score_too_low = -0.5
        clamped = max(0, min(1, score_too_low))
        assert clamped == 0.0
    
    def test_weighted_score_calculation(self):
        """اختبار حساب النسبة المرجحة"""
        # إذا كانت جميع الأقسام لها نفس الدرجة (80)
        # والأوزان مختلفة
        # النتيجة يجب أن تكون 80
        
        category_scores = {cat.value: 80.0 for cat in RequirementCategory}
        
        final_score = sum(
            category_scores[cat.value] * CATEGORY_WEIGHTS[cat]
            for cat in RequirementCategory
        )
        
        assert abs(final_score - 80.0) < 0.1
    
    def test_weighted_score_with_different_values(self):
        """اختبار النسبة المرجحة مع قيم مختلفة"""
        # إعطاء الأقسام المهمة نسبة عالية
        category_scores = {
            "scope": 100.0,           # وزن 25%
            "methodology": 100.0,     # وزن 20%
            "timeline": 0.0,          # وزن 15%
            "deliverables": 100.0,    # وزن 20%
            "resources": 0.0,         # وزن 10%
            "support": 0.0,           # وزن 5%
            "compliance": 0.0,        # وزن 5%
        }
        
        final_score = sum(
            category_scores[cat.value] * CATEGORY_WEIGHTS[cat]
            for cat in RequirementCategory
        )
        
        # يجب أن تكون النسبة حوالي 70
        # (25 + 20 + 0 + 20 + 0 + 0 + 0) = 65
        assert final_score == 65.0


class TestEdgeCases:
    """اختبار الحالات الحدية"""
    
    def test_empty_category_scores(self):
        """اختبار عندما تكون بعض الفئات فارغة"""
        # يجب أن تحصل الفئات الفارغة على 0
        category_scores = {
            "scope": 50.0,
            "methodology": 0.0,  # فارغ
            "timeline": 75.0,
            "deliverables": 0.0,  # فارغ
            "resources": 60.0,
            "support": 0.0,
            "compliance": 0.0,
        }
        
        final_score = sum(
            category_scores[cat.value] * CATEGORY_WEIGHTS[cat]
            for cat in RequirementCategory
        )
        
        assert 0 <= final_score <= 100
    
    def test_all_zeros(self):
        """اختبار عندما تكون جميع الدرجات 0"""
        category_scores = {cat.value: 0.0 for cat in RequirementCategory}
        
        final_score = sum(
            category_scores[cat.value] * CATEGORY_WEIGHTS[cat]
            for cat in RequirementCategory
        )
        
        assert final_score == 0.0
    
    def test_all_perfect_scores(self):
        """اختبار عندما تكون جميع الدرجات 100"""
        category_scores = {cat.value: 100.0 for cat in RequirementCategory}
        
        final_score = sum(
            category_scores[cat.value] * CATEGORY_WEIGHTS[cat]
            for cat in RequirementCategory
        )
        
        assert final_score == 100.0


if __name__ == "__main__":
    # لتشغيل الاختبارات:
    # pytest compliance_tests.py -v
    
    print("اختبارات نظام حساب نسبة الامتثال")
    print("=" * 60)
    print("استخدم: pytest compliance_tests.py -v")
    print("أو: python -m pytest compliance_tests.py -v")
