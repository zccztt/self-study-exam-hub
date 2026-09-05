# -*- coding: utf-8 -*-
"""Seed script: import Hebei province (河北省) self-study exam data.

Data source: 河北省教育考试院 开考专业及课程设置
Reference: https://www.hebeea.edu.cn (自学考试 > 开考专业)

Usage:
    python -m scripts.seed_hebei_data

Covers:
- 河北省 major examination schools
- Popular undergraduate/diploma majors
- Full course plans (考试计划) with course codes, credits, types
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.enrollment import Major, MajorSubject, Province, School
from backend.models.subject import Subject


# ------------------------------------------------------------------
# 河北省 Province
# ------------------------------------------------------------------

PROVINCE = {"code": "13", "name": "河北省"}

# ------------------------------------------------------------------
# 河北省主考院校
# ------------------------------------------------------------------

SCHOOLS = [
    {"name": "河北大学", "code": "10075"},
    {"name": "河北经贸大学", "code": "11832"},
    {"name": "河北师范大学", "code": "10094"},
    {"name": "河北科技大学", "code": "10082"},
    {"name": "河北农业大学", "code": "10086"},
    {"name": "河北医科大学", "code": "10089"},
    {"name": "石家庄铁道大学", "code": "10107"},
    {"name": "河北工业大学", "code": "10080"},
    {"name": "燕山大学", "code": "10216"},
    {"name": "华北理工大学", "code": "10081"},
    {"name": "河北工程大学", "code": "10076"},
    {"name": "河北地质大学", "code": "10077"},
    {"name": "中国人民公安大学", "code": "10041"},
]

# ------------------------------------------------------------------
# 课程数据 (全国统一编码)
# ------------------------------------------------------------------

# 课程编码: (name, default_credits)
COURSE_CATALOG = {
    "03708": ("中国近现代史纲要", 2),
    "03709": ("马克思主义基本原理概论", 4),
    "00015": ("英语(二)", 14),
    "00016": ("日语(二)", 14),
    "00018": ("计算机应用基础", 2),
    "00019": ("计算机应用基础(实践)", 2),
    "00020": ("高等数学(一)", 6),
    "00023": ("高等数学(工本)", 10),
    "00051": ("管理系统中计算机应用", 3),
    "00052": ("管理系统中计算机应用(实践)", 1),
    "00054": ("管理学原理", 6),
    "00055": ("企业会计学", 6),
    "00058": ("市场营销学", 5),
    "00060": ("财政学", 4),
    "00065": ("国民经济统计概论", 6),
    "00067": ("财务管理学", 6),
    "00070": ("政府与事业单位会计", 4),
    "00071": ("社会保障概论", 5),
    "00072": ("商业银行业务与经营", 5),
    "00073": ("银行信贷管理学", 6),
    "00074": ("中央银行概论", 5),
    "00075": ("证券投资与管理", 5),
    "00076": ("国际金融", 6),
    "00077": ("金融市场学", 5),
    "00078": ("银行会计学", 5),
    "00079": ("保险学原理", 5),
    "00098": ("国际市场营销学", 5),
    "00107": ("现代管理学", 6),
    "00139": ("西方经济学", 6),
    "00140": ("国际经济学", 6),
    "00141": ("发展经济学", 6),
    "00142": ("计量经济学", 6),
    "00143": ("经济思想史", 5),
    "00144": ("企业管理概论", 5),
    "00146": ("中国税制", 4),
    "00149": ("国际贸易理论与实务", 6),
    "00150": ("金融理论与实务", 6),
    "00151": ("企业经营战略", 6),
    "00152": ("组织行为学", 4),
    "00153": ("质量管理(一)", 4),
    "00154": ("企业管理咨询", 4),
    "00155": ("中级财务会计", 8),
    "00156": ("成本会计", 5),
    "00157": ("管理会计(一)", 6),
    "00158": ("资产评估", 4),
    "00159": ("高级财务会计", 6),
    "00160": ("审计学", 4),
    "00161": ("财务报表分析(一)", 5),
    "00162": ("会计制度设计", 5),
    "00163": ("管理心理学", 5),
    "00167": ("劳动法", 4),
    "00169": ("房地产法", 3),
    "00182": ("公共关系学", 4),
    "00226": ("知识产权法", 4),
    "00227": ("公司法", 4),
    "00228": ("环境与资源保护法学", 4),
    "00230": ("合同法", 5),
    "00233": ("税法", 3),
    "00246": ("国际经济法概论", 6),
    "00249": ("国际私法", 4),
    "00258": ("保险法", 3),
    "00259": ("公证与律师制度", 3),
    "00260": ("刑事诉讼法学", 4),
    "00261": ("行政法学", 5),
    "00262": ("法律文书写作", 3),
    "00263": ("外国法制史", 4),
    "00264": ("中国法律思想史", 4),
    "00265": ("西方法律思想史", 4),
    "00266": ("社会学概论", 6),
    "00277": ("行政管理学", 6),
    "00292": ("市政学", 6),
    "00312": ("政治学概论", 6),
    "00315": ("当代中国政治制度", 6),
    "00316": ("西方政治制度", 6),
    "00318": ("公共政策", 4),
    "00319": ("行政组织理论", 4),
    "00320": ("领导科学", 4),
    "00321": ("中国文化概论", 5),
    "00322": ("中国行政史", 5),
    "00323": ("西方行政学说史", 4),
    "00341": ("公文写作与处理", 6),
    "00342": ("高级语言程序设计(一)", 3),
    "00370": ("刑事证据学", 4),
    "00373": ("涉外警务概论", 5),
    "00388": ("学前儿童数学教育", 4),
    "00394": ("幼儿园课程", 4),
    "00398": ("学前教育原理", 6),
    "00401": ("学前比较教育", 6),
    "00402": ("学前教育史", 6),
    "00467": ("课程与教学论", 6),
    "00468": ("德育原理", 4),
    "00469": ("教育学原理", 6),
    "00471": ("认知心理", 4),
    "00472": ("比较教育", 4),
    "00495": ("体育保健学", 6),
    "00497": ("运动训练学", 6),
    "00502": ("体育管理学", 5),
    "00503": ("体育教育学", 4),
    "00506": ("写作(一)", 7),
    "00529": ("文学概论(一)", 7),
    "00530": ("中国现代文学作品选", 6),
    "00531": ("中国当代文学作品选", 5),
    "00532": ("中国古代文学作品选(一)", 6),
    "00533": ("中国古代文学作品选(二)", 6),
    "00534": ("外国文学作品选", 6),
    "00535": ("现代汉语", 7),
    "00536": ("古代汉语", 8),
    "00537": ("中国现代文学史", 6),
    "00538": ("中国古代文学史(一)", 7),
    "00539": ("中国古代文学史(二)", 7),
    "00540": ("外国文学史", 6),
    "00541": ("语言学概论", 6),
    "00595": ("英语阅读(一)", 6),
    "00596": ("英语阅读(二)", 6),
    "00597": ("英语写作基础", 4),
    "00600": ("高级英语", 12),
    "00602": ("口译与听力", 6),
    "00603": ("英语写作", 4),
    "00604": ("英美文学选读", 6),
    "00795": ("综合英语(二)", 10),
    "00831": ("英语语法", 4),
    "00832": ("英语词汇学", 4),
    "00840": ("第二外语(日语)", 6),
    "00841": ("第二外语(法语)", 6),
    "00882": ("学前教育心理学", 6),
    "01178": ("机械工程控制基础", 4),
    "02120": ("数据库及其应用", 3),
    "02141": ("计算机网络技术", 4),
    "02142": ("数据结构导论", 4),
    "02197": ("概率论与数理统计(二)", 3),
    "02198": ("线性代数", 3),
    "02318": ("计算机组成原理", 4),
    "02323": ("操作系统概论", 4),
    "02324": ("离散数学", 3),
    "02325": ("计算机系统结构", 4),
    "02326": ("操作系统", 5),
    "02331": ("数据结构", 3),
    "02333": ("软件工程", 3),
    "02339": ("计算机网络与通信", 6),
    "02369": ("计算机通信接口技术", 3),
    "02375": ("运筹学基础", 4),
    "02378": ("信息资源管理", 4),
    "02382": ("管理信息系统", 4),
    "02628": ("管理经济学", 5),
    "03706": ("思想道德修养与法律基础", 2),
    "03707": ("毛泽东思想和中国特色社会主义理论体系概论", 4),
    "04183": ("概率论与数理统计(经管类)", 5),
    "04184": ("线性代数(经管类)", 4),
    "04729": ("大学语文", 4),
    "04730": ("电子技术基础(三)", 5),
    "04735": ("数据库系统原理", 4),
    "04737": ("C++程序设计", 3),
    "04741": ("计算机网络原理", 4),
    "04747": ("Java语言程序设计(一)", 3),
    "04749": ("网络工程", 4),
    "05680": ("婚姻家庭法", 3),
    "05723": ("非政府组织管理", 4),
    "05724": ("公共卫生管理", 4),
    "06088": ("管理思想史", 9),
    "06089": ("劳动关系学", 8),
    "06090": ("人员素质测评理论与方法", 6),
    "06091": ("薪酬管理", 6),
    "06092": ("工作分析", 4),
    "06093": ("人力资源开发与管理", 6),
    "06779": ("应用写作学", 5),
    "07484": ("社会统计学", 6),
    "07750": ("国际投资学", 6),
    "08118": ("法律基础", 5),
    "08533": ("英语语言学概论", 4),
    "12656": ("毛泽东思想和中国特色社会主义理论体系概论", 4),
}

# ------------------------------------------------------------------
# 河北省开考专业 + 考试计划
# (major_code, name, level, school_name, total_credits, courses)
# courses: [(course_code, course_type, credits, sort_order), ...]
# ------------------------------------------------------------------

MAJORS = [
    # ====== 经管类 ======
    {
        "code": "120201K",
        "name": "工商管理",
        "level": "bk",
        "school": "河北经贸大学",
        "total_credits": 75,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("04183", "required", 5, 4),
            ("04184", "required", 4, 5),
            ("00054", "required", 6, 6),
            ("00067", "required", 6, 7),
            ("00149", "required", 6, 8),
            ("00150", "required", 6, 9),
            ("00151", "required", 6, 10),
            ("00152", "required", 4, 11),
            ("00153", "required", 4, 12),
            ("00154", "required", 4, 13),
            ("00051", "elective", 3, 14),
            ("00058", "elective", 5, 15),
        ],
    },
    {
        "code": "120203K",
        "name": "会计学",
        "level": "bk",
        "school": "河北经贸大学",
        "total_credits": 74,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("04183", "required", 5, 4),
            ("04184", "required", 4, 5),
            ("00058", "required", 5, 6),
            ("00150", "required", 6, 7),
            ("00155", "required", 8, 8),
            ("00159", "required", 6, 9),
            ("00160", "required", 4, 10),
            ("00161", "required", 5, 11),
            ("00162", "required", 5, 12),
            ("00149", "elective", 6, 13),
            ("00233", "elective", 3, 14),
            ("00051", "elective", 3, 15),
        ],
    },
    {
        "code": "020301K",
        "name": "金融学",
        "level": "bk",
        "school": "河北经贸大学",
        "total_credits": 73,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("04183", "required", 5, 4),
            ("04184", "required", 4, 5),
            ("00058", "required", 5, 6),
            ("00076", "required", 6, 7),
            ("00077", "required", 5, 8),
            ("00078", "required", 5, 9),
            ("00079", "required", 5, 10),
            ("00067", "required", 6, 11),
            ("00150", "required", 6, 12),
            ("00072", "elective", 5, 13),
            ("00074", "elective", 5, 14),
            ("00075", "elective", 5, 15),
        ],
    },
    {
        "code": "120206",
        "name": "人力资源管理",
        "level": "bk",
        "school": "河北大学",
        "total_credits": 73,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00054", "required", 6, 4),
            ("00152", "required", 4, 5),
            ("06090", "required", 6, 6),
            ("06091", "required", 6, 7),
            ("06092", "required", 4, 8),
            ("06093", "required", 6, 9),
            ("06088", "required", 9, 10),
            ("06089", "required", 8, 11),
            ("00051", "elective", 3, 12),
            ("00071", "elective", 5, 13),
            ("00144", "elective", 5, 14),
        ],
    },
    {
        "code": "120402",
        "name": "行政管理",
        "level": "bk",
        "school": "河北大学",
        "total_credits": 72,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00277", "required", 6, 4),
            ("00315", "required", 6, 5),
            ("00316", "required", 6, 6),
            ("00318", "required", 4, 7),
            ("00319", "required", 4, 8),
            ("00320", "required", 4, 9),
            ("00322", "required", 5, 10),
            ("00323", "required", 4, 11),
            ("00261", "required", 5, 12),
            ("00312", "elective", 6, 13),
            ("00266", "elective", 6, 14),
            ("05723", "elective", 4, 15),
        ],
    },
    # ====== 法学类 ======
    {
        "code": "030101K",
        "name": "法学",
        "level": "bk",
        "school": "河北大学",
        "total_credits": 72,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00226", "required", 4, 4),
            ("00227", "required", 4, 5),
            ("00228", "required", 4, 6),
            ("00230", "required", 5, 7),
            ("00246", "required", 6, 8),
            ("00249", "required", 4, 9),
            ("00258", "required", 3, 10),
            ("00262", "required", 3, 11),
            ("00263", "required", 4, 12),
            ("00264", "required", 4, 13),
            ("05680", "elective", 3, 14),
            ("00169", "elective", 3, 15),
            ("00259", "elective", 3, 16),
        ],
    },
    # ====== 教育类 ======
    {
        "code": "040106",
        "name": "学前教育",
        "level": "bk",
        "school": "河北师范大学",
        "total_credits": 72,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00394", "required", 4, 4),
            ("00398", "required", 6, 5),
            ("00401", "required", 6, 6),
            ("00402", "required", 6, 7),
            ("00882", "required", 6, 8),
            ("00467", "required", 6, 9),
            ("00388", "required", 4, 10),
            ("00321", "elective", 5, 11),
            ("00163", "elective", 5, 12),
            ("00107", "elective", 6, 13),
        ],
    },
    {
        "code": "040101",
        "name": "教育学",
        "level": "bk",
        "school": "河北师范大学",
        "total_credits": 70,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00469", "required", 6, 4),
            ("00467", "required", 6, 5),
            ("00468", "required", 4, 6),
            ("00471", "required", 4, 7),
            ("00472", "required", 4, 8),
            ("00266", "required", 6, 9),
            ("00163", "required", 5, 10),
            ("00321", "elective", 5, 11),
            ("00107", "elective", 6, 12),
            ("00312", "elective", 6, 13),
        ],
    },
    # ====== 文学类 ======
    {
        "code": "050101",
        "name": "汉语言文学",
        "level": "bk",
        "school": "河北师范大学",
        "total_credits": 70,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00537", "required", 6, 4),
            ("00538", "required", 7, 5),
            ("00539", "required", 7, 6),
            ("00540", "required", 6, 7),
            ("00541", "required", 6, 8),
            ("00321", "required", 5, 9),
            ("00529", "elective", 7, 10),
            ("00266", "elective", 6, 11),
        ],
    },
    {
        "code": "050201",
        "name": "英语",
        "level": "bk",
        "school": "河北师范大学",
        "total_credits": 70,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00600", "required", 12, 3),
            ("00602", "required", 6, 4),
            ("00603", "required", 4, 5),
            ("00604", "required", 6, 6),
            ("00832", "required", 4, 7),
            ("08533", "required", 4, 8),
            ("00840", "required", 6, 9),
            ("00841", "elective", 6, 10),
            ("00321", "elective", 5, 11),
        ],
    },
    # ====== 工学/计算机类 ======
    {
        "code": "080901",
        "name": "计算机科学与技术",
        "level": "bk",
        "school": "河北大学",
        "total_credits": 73,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00023", "required", 10, 4),
            ("02197", "required", 3, 5),
            ("02324", "required", 3, 6),
            ("02325", "required", 4, 7),
            ("02326", "required", 5, 8),
            ("02331", "required", 3, 9),
            ("02333", "required", 3, 10),
            ("04735", "required", 4, 11),
            ("04737", "required", 3, 12),
            ("04741", "required", 4, 13),
            ("04747", "elective", 3, 14),
            ("02318", "elective", 4, 15),
        ],
    },
    # ====== 经济学类 ======
    {
        "code": "020101",
        "name": "经济学",
        "level": "bk",
        "school": "河北经贸大学",
        "total_credits": 73,
        "courses": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("04183", "required", 5, 4),
            ("04184", "required", 4, 5),
            ("00139", "required", 6, 6),
            ("00140", "required", 6, 7),
            ("00141", "required", 6, 8),
            ("00142", "required", 6, 9),
            ("00143", "required", 5, 10),
            ("00058", "required", 5, 11),
            ("00051", "elective", 3, 12),
            ("00060", "elective", 4, 13),
            ("00146", "elective", 4, 14),
        ],
    },
    # ====== 专科层次 ======
    {
        "code": "630302",
        "name": "会计",
        "level": "zk",
        "school": "河北经贸大学",
        "total_credits": 68,
        "courses": [
            ("03706", "required", 2, 1),
            ("03707", "required", 4, 2),
            ("04729", "required", 4, 3),
            ("00020", "required", 6, 4),
            ("00065", "required", 6, 5),
            ("00055", "required", 6, 6),
            ("00067", "required", 6, 7),
            ("00155", "required", 8, 8),
            ("00156", "required", 5, 9),
            ("00157", "required", 6, 10),
            ("00146", "required", 4, 11),
            ("00144", "elective", 5, 12),
            ("00070", "elective", 4, 13),
        ],
    },
    {
        "code": "690206",
        "name": "行政管理",
        "level": "zk",
        "school": "河北大学",
        "total_credits": 69,
        "courses": [
            ("03706", "required", 2, 1),
            ("03707", "required", 4, 2),
            ("04729", "required", 4, 3),
            ("00018", "required", 2, 4),
            ("00107", "required", 6, 5),
            ("00277", "required", 6, 6),
            ("00292", "required", 6, 7),
            ("00312", "required", 6, 8),
            ("00341", "required", 6, 9),
            ("00163", "required", 5, 10),
            ("00182", "required", 4, 11),
            ("00261", "elective", 5, 12),
            ("00266", "elective", 6, 13),
            ("00071", "elective", 5, 14),
        ],
    },
    {
        "code": "670102K",
        "name": "学前教育",
        "level": "zk",
        "school": "河北师范大学",
        "total_credits": 69,
        "courses": [
            ("03706", "required", 2, 1),
            ("03707", "required", 4, 2),
            ("04729", "required", 4, 3),
            ("00018", "required", 2, 4),
            ("00388", "required", 4, 5),
            ("00394", "required", 4, 6),
            ("00398", "required", 6, 7),
            ("00882", "required", 6, 8),
            ("00107", "required", 6, 9),
            ("00163", "required", 5, 10),
            ("00321", "elective", 5, 11),
            ("00182", "elective", 4, 12),
        ],
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        # 1. Province
        province = db.query(Province).filter(Province.code == PROVINCE["code"]).first()
        if not province:
            province = Province(code=PROVINCE["code"], name=PROVINCE["name"])
            db.add(province)
            db.flush()
        province_id = province.id

        # 2. Schools
        school_map = {}  # name -> id
        for s in SCHOOLS:
            existing = db.query(School).filter(
                School.name == s["name"], School.province_id == province_id
            ).first()
            if not existing:
                obj = School(name=s["name"], province_id=province_id, code=s["code"])
                db.add(obj)
                db.flush()
                school_map[s["name"]] = obj.id
            else:
                school_map[s["name"]] = existing.id

        # 3. Ensure all courses exist in subjects table
        for code, (name, _) in COURSE_CATALOG.items():
            existing = db.query(Subject).filter(Subject.code == code).first()
            if not existing:
                db.add(Subject(code=code, name=name, category="public"))
        db.flush()

        # Build code -> subject_id map
        all_subjects = db.query(Subject).all()
        subject_id_map = {s.code: s.id for s in all_subjects}

        # 4. Majors + MajorSubjects
        majors_created = 0
        links_created = 0
        for m in MAJORS:
            school_id = school_map.get(m["school"])
            if not school_id:
                print(f"  WARNING: School '{m['school']}' not found, skipping major {m['code']}")
                continue

            existing_major = (
                db.query(Major)
                .filter(
                    Major.code == m["code"],
                    Major.province_id == province_id,
                    Major.school_id == school_id,
                    Major.level == m["level"],
                )
                .first()
            )
            if existing_major:
                major_id = existing_major.id
            else:
                major_obj = Major(
                    code=m["code"],
                    name=m["name"],
                    level=m["level"],
                    province_id=province_id,
                    school_id=school_id,
                    total_credits=m.get("total_credits"),
                )
                db.add(major_obj)
                db.flush()
                major_id = major_obj.id
                majors_created += 1

            # Link courses
            for course_code, course_type, credits, sort_order in m["courses"]:
                subject_id = subject_id_map.get(course_code)
                if not subject_id:
                    # Create on-the-fly from catalog
                    cat_name, cat_credits = COURSE_CATALOG.get(course_code, (f"课程{course_code}", credits))
                    subj = Subject(code=course_code, name=cat_name, category="public")
                    db.add(subj)
                    db.flush()
                    subject_id = subj.id
                    subject_id_map[course_code] = subject_id

                existing_link = (
                    db.query(MajorSubject)
                    .filter(MajorSubject.major_id == major_id, MajorSubject.subject_id == subject_id)
                    .first()
                )
                if not existing_link:
                    db.add(MajorSubject(
                        major_id=major_id,
                        subject_id=subject_id,
                        course_type=course_type,
                        credits=credits,
                        sort_order=sort_order,
                    ))
                    links_created += 1

        db.commit()
        print("[OK] 河北省自考数据导入成功!")
        print(f"   省份: 河北省 (code=13)")
        print(f"   院校: {len(SCHOOLS)} 所")
        print(f"   专业: {len(MAJORS)} 个 (新增 {majors_created})")
        print(f"   课程: {len(COURSE_CATALOG)} 门")
        print(f"   专业-课程关联: 新增 {links_created} 条")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] 导入失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
