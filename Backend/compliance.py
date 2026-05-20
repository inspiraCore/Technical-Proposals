import re
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field


# ===========================
# Enums و Data Classes
# ===========================

class RequirementCategory(str, Enum):
    """أقسام المتطلبات الرئيسية"""
    SCOPE = "scope"  # نطاق العمل
    METHODOLOGY = "methodology"  # المنهجية
    TIMELINE = "timeline"  # الجدول الزمني
    DELIVERABLES = "deliverables"  # المخرجات والتسليمات
    RESOURCES = "resources"  # الموارد والكفاءات
    SUPPORT = "support"  # الدعم والضمان
    COMPLIANCE = "compliance"  # الامتثال والشروط


# أوزان كل قسم في النسبة النهائية
CATEGORY_WEIGHTS = {
    RequirementCategory.SCOPE: 0.25,
    RequirementCategory.METHODOLOGY: 0.20,
    RequirementCategory.TIMELINE: 0.15,
    RequirementCategory.DELIVERABLES: 0.20,
    RequirementCategory.RESOURCES: 0.10,
    RequirementCategory.SUPPORT: 0.05,
    RequirementCategory.COMPLIANCE: 0.05,
}

# عتبات للتطابق الدلالي
SIMILARITY_THRESHOLDS = {
    # تم رفع العتبات حتى لا يتم قبول أي تشابه ضعيف على أنه امتثال حقيقي
    "high": 0.82,      # تطابق عالي وواضح
    "medium": 0.68,    # تطابق جيد ومقبول
    "partial": 0.55,   # تطابق جزئي يحتاج تحقق بالكلمات المفتاحية
    "low": 0.35,       # حد أدنى للبحث فقط وليس للحكم النهائي
}

IMPORTANT_KEYWORDS = [
    "مقدمة", "فهم", "نطاق العمل", "متطلبات", "منهجية", "تنفيذ",
    "خطة", "جدول زمني", "مراحل", "مخرجات", "تسليمات", "تقرير",
    "تقارير", "دعم فني", "ضمان", "صيانة", "امتثال", "الشروط",
    "الأمن السيبراني", "اختبار", "اختبارات", "ثغرات", "مخاطر",
    "استجابة", "حوادث", "تدريب", "نقل المعرفة", "SLA", "NDA",
]


@dataclass
class Requirement:
    """تمثيل متطلب واحد"""
    text: str
    category: RequirementCategory
    importance: str = "high"  # high, medium, low


@dataclass
class RequirementMatch:
    """نتيجة مطابقة متطلب"""
    requirement: Requirement
    matched_text: Optional[str] = None
    similarity_score: float = 0.0
    is_covered: bool = False


class ComplianceRequest(BaseModel):
    source_text: str = Field(..., description="النص المصدر RFP أو الكراسة")
    output_text: str = Field(..., description="النص المخرج العرض الفني")


class ComplianceResponse(BaseModel):
    score: float = Field(description="نسبة الامتثال من 0-100")
    category_scores: Dict[str, float] = Field(description="نسب الامتثال لكل قسم")
    segments: List[Dict[str, Any]] = Field(description="تفاصيل الأجزاء المحللة")
    compliance_level: Optional[str] = Field(None, description="تصنيف الامتثال النهائي")
    error: Optional[str] = Field(None, description="رسالة الخطأ إن وجدت")


def clean_text(text: str) -> str:
    """تنظيف بسيط للنص بدون تغيير المعنى"""
    text = re.sub(r"\s+", " ", text or "")
    text = text.replace("ـ", "")
    return text.strip()

def segment_text_into_chunks(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
    """
    تقسيم النص إلى أجزاء صغيرة للمطابقة الدلالية.
    التقسيم بسيط ومستقر ويعتمد على الكلمات.
    """
    text = clean_text(text)
    words = text.split()

    if not words:
        return []

    chunks = []
    step = max(1, chunk_size - overlap)

    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)

    return chunks


# ===========================
# دوال استخراج المتطلبات
# ===========================

def get_compliance_level(score: float) -> str:
    """تصنيف النتيجة النهائية بطريقة أوضح للمستخدم."""
    if score >= 85:
        return "🟢 متطابق بدرجة عالية"
    if score >= 70:
        return "🟡 متطابق جيد"
    if score >= 50:
        return "🟠 متطابق جزئياً"
    return "🔴 غير متطابق"


def count_important_keywords(text: Optional[str]) -> int:
    """حساب الكلمات المفتاحية المهمة الموجودة في النص المطابق."""
    normalized = clean_text(text or "")
    return sum(1 for keyword in IMPORTANT_KEYWORDS if keyword in normalized)


def calculate_keyword_fallback_score(input_text: str, output_text: str) -> float:
    """
    تقييم احتياطي بسيط عند فشل النموذج في إرجاع JSON صحيح.
    لا يعتمد على 50 كقيمة افتراضية، بل يحسب درجة تقريبية من تغطية الكلمات والأقسام المهمة.
    """
    source = clean_text(input_text)
    output = clean_text(output_text)

    if not source or not output:
        return 0.0

    section_keywords = [
        "مقدمة", "فهم عام", "نطاق العمل", "الشروط الخاصة", "منهجية",
        "خطة العمل", "جدول زمني", "مخرجات", "تسليمات", "دعم فني",
        "ضمان", "امتثال", "تقارير", "تدريب", "اختبار", "إدارة المخاطر",
    ]

    required_keywords = [kw for kw in section_keywords if kw in source]
    if not required_keywords:
        required_keywords = section_keywords

    found = sum(1 for kw in required_keywords if kw in output)
    keyword_ratio = found / max(len(required_keywords), 1)

    # عامل الطول يمنع النص القصير جداً من أخذ درجة مرتفعة.
    source_words = len(source.split())
    output_words = len(output.split())
    length_ratio = min(1.0, output_words / max(source_words * 0.35, 1))

    score = (keyword_ratio * 0.75 + length_ratio * 0.25) * 100
    return round(max(0, min(100, score)), 2)


def extract_json(text: str) -> Dict[str, Any]:
    """استخراج JSON من رد النموذج"""
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass

    return {}


def extract_requirements_with_ai(
    client: Any,
    model_name: str,
    text: str,
) -> List[Requirement]:
    """
    استخراج المتطلبات من النص باستخدام Gemini
    وتصنيفها حسب الأقسام الرئيسية
    """
    
    max_chars = 15000
    text_for_analysis = clean_text(text[:max_chars])
    
    extraction_prompt = f"""أنت خبير في تحليل المتطلبات.

مهمتك استخراج جميع المتطلبات من النص التالي وتصنيفها إلى الأقسام التالية:
- scope: نطاق العمل والخدمات المطلوبة
- methodology: المنهجية والطريقة المتبعة
- timeline: الجدول الزمني والمراحل
- deliverables: المخرجات والتسليمات
- resources: الموارد والكفاءات المطلوبة
- support: الدعم والضمان والصيانة
- compliance: الامتثال والشروط القانونية

أعد النتيجة بصيغة JSON فقط:

{{
  "requirements": [
    {{"text": "نص المتطلب", "category": "scope", "importance": "high"}},
    ...
  ]
}}

النص:
{text_for_analysis}
"""
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=extraction_prompt,
            config={
                "temperature": 0.2,
                "max_output_tokens": 2000,
            },
        )
        
        response_text = (response.text or "").strip()
        data = extract_json(response_text)
        
        requirements = []
        for req_data in data.get("requirements", []):
            try:
                category = RequirementCategory(req_data.get("category", "scope"))
                requirement = Requirement(
                    text=req_data.get("text", ""),
                    category=category,
                    importance=req_data.get("importance", "high"),
                )
                if requirement.text.strip():
                    requirements.append(requirement)
            except (ValueError, KeyError):
                continue
        
        return requirements
    
    except Exception as e:
        print(f"Error extracting requirements: {e}")
        return []


def find_matching_segments_in_output(
    requirement: Requirement,
    output_text: str,
    embedder: Any,
    similarity_threshold: float = SIMILARITY_THRESHOLDS["medium"],
) -> Optional[Tuple[str, float]]:
    """
    البحث عن أجزاء النص التي تطابق المتطلب
    باستخدام التشابه الدلالي
    """
    
    chunks = segment_text_into_chunks(output_text, chunk_size=300)
    if not chunks:
        return None
    
    try:
        # تحويل المتطلب إلى embedding
        req_embedding = embedder.encode(requirement.text, normalize_embeddings=True)
        
        best_match = None
        best_score = 0.0
        
        # البحث عن أفضل تطابق
        for chunk in chunks:
            chunk_embedding = embedder.encode(chunk, normalize_embeddings=True)
            
            # حساب التشابه الكوسيني
            similarity = float(
                (req_embedding @ chunk_embedding.T).item()
                if hasattr(req_embedding @ chunk_embedding.T, 'item')
                else (req_embedding @ chunk_embedding.T)
            )
            
            if similarity > best_score:
                best_score = similarity
                best_match = chunk
        
        if best_score >= similarity_threshold and best_match:
            return best_match, best_score
        
        return None
    
    except Exception as e:
        print(f"Error in semantic search: {e}")
        return None


def search_requirement_in_qdrant(
    requirement: Requirement,
    qdrant_client: Any,
    embedder: Any,
    collection_name: str = "inspira_chunks_v1",
    limit: int = 3,
    score_threshold: float = SIMILARITY_THRESHOLDS["low"],
) -> List[Tuple[str, float]]:
    """
    البحث عن المتطلب في مكتبة Qdrant
    للحصول على سياق إضافي وتحسين المطابقة
    """
    
    try:
        req_embedding = embedder.encode(requirement.text, normalize_embeddings=True)
        
        if hasattr(qdrant_client, "search"):
            search_result = qdrant_client.search(
                collection_name=collection_name,
                query_vector=req_embedding.tolist() if hasattr(req_embedding, "tolist") else req_embedding,
                limit=limit,
                score_threshold=score_threshold,
            )
        else:
            # توافق مع الإصدارات الجديدة من qdrant-client التي تستخدم query_points
            response = qdrant_client.query_points(
                collection_name=collection_name,
                query=req_embedding.tolist() if hasattr(req_embedding, "tolist") else req_embedding,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            )
            search_result = response.points
        
        matches = []
        for point in search_result:
            if hasattr(point, 'payload') and 'text' in point.payload:
                matches.append((point.payload['text'], point.score))
        
        return matches
    
    except Exception as e:
        print(f"Error searching in Qdrant: {e}")
        return []


def calculate_compliance_score_advanced(
    client: Any,
    embedder: Any,
    qdrant_client: Any,
    model_name: str,
    input_text: str,
    output_text: str,
    use_qdrant: bool = True,
    collection_name: str = "inspira_chunks_v1",
) -> Dict[str, Any]:
    """
    حساب نسبة الامتثال المتقدمة:
    
    1. استخراج المتطلبات من النص المصدر وتصنيفها
    2. البحث الدلالي عن تطابقات في العرض الفني و/أو Qdrant
    3. حساب نسبة التطابق لكل قسم
    4. حساب النسبة النهائية مع الأوزان
    """
    
    try:
        # الخطوة 1: استخراج المتطلبات
        requirements = extract_requirements_with_ai(
            client=client,
            model_name=model_name,
            text=input_text,
        )
        
        if not requirements:
            return {
                "score": 0.0,
                "compliance_level": get_compliance_level(0.0),
                "category_scores": {},
                "segments": [],
                "error": "Failed to extract requirements",
            }
        
        # الخطوة 2: تصنيف المتطلبات حسب الفئات
        requirements_by_category: Dict[RequirementCategory, List[Requirement]] = {}
        for category in RequirementCategory:
            requirements_by_category[category] = [
                r for r in requirements if r.category == category
            ]
        
        # الخطوة 3: البحث عن التطابقات
        matches_by_category: Dict[RequirementCategory, List[RequirementMatch]] = {}
        
        for category, reqs in requirements_by_category.items():
            matches = []
            
            for requirement in reqs:
                match = RequirementMatch(requirement=requirement)
                
                # البحث في العرض الفني
                result = find_matching_segments_in_output(
                    requirement=requirement,
                    output_text=output_text,
                    embedder=embedder,
                    similarity_threshold=SIMILARITY_THRESHOLDS["low"],
                )
                
                if result:
                    match.matched_text, match.similarity_score = result
                    
                    # تحديد مستوى التطابق الحقيقي
                    if match.similarity_score >= SIMILARITY_THRESHOLDS["high"]:
                        match.is_covered = True

                    elif match.similarity_score >= SIMILARITY_THRESHOLDS["medium"]:
                        match.is_covered = True

                    elif match.similarity_score >= SIMILARITY_THRESHOLDS["partial"]:
                        # التشابه الجزئي لا يكفي وحده؛ نقبله فقط إذا ظهرت كلمات مهمة
                        # حتى لا تثبت النتيجة دائماً حول 50/100.
                        matched_keywords = count_important_keywords(match.matched_text)
                        if matched_keywords >= 2:
                            match.is_covered = True
                            match.similarity_score = min(1.0, match.similarity_score + 0.08)
                else:
                    # البحث في Qdrant إذا كان متاحاً
                    if use_qdrant:
                        qdrant_matches = search_requirement_in_qdrant(
                            requirement=requirement,
                            qdrant_client=qdrant_client,
                            embedder=embedder,
                            collection_name=collection_name,
                            score_threshold=SIMILARITY_THRESHOLDS["medium"],
                        )
                        
                        if qdrant_matches:
                            best_match_text, best_score = qdrant_matches[0]
                            match.matched_text = best_match_text
                            match.similarity_score = best_score
                            # التطابق من Qdrant سياق مساعد فقط، ولا نعتبره امتثالاً إلا إذا كان قوياً
                            # أو كان معه كلمات مفتاحية كافية.
                            if best_score >= SIMILARITY_THRESHOLDS["high"]:
                                match.is_covered = True
                            elif best_score >= SIMILARITY_THRESHOLDS["medium"]:
                                matched_keywords = count_important_keywords(best_match_text)
                                if matched_keywords >= 2:
                                    match.is_covered = True
                                    match.similarity_score = min(1.0, match.similarity_score + 0.05)
                
                matches.append(match)
            
            matches_by_category[category] = matches
        
        # الخطوة 4: حساب نسب الامتثال لكل قسم
        category_scores: Dict[str, float] = {}
        
        for category in RequirementCategory:
            matches = matches_by_category.get(category, [])
            
            if not matches:
                category_scores[category.value] = 0.0
                continue
            
            # حساب النسبة المئوية للمتطلبات المغطاة
            covered_count = sum(1 for m in matches if m.is_covered)
            avg_similarity = sum(
                m.similarity_score for m in matches if m.similarity_score > 0
            ) / max(len([m for m in matches if m.similarity_score > 0]), 1)
            
            # النسبة تعتمد أكثر على التغطية الفعلية، وأقل على التشابه الدلالي الخام.
            # هذا يمنع ظهور نتيجة "متوسطة" دائماً عند وجود تشابه لغوي فقط.
            coverage_ratio = covered_count / len(matches)
            quality_ratio = max(0, min(1, avg_similarity))

            category_score = (coverage_ratio * 0.75 + quality_ratio * 0.25) * 100
            category_scores[category.value] = max(0, min(100, category_score))
        
        # Bonus بسيط للعرض المنظم والمتكامل
        bonus = 0
        if category_scores.get("methodology", 0) >= 70:
            bonus += 3
        if category_scores.get("deliverables", 0) >= 70:
            bonus += 3
        if category_scores.get("timeline", 0) >= 70:
            bonus += 2
        if category_scores.get("compliance", 0) >= 70:
            bonus += 2

        # الخطوة 5: حساب النسبة النهائية مع الأوزان
        final_score = (
            sum(
                category_scores[cat.value] * CATEGORY_WEIGHTS[cat]
                for cat in RequirementCategory
            )
            + bonus
        )
        final_score = max(0, min(100, final_score))
        compliance_level = get_compliance_level(final_score)
        
        # الخطوة 6: إنشاء التقرير المفصل
        segments = []
        
        for category in RequirementCategory:
            category_matches = matches_by_category.get(category, [])
            
            covered = [m for m in category_matches if m.is_covered]
            uncovered = [m for m in category_matches if not m.is_covered]
            
            segment = {
                "category": category.value,
                "score": category_scores.get(category.value, 0.0),
                "weight": CATEGORY_WEIGHTS[category] * 100,
                "total_requirements": len(category_matches),
                "covered_requirements": len(covered),
                "coverage_percentage": (
                    len(covered) / len(category_matches) * 100
                    if category_matches else 0
                ),
                "covered": [
                    {
                        "requirement": m.requirement.text,
                        "matched_text": m.matched_text[:200] if m.matched_text else None,
                        "similarity": round(m.similarity_score, 3),
                    }
                    for m in covered[:3]  # أفضل 3 تطابقات
                ],
                "uncovered": [
                    {
                        "requirement": m.requirement.text,
                        "importance": m.requirement.importance,
                    }
                    for m in uncovered[:3]  # أول 3 غير مغطاة
                ],
            }
            
            segments.append(segment)
        
        return {
            "score": round(final_score, 2),
            "compliance_level": compliance_level,
            "category_scores": {
                cat: round(score, 2)
                for cat, score in category_scores.items()
            },
            "segments": segments,
            "error": None,
        }
    
    except Exception as e:
        import traceback
        print(f"Error in calculate_compliance_score_advanced: {traceback.format_exc()}")
        return {
            "score": 0.0,
            "compliance_level": get_compliance_level(0.0),
            "category_scores": {},
            "segments": [],
            "error": str(e),
        }


def calculate_compliance_score(
    client: Any,
    model_name: str,
    input_text: str,
    output_text: str,
    embedder: Any = None,
    qdrant_client: Any = None,
    use_advanced: bool = False,
    collection_name: str = "inspira_chunks_v1",
) -> Dict[str, Any]:
    """
    حساب نسبة الامتثال (بسيطة أو متقدمة)
    
    إذا كان use_advanced=True والـ embedder و qdrant_client متاحين،
    سيتم استخدام الطريقة المتقدمة مع الـ Embeddings والبحث الدلالي.
    وإلا سيتم استخدام الطريقة البسيطة.
    """
    
    # استخدام الطريقة المتقدمة إذا كانت جميع المتطلبات متاحة
    if use_advanced and embedder is not None and qdrant_client is not None:
        return calculate_compliance_score_advanced(
            client=client,
            embedder=embedder,
            qdrant_client=qdrant_client,
            model_name=model_name,
            input_text=input_text,
            output_text=output_text,
            use_qdrant=True,
            collection_name=collection_name,
        )
    
    # الطريقة البسيطة (التوافقية)
    max_chars = 12000

    input_for_analysis = clean_text(input_text[:max_chars])
    output_for_analysis = clean_text(output_text[:max_chars])

    compliance_prompt = f"""
أنت محلل امتثال للعروض الفنية والمنافسات.

مهمتك تقييم مدى امتثال "العرض الفني" لمتطلبات "الكراسة أو RFP".

قيّم بناءً على:
1. تغطية المتطلبات الأساسية.
2. تغطية الشروط الخاصة.
3. تغطية نطاق العمل.
4. وجود منهجية تنفيذ واضحة.
5. وجود مخرجات وتسليمات.
6. وجود خطة زمنية.
7. وجود دعم فني أو ضمان إذا كان مطلوباً.
8. جودة ووضوح العرض.

مهم:
- لا تعتمد على التطابق الحرفي فقط.
- اقبل الصياغات المختلفة إذا كانت تحمل نفس المعنى.
- لا تعطِ درجة عالية إذا كان الكلام عاماً وغير مفصل.
- لا تعطِ درجة منخفضة إذا كان المعنى موجوداً لكن بصياغة مختلفة.

أعد النتيجة بصيغة JSON فقط بهذا الشكل، بدون أي نص قبل أو بعد JSON:

{{
  "score": 0,
  "matched_items": [],
  "missing_items": [],
  "weak_items": [],
  "reason": ""
}}

إرشاد الدرجات:
- 85 إلى 100: العرض يغطي أغلب المتطلبات بتفصيل واضح.
- 70 إلى 84: العرض جيد مع نواقص بسيطة.
- 50 إلى 69: العرض جزئي أو عام ويحتاج تحسين.
- أقل من 50: العرض ضعيف أو لا يغطي المتطلبات الأساسية.

النص المصدر:
{input_for_analysis}

---

العرض الفني:
{output_for_analysis}
"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=compliance_prompt,
            config={
                "temperature": 0.1,
                "max_output_tokens": 1000,
            },
        )

        response_text = (response.text or "").strip()
        data = extract_json(response_text)

        if not data:
            fallback_score = calculate_keyword_fallback_score(input_for_analysis, output_for_analysis)
            return {
                "score": fallback_score,
                "compliance_level": get_compliance_level(fallback_score),
                "category_scores": {},
                "segments": [
                    {
                        "type": "reason",
                        "text": "تم استخدام تقييم احتياطي لأن رد النموذج لم يكن JSON صالحاً.",
                    }
                ],
                "error": f"Could not parse JSON from response: {response_text[:100]}",
            }

        score = float(data.get("score", 0))
        score = max(0, min(100, score))

        # إذا رجع النموذج 50 بدون تفاصيل، غالباً هذا تقييم عام غير دقيق.
        # نستخدم التقييم الاحتياطي حتى لا تثبت النتيجة على 50.
        if (
            score == 50
            and not data.get("matched_items")
            and not data.get("missing_items")
            and not data.get("weak_items")
        ):
            score = calculate_keyword_fallback_score(input_for_analysis, output_for_analysis)

        segments = [
            {
                "type": "matched",
                "items": data.get("matched_items", []),
            },
            {
                "type": "missing",
                "items": data.get("missing_items", []),
            },
            {
                "type": "weak",
                "items": data.get("weak_items", []),
            },
            {
                "type": "reason",
                "text": data.get("reason", ""),
            },
        ]

        return {
            "score": score,
            "compliance_level": get_compliance_level(score),
            "category_scores": {},
            "segments": segments,
            "error": None,
        }

    except Exception as e:
        return {
            "score": 0.0,
            "compliance_level": get_compliance_level(0.0),
            "category_scores": {},
            "segments": [],
            "error": str(e),
        }