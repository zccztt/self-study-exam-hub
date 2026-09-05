# -*- coding: utf-8 -*-
"""Seed script: 填充河北大学相关课程题库数据。

为河北大学 5 个专业的所有课程批量生成自考模拟真题，
覆盖单选、多选、填空、简答题型。

Usage:
    python -m scripts.seed_hebei_university_questions
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.chapter import Chapter
from backend.models.question import Question
from backend.models.subject import Subject

# ==================================================================
# 河北大学各专业核心课程题库
# key = subject_code, value = list of question dicts
# ==================================================================

QUESTION_BANK = {
    # ==============================================================
    # 公共课
    # ==============================================================
    "03708": [  # 中国近现代史纲要
        {
            "content": "标志着中国近代史开端的事件是（ ）。",
            "question_type": "single_choice",
            "options": ["鸦片战争", "太平天国运动", "洋务运动", "戊戌变法"],
            "answer": "A",
            "explanation": "1840年鸦片战争使中国开始沦为半殖民地半封建社会，是中国近代史的开端。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 9,
        },
        {
            "content": "洋务运动的指导思想是（ ）。",
            "question_type": "single_choice",
            "options": ["中体西用", "师夷长技以制夷", "变法维新", "民主共和"],
            "answer": "A",
            "explanation": "洋务派主张在维护封建制度的前提下学习西方技术，即'中学为体，西学为用'。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "辛亥革命的历史功绩包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["推翻了清王朝", "结束了君主专制制度", "传播了民主共和理念", "完成了反帝反封建任务"],
            "answer": "ABC",
            "explanation": "辛亥革命没有完成反帝反封建任务，D项错误。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "五四运动的直接导火线是（ ）。",
            "question_type": "single_choice",
            "options": ["巴黎和会中国外交失败", "俄国十月革命", "新文化运动", "二十一条"],
            "answer": "A",
            "explanation": "1919年巴黎和会决定将德国在山东的权益转让给日本，直接引发五四运动。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "中国共产党成立的历史条件有哪些？",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）马克思主义在中国的广泛传播（思想基础）；（2）中国工人阶级的壮大和工人运动的发展（阶级基础）；（3）各地共产主义小组的建立（组织基础）；（4）共产国际的帮助（外部条件）。",
            "explanation": "从思想、阶级、组织、外部四个维度展开论述。",
            "difficulty": "medium", "score": 6, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "新民主主义革命的总路线是（ ）。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "无产阶级领导的，人民大众的，反对帝国主义、封建主义和官僚资本主义的革命",
            "explanation": "毛泽东在《在晋绥干部会议上的讲话》中完整表述了新民主主义革命总路线。",
            "difficulty": "medium", "score": 3, "year": 2025, "month": 10, "frequency": 6,
        },
        {
            "content": "遵义会议的主要内容和历史意义是什么？",
            "question_type": "short_answer",
            "options": [],
            "answer": "主要内容：纠正了博古等人军事上和组织上的'左'倾错误，确立了毛泽东在中共中央和红军的领导地位。历史意义：是党的历史上生死攸关的转折点，标志着中国共产党从幼年走向成熟。",
            "explanation": "答题要点：内容+意义，突出'转折点'和'走向成熟'。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 8,
        },
        {
            "content": "社会主义改造中对资本主义工商业的改造采用的方式是（ ）。",
            "question_type": "single_choice",
            "options": ["和平赎买", "没收充公", "合作社", "人民公社"],
            "answer": "A",
            "explanation": "对资本主义工商业实行和平赎买政策，通过国家资本主义形式逐步过渡。",
            "difficulty": "easy", "score": 2, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
    "03709": [  # 马克思主义基本原理概论
        {
            "content": "马克思主义哲学最根本的特征是（ ）。",
            "question_type": "single_choice",
            "options": ["实践性", "革命性", "科学性", "阶级性"],
            "answer": "A",
            "explanation": "实践性是马克思主义哲学区别于一切旧哲学的最显著特征。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "唯物辩证法的实质和核心是（ ）。",
            "question_type": "single_choice",
            "options": ["对立统一规律", "量变质变规律", "否定之否定规律", "因果联系"],
            "answer": "A",
            "explanation": "对立统一规律揭示了事物发展的根本动力和源泉。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 9,
        },
        {
            "content": "认识的本质是（ ）。",
            "question_type": "single_choice",
            "options": ["主体对客体的能动反映", "主观自生的", "客观精神的外化", "人脑的分泌物"],
            "answer": "A",
            "explanation": "马克思主义认识论认为认识是主体对客体的能动的、创造性的反映。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "剩余价值的两种基本形式是（ ）。",
            "question_type": "multiple_choice",
            "options": ["绝对剩余价值", "相对剩余价值", "超额剩余价值", "平均利润"],
            "answer": "AB",
            "explanation": "绝对剩余价值和相对剩余价值是资本家获取剩余价值的两种基本方法。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "简述量变和质变的辩证关系。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）量变是质变的必要准备；（2）质变是量变的必然结果；（3）量变和质变相互渗透：量变中有部分质变，质变中有量的扩张。",
            "explanation": "三点论述，注意互相渗透这一点常被遗漏。",
            "difficulty": "medium", "score": 6, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "社会主义从空想到科学的标志是（ ）的创立。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "唯物史观和剩余价值学说",
            "explanation": "马克思的两大发现使社会主义由空想变为科学。",
            "difficulty": "medium", "score": 3, "year": 2026, "month": 4, "frequency": 6,
        },
        {
            "content": "商品的二因素是（ ）。",
            "question_type": "multiple_choice",
            "options": ["使用价值", "价值", "交换价值", "剩余价值"],
            "answer": "AB",
            "explanation": "商品是使用价值和价值的统一体；交换价值是价值的表现形式。",
            "difficulty": "easy", "score": 4, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "试述实践是检验真理唯一标准的原理。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）真理的本性要求实践来检验——真理是主观符合客观，仅靠主观认识自身不能证明；（2）实践的特点决定了它能成为标准——实践具有直接现实性，能把主观认识变成客观现实来对照；（3）实践标准既是确定的又是不确定的——确定性在于只有实践能检验，不确定在于具体的实践检验是历史的、发展的。",
            "explanation": "三层次：真理本性、实践特点、确定与不确定的统一。",
            "difficulty": "hard", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
    "00015": [  # 英语(二)
        {
            "content": "The manager insisted that the report ______ finished by Friday.",
            "question_type": "single_choice",
            "options": ["be", "was", "is", "will be"],
            "answer": "A",
            "explanation": "insist表'坚持要求'时，从句用虚拟语气(should) + 动词原形。",
            "difficulty": "medium", "score": 2, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "Which of the following sentences uses the subjunctive mood correctly? ( )",
            "question_type": "single_choice",
            "options": ["If I were you, I would accept the offer.", "If I am you, I will accept the offer.", "If I was you, I would accept the offer.", "If I be you, I shall accept the offer."],
            "answer": "A",
            "explanation": "虚拟条件句中与现在事实相反，be动词用were。",
            "difficulty": "medium", "score": 2, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "He is the only one of the students who ______ passed all the exams.",
            "question_type": "single_choice",
            "options": ["has", "have", "had", "having"],
            "answer": "A",
            "explanation": "'the only one of...who'引导定语从句，先行词为the only one，谓语用单数。",
            "difficulty": "medium", "score": 2, "year": 2025, "month": 4, "frequency": 6,
        },
        {
            "content": "Not until he arrived at the station ______ that he had left his ticket at home.",
            "question_type": "single_choice",
            "options": ["did he realize", "he realized", "he did realize", "realized he"],
            "answer": "A",
            "explanation": "Not until置于句首时主句需要部分倒装。",
            "difficulty": "medium", "score": 2, "year": 2026, "month": 4, "frequency": 7,
        },
        {
            "content": "The word 'substantial' in the passage is closest in meaning to ______.",
            "question_type": "single_choice",
            "options": ["considerable", "minor", "acceptable", "invisible"],
            "answer": "A",
            "explanation": "substantial意为'大量的、相当多的'，与considerable同义。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 5,
        },
        {
            "content": "将下列句子翻译为中文：The development of science and technology has greatly changed the way people live and work.",
            "question_type": "short_answer",
            "options": [],
            "answer": "科学技术的发展极大地改变了人们生活和工作的方式。",
            "explanation": "翻译要点：science and technology科学技术；greatly极大地；the way...的方式。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 6,
        },
    ],
    # ==============================================================
    # 行政管理(本科) 专业课
    # ==============================================================
    "00277": [  # 行政管理学
        {
            "content": "行政管理学的研究对象是（ ）。",
            "question_type": "single_choice",
            "options": ["政府行政组织对公共事务的管理活动", "企业内部管理", "社会团体管理", "立法机关运行"],
            "answer": "A",
            "explanation": "行政管理学以政府行政组织及其管理公共事务的活动为研究对象。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "行政环境中影响最为直接的因素是（ ）。",
            "question_type": "single_choice",
            "options": ["政治环境", "经济环境", "文化环境", "自然环境"],
            "answer": "A",
            "explanation": "政治环境直接影响行政体制、行政权力的来源与运行方式。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "行政职能的特点包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["执行性", "多样性", "动态性", "立法性"],
            "answer": "ABC",
            "explanation": "行政职能具有执行性、多样性、动态性等特点，不具有立法性。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 6,
        },
        {
            "content": "我国行政管理中的首长负责制包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["国务院总理负责制", "各部部长负责制", "地方各级政府行政首长负责制", "全国人大委员长负责制"],
            "answer": "ABC",
            "explanation": "全国人大委员长不属于行政系统，D项错误。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "简述行政决策的基本程序。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）发现问题，确定目标；（2）调查预测，拟定方案；（3）评估优选，确定方案；（4）实施反馈，修正完善。",
            "explanation": "按四步流程展开，强调'反馈修正'环节。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 8,
        },
        {
            "content": "行政监督的类型按监督主体划分包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["权力机关监督", "司法监督", "政党监督", "社会监督"],
            "answer": "ABCD",
            "explanation": "按主体分为权力机关、司法机关、政党、社会舆论等类型的监督。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "行政效率的含义是（ ）。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "行政机关在行政管理活动中投入的工作量与获得的行政效果之间的比率",
            "explanation": "行政效率=行政产出/行政投入。",
            "difficulty": "medium", "score": 3, "year": 2025, "month": 10, "frequency": 6,
        },
        {
            "content": "试论行政组织设置的基本原则。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）职能目标原则——以职能需要确定机构设置；（2）精简统一原则——减少层级，避免职能交叉；（3）权责一致原则——有权必有责，权责对等；（4）法制原则——机构设置依法进行；（5）效率原则——以最少资源实现行政目标。",
            "explanation": "5个原则，可简记为：目标、精简、权责、法制、效率。",
            "difficulty": "hard", "score": 8, "year": 2026, "month": 4, "frequency": 6,
        },
    ],
    "00315": [  # 当代中国政治制度
        {
            "content": "我国最高国家权力机关是（ ）。",
            "question_type": "single_choice",
            "options": ["全国人民代表大会", "国务院", "中共中央", "全国政协"],
            "answer": "A",
            "explanation": "宪法规定全国人民代表大会是最高国家权力机关。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "我国的根本政治制度是（ ）。",
            "question_type": "single_choice",
            "options": ["人民代表大会制度", "政治协商制度", "民族区域自治制度", "基层群众自治制度"],
            "answer": "A",
            "explanation": "人民代表大会制度是我国的根本政治制度。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 9,
        },
        {
            "content": "我国的政党制度是（ ）。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "中国共产党领导的多党合作和政治协商制度",
            "explanation": "这是我国基本政治制度之一。",
            "difficulty": "easy", "score": 3, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "全国人大常委会的职权包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["解释宪法", "监督宪法实施", "制定和修改基本法律以外的法律", "修改宪法"],
            "answer": "ABC",
            "explanation": "修改宪法的权力属于全国人大而非全国人大常委会。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "简述民族区域自治制度的基本内容。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）各少数民族聚居的地方实行区域自治，设立自治机关；（2）自治机关享有自治权，包括立法权、变通执行权、经济管理权、文化管理权等；（3）自治地方分为自治区、自治州、自治县三级；（4）国家帮助各自治地方加快发展。",
            "explanation": "要答出自治机关、自治权、层级、国家帮助四个方面。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
        {
            "content": "中国人民政治协商会议的主要职能是（ ）。",
            "question_type": "multiple_choice",
            "options": ["政治协商", "民主监督", "参政议政", "国家立法"],
            "answer": "ABC",
            "explanation": "政协不具有国家立法权。其三大职能为政治协商、民主监督、参政议政。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 8,
        },
    ],
    "00318": [  # 公共政策
        {
            "content": "公共政策的本质属性是（ ）。",
            "question_type": "single_choice",
            "options": ["阶级性与公共性的统一", "纯粹的阶级性", "纯粹的公共性", "技术性"],
            "answer": "A",
            "explanation": "公共政策既体现统治阶级意志，又具有公共利益指向。",
            "difficulty": "medium", "score": 2, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "政策评估的标准包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["效率标准", "效果标准", "公平标准", "回应性标准"],
            "answer": "ABCD",
            "explanation": "政策评估采用多元标准，包括效率、效果、公平、回应性等。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 6,
        },
        {
            "content": "渐进决策模型的提出者是（ ）。",
            "question_type": "single_choice",
            "options": ["林德布洛姆", "西蒙", "德洛尔", "拉斯韦尔"],
            "answer": "A",
            "explanation": "林德布洛姆提出渐进决策模型，强调政策变迁的渐进性。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "简述公共政策制定的主要步骤。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）政策问题确认与议程建立；（2）政策目标设定；（3）政策方案设计与评估；（4）政策合法化与采纳。",
            "explanation": "四步流程，政策合法化不可遗漏。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
        {
            "content": "政策终结的方式包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["政策废止", "政策替代", "政策合并", "政策分解"],
            "answer": "ABCD",
            "explanation": "政策终结的四种主要形式：废止、替代、合并、分解。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 6,
        },
    ],
    "00319": [  # 行政组织理论
        {
            "content": "行政组织的核心特征是（ ）。",
            "question_type": "single_choice",
            "options": ["政治性和社会性的统一", "单纯的经济性", "完全的自治性", "学术性"],
            "answer": "A",
            "explanation": "行政组织既是政治统治工具，又承担社会管理职能。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "韦伯的官僚制理论的核心特征包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["层级制", "规则化", "非人格化", "完全弹性化"],
            "answer": "ABC",
            "explanation": "韦伯官僚制强调层级分明、规则清晰、非人格化管理，而非完全弹性化。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "管理幅度与管理层次的关系是（ ）。",
            "question_type": "single_choice",
            "options": ["反比关系", "正比关系", "无关系", "随机关系"],
            "answer": "A",
            "explanation": "管理幅度越大，所需管理层次越少，二者呈反比关系。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "简述行政组织变革的动力因素。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）社会环境变化（经济、政治、文化环境变迁）；（2）科学技术进步；（3）组织内部矛盾（效率低下、人员膨胀、职能交叉）；（4）管理思想与理论的发展。",
            "explanation": "从外部环境、技术、内部、理论四个维度论述。",
            "difficulty": "medium", "score": 6, "year": 2025, "month": 10, "frequency": 6,
        },
    ],
    "00320": [  # 领导科学
        {
            "content": "领导的本质是（ ）。",
            "question_type": "single_choice",
            "options": ["影响力", "权力", "权威", "职位"],
            "answer": "A",
            "explanation": "领导的本质在于影响力，即引导和影响他人实现组织目标的能力。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "领导者的权力可分为（ ）。",
            "question_type": "multiple_choice",
            "options": ["职位权力", "个人权力", "专家权力", "信息权力"],
            "answer": "ABCD",
            "explanation": "领导权力来源多元，既有正式的职位权力，也有个人魅力、专业能力、信息掌握等。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "简述领导者应具备的基本素质。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）政治素质——坚定的政治方向和立场；（2）知识素质——渊博的知识结构；（3）能力素质——决策、组织、协调、创新能力；（4）心理素质——坚强意志和健康心态；（5）身体素质——旺盛精力和健康体魄。",
            "explanation": "五维素质模型：政治、知识、能力、心理、身体。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
        {
            "content": "领导决策的科学化要求做到______、______、______。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "合理的决策体制、科学的决策程序、有效的决策方法",
            "explanation": "从体制、程序、方法三方面保证决策科学化。",
            "difficulty": "medium", "score": 3, "year": 2025, "month": 10, "frequency": 6,
        },
    ],
    "00322": [  # 中国行政史
        {
            "content": "中国古代最早的比较系统的行政管理制度产生于（ ）。",
            "question_type": "single_choice",
            "options": ["西周", "夏朝", "商朝", "秦朝"],
            "answer": "A",
            "explanation": "西周建立了比较完备的分封制和宗法制，形成系统的行政管理制度。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "秦始皇统一中国后实行的地方行政制度是（ ）。",
            "question_type": "single_choice",
            "options": ["郡县制", "分封制", "行省制", "州县制"],
            "answer": "A",
            "explanation": "秦始皇废分封、行郡县，建立了郡县两级地方行政制度。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "唐代中央行政体制的核心是（ ）。",
            "question_type": "single_choice",
            "options": ["三省六部制", "二府三司制", "内阁制", "军机处"],
            "answer": "A",
            "explanation": "唐代实行三省（中书、门下、尚书）六部制。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "科举制正式确立于（ ）。",
            "question_type": "single_choice",
            "options": ["隋朝", "唐朝", "宋朝", "汉朝"],
            "answer": "A",
            "explanation": "隋炀帝设进士科，标志科举制正式确立。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "简述明代内阁制度的特点。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）内阁始终不是法定的中央决策机构；（2）阁臣只有票拟权而无最终决定权；（3）内阁权力大小取决于皇帝信任程度；（4）与宦官之间存在制约关系。",
            "explanation": "突出非法定性、票拟与批红分离、依附皇权等特点。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 6,
        },
    ],
    "00261": [  # 行政法学
        {
            "content": "行政法的基本原则中最核心的是（ ）。",
            "question_type": "single_choice",
            "options": ["依法行政原则", "合理行政原则", "程序正当原则", "高效便民原则"],
            "answer": "A",
            "explanation": "依法行政是行政法的基本原则之首，是法治政府的核心要求。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "行政行为的分类中，按照是否需要相对人申请可分为（ ）。",
            "question_type": "multiple_choice",
            "options": ["依职权行政行为", "依申请行政行为", "抽象行政行为", "羁束行政行为"],
            "answer": "AB",
            "explanation": "按是否需要相对人申请分为依职权和依申请两类。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "行政复议的申请期限一般为知道具体行政行为之日起（ ）日内。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "60",
            "explanation": "《行政复议法》规定，公民、法人或者其他组织认为具体行政行为侵犯其合法权益的，可以自知道该具体行政行为之日起60日内提出行政复议申请。",
            "difficulty": "easy", "score": 3, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "简述行政许可的设定原则。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）法定原则——只有法律、行政法规、地方性法规可以设定行政许可；（2）必要性原则——能通过市场机制等其他方式解决的不设许可；（3）公开、公正、公平原则；（4）便民高效原则。",
            "explanation": "《行政许可法》第11-13条确立了行政许可设定的原则体系。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
    # ==============================================================
    # 法学(本科) 专业课
    # ==============================================================
    "00226": [  # 知识产权法
        {
            "content": "著作权自作品（ ）之日起产生。",
            "question_type": "single_choice",
            "options": ["创作完成", "发表", "登记", "出版"],
            "answer": "A",
            "explanation": "我国著作权法规定著作权自作品创作完成之日起自动产生，不以发表或登记为条件。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "发明专利的保护期限为（ ）年。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "20",
            "explanation": "发明专利权保护期限为20年，自申请日起计算。",
            "difficulty": "easy", "score": 3, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "商标注册的原则包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["自愿注册原则", "申请在先原则", "诚实信用原则", "自动取得原则"],
            "answer": "ABC",
            "explanation": "我国商标法不实行自动取得原则，需经注册才能获得专用权保护。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "简述专利权的授予条件。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）新颖性——不属于现有技术，没有同样的申请在先；（2）创造性——与现有技术相比具有突出的实质性特点和显著进步；（3）实用性——能够制造或使用，并能产生积极效果。",
            "explanation": "三性缺一不可，注意新颖性的判断标准包括现有技术和抵触申请。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 8,
        },
    ],
    "00227": [  # 公司法
        {
            "content": "有限责任公司的股东人数上限为（ ）人。",
            "question_type": "single_choice",
            "options": ["50", "30", "100", "200"],
            "answer": "A",
            "explanation": "公司法规定有限责任公司股东人数为1-50人。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "股份有限公司设立的最低注册资本为（ ）。",
            "question_type": "single_choice",
            "options": ["500万元", "100万元", "1000万元", "无最低限额"],
            "answer": "A",
            "explanation": "公司法规定股份有限公司设立的最低注册资本为500万元。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "公司的独立人格体现在（ ）。",
            "question_type": "multiple_choice",
            "options": ["独立的财产", "独立的名义", "独立承担责任", "股东承担无限责任"],
            "answer": "ABC",
            "explanation": "公司独立人格三要素：独立财产、独立名义、独立责任。股东承担有限责任。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "简述有限责任公司与股份有限公司的主要区别。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）股东人数不同：有限公司50人以下，股份公司2人以上、200人以下发起人；（2）出资方式不同：有限公司出资不分等额股份，股份公司将资本分为等额股份；（3）股权转让限制不同：有限公司有对内对外转让限制，股份公司股份可自由转让；（4）组织机构不同：股份公司必须设董事会和监事会。",
            "explanation": "从人数、出资、转让、组织四维度对比。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
    "00230": [  # 合同法
        {
            "content": "合同成立的一般要件是（ ）。",
            "question_type": "multiple_choice",
            "options": ["双方当事人", "意思表示一致", "标的确定", "必须采用书面形式"],
            "answer": "ABC",
            "explanation": "合同并非都须书面形式，口头合同、行为合同等同样有效。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "要约生效的时间采用（ ）主义。",
            "question_type": "single_choice",
            "options": ["到达主义", "发出主义", "了解主义", "邮寄主义"],
            "answer": "A",
            "explanation": "我国合同法规定要约到达受要约人时生效。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "合同解除的法定条件包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["因不可抗力致使不能实现合同目的", "当事人一方迟延履行主要债务经催告后仍不履行", "当事人一方迟延履行债务致使不能实现合同目的", "当事人一方主观上不想履行"],
            "answer": "ABC",
            "explanation": "法定解除权的行使需满足合同法规定的情形，主观不想履行不构成法定解除条件。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "简述违约责任的承担方式。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）继续履行；（2）采取补救措施；（3）赔偿损失；（4）支付违约金；（5）定金罚则。注意违约金与定金不能并用。",
            "explanation": "五种方式，最后注意二选一规则。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 8,
        },
    ],
    # ==============================================================
    # 计算机科学与技术(本科) 专业课
    # ==============================================================
    "02324": [  # 离散数学
        {
            "content": "命题公式 p->q 与下列哪个公式等价（ ）。",
            "question_type": "single_choice",
            "options": ["¬p∨q", "p∨q", "¬p∧q", "p∧¬q"],
            "answer": "A",
            "explanation": "p->q等价于¬p∨q，这是蕴含式的等价变换。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "设集合A={1,2,3}，则A的幂集|P(A)|=（ ）。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "8",
            "explanation": "|P(A)|=2^|A|=2^3=8。",
            "difficulty": "easy", "score": 3, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "一个连通图的生成树包含图中所有（ ）个顶点和（ ）条边。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "n; n-1",
            "explanation": "n个顶点的连通图的生成树有n个顶点和n-1条边。",
            "difficulty": "easy", "score": 3, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "关系R是等价关系的充要条件是R具有（ ）。",
            "question_type": "multiple_choice",
            "options": ["自反性", "对称性", "传递性", "反对称性"],
            "answer": "ABC",
            "explanation": "等价关系必须同时满足自反性、对称性、传递性。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 8,
        },
    ],
    "02331": [  # 数据结构
        {
            "content": "栈的基本特征是（ ）。",
            "question_type": "single_choice",
            "options": ["后进先出", "先进先出", "随机存取", "顺序存取"],
            "answer": "A",
            "explanation": "栈(Stack)是后进先出(LIFO)的线性结构。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "二叉树的第i层最多有______个结点。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "2^(i-1)",
            "explanation": "二叉树第i层（i>=1）最多有2^(i-1)个结点。",
            "difficulty": "easy", "score": 3, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "在最坏情况下，快速排序的时间复杂度是（ ）。",
            "question_type": "single_choice",
            "options": ["O(n^2)", "O(nlogn)", "O(n)", "O(logn)"],
            "answer": "A",
            "explanation": "快速排序最坏情况（已排序数组且取首元素为pivot）时间复杂度为O(n^2)。",
            "difficulty": "medium", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "图的深度优先搜索(DFS)使用的数据结构是（ ）。",
            "question_type": "single_choice",
            "options": ["栈", "队列", "数组", "链表"],
            "answer": "A",
            "explanation": "DFS使用栈（系统递归调用栈或显式栈）来实现。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "简述哈希冲突的处理方法。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）开放定址法：线性探测、二次探测、双重散列；（2）链地址法：将同义词链接在同一链表中；（3）再散列法：使用另一个哈希函数；（4）建立公共溢出区。",
            "explanation": "最常用的是开放定址法和链地址法。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
    "02333": [  # 软件工程
        {
            "content": "软件生命周期中耗时最长的阶段通常是（ ）。",
            "question_type": "single_choice",
            "options": ["维护阶段", "编码阶段", "设计阶段", "测试阶段"],
            "answer": "A",
            "explanation": "软件维护阶段通常占整个生命周期60%-80%的时间。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "面向对象设计的基本原则包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["单一职责原则", "开放封闭原则", "里氏替换原则", "不需要接口原则"],
            "answer": "ABC",
            "explanation": "SOLID原则中不包含'不需要接口原则'，应为接口隔离原则。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "需求分析阶段产出的主要文档是（ ）。",
            "question_type": "single_choice",
            "options": ["软件需求规格说明书(SRS)", "概要设计说明书", "详细设计说明书", "用户手册"],
            "answer": "A",
            "explanation": "SRS是需求分析的主要产出，描述系统的功能和非功能需求。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "简述黑盒测试和白盒测试的区别。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）黑盒测试：不考虑程序内部结构，仅根据功能需求设计测试用例，关注输入输出是否正确；（2）白盒测试：基于程序内部逻辑结构，通过覆盖语句、分支、路径等来设计测试用例；（3）黑盒测试发现功能缺陷，白盒测试发现逻辑缺陷。",
            "explanation": "从定义、方法、发现问题类型三方面对比。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
    "04735": [  # 数据库系统原理
        {
            "content": "数据库系统的三级模式结构包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["外模式", "模式（概念模式）", "内模式", "控制模式"],
            "answer": "ABC",
            "explanation": "三级模式为外模式（用户视图）、模式（逻辑结构）、内模式（存储结构）。",
            "difficulty": "easy", "score": 4, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "关系数据库中主键的作用是（ ）。",
            "question_type": "single_choice",
            "options": ["唯一标识元组", "加快查询速度", "实现数据加密", "控制并发访问"],
            "answer": "A",
            "explanation": "主键用于唯一标识关系中的每一个元组，不允许为空值。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "将一个关系模式分解为若干满足BCNF的子模式，这一过程称为（ ）。",
            "question_type": "single_choice",
            "options": ["规范化", "索引化", "视图定义", "事务处理"],
            "answer": "A",
            "explanation": "规范化是通过分解关系模式消除不合适的数据依赖的过程。",
            "difficulty": "medium", "score": 2, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "事务的ACID特性分别是指______。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "原子性(Atomicity)、一致性(Consistency)、隔离性(Isolation)、持久性(Durability)",
            "explanation": "ACID是数据库事务的四大基本特性。",
            "difficulty": "easy", "score": 3, "year": 2025, "month": 10, "frequency": 9,
        },
        {
            "content": "简述数据库并发控制中封锁协议的分类及其作用。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）一级封锁协议：事务在修改数据前加X锁，直到事务结束释放，可防止丢失更新；（2）二级封锁协议：在一级基础上，读数据前加S锁，读完即释放，可再防止读脏数据；（3）三级封锁协议：在一级基础上，读数据前加S锁，直到事务结束释放，可再防止不可重复读。",
            "explanation": "按级别递进，每级解决一个新问题。",
            "difficulty": "hard", "score": 6, "year": 2026, "month": 4, "frequency": 6,
        },
    ],
    "04741": [  # 计算机网络原理
        {
            "content": "OSI参考模型共有（ ）层。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "7",
            "explanation": "OSI七层：物理层、数据链路层、网络层、传输层、会话层、表示层、应用层。",
            "difficulty": "easy", "score": 3, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "TCP协议提供的服务特点包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["面向连接", "可靠传输", "流量控制", "无连接"],
            "answer": "ABC",
            "explanation": "TCP是面向连接的、可靠的传输协议，提供流量控制和拥塞控制。UDP是无连接的。",
            "difficulty": "easy", "score": 4, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "IP地址192.168.1.0/24中，子网掩码是（ ）。",
            "question_type": "single_choice",
            "options": ["255.255.255.0", "255.255.0.0", "255.0.0.0", "255.255.255.128"],
            "answer": "A",
            "explanation": "/24表示前24位为网络号，对应子网掩码255.255.255.0。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "HTTP协议的默认端口号是（ ）。",
            "question_type": "single_choice",
            "options": ["80", "443", "21", "25"],
            "answer": "A",
            "explanation": "HTTP默认80端口，HTTPS默认443端口，FTP默认21端口，SMTP默认25端口。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 9,
        },
    ],
    "02326": [  # 操作系统
        {
            "content": "进程和程序的根本区别在于（ ）。",
            "question_type": "single_choice",
            "options": ["进程是动态的，程序是静态的", "进程存储在磁盘上", "程序可以并发执行", "进程是程序的子集"],
            "answer": "A",
            "explanation": "进程是程序的一次执行过程，是动态概念；程序是指令的有序集合，是静态概念。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "产生死锁的四个必要条件是（ ）。",
            "question_type": "multiple_choice",
            "options": ["互斥条件", "请求与保持条件", "不可剥夺条件", "循环等待条件"],
            "answer": "ABCD",
            "explanation": "四个条件同时成立才会产生死锁，破坏其中任一条件即可预防死锁。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 9,
        },
        {
            "content": "虚拟内存的实现基于（ ）原理。",
            "question_type": "single_choice",
            "options": ["局部性原理", "时间片轮转", "优先级调度", "中断机制"],
            "answer": "A",
            "explanation": "虚拟内存利用程序的时间局部性和空间局部性实现。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "简述进程的三种基本状态及其转换关系。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）就绪态(Ready)：具备运行条件，等待CPU分配；（2）运行态(Running)：占有CPU正在执行；（3）阻塞态(Blocked)：因等待某事件而暂停执行。转换关系：就绪->运行（被调度）、运行->就绪（时间片用完）、运行->阻塞（等待I/O）、阻塞->就绪（I/O完成）。",
            "explanation": "三态+四种转换是操作系统基础。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 8,
        },
    ],
    # ==============================================================
    # 人力资源管理(本科) 专业课
    # ==============================================================
    "00152": [  # 组织行为学
        {
            "content": "马斯洛需要层次理论中，最高层次的需要是（ ）。",
            "question_type": "single_choice",
            "options": ["自我实现需要", "尊重需要", "社交需要", "安全需要"],
            "answer": "A",
            "explanation": "马斯洛五层需要从低到高：生理、安全、社交、尊重、自我实现。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "赫茨伯格双因素理论中的激励因素包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["工作成就感", "工作本身的挑战性", "晋升机会", "工资福利"],
            "answer": "ABC",
            "explanation": "工资福利属于保健因素，不属于激励因素。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "群体决策的优点包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["信息更全面", "方案更多样", "提高决策接受度", "效率一定更高"],
            "answer": "ABC",
            "explanation": "群体决策效率不一定更高（耗时更长），但在质量和接受度方面有优势。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 6,
        },
        {
            "content": "简述组织文化的功能。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）导向功能——引导成员行为方向；（2）凝聚功能——增强组织向心力；（3）约束功能——规范成员行为；（4）激励功能——激发成员积极性；（5）辐射功能——向社会传播组织形象。",
            "explanation": "五大功能，可简记为：导向、凝聚、约束、激励、辐射。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
    "06090": [  # 人员素质测评理论与方法
        {
            "content": "人员素质测评的核心概念是（ ）。",
            "question_type": "single_choice",
            "options": ["对人的素质进行量化描述", "对物品进行评估", "对生产工具的检测", "对市场进行调查"],
            "answer": "A",
            "explanation": "人员素质测评是运用科学方法对人的素质状况进行量化描述的过程。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "结构化面试的主要特点包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["问题预先确定", "评分标准统一", "面试程序规范", "完全自由发挥"],
            "answer": "ABC",
            "explanation": "结构化面试要求问题、程序、评分标准均预先确定，不是完全自由发挥。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "评价中心技术中最常用的方法是（ ）。",
            "question_type": "single_choice",
            "options": ["无领导小组讨论", "笔试", "体检", "背景调查"],
            "answer": "A",
            "explanation": "无领导小组讨论(LGD)是评价中心技术中应用最广泛的方法之一。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "简述信度与效度的关系。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）信度是效度的必要条件——没有信度就没有效度；（2）信度不是效度的充分条件——有信度不一定有效度；（3）效度受信度制约——效度的最高值不超过信度的平方根。",
            "explanation": "三层关系：必要非充分、信度>效度、上限约束。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
    "06091": [  # 薪酬管理
        {
            "content": "薪酬管理的基本原则中最重要的是（ ）。",
            "question_type": "single_choice",
            "options": ["公平性原则", "保密性原则", "简单性原则", "灵活性原则"],
            "answer": "A",
            "explanation": "公平性是薪酬管理的首要原则，包括内部公平、外部公平和个人公平。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "岗位评价的常用方法包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["排列法", "分类法", "因素比较法", "点数法"],
            "answer": "ABCD",
            "explanation": "四种基本的岗位评价方法。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "宽带薪酬结构的特点是（ ）。",
            "question_type": "single_choice",
            "options": ["薪酬等级少，每级跨度大", "薪酬等级多，每级跨度小", "完全固定薪酬", "不设等级"],
            "answer": "A",
            "explanation": "宽带薪酬将传统多级薪酬压缩为少数几个大跨度等级。",
            "difficulty": "medium", "score": 2, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "简述绩效薪酬的优缺点。",
            "question_type": "short_answer",
            "options": [],
            "answer": "优点：（1）激励性强，多劳多得；（2）有利于吸引和保留高绩效员工；（3）控制人工成本。缺点：（1）可能导致短期行为；（2）不利于团队合作；（3）绩效评估困难；（4）可能产生收入不稳定感。",
            "explanation": "分优缺点两面论述，各3-4点。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 6,
        },
    ],
    # ==============================================================
    # 行政管理(专科) 专业课
    # ==============================================================
    "00107": [  # 现代管理学
        {
            "content": "管理的基本职能包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["计划", "组织", "领导", "控制"],
            "answer": "ABCD",
            "explanation": "管理四大基本职能：计划、组织、领导、控制。",
            "difficulty": "easy", "score": 4, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "科学管理理论的创始人是（ ）。",
            "question_type": "single_choice",
            "options": ["泰勒", "法约尔", "韦伯", "梅奥"],
            "answer": "A",
            "explanation": "泰勒被称为'科学管理之父'，代表作《科学管理原理》。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 9,
        },
        {
            "content": "SWOT分析中的W代表（ ）。",
            "question_type": "single_choice",
            "options": ["Weaknesses（劣势）", "Wants（需求）", "Wins（胜利）", "Wills（意愿）"],
            "answer": "A",
            "explanation": "SWOT: Strengths优势、Weaknesses劣势、Opportunities机会、Threats威胁。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "简述计划工作的程序。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）估量机会，确定目标；（2）确定前提条件；（3）拟定和比较备选方案；（4）选择方案；（5）制定派生计划；（6）编制预算。",
            "explanation": "六步程序，从机会评估到预算编制。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
    "00163": [  # 管理心理学
        {
            "content": "管理心理学的研究对象是（ ）。",
            "question_type": "single_choice",
            "options": ["组织中人的心理与行为规律", "市场消费行为", "临床心理治疗", "教育教学心理"],
            "answer": "A",
            "explanation": "管理心理学研究管理活动中人的心理与行为规律。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "态度的三个组成成分是（ ）。",
            "question_type": "multiple_choice",
            "options": ["认知成分", "情感成分", "行为倾向成分", "生理成分"],
            "answer": "ABC",
            "explanation": "态度ABC模型：Affective情感、Behavioral行为倾向、Cognitive认知。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "期望理论的公式是 M = V * E，其中 M 代表（ ）。",
            "question_type": "single_choice",
            "options": ["激励力量", "期望值", "效价", "满意度"],
            "answer": "A",
            "explanation": "弗鲁姆期望理论：M(激励力量)=V(效价)*E(期望值)。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "简述影响群体凝聚力的因素。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）群体规模——规模越小凝聚力越强；（2）成员相似性——背景、价值观相近促进凝聚；（3）群体目标——共同目标增强凝聚力；（4）外部威胁——外部压力促使群体团结；（5）群体成功经历——成功体验增强凝聚力。",
            "explanation": "五因素，注意群体规模与凝聚力呈反向关系。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 6,
        },
    ],
    "00182": [  # 公共关系学
        {
            "content": "公共关系的三个基本要素是（ ）。",
            "question_type": "multiple_choice",
            "options": ["组织", "公众", "传播", "利润"],
            "answer": "ABC",
            "explanation": "公共关系三要素：组织（主体）、公众（客体）、传播（中介）。",
            "difficulty": "easy", "score": 4, "year": 2025, "month": 4, "frequency": 9,
        },
        {
            "content": "危机公关的第一原则是（ ）。",
            "question_type": "single_choice",
            "options": ["快速反应原则", "利润优先原则", "保密原则", "拖延策略"],
            "answer": "A",
            "explanation": "危机发生后应在黄金时间内快速回应，表明态度和措施。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 10, "frequency": 7,
        },
        {
            "content": "简述公共关系的基本职能。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）采集信息——收集内外部环境信息；（2）咨询建议——为管理决策提供参考；（3）协调沟通——处理组织与公众的关系；（4）教育引导——引导公众舆论和组织成员行为；（5）服务社会——承担社会责任。",
            "explanation": "五项基本职能。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 6,
        },
    ],
    "00312": [  # 政治学概论
        {
            "content": "国家的本质属性是（ ）。",
            "question_type": "single_choice",
            "options": ["阶级统治的工具", "社会福利机构", "纯粹的暴力机器", "经济组织"],
            "answer": "A",
            "explanation": "马克思主义认为国家本质上是阶级统治的工具。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "政治权力的来源包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["暴力", "财富", "知识信息", "组织"],
            "answer": "ABCD",
            "explanation": "政治权力来源多元，包括暴力强制、经济财富、知识信息和组织力量等。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 10, "frequency": 6,
        },
        {
            "content": "民主的基本含义是（ ）。",
            "question_type": "fill_blank",
            "options": [],
            "answer": "人民的统治或权力",
            "explanation": "Democracy源自希腊语demos(人民)+kratos(权力/统治)。",
            "difficulty": "easy", "score": 3, "year": 2025, "month": 4, "frequency": 7,
        },
    ],
    "00341": [  # 公文写作与处理
        {
            "content": "公文的最主要特点是（ ）。",
            "question_type": "single_choice",
            "options": ["法定权威性", "文学性", "娱乐性", "随意性"],
            "answer": "A",
            "explanation": "公文是法定机关依法制发的具有法定权威和效力的文书。",
            "difficulty": "easy", "score": 2, "year": 2025, "month": 4, "frequency": 8,
        },
        {
            "content": "按公文行文方向分类，可分为（ ）。",
            "question_type": "multiple_choice",
            "options": ["上行文", "下行文", "平行文", "斜行文"],
            "answer": "ABC",
            "explanation": "公文按行文方向分为上行文（向上级）、下行文（向下级）、平行文（同级或不相隶属机关之间）。",
            "difficulty": "easy", "score": 4, "year": 2025, "month": 10, "frequency": 8,
        },
        {
            "content": "请示的特点包括（ ）。",
            "question_type": "multiple_choice",
            "options": ["一文一事", "必须事前行文", "需要批复", "可以多头请示"],
            "answer": "ABC",
            "explanation": "请示必须一文一事、事前行文、需要上级批复，不允许多头请示。",
            "difficulty": "medium", "score": 4, "year": 2025, "month": 4, "frequency": 7,
        },
        {
            "content": "简述通知的分类及用途。",
            "question_type": "short_answer",
            "options": [],
            "answer": "（1）发布性通知——发布规章制度和行政措施；（2）批转性通知——批转下级或转发上级、不相隶属机关的公文；（3）指示性通知——布置工作、阐明事项；（4）知照性通知——告知事项（会议通知、人事任免等）。",
            "explanation": "四种类型，每种举出典型用途。",
            "difficulty": "medium", "score": 6, "year": 2026, "month": 4, "frequency": 7,
        },
    ],
}


def seed() -> None:
    """Insert question data for Hebei University courses."""
    db = SessionLocal()
    try:
        inserted = 0
        skipped = 0

        for subject_code, questions in QUESTION_BANK.items():
            # Find subject by code
            subject = db.query(Subject).filter(Subject.code == subject_code).first()
            if not subject:
                print(f"  WARNING: Subject '{subject_code}' not found, skipping")
                skipped += len(questions)
                continue

            # Get first chapter for this subject (fallback)
            first_chapter = (
                db.query(Chapter)
                .filter(Chapter.subject_id == subject.id)
                .order_by(Chapter.order)
                .first()
            )

            for idx, q in enumerate(questions):
                # Check duplicate by content + subject_id
                existing = (
                    db.query(Question)
                    .filter(
                        Question.subject_id == subject.id,
                        Question.content == q["content"],
                    )
                    .first()
                )
                if existing:
                    skipped += 1
                    continue

                # Determine chapter: distribute across available chapters
                chapters = (
                    db.query(Chapter)
                    .filter(Chapter.subject_id == subject.id)
                    .order_by(Chapter.order)
                    .all()
                )
                if chapters:
                    chapter_id = chapters[idx % len(chapters)].id
                else:
                    chapter_id = first_chapter.id if first_chapter else None

                import json
                options_json = json.dumps(q["options"], ensure_ascii=False) if q["options"] else "[]"

                question_obj = Question(
                    subject_id=subject.id,
                    content=q["content"],
                    question_type=q["question_type"],
                    options=options_json,
                    answer=q["answer"],
                    explanation=q.get("explanation", ""),
                    year=q.get("year", 2025),
                    month=q.get("month", 4),
                    chapter_id=chapter_id,
                    difficulty=q.get("difficulty", "medium"),
                    frequency=q.get("frequency", 5),
                    score=q.get("score", 2),
                    source=f"河北大学自考题库（{subject.name}）",
                )
                db.add(question_obj)
                inserted += 1

        db.commit()
        print("[OK] 河北大学题库数据填充完成!")
        print(f"   涉及课程: {len(QUESTION_BANK)} 门")
        print(f"   新增题目: {inserted} 道")
        print(f"   跳过(已存在): {skipped} 道")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] 填充失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
