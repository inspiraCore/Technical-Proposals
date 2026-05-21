# main.py
import os
import re
import traceback
from datetime import date
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict, AliasChoices

from google import genai

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from sentence_transformers import SentenceTransformer

try:
    from Backend.compliance import ComplianceRequest, ComplianceResponse, calculate_compliance_score
except ImportError:
    from compliance import ComplianceRequest, ComplianceResponse, calculate_compliance_score

# =========================
# Env + Init
# =========================
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION = os.getenv("QDRANT_COLLECTION", "inspira_chunks_v1")

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY / GEMINI_API_KEY in environment variables.")

# ✅ Gemini 2.5 Pro - أفضل model للمخرجات الطويلة
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
print("GEMINI_MODEL =", GEMINI_MODEL)

# Clients
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
embedder = SentenceTransformer(EMBED_MODEL_NAME)
client = genai.Client(api_key=GEMINI_API_KEY)


def embed(text: str) -> List[float]:
    return embedder.encode(text, normalize_embeddings=True).tolist()


def qdrant_search(
    collection_name: str,
    query_vector: List[float],
    query_filter: Optional[qm.Filter] = None,
    limit: int = 8,
    score_threshold: Optional[float] = None,
    with_payload: bool = True,
):
    """Search Qdrant by vector using the installed qdrant-client API."""
    if hasattr(qdrant, "search"):
        return qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=with_payload,
        )

    search_request = qm.SearchRequest(
        vector=query_vector,
        filter=query_filter,
        limit=limit,
        score_threshold=score_threshold,
        with_payload=with_payload,
    )

    response = qdrant._client.rest.search_api.search_points(
        collection_name=collection_name,
        search_request=search_request,
    )

    return response.result or []


# =========================
# ✅ Structure - 7 أقسام (نفس الكود الحالي)
# =========================
TECH_OFFER_STRUCTURE = [
    {"key": "intro",       "title": "1) مقدمة وفهم عام للمشروع",          "required": True},
    {"key": "scope",       "title": "2) فهم نطاق العمل والمتطلبات",        "required": True},
    {"key": "methodology", "title": "3) منهجية التنفيذ وآلية العمل",       "required": True},
    {"key": "timeline",    "title": "4) خطة العمل والجدول الزمني",          "required": True},
    {"key": "deliverables","title": "5) المخرجات والتسليمات",              "required": True},
    {"key": "assumptions", "title": "6) الافتراضات والقيود",               "required": False},
    {"key": "compliance",  "title": "7) الالتزام والمتطلبات النظامية",     "required": True},
]


# =========================
# ✅ System Prompt - محسّن لمنع "يتطلب تأكيد"
# =========================
SYSTEM_PROMPT_FINAL = """
أنت كاتب عروض فنية حكومية سعودية (Technical Proposal) بصياغة رسمية مهنية احترافية.

## مصادر المعلومات (مصنّفة بوضوح):
1) RFP_EVIDENCE (مصدر حقائق):
   - مقتطفات من كراسة المنافسة/طلب تقديم العروض.
   - يُسمح لك باستخلاص الحقائق والمتطلبات منه فقط.

2) USER_INPUTS (مصدر حقائق إضافي):
   - نطاق عمل وشروط خاصة أدخلها المستخدم.
   - تعتبر حقائق ما لم تتعارض مع RFP_EVIDENCE.

3) TP_STYLE (أسلوب فقط وليس حقائق):
   - مقتطفات من عروض فنية سابقة.
   - يُستخدم فقط لتقليد النبرة وطريقة العرض، وممنوع استخراج متطلبات/أرقام/أسماء/تفاصيل منه.

## قواعد صارمة (غير قابلة للتجاوز):
1) ممنوع جمل الترحيب والافتتاحيات:
   - ممنوع تماماً: "بسم الله الرحمن الرحيم"، "الحمد لله"، "شكراً"، "مرحباً"، "تشرفنا"، "يسعدنا"
   - ابدأ مباشرة بالعنوان الأول من TECH_OFFER_STRUCTURE
   - اكتب المحتوى الفني مباشرة بدون تمهيدات أو جمل ترحيب

2) ممنوع النسخ:
   - لا تنقل جملًا أو فقرات أو أرقامًا أو أسماء من RFP_EVIDENCE أو TP_STYLE حرفيًا.
   - أعد الصياغة دائمًا بأسلوب جديد.

3) ⚠️ قاعدة "يتطلب تأكيد" (مُحدثة):
   - استخدم "يتطلب تأكيد:" فقط إذا كانت المعلومة:
     * أساسية وحرجة للتنفيذ
     * غير موجودة نهائياً في RFP_EVIDENCE أو USER_INPUTS
     * تؤثر بشكل مباشر على نجاح المشروع
   - في الحالات الأخرى: اكتب بأسلوب عام احترافي قابل للتطبيق بناءً على أفضل الممارسات
   - مثال جيد: "سيتم تطوير المنصة باستخدام تقنيات حديثة ومتوافقة مع معايير الأمن السيبراني السعودية"
   - مثال سيء: "يتطلب تأكيد: التقنية المستخدمة"

4) الالتزام بالهيكل:
   - التزم حرفيًا بالعناوين وترتيبها كما في TECH_OFFER_STRUCTURE.

5) الكتابة التنفيذية:
   - اكتب بأسلوب تنفيذي (كيف ننفّذ) وليس إنشائي
   - استخدم أمثلة واقعية من المشاريع الحكومية السعودية
   - أضف جداول وقوائم نقطية وخطوات تنفيذية واضحة

اكتب الناتج بصيغة Markdown احترافية.
""".strip()


# =========================
# ✅ Activity/Competition prompts
# =========================
ACTIVITY_PROMPTS = {
    "استشارات": """
[توجيهات نشاط المنافسة: استشارات]
- اكتب بمنهجية استشارية تنفيذية: تشخيص → تحليل فجوات → توصيات → خارطة طريق → تمكين.
- ركّز على ورش العمل، المقابلات، تحليل الوثائق، والتقارير التنفيذية.
""".strip(),
    "تطوير": """
[توجيهات نشاط المنافسة: تطوير]
- اكتب بمنهجية هندسية: تحليل متطلبات → تصميم → تطوير → اختبار → إطلاق → دعم.
- ركّز على الأمن السيبراني، الاختبارات، وإدارة الإصدارات والتوثيق.
""".strip(),
    "تصميم": """
[توجيهات نشاط المنافسة: تصميم]
- اكتب بمنهجية تصميم: بحث → متطلبات → نماذج أولية → تصميم واجهات → تسليم أصول.
- ركّز على الاتساق، سهولة الاستخدام، وRTL.
""".strip(),
    "تسويق": """
[توجيهات نشاط المنافسة: تسويق]
- اكتب بمنهجية حملات: استراتيجية → محتوى → قنوات → إعلانات → تحسين → تقارير.
- ركّز على KPIs والقياس والتحسين المستمر.
""".strip(),
    "إدارة مشاريع": """
[توجيهات نشاط المنافسة: إدارة مشاريع]
- اكتب بمنهجية PMO: خطة مشروع → حوكمة → تقارير → مخاطر → أصحاب مصلحة.
""".strip(),
    "توريد": """
[توجيهات نشاط المنافسة: توريد]
- اكتب بمنهجية توريد: مواصفات → توريد → تركيب/تسليم → اختبار قبول → ضمان.
""".strip(),
}

COMPETITION_PROMPTS = {
    "منافسة عامة": """
[توجيهات نوع المنافسة: منافسة عامة]
- أظهر الامتثال والحوكمة والتميّز التشغيلي بشكل واضح.
""".strip(),
    "منافسة محدودة": """
[توجيهات نوع المنافسة: منافسة محدودة]
- اكتب بشكل مركز ومباشر واظهر جاهزية التنفيذ وتقليل المخاطر.
""".strip(),
    "منافسة على مرحلتين": """
[توجيهات نوع المنافسة: منافسة على مرحلتين]
- وضّح مخرجات المرحلة الأولى ثم الثانية وآلية الانتقال بينهما.
""".strip(),
    "اتفاقية إطار": """
[توجيهات نوع المنافسة: اتفاقية إطار]
- ركّز على نموذج تشغيل قياسي وتفعيل أوامر العمل والتقارير.
""".strip(),
    "شراء مباشر / تعميد": """
[توجيهات نوع المنافسة: شراء مباشر/تعميد]
- اكتب بخطة بدء سريعة ووضوح عالي في التسليمات والحوكمة.
""".strip(),
}

def selection_guidance(activity: str, competition_type: str) -> str:
    a = (ACTIVITY_PROMPTS.get(activity or "", "") or "").strip()
    c = (COMPETITION_PROMPTS.get(competition_type or "", "") or "").strip()
    return "\n\n".join([x for x in [c, a] if x]).strip()


# =========================
# ✅ TP Style retrieval - محسّن
# =========================
def retrieve_tp_style(top_k: int = 18, max_chars_total: int = 9000) -> str:
    """استرجاع أسلوب الكتابة من العروض الفنية السابقة"""
    query = "أسلوب كتابة عرض فني حكومي مقدمة فهم نطاق العمل منهجية التنفيذ المخرجات الحوكمة"
    vec = embed(query)

    hits = qdrant_search(
        collection_name=COLLECTION,
        query_vector=vec,
        query_filter=qm.Filter(
            must=[qm.FieldCondition(key="doc_type", match=qm.MatchValue(value="tp"))]
        ),
        limit=top_k,
        with_payload=True,
    )

    style_blocks = []
    seen = set()
    total = 0

    for h in hits:
        txt = (h.payload.get("text", "") or "").strip()
        if not txt:
            continue
        key = txt[:160]
        if key in seen:
            continue
        seen.add(key)

        chunk = txt[:1200]
        if total + len(chunk) > max_chars_total:
            break

        style_blocks.append(chunk)
        total += len(chunk)

    return "\n\n---\n\n".join(style_blocks)


# =========================
# ✅ RFP evidence builder
# =========================
def generate_rfp_evidence(
    pair_id: int,
    project_title: str,
    structure: List[Dict[str, Any]],
    scope_text: str = "",
    timeline_text: str = "",
    special_terms: str = "",
    top_k: int = 8,
    min_score: float = 0.35,
) -> str:
    """استرجاع الأدلة من RFP مع مدخلات المستخدم"""
    
    DEFAULT_INTENTS = {
        "intro": "استخرج وصف المشروع وأهدافه وخلفيته وسبب تنفيذ المشروع.",
        "scope": "استخرج نطاق العمل: المهام والأنشطة والمتطلبات الفنية وما يجب تسليمه.",
        "methodology": "استخرج متطلبات طريقة التنفيذ أو إدارة المشروع أو مراحل العمل أو التقارير.",
        "timeline": "استخرج المدة والجدول الزمني والمراحل ومتطلبات التسليم الزمنية.",
        "deliverables": "استخرج قائمة المخرجات: وثائق وتقارير وتسليمات ومعايير الاستلام.",
        "assumptions": "استخرج أي افتراضات أو قيود أو شروط تؤثر على التنفيذ.",
        "compliance": "استخرج الالتزامات النظامية أو شروط امتثال أو معايير يجب الالتزام بها."
    }

    def _retrieve(key: str):
        query = f"{project_title}\n{DEFAULT_INTENTS.get(key, '')}"
        vec = embed(query)
        
        flt = qm.Filter(
            must=[
                qm.FieldCondition(key="pair_id", match=qm.MatchValue(value=pair_id)),
                qm.FieldCondition(key="doc_type", match=qm.MatchValue(value="rfp")),
            ]
        )
        
        hits = qdrant_search(
            
            collection_name=COLLECTION,
            query_vector=vec,
            query_filter=flt,
            limit=top_k,
            score_threshold=min_score,
            with_payload=True,
        )
        print(f"[QDRANT] section={key} | retrieved_chunks={len(hits)}")
        chunks = []
        for h in hits:
            txt = (h.payload.get("text", "") or "").strip()
            if txt:
                chunks.append(f"- {txt}")
        
        return "\n".join(chunks) if chunks else "(لم يتم العثور على معلومات كافية)"

    md = []
    md.append("## RFP_EVIDENCE + USER_INPUTS\n")
    md.append(f"المشروع: {project_title}\n")
    
    # إضافة مدخلات المستخدم في البداية
    if scope_text.strip():
        md.append(f"\n### نطاق العمل (من المستخدم):\n{scope_text}\n")
    if timeline_text.strip():
        md.append(f"\n### الجدول الزمني (من المستخدم):\n{timeline_text}\n")
    if special_terms.strip():
        md.append(f"\n### الشروط الخاصة (من المستخدم):\n{special_terms}\n")

    # استرجاع من RFP
    for sec in structure:
        key = sec["key"]
        title = sec["title"]
        evidence = _retrieve(key)
        md.append(f"\n### {title}\n{evidence}\n")

    return "\n".join(md).strip()


# =========================
# ✅ FastAPI schemas
# =========================
class GenerateRequest(BaseModel):
    pair_id: int = Field(0, validation_alias=AliasChoices("pair_id", "pairId"))

    project_title: str = Field(
        ...,
        validation_alias=AliasChoices("project_title", "project_name", "projectName"),
    )

    project_activity: str = Field(
        "",
        validation_alias=AliasChoices("project_activity", "activity", "projectActivity"),
    )

    competition_type: str = Field(
        "",
        validation_alias=AliasChoices("competition_type", "competitionType"),
    )

    scope_text: str = Field(
        "",
        validation_alias=AliasChoices("scope_text", "scope_of_work", "workScope"),
    )

    special_terms: str = Field(
        "",
        validation_alias=AliasChoices("special_terms", "special_conditions", "specialConditions"),
    )

    timeline_text: str = Field(
        "",
        validation_alias=AliasChoices("timeline_text", "project_duration", "projectDuration"),
    )

    top_k: int = 8
    min_score: float = 0.35
    temperature: float = 0.15

    model_config = ConfigDict(extra="allow")


class GenerateResponse(BaseModel):
    model: str
    markdown: str
    words: int
    chars: int
    compliance_score: Optional[float] = None
    compliance_category_scores: Optional[Dict[str, float]] = None
    compliance_segments: Optional[List[Dict[str, Any]]] = None
    compliance_error: Optional[str] = None


# =========================
# ✅ FastAPI app
# =========================
app = FastAPI(title="InspiraCore API", version="2.0.0")

# ✅ CORS - للـ Vercel والـ local development
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {
        "ok": True, 
        "model": GEMINI_MODEL,
        "version": "2.0.0 - Optimized Single Call"
    }


@app.post("/api/generate-proposal", response_model=GenerateResponse)
@app.post("/api/generate-tech-offer", response_model=GenerateResponse)
def generate_proposal(req: GenerateRequest):
    """
    ✅ توليد العرض الفني - نسخة محسّنة
    - Single call بدل multiple calls
    - أسرع وأكثر اتساقاً
    - يقلل من "يتطلب تأكيد"
    """
    try:
        today_str = date.today().isoformat()

        # 1) استرجاع RFP evidence + مدخلات المستخدم
        rfp_evidence = generate_rfp_evidence(
            pair_id=req.pair_id,
            project_title=req.project_title,
            structure=TECH_OFFER_STRUCTURE,
            scope_text=req.scope_text,
            timeline_text=req.timeline_text,
            special_terms=req.special_terms,
            top_k=req.top_k,
            min_score=req.min_score,
        )

        # 2) استرجاع TP style
        tp_style = retrieve_tp_style(top_k=18, max_chars_total=9000)

        # 3) توجيهات النشاط ونوع المنافسة
        guidance = selection_guidance(req.project_activity, req.competition_type)

        # 4) بناء البرومبت الكامل
        structure_text = "\n".join([f"{s['title']}" for s in TECH_OFFER_STRUCTURE])

        prompt = f"""
{SYSTEM_PROMPT_FINAL}

[USER_INPUTS]
- اسم المشروع: {req.project_title}
- تاريخ التقديم: {today_str}
- نوع المنافسة: {req.competition_type or "غير محدد"}
- نشاط المنافسة: {req.project_activity or "غير محدد"}

[SELECTION_GUIDANCE]
{guidance}

[RFP_EVIDENCE]
{rfp_evidence}

[TECH_OFFER_STRUCTURE]
يجب أن يحتوي العرض على الأقسام التالية بنفس الترتيب:
{structure_text}

[TP_STYLE] (أسلوب فقط - ليس مصدر حقائق)
{tp_style}

---

قواعد الإنتاج النهائية:
- التزم حرفياً بعناوين TECH_OFFER_STRUCTURE وبنفس ترتيبها
- اكتب محتوى تنفيذي (كيف ننفّذ) وليس إنشائي
- استخدم المعلومات من RFP_EVIDENCE و USER_INPUTS فقط
- استخدم TP_STYLE للأسلوب فقط، ليس للحقائق
- قلّل استخدام "يتطلب تأكيد:" واكتب بأسلوب عام احترافي عند الإمكان
- كل قسم يجب أن يحتوي على: (الأعمال/الأنشطة) + (المخرجات) + (آلية التنفيذ)

الآن: اكتب العرض الفني كاملاً بصيغة Markdown احترافية.
""".strip()

        # 5) ✅ توليد واحد (Single Call)
        print(f"[{date.today()}] Generating proposal: {req.project_title[:50]}...")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={"temperature": req.temperature},
        )

        markdown = (getattr(response, "text", None) or "").strip()

        if not markdown or len(markdown) < 500:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate complete proposal. Please try again."
            )

        #  حساب نسبة الامتثال
        compliance_data = calculate_compliance_score(client, GEMINI_MODEL, rfp_evidence, markdown)
        
        return GenerateResponse(
            model=GEMINI_MODEL,
            markdown=markdown,
            words=len(markdown.split()),
            chars=len(markdown),
            compliance_score=compliance_data.get("score"),
            compliance_category_scores=compliance_data.get("category_scores", {}),
            compliance_segments=compliance_data.get("segments"),
            compliance_error=compliance_data.get("error"),
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating proposal: {str(e)}"
        )


@app.post("/api/compliance-score", response_model=ComplianceResponse)
def calculate_compliance(req: ComplianceRequest):
    """
    ✅ حساب نسبة الامتثال بين نص مصدر ونص مُخرَج
    
    التفاصيل:
    - يحسب نسبة المحتوى المأخوذ من المصدر في النص المُخرَج
    - يعيد JSON مع درجة (0-100) وتفاصيل الأجزاء
    """
    try:
        if not req.source_text.strip():
            raise HTTPException(
                status_code=400,
                detail="source_text cannot be empty"
            )
        if not req.output_text.strip():
            raise HTTPException(
                status_code=400,
                detail="output_text cannot be empty"
            )
        
        result = calculate_compliance_score(client, GEMINI_MODEL, req.source_text, req.output_text)
        return ComplianceResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return ComplianceResponse(
            score=0,
            category_scores={},
            segments=[],
            error=str(e)
        )
    
# =========================
#  Static data - Competitions + Terms
# =========================
COMPETITIONS_DATA = {
    "competitions": [
        {
            "name": "مشاركة في الدخل",
            "scope_of_work": "[في هذه الفقرة على الجهة الحكومية ذكر وبشكل تفصيلي المعلومات والبيانات الخاصة بالسلع والخدمات محل المشاركة في الدخل وتوضيح النطاق والتفاصيل التي يجب مراعاتها، كذلك يجب أن يتضمن هذا النطاق عملية التعاقد لتأمين السلع والخدمات بحيث تكون في أي مما يأتي: أ. منح حق انتفاع أو تأجيراً أو ترخيصاً لأصول حكومية إلى الشريك الخاص بغرض تمكينه من توفير السلع والخدمات التي يتم تأمينها للجهة الحكومية وذلك وفقاً لأحكام النظامية ذات العلاقة. ب. منح الشريك الخاص بعض الحقوق المعنوية الخاصة بالدولة والمترطبة بتقديم الخدمات العامة وفقاً للأحكام النظامية ذات العلاقة. كما يجب على الجهة الحكومية تضمين المعلومات والبيانات الخاصة بالسلع والخدمات المطروحة وفقاً لأحكام النظام واللوائح. ويجب ألا تتجاوز مدة العقد -المزمع إبرامه كنتيجة لهذه المنافسة- خمس سنوات ويجوز زيادتها في العقود التي تتطلب طبيعتها ذلك بعد موافقة الوزارة وذلك دون الإخلال بحكم الفقرة (3) من المادة (الثالثة) من القواعد، كما يجب ألا يكون مصدر الدخل الناتج عن العقد مدفوعاً من الدولة بشكل رئيس وألا يتضمن العقد تقديم الدولة للشريك الخاص أي شكل من أشكال الضمان أو الدعم الائتماني المرتبط بمستوى معين لتأمين السلع والخدمات، عدا ضمانات الحد الأدنى من الاستخدام المتعلقة فقط باستخدام الجهة الحكومية (إن وجدت) دون أن يخل ذلك بحكم الفقرة (3) من المادة (الخامسة) من القواعد. كما يجوز للجهة الحكومية بأن تضمن في وثائق المنافسة متطلباً بأن يقوم الشريك الخاص بتأسيس شركة لتنفيذ العقد، ويمكن أن تبين وثائق المنافسة الأحكام الخاصة بتأسيس الشركة بما في ذلك الإطار الزمني لإنشائها والحد الأدنى لرأس مالها دون الإخلال بما يقضي به نظام الشركات]",
            "special_conditions": "( تضيف الجهة الشروط الخاصة التي تراها مناسبة بحسب نطاق العمل )"
        },
        {
            "name": "اتفاقية اطارية الخدمات الاستشارية",
            "scope_of_work": "في هذه الفقرة يتم توضيح نطاق العمل الخاص بالمشروع والتفاصيل التي يجب مراعاتها عند تقديم الخدمة من المتعاقد. وفيما يلي، مثال على ذلك: تطوير التوجه الاستراتيجي وإطار الحوكمة والتمويل، من خلال الأنشطة التالية: 1- تقييم الوضع الراهن: تقييم الوضع الراهن في الجهة وتحديد الفجوات، تقييم الوضع الراهن في المملكة العربية السعودية وتحديد الفجوات. 2- الدراسات المعيارية: تحديد عدد 4 دول للدراسة المعيارية، دولة إقليمية و3 دول عالمية، تحديد أنواع المؤسسات والمشاريع التي تخدم تفعيل المشاركة المجتمعية. 3- تطوير نظام الحوكمة: إعداد الهيكل التنظيمي للبرنامج، تحديد الأدوار والمسؤوليات على مستوى الوزارة والأمانات، والجهات الخارجية. 4- تطوير منظومة التمويل: تحديد أنواع المشاريع التي يتضمنها نطاق عمل البرنامج، تحديد عملية اعتماد الميزانية.",
            "special_conditions": "[تضيف الجهة الشروط الخاصة التي تراها مناسبة بحسب نطاق العمل]"
        },
        {
            "name": "الخدمات الاستشارية - تفعيل مكتب إدارة المشاريع",
            "scope_of_work": "تأسيس مكتب الإدارة العامة للمشاريع بالجهة الحكومية، إدارة محفظة المشاريع، تحديد الأدوار والمسؤوليات، إدارة الأداء الداخلي، تطبيق إجراءات هيئة كفاءة الإنفاق والمشروعات الحكومية، إشراك الموارد، تقييم الموظفين، تقديم خدمات إدارة المشاريع (التخطيط، الإدارة الهندسية، العقود، التكلفة، التشييد، التشغيل، التسليم)، إعداد الخطة الخمسية، تنفيذ دورة حياة المشروع كاملة.",
            "special_conditions": "تقديم تقرير شهري تفصيلي يشمل الملخص التنفيذي، التقدم، السلامة، التكاليف، الجداول، المخاطر، الاجتماعات، وسجلات التغيير."
        },
        {
            "name": "الخدمات الاستشارية",
            "scope_of_work": "تطوير التوجه الاستراتيجي وإطار الحوكمة والتمويل من خلال تقييم الوضع الراهن، الدراسات المعيارية، تطوير الحوكمة، وتطوير منظومة التمويل.",
            "special_conditions": "تضيف الجهة الشروط الخاصة التي تراها مناسبة بحسب نطاق العمل."
        },
        {
            "name": "تقنية المعلومات",
            "scope_of_work": "تصميم وتطوير نظام إلكتروني لمتابعة التدريب، إدارة المستخدمين والصلاحيات، إنشاء مساحات عمل، تسجيل المتدربين، تقارير الحضور، الدعم الفني، توريد أجهزة شبكية وقطع غيار، تطوير الأمن السيبراني من خلال التقييم، وضع خطط استراتيجية، التشفير، تدريب الكوادر.",
            "special_conditions": "تضيف الجهة الحكومية الشروط الخاصة التي تراها مناسبة بحسب نطاق العمل."
        }
    ]
}

# =========================
# ✅ Server startup
# =========================
if __name__ == "__main__":
    try:
        import uvicorn
        import sys
    except ImportError as e:
        raise RuntimeError(
            "uvicorn is required to run this file directly. Install it with 'pip install uvicorn'."
        ) from e

    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = int(os.getenv("API_PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    print(f"\n✅ Starting InspiraCore API server")
    print(f"Host: {HOST}:{PORT}", flush=True)
    print(f"Model: {GEMINI_MODEL}", flush=True)
    print(f"Qdrant: {QDRANT_URL}", flush=True)
    print(f"Collection: {COLLECTION}", flush=True)
    print(f"Debug: {DEBUG}\n", flush=True)
    sys.stdout.flush()

    try:
        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            log_level="info",
            reload=DEBUG,
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

TERMS_DATA = {
    "terms": [
        {
            "arabic_term": "موازنة",
            "arabic_definition": "تقدير الإيرادات والنفقات المتوقعة خلال فترة مالية محددة (عادةً عام مالي)، وخطط الحكومة لتخصيص الموارد للقطاعات المختلفة.",
            "english_term": "Budgeting",
            "english_definition": "Estimates of the expected revenues and expenditures over a specific financial period (usually a fiscal year), and the government’s plans for allocating resources to various sectors."
        },
        {
            "arabic_term": "ميزانية",
            "arabic_definition": "المبالغ الفعلية التي تم تخصيصها أو إنفاقها بناءً على ما تم تحديده في الموازنة العامة.",
            "english_term": "Budget",
            "english_definition": "The actual amounts allocated or spent based on the estimates outlined in the general budget."
        },
        {
            "arabic_term": "أثر مالي",
            "arabic_definition": "القيمة المقدّرة أو المحقّقة للتكاليف، بما يعكس التغير في الوضع المالي.",
            "english_term": "Financial Impact",
            "english_definition": "The estimated or realized value of the costs."
        },
        {
            "arabic_term": "النفقات",
            "arabic_definition": "ما تصرفه الحكومة على القطاعات المختلفة كالتعليم والصحة.",
            "english_term": "Expenses",
            "english_definition": "What the government spends on various sectors."
        },
        {
            "arabic_term": "كفاءة الإنفاق",
            "arabic_definition": "تعظيم الأثر مقابل الصرف باستخدام الموارد بشكل أمثل.",
            "english_term": "Spending Efficiency",
            "english_definition": "Maximizing impact relative to expenditure."
        },
        {
            "arabic_term": "اتفاقية إطارية",
            "arabic_definition": "اتفاقية بين جهة حكومية وموردين تتضمن شروط العقود.",
            "english_term": "Framework Agreement",
            "english_definition": "A formal agreement between government bodies and suppliers."
        },
        {
            "arabic_term": "اتفاقية إعادة الشراء",
            "arabic_definition": "معاملة مالية لبيع أوراق مالية مع اتفاق لإعادة شرائها لاحقًا.",
            "english_term": "Repurchase Agreement",
            "english_definition": "A financial transaction where securities are sold with agreement to repurchase."
        },
        {
            "arabic_term": "الناتج المحلي الإجمالي",
            "arabic_definition": "إجمالي قيمة السلع والخدمات المنتجة داخل الدولة.",
            "english_term": "Gross Domestic Product (GDP)",
            "english_definition": "The total value of goods and services produced within a country."
        },
        {
            "arabic_term": "ائتمان مصرفي",
            "arabic_definition": "إجمالي الأموال التي يمكن اقتراضها من مؤسسة مالية.",
            "english_term": "Bank Credit",
            "english_definition": "Total amount of money a person or corporation may borrow."
        },
        {
            "arabic_term": "إدارة المخاطر",
            "arabic_definition": "عملية تحديد وتقييم المخاطر واتخاذ إجراءات للتقليل منها.",
            "english_term": "Risk Management",
            "english_definition": "The process of identifying and managing risks."
        },
        {
            "arabic_term": "إدارة الجودة",
            "arabic_definition": "نهج لتحسين جودة المنتجات والخدمات.",
            "english_term": "Quality Management",
            "english_definition": "A comprehensive approach to improving quality."
        }
    ]
}