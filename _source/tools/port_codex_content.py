"""One-time port of the Codex category content into src/content/*.py.

Reads the structured data Codex used (work/industrial/content.py and the literals in
work/build_content.py) so the Arabic copy is carried over exactly, then adds the fields
this site needs: anchors, short labels, images, calculators and home-card copy.
After porting, edit the files in src/content/ directly; this script is kept for reference.
"""
import ast
import importlib.util
import pprint
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODEX = Path("/Users/a/Documents/Codex/2026-09-30/change-number-to-966-55-989/work")
OUT = ROOT / "src" / "content"


def literals(path, names):
    """Evaluate only the named top-level assignments (literals and dict(...) calls);
    the rest of the Codex script writes files, so it must not run."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in names:
                    expr = ast.Expression(node.value)
                    found[t.id] = eval(compile(expr, str(path), "eval"), {"__builtins__": {}, "dict": dict})
    return found


def load_industrial():
    spec = importlib.util.spec_from_file_location("codex_content", CODEX / "industrial" / "content.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {p["slug"]: p for p in mod.PAGES}


# Codex product id -> (anchor used on this site, image file stem)
INDUSTRIAL_IDS = {
    "pack-pouch": "pouch-filling", "pack-liquid": "liquid-filling", "pack-powder": "powder-filling",
    "pack-tray": "tray-sealing", "pack-shrink": "shrink-wrapping",
    "recycle-sort": "plastic-sorting", "recycle-wash": "plastic-washing", "recycle-pellet": "plastic-pelletizing",
    "recycle-baler": "cardboard-baler", "recycle-eps": "eps-compactor",
    "wash-touchless": "touchless", "wash-smart": "smart-gantry", "wash-tunnel": "wash-tunnel",
    "wash-fleet": "fleet-wash", "wash-water": "water-recycling",
}

VENDING_IDS = {  # codex id -> (anchor, short label)
    "flowers": ("flower-vending", "الورد والباقات"),
    "cotton-candy": ("cotton-candy-vending", "غزل البنات"),
    "ice-cream": ("ice-cream-vending", "الآيس كريم"),
    "protein": ("protein-shake-vending", "مخفوق البروتين"),
    "orange-juice": ("orange-juice-vending", "عصير البرتقال"),
}


def vending():
    v = literals(CODEX / "build_content.py", {"title", "description", "products", "families", "faqs"})
    products = []
    for p in v["products"]:
        anchor, short = VENDING_IDS[p["id"]]
        products.append(dict(
            id=anchor, image=Path(p["image"]).stem, orientation="portrait",
            name=p["title"], short=short, tag=p["tag"], body=p["body"],
            features=[list(f) for f in p["features"]], value=None,
            opportunity=p["opportunity"], check=p["check"],
        ))
    return dict(
        slug="vending-machines",
        nav="البيع الذاتي",
        name="مكائن البيع الذاتي",
        title=v["title"].replace("| IGA", "| IGA Lines"),
        description=v["description"],
        h1_main="مكائن البيع الذاتي",
        h1_tail="في السعودية",
        eyebrow="مكائن جديدة · حلول حسب المشروع",
        lead=("اختر ماكينة تُناسب موقعك وما يحتاجه عملاؤك: باقة ورد، حلوى تُحضّر أمامهم، أو مشروب بعد التمرين. "
              "اكتشف مكائن جديدة بفئات متنوعة، وقارن تجربة العميل ومتطلبات التشغيل قبل بدء مشروعك."),
        card_lead="ورد وغزل بنات وآيس كريم وبروتين وعصير طازج: نقاط بيع ذاتية تُختار حسب الموقع والجمهور.",
        intro=dict(
            title="نقطة بيع إضافية تبدأ من اختيار صحيح",
            paragraphs=[
                "تتيح مكائن البيع الذاتي تقديم المنتجات في مساحة محدودة، وتوسيع ساعات إتاحتها بحسب نظام الموقع. "
                "ويمكن لتجهيزات الدفع الإلكتروني ومتابعة المخزون عن بُعد أن تجعل الشراء والمتابعة أسهل. "
                "لكن نجاح المشروع يبدأ من توافق المنتج مع الجمهور، ثم انتظام التعبئة والنظافة والصيانة.",
                "في السعودية، تمثل سهولة الدفع جزءًا مهمًا من تجربة العميل؛ فقد بلغت المدفوعات الإلكترونية 85% "
                "من عدد مدفوعات الأفراد في التجزئة خلال 2025، بحسب "
                "[البنك المركزي السعودي](https://www.sama.gov.sa/ar-sa/MediaCenter/News/Pages/news-1139.aspx). "
                "لذلك اجعل تكامل الدفع المحلي بندًا واضحًا عند مقارنة الموديلات.",
            ],
            note=None,
        ),
        solutions=dict(
            title="خمس فئات تستحق الدراسة لمشروعك",
            intro="قارن وظيفة كل فئة وتجربة الشراء ومتطلبات التشغيل. تتحدد المزايا المتاحة بحسب الموديل والتجهيز.",
            opportunity_label="فرصة تشغيل",
        ),
        products=products,
        extras=dict(
            title="فئات إضافية من مكائن البيع الذاتي الجديدة",
            intro=("ابدأ بالمنتج الذي تريد بيعه، ثم حدد طريقة حفظه وتحضيره وتسليمه. هذه الفئات توسّع خيارات المشروع "
                   "حسب الموقع والجمهور، ويُحدد التوفر والتكوين الفني عند طلب العرض."),
            items=[list(f) for f in v["families"]],
        ),
        specs=dict(
            title="المواصفات التي تؤثر في التشغيل اليومي",
            intro=None,
            head=["ما الذي تقارنه؟", "ما الذي تطلبه في العرض؟", "قيمته للمشروع"],
            rows=[
                ["الدفع وتجربة الاستخدام", "واجهة عربية واضحة، الأسعار، وسائل الدفع المحلية، وسياسة معالجة فشل التسليم.", "شراء أسهل وتقليل حالات الدفع دون استلام."],
                ["السعة وزمن الخدمة", "عدد المنتجات أو الأكواب الفعلي، وزمن دورة كاملة، وتجربة تشغيل متتابعة.", "موازنة ازدحام العملاء مع دورية التعبئة."],
                ["الكهرباء وبيئة الموقع", "الجهد والتردد والقدرة القصوى، وحمل بدء التشغيل، ودرجة الحرارة المحيطة المسموحة.", "تجنب اختيار جهاز لا يناسب مصدر الكهرباء أو بيئة التشغيل."],
                ["التبريد والنظافة", "درجات الحفظ، تنبيهات الحرارة، وسهولة فك أجزاء الغذاء والماء والصرف.", "حماية جودة المنتج وتقليل الهدر ووقت الخدمة."],
                ["الإدارة والاتصال", "تقارير المبيعات والمخزون، تنبيهات الأعطال، الاتصال المتاح، والرسوم الدورية.", "تخطيط زيارات التعبئة والصيانة وفق الحاجة."],
                ["الدعم والتكلفة الكلية", "مدة الضمان ونطاقه، قطع الغيار، التدريب، التركيب وزمن الاستجابة المتفق عليه.", "مقارنة تكلفة الامتلاك، وليس سعر الشراء وحده."],
            ],
        ),
        locations=dict(
            title="فرص تشغيل حسب الموقع",
            head=["الموقع المقترح للدراسة", "فئات مناسبة للاختبار", "ما الذي تقيسه؟"],
            rows=[
                ["المولات ومناطق الترفيه", "غزل البنات، الآيس كريم، الألعاب والكبسولات.", "تحول المارة إلى مشترين، وقت الانتظار، ومبيعات نهاية الأسبوع."],
                ["الأندية والاستوديوهات الرياضية", "البروتين، المشروبات الرياضية، الماء والعصير.", "تكرار الشراء بعد التمرين وتكلفة الحصة."],
                ["الفنادق ومواقع الهدايا", "الورد والباقات، العطور، المستلزمات الشخصية.", "توقيت الحاجة، متوسط السلة، والهدر."],
                ["الجامعات ومراكز الأعمال", "القهوة، السناكات، الوجبات الجاهزة والشواحن.", "الطلب في فترات الاستراحة وسهولة إعادة التعبئة."],
            ],
            note="هذه استخدامات مقترحة للتحقق ميدانيًا؛ اختيار الموقع وعقده وتكلفة تشغيله عوامل مستقلة عن مواصفات الجهاز.",
        ),
        business=dict(
            title="كيف تقارن جدوى مشروع مكائن البيع الذاتي؟",
            paragraphs=[
                "احسب هامش المساهمة لكل عملية بيع بعد تكلفة المنتج والتغليف ورسوم الدفع والهدر المتغير، ثم قارنه بإيجار "
                "الموقع أو حصته وتكلفة التعبئة والنظافة والصيانة والكهرباء والاتصال. قِس المبيعات الواقعية قبل إضافة ماكينة ثانية.",
            ],
            formula=("**نقطة التعادل التشغيلية:** التكاليف الثابتة الشهرية ÷ هامش المساهمة لكل عملية بيع = عدد العمليات "
                     "المطلوبة لتغطية التشغيل. استرداد ثمن الماكينة حساب إضافي يعتمد على صافي التدفقات الفعلية."),
            after=[
                "للموقع الجديد، جهّز سيناريو طلب منخفض وآخر متوسط، واختبر أثر العطل والهدر وتغير سعر المواد. "
                "ارتفاع هامش الحصة وحده لا يكفي إذا كان عدد المشترين قليلًا.",
            ],
        ),
        calculator=dict(
            kind="breakeven",
            title="احسب نقطة التعادل لموقعك",
            unit="عملية بيع",
            price=("متوسط سعر البيع للعملية", "ر.س"),
            variable=("التكلفة المتغيرة لكل عملية", "المنتج والتغليف ورسوم الدفع والهدر"),
            fixed=("التكاليف الثابتة الشهرية", "إيجار الموقع أو حصته، التعبئة، النظافة، الصيانة، الكهرباء، الاتصال"),
            expected="المبيعات المتوقعة شهريًا",
            capital="سعر الماكينة",
        ),
        faq=dict(
            title="أسئلة شائعة عن مكائن البيع الذاتي",
            items=[list(f) for f in v["faqs"]],
            source=("للاطلاع على المتطلبات بحسب النشاط، راجع "
                    "[خدمة الأنشطة التجارية والاشتراطات البلدية في بلدي](https://balady.gov.sa/ar/services/الأنشطة-التجارية-والاشتراطات-البلدية)."),
        ),
        quote=dict(
            title="ابدأ بما يناسب موقعك",
            intro=("لطلب عرض ماكينة بيع ذاتي جديدة من IGA Lines، حدّد المنتج والموقع والكمية المطلوبة. بهذه المعلومات يمكن "
                   "مقارنة السعات والتجهيزات وتقدير نطاق التوريد والتشغيل بصورة أوضح."),
            items=[
                "المدينة ونوع الموقع: مول، نادٍ، جامعة، فندق أو غير ذلك.",
                "الفئة المطلوبة وعدد المكائن والمساحة المتاحة.",
                "الجمهور المتوقع وساعات العمل والميزانية المستهدفة.",
                "الدفع والتخصيص المطلوبان، والكهرباء والماء والصرف المتاحة.",
                "الموعد المستهدف ومتطلبات التركيب والتدريب والصيانة.",
            ],
            closing="اطلب عرضًا فنيًا وتجاريًا مفصلًا، وابدأ بقرار مبني على احتياج مشروعك.",
        ),
    )


INDUSTRIAL_META = {
    "packaging": dict(
        slug="packaging-machines", nav="التعبئة والتغليف",
        h1_main="آلات ومكائن التعبئة والتغليف", h1_tail="في السعودية",
        card_lead="تعبئة الأكياس والسوائل والبهارات وتغليف الوجبات والشرنك، بتجهيز يبدأ من منتجك.",
        source=None,
        calculator=dict(
            kind="savings",
            title="احسب وفر الأتمتة لكل عبوة",
            unit="عبوة",
            current=("تكلفة العبوة المقبولة حاليًا", "مواد التغليف والمنتج المهدور والعمل والطاقة والصيانة"),
            new=("تكلفة العبوة المقبولة بعد الأتمتة", "من العرض الفني ونتيجة اختبار عينتك"),
            volume="العبوات المقبولة شهريًا",
            capital="قيمة الاستثمار",
        ),
    ),
    "recycling": dict(
        slug="recycling-lines", nav="إعادة التدوير",
        h1_main="مكائن إعادة التدوير", h1_tail="في السعودية",
        card_lead="فرز ذكي وغسيل وتحبيب للبلاستيك وكبس للكرتون والفلين، بمخرجات قابلة للبيع.",
        source=("للمتطلبات المحلية بحسب النشاط والموقع: "
                "[المركز الوطني لإدارة النفايات](https://mwared.mwan.gov.sa/en)."),
        calculator=dict(
            kind="breakeven",
            title="احسب نقطة التعادل لمشروعك",
            unit="طن مقبول",
            price=("الإيراد من الطن المقبول", "ر.س"),
            variable=("التكلفة المتغيرة لكل طن", "الخام والنقل والطاقة والمياه والعمل والمستهلكات والتخلص من الرفض"),
            fixed=("التكاليف الثابتة الشهرية", "الإيجار والرواتب الثابتة والصيانة الدورية"),
            expected="الكمية المتوقعة شهريًا (طن مقبول)",
            capital="تكلفة المعدات",
        ),
    ),
    "car-wash": dict(
        slug="car-wash", nav="مغاسل السيارات",
        h1_main="مغاسل السيارات الأوتوماتيكية", h1_tail="في السعودية",
        card_lead="غسيل بدون لمس وبوابات ذكية وأنفاق غسيل وحلول للأساطيل واسترجاع للمياه.",
        source=("للمتطلبات المحلية بحسب النشاط والموقع: "
                "[خدمة الأنشطة والاشتراطات في بلدي](https://balady.gov.sa/ar/services/الأنشطة-التجارية-والاشتراطات-البلدية)."),
        calculator=dict(
            kind="breakeven",
            title="احسب نقطة التعادل لمغسلتك",
            unit="غسلة",
            price=("متوسط سعر الغسلة", "ر.س"),
            variable=("التكلفة المتغيرة لكل غسلة", "الماء والطاقة والمواد ورسوم الدفع والعمل المتغير"),
            fixed=("التكاليف الثابتة الشهرية", "إيجار الموقع والعمالة الثابتة والصيانة وبقية مصروفات التشغيل"),
            expected="الغسلات المتوقعة شهريًا",
            capital="تكلفة المعدات والأعمال المدنية",
        ),
    ),
}


def industrial(p):
    meta = INDUSTRIAL_META[p["slug"]]
    products = [dict(
        id=INDUSTRIAL_IDS[x["id"]], image="iga-" + x["id"], orientation="landscape",
        name=x["name"], short=x["short"], tag=x["tag"], body=x["body"],
        features=[list(f) for f in x["features"]], value=x["value"],
        opportunity=x["opportunity"], check=x["check"],
    ) for x in p["products"]]
    return dict(
        slug=meta["slug"],
        nav=meta["nav"],
        name=p["name"],
        title=p["title"].replace("| IGA", "| IGA Lines"),
        description=p["description"],
        h1_main=meta["h1_main"],
        h1_tail=meta["h1_tail"],
        eyebrow="مكائن جديدة · تجهيز يناسب مشروعك",
        lead=p["lead"],
        card_lead=meta["card_lead"],
        intro=dict(
            title="اختر الحل حسب احتياج التشغيل",
            paragraphs=[p["intro"], p["modern"]],
            note="المزايا المذكورة خيارات للمقارنة وتحديد نطاق التجهيز. يعتمد توفرها وأداؤها على الموديل والعينة والاختبار المتفق عليه.",
        ),
        solutions=dict(title=None, intro=None, opportunity_label="فرصة مناسبة للدراسة"),
        products=products,
        extras=dict(title="حلول مكملة حسب حجم المشروع", intro=None, items=[list(e) for e in p["extras"]]),
        specs=dict(
            title="المواصفات التي تستحق المقارنة",
            intro="اطلب عرضًا فنيًا يوضح نتيجة التشغيل وحدود التوريد، ثم قارن الخيارات على أساس الشروط نفسها.",
            head=["بند المقارنة", "ما الذي تطلبه؟"],
            rows=[list(s) for s in p["specs"]],
        ),
        locations=None,
        business=dict(title=p["business_title"], paragraphs=[p["business"], p["business2"]],
                      formula=None, after=[], source=meta["source"]),
        calculator=meta["calculator"],
        faq=dict(title="أسئلة شائعة", items=[list(f) for f in p["faq"]], source=None),
        quote=dict(
            title=p["quote_title"],
            intro=("لطلب عرض من IGA Lines، جهّز المعلومات التالية حتى يكون اقتراح التجهيز والسعة والتكلفة أقرب إلى احتياجك:"),
            items=list(p["quote"]),
            closing="ابدأ بعرض فني وتجاري واضح، واختبر النتيجة التي يحتاجها مشروعك.",
        ),
    )


def write(name, data):
    body = pprint.pformat(data, width=110, sort_dicts=False)
    text = (f'"""{data["name"]} — page content. Edit freely; run build.py afterwards."""\n\n'
            f"CATEGORY = {body}\n")
    (OUT / f"{name}.py").write_text(text, encoding="utf-8")
    print("wrote", name, len(text), "chars")


if __name__ == "__main__":
    ind = load_industrial()
    write("vending", vending())
    write("packaging", industrial(ind["packaging"]))
    write("recycling", industrial(ind["recycling"]))
    write("car_wash", industrial(ind["car-wash"]))
