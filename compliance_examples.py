"""
أمثلة عملية لاستخدام نظام حساب نسبة الامتثال المتقدم
"""

# ===========================
# المثال 1: استخراج المتطلبات
# ===========================

from Backend.compliance import (
    extract_requirements_with_ai,
    RequirementCategory,
)
from google import genai

# تهيئة الـ client
client = genai.Client(api_key="YOUR_GEMINI_KEY")

rfp_text = """
مشروع تطوير نظام إدارة الموارد البشرية

المتطلبات:
1. نطاق العمل: تطوير نظام متكامل لإدارة الموظفين والرواتب والإجازات
2. المنهجية: استخدام Agile مع تقسيم المشروع إلى 4 sprints
3. الجدول الزمني: 4 أشهر من البدء إلى الإطلاق
4. المخرجات: نظام ويب كامل + تطبيق جوال + تقارير شاملة
5. الدعم: ضمان سنة واحدة مع دعم فني 24/7
"""

requirements = extract_requirements_with_ai(
    client=client,
    model_name="gemini-2.5-pro",
    text=rfp_text,
)

print("=" * 60)
print("المتطلبات المستخرجة:")
print("=" * 60)

for req in requirements:
    print(f"\n📌 [{req.category.value.upper()}] ({req.importance})")
    print(f"   {req.text}")

# ===========================
# المثال 2: حساب نسبة الامتثال
# ===========================

from Backend.compliance import calculate_compliance_score
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import json

# تهيئة المكونات
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
qdrant = QdrantClient(url="http://localhost:6333")

source_text = rfp_text

technical_offer = """
عرض فني لمشروع نظام إدارة الموارد البشرية

1. فهمنا للمشروع:
نحن نفهم أن المشروع يتطلب نظاماً شاملاً يدير جميع جوانب الموارد البشرية بما في ذلك
إدارة الموظفين، الرواتب، الإجازات، والتقارير.

2. نطاق العمل الذي سنوفره:
- نظام إدارة الموظفين: إنشاء، تعديل، حذف الموظفين، إدارة البيانات الشخصية
- نظام الرواتب: حساب الرواتب، الخصومات، الإقرارات الضريبية
- إدارة الإجازات: طلبات الإجازات، الموافقات، التقارير
- التقارير: تقارير شاملة عن الموظفين والرواتب والإجازات

3. منهجية التنفيذ:
سنستخدم منهجية Agile مع تقسيم العمل إلى مراحل:
- المرحلة 1: تحليل وتصميم النظام (4 أسابيع)
- المرحلة 2: تطوير Backend والقاعدة (4 أسابيع)
- المرحلة 3: تطوير Frontend والتطبيق الجوال (4 أسابيع)
- المرحلة 4: الاختبار والنشر (4 أسابيع)

4. الجدول الزمني:
الإجمالي: 4 أشهر (16 أسبوع)
البدء: الشهر الجاري
الانتهاء: بعد 4 أشهر

5. المخرجات والتسليمات:
- نظام ويب كامل مع لوحة تحكم
- تطبيق جوال iOS و Android
- وثائق شاملة
- دليل المستخدم
- تقارير شاملة

6. الدعم والصيانة:
- ضمان سنة واحدة من تاريخ الإطلاق
- دعم فني متاح خلال ساعات العمل (8-5)
- صيانة دورية شهرية
"""

# الطريقة المتقدمة
result = calculate_compliance_score(
    client=client,
    model_name="gemini-2.5-pro",
    input_text=source_text,
    output_text=technical_offer,
    embedder=embedder,
    qdrant_client=qdrant,
    use_advanced=True,
)

print("\n" + "=" * 60)
print("نتائج نسبة الامتثال:")
print("=" * 60)

print(f"\n🎯 النسبة النهائية: {result['score']}/100")
print(f"\n📊 نسب الأقسام:")
print("-" * 40)

category_labels = {
    "scope": "نطاق العمل",
    "methodology": "المنهجية",
    "timeline": "الجدول الزمني",
    "deliverables": "المخرجات",
    "resources": "الموارد",
    "support": "الدعم",
    "compliance": "الامتثال",
}

for category, score in result['category_scores'].items():
    label = category_labels.get(category, category)
    bar = "█" * int(score // 10) + "░" * (10 - int(score // 10))
    print(f"  {label:15} {bar} {score:5.1f}%")

# طباعة التفاصيل
print(f"\n📋 تفاصيل كل قسم:")
print("-" * 40)

for segment in result['segments']:
    if segment['coverage_percentage'] > 0:  # اطبع فقط الأقسام التي بها متطلبات
        print(f"\n[{segment['category'].upper()}]")
        print(f"  درجة: {segment['score']:.1f} (وزن: {segment['weight']:.0f}%)")
        print(f"  التغطية: {segment['covered_requirements']}/{segment['total_requirements']} ({segment['coverage_percentage']:.0f}%)")
        
        if segment['covered']:
            print(f"  ✅ متطلبات مغطاة:")
            for match in segment['covered'][:2]:
                similarity = match['similarity']
                print(f"     - {match['requirement'][:50]}... (تشابه: {similarity:.2f})")
        
        if segment['uncovered']:
            print(f"  ❌ متطلبات ناقصة:")
            for missing in segment['uncovered'][:2]:
                print(f"     - {missing['requirement'][:50]}...")

# ===========================
# المثال 3: مقارنة عدة عروض
# ===========================

print("\n" + "=" * 60)
print("المثال 3: مقارنة عدة عروض فنية")
print("=" * 60)

offers = [
    {
        "name": "العرض الأول",
        "text": "نحن سنوفر النظام الكامل مع جميع المتطلبات..."
    },
    {
        "name": "العرض الثاني",
        "text": "عرفنا على المشروع، سنطور النظام بنجاح..."
    },
]

results_comparison = []

for offer in offers:
    result = calculate_compliance_score(
        client=client,
        model_name="gemini-2.5-pro",
        input_text=source_text,
        output_text=offer['text'],
        embedder=embedder,
        qdrant_client=qdrant,
        use_advanced=True,
    )
    
    results_comparison.append({
        "name": offer['name'],
        "score": result['score'],
        "category_scores": result['category_scores'],
    })

# ترتيب الأفضل فالأسوأ
results_comparison.sort(key=lambda x: x['score'], reverse=True)

print("\n🏆 ترتيب العروض حسب الامتثال:")
for rank, result in enumerate(results_comparison, 1):
    print(f"{rank}. {result['name']}: {result['score']:.1f}/100")

# ===========================
# المثال 4: تحليل نقاط الضعف
# ===========================

print("\n" + "=" * 60)
print("المثال 4: تحليل نقاط الضعف")
print("=" * 60)

result = calculate_compliance_score(
    client=client,
    model_name="gemini-2.5-pro",
    input_text=source_text,
    output_text=technical_offer,
    embedder=embedder,
    qdrant_client=qdrant,
    use_advanced=True,
)

# إيجاد أضعف الأقسام
weak_categories = sorted(
    result['category_scores'].items(),
    key=lambda x: x[1]
)[:3]

print("\n⚠️  أضعف 3 أقسام:")
for category, score in weak_categories:
    print(f"\n📌 {category.upper()}: {score:.1f}%")
    
    # البحث عن هذا القسم في segments
    for segment in result['segments']:
        if segment['category'] == category:
            print(f"   المتطلبات الناقصة:")
            for missing in segment.get('uncovered', []):
                print(f"   - {missing['requirement']}")

# ===========================
# المثال 5: صيغة JSON للعرض
# ===========================

print("\n" + "=" * 60)
print("المثال 5: صيغة JSON الكاملة للنتيجة")
print("=" * 60)

print(json.dumps(result, indent=2, ensure_ascii=False))
