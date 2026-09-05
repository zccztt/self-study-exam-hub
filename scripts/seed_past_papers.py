# -*- coding: utf-8 -*-
"""Seed script: 填充河北省历年真题数据。

为河北大学相关课程填充 2023年10月、2024年4月、2024年10月 三期完整真题试卷。
每套真题：单选20题×2分 + 多选5题×4分 + 填空5题×2分 + 简答4题×6分 + 论述2题×10分 = 100分

Usage:
    python -m scripts.seed_past_papers
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.chapter import Chapter
from backend.models.enrollment import Province
from backend.models.past_paper import PastPaper
from backend.models.question import Question
from backend.models.subject import Subject

# ==================================================================
# 真题数据：每套卷包含完整题目
# ==================================================================

PAPERS = [
    # ================================================================
    # 行政管理学 (00277) — 2023年10月
    # ================================================================
    {
        "subject_code": "00277",
        "year": 2023,
        "month": 10,
        "source": "河北省2023年10月高等教育自学考试真题",
        "questions": [
            # 单选题 20题×2分
            {"content": "行政管理学作为一门独立学科诞生的标志是（ ）的发表。", "question_type": "single_choice", "options": ["《行政学研究》", "《政治与行政》", "《行政学导论》", "《科学管理原理》"], "answer": "A", "explanation": "1887年威尔逊发表《行政学研究》，标志着行政管理学的诞生。", "difficulty": "easy", "score": 2},
            {"content": "行政管理的主体是（ ）。", "question_type": "single_choice", "options": ["国家行政机关", "立法机关", "司法机关", "政党组织"], "answer": "A", "explanation": "行政管理的主体是国家行政机关，即政府及其工作部门。", "difficulty": "easy", "score": 2},
            {"content": "下列属于行政环境特点的是（ ）。", "question_type": "single_choice", "options": ["复杂性", "单一性", "封闭性", "静态性"], "answer": "A", "explanation": "行政环境具有复杂性、动态性和多样性等特点。", "difficulty": "easy", "score": 2},
            {"content": "在我国，最高行政机关是（ ）。", "question_type": "single_choice", "options": ["国务院", "全国人大", "国家主席", "最高法院"], "answer": "A", "explanation": "国务院即中央人民政府，是最高国家行政机关。", "difficulty": "easy", "score": 2},
            {"content": "行政职能的实施基础是（ ）。", "question_type": "single_choice", "options": ["行政权力", "立法权力", "司法权力", "军事权力"], "answer": "A", "explanation": "行政职能以行政权力为后盾和基础。", "difficulty": "easy", "score": 2},
            {"content": "西方国家行政职能经历的第一个阶段是（ ）。", "question_type": "single_choice", "options": ["限制干预阶段", "积极干预阶段", "放松管制阶段", "福利国家阶段"], "answer": "A", "explanation": "'守夜人'时期政府职能有限，主张限制干预。", "difficulty": "medium", "score": 2},
            {"content": "行政组织结构中，上级对下级的指挥与监督关系属于（ ）。", "question_type": "single_choice", "options": ["纵向结构", "横向结构", "矩阵结构", "网络结构"], "answer": "A", "explanation": "纵向结构反映上下级之间的指挥、领导与被领导关系。", "difficulty": "easy", "score": 2},
            {"content": "集权制的优点不包括（ ）。", "question_type": "single_choice", "options": ["有利于发挥下级积极性", "政令统一", "指挥灵便", "有利于统筹兼顾"], "answer": "A", "explanation": "发挥下级积极性是分权制的优点。", "difficulty": "medium", "score": 2},
            {"content": "人事行政中的'事'主要指（ ）。", "question_type": "single_choice", "options": ["职位", "事件", "事务", "事业"], "answer": "A", "explanation": "人事行政的'事'指政府中的职位和工作。", "difficulty": "easy", "score": 2},
            {"content": "品位分类制度的典型代表国家是（ ）。", "question_type": "single_choice", "options": ["英国", "美国", "法国", "日本"], "answer": "A", "explanation": "英国是品位分类的典型代表。", "difficulty": "easy", "score": 2},
            {"content": "零基预算法的基本特征是（ ）。", "question_type": "single_choice", "options": ["不考虑以前年度的预算基数", "以上年预算为基础", "仅调整增量部分", "保持基数不变"], "answer": "A", "explanation": "零基预算从零开始审核每一项支出的必要性。", "difficulty": "medium", "score": 2},
            {"content": "行政决策的第一步是（ ）。", "question_type": "single_choice", "options": ["发现问题", "拟定方案", "评估方案", "执行方案"], "answer": "A", "explanation": "发现问题、界定问题是行政决策的起点。", "difficulty": "easy", "score": 2},
            {"content": "头脑风暴法属于（ ）方案设计方法。", "question_type": "single_choice", "options": ["创造性思维方法", "定量分析方法", "模拟方法", "经验判断法"], "answer": "A", "explanation": "头脑风暴法鼓励自由思考，属于创造性思维方法。", "difficulty": "easy", "score": 2},
            {"content": "行政执行的起始环节是（ ）。", "question_type": "single_choice", "options": ["计划准备", "组织动员", "具体实施", "检查总结"], "answer": "A", "explanation": "执行前需要进行计划准备和资源筹备。", "difficulty": "easy", "score": 2},
            {"content": "行政协调的目的是（ ）。", "question_type": "single_choice", "options": ["统一意志和行动", "扩大行政权力", "增加组织层级", "减少行政人员"], "answer": "A", "explanation": "行政协调旨在消除分歧、统一认识和行动。", "difficulty": "easy", "score": 2},
            {"content": "行政监督体系中，来自政党的监督属于（ ）。", "question_type": "single_choice", "options": ["外部监督", "内部监督", "自我监督", "专门监督"], "answer": "A", "explanation": "政党监督属于行政系统外部监督。", "difficulty": "easy", "score": 2},
            {"content": "行政法制的核心内容是（ ）。", "question_type": "single_choice", "options": ["依法行政", "行政立法", "行政处罚", "行政强制"], "answer": "A", "explanation": "依法行政是行政法制的核心，要求行政机关依法办事。", "difficulty": "easy", "score": 2},
            {"content": "行政道德的基本功能是（ ）。", "question_type": "single_choice", "options": ["规范与约束行政行为", "制定行政法规", "惩罚腐败行为", "考核公务人员"], "answer": "A", "explanation": "行政道德通过内在信念约束行政行为。", "difficulty": "easy", "score": 2},
            {"content": "行政效率测量的基本方法是（ ）。", "question_type": "single_choice", "options": ["行政投入与产出的比较", "民意调查", "专家评审", "领导评分"], "answer": "A", "explanation": "行政效率=行政产出/行政投入，本质是投入产出比。", "difficulty": "medium", "score": 2},
            {"content": "行政改革的根本动力来自（ ）。", "question_type": "single_choice", "options": ["社会环境的变化", "领导意志", "技术发展", "国际压力"], "answer": "A", "explanation": "社会环境变化是推动行政改革的根本动力。", "difficulty": "easy", "score": 2},
            # 多选题 5题×4分
            {"content": "行政管理的特点包括（ ）。", "question_type": "multiple_choice", "options": ["执行性", "政治性", "权威性", "公共性"], "answer": "ABCD", "explanation": "行政管理具有执行性、政治性、权威性和公共性等特点。", "difficulty": "medium", "score": 4},
            {"content": "行政组织设置原则包括（ ）。", "question_type": "multiple_choice", "options": ["精简原则", "统一原则", "效能原则", "法治原则"], "answer": "ABCD", "explanation": "行政组织设置需遵循精简、统一、效能、法治等原则。", "difficulty": "medium", "score": 4},
            {"content": "行政领导者的产生方式有（ ）。", "question_type": "multiple_choice", "options": ["选举制", "委任制", "考任制", "聘任制"], "answer": "ABCD", "explanation": "四种方式各有适用范围和利弊。", "difficulty": "easy", "score": 4},
            {"content": "行政监督的原则包括（ ）。", "question_type": "multiple_choice", "options": ["合法性原则", "经常性原则", "公正性原则", "实效性原则"], "answer": "ABCD", "explanation": "行政监督应坚持合法、经常、公正和注重实效。", "difficulty": "medium", "score": 4},
            {"content": "影响行政效率的主要因素有（ ）。", "question_type": "multiple_choice", "options": ["组织结构", "人员素质", "管理方法", "法制建设"], "answer": "ABCD", "explanation": "组织结构、人员素质、方法和法制都影响行政效率。", "difficulty": "medium", "score": 4},
            # 填空题 5题×2分
            {"content": "行政管理学的研究对象是______。", "question_type": "fill_blank", "options": [], "answer": "国家行政机关对公共事务的管理活动及其规律", "explanation": "核心是行政活动及其规律。", "difficulty": "easy", "score": 2},
            {"content": "行政组织中管理幅度与管理层次成______关系。", "question_type": "fill_blank", "options": [], "answer": "反比", "explanation": "管理幅度越大，层次越少。", "difficulty": "easy", "score": 2},
            {"content": "行政决策按决策条件分为确定型决策、风险型决策和______。", "question_type": "fill_blank", "options": [], "answer": "不确定型决策", "explanation": "三类决策的区分依据是信息掌握程度。", "difficulty": "easy", "score": 2},
            {"content": "我国公务员制度正式建立的标志是______的颁布实施。", "question_type": "fill_blank", "options": [], "answer": "《国家公务员暂行条例》", "explanation": "1993年颁布施行。", "difficulty": "medium", "score": 2},
            {"content": "行政效率的公式是：行政效率=______/行政投入。", "question_type": "fill_blank", "options": [], "answer": "行政产出", "explanation": "效率即产出与投入之比。", "difficulty": "easy", "score": 2},
            # 简答题 4题×6分
            {"content": "简述行政职能转变的主要内容。", "question_type": "short_answer", "options": [], "answer": "（1）职能重心的转变——由政治统治职能为主转向经济社会管理职能为主；（2）职能方式的转变——由直接管理为主转向间接管理为主；（3）职能关系的调整——理顺中央与地方、政府与市场、政府与社会的关系。", "explanation": "三个转变维度。", "difficulty": "medium", "score": 6},
            {"content": "简述行政决策科学化的要求。", "question_type": "short_answer", "options": [], "answer": "（1）建立科学的决策体制——领导、参谋、信息系统健全；（2）遵循科学的决策程序——发现问题、拟定方案、评估选优；（3）运用科学的决策方法——定性与定量相结合；（4）提高决策者素质——科学态度与民主作风。", "explanation": "四方面要求。", "difficulty": "medium", "score": 6},
            {"content": "简述行政监督的基本功能。", "question_type": "short_answer", "options": [], "answer": "（1）预防功能——事前防止违法违规行为发生；（2）纠错功能——发现并纠正行政偏差和失误；（3）补救功能——对已造成损害进行补偿和救济；（4）教育功能——通过监督案例警示教育。", "explanation": "四大功能：预防、纠错、补救、教育。", "difficulty": "medium", "score": 6},
            {"content": "简述提高行政效率的途径。", "question_type": "short_answer", "options": [], "answer": "（1）优化行政组织结构，精简机构和人员；（2）提高行政人员素质和能力；（3）改善行政管理方法和技术手段；（4）健全行政法规制度；（5）加强行政监督。", "explanation": "五条途径。", "difficulty": "medium", "score": 6},
            # 论述题 2题×10分
            {"content": "试论我国行政改革的主要内容和方向。", "question_type": "essay", "options": [], "answer": "（1）转变政府职能——建设服务型政府，减少对微观经济的直接干预；（2）优化组织结构——推进大部制改革，减少行政层级；（3）完善运行机制——推进依法行政，提高行政透明度；（4）加强队伍建设——深化公务员制度改革，提高行政能力；（5）创新管理方式——运用信息技术推进电子政务。方向：建设法治政府、廉洁政府、服务型政府。", "explanation": "从职能、结构、机制、队伍、方式五方面论述，最后总结方向。", "difficulty": "hard", "score": 10},
            {"content": "试论行政领导在行政管理中的地位和作用。", "question_type": "essay", "options": [], "answer": "（1）地位：行政领导是行政管理活动的核心和关键环节，领导者是组织的灵魂和方向引导者。（2）作用：①战略决策作用——确定组织目标和发展方向；②组织指挥作用——整合资源、协调各方、推动执行；③激励约束作用——调动下属积极性并规范行为；④创新变革作用——推动组织适应环境变化。（3）对领导者的要求：政治素质、业务能力、领导艺术三者兼备。", "explanation": "从地位、作用（四点）、要求三个层次展开。", "difficulty": "hard", "score": 10},
        ],
    },
    # ================================================================
    # 行政管理学 (00277) — 2024年4月
    # ================================================================
    {
        "subject_code": "00277",
        "year": 2024,
        "month": 4,
        "source": "河北省2024年4月高等教育自学考试真题",
        "questions": [
            {"content": "古德诺对政治与行政关系的经典论述出自其著作（ ）。", "question_type": "single_choice", "options": ["《政治与行政》", "《行政学研究》", "《行政学导论》", "《行政国家》"], "answer": "A", "explanation": "1900年古德诺发表《政治与行政》。", "difficulty": "easy", "score": 2},
            {"content": "行政权力的根本来源是（ ）。", "question_type": "single_choice", "options": ["人民主权", "暴力强制", "财产占有", "血缘关系"], "answer": "A", "explanation": "人民主权是行政权力的最终来源，我国宪法规定一切权力属于人民。", "difficulty": "easy", "score": 2},
            {"content": "'经济人'假设的提出者是（ ）。", "question_type": "single_choice", "options": ["亚当·斯密", "韦伯", "泰勒", "梅奥"], "answer": "A", "explanation": "亚当·斯密在《国富论》中提出经济人假设。", "difficulty": "easy", "score": 2},
            {"content": "科层制理论的创立者是（ ）。", "question_type": "single_choice", "options": ["韦伯", "泰勒", "法约尔", "西蒙"], "answer": "A", "explanation": "韦伯提出理想的科层制（官僚制）组织理论。", "difficulty": "easy", "score": 2},
            {"content": "行政组织中'帕金森定律'揭示的现象是（ ）。", "question_type": "single_choice", "options": ["机构和人员不断膨胀", "效率不断提高", "层级不断减少", "权力不断分散"], "answer": "A", "explanation": "帕金森定律揭示官僚组织中机构和人员自我膨胀的规律。", "difficulty": "medium", "score": 2},
            {"content": "我国公务员职务分为领导职务和（ ）。", "question_type": "single_choice", "options": ["非领导职务", "技术职务", "管理职务", "专业职务"], "answer": "A", "explanation": "2018年修订后改为领导职务和职级，但传统分为领导和非领导。", "difficulty": "easy", "score": 2},
            {"content": "预算年度开始到结束的时间在我国是（ ）。", "question_type": "single_choice", "options": ["1月1日至12月31日", "4月1日至次年3月31日", "7月1日至次年6月30日", "10月1日至次年9月30日"], "answer": "A", "explanation": "我国预算年度与自然年度一致。", "difficulty": "easy", "score": 2},
            {"content": "行政信息公开制度的核心原则是（ ）。", "question_type": "single_choice", "options": ["以公开为原则，不公开为例外", "完全保密", "选择性公开", "内部公开"], "answer": "A", "explanation": "阳光政府建设要求信息以公开为常态。", "difficulty": "easy", "score": 2},
            {"content": "新公共管理运动兴起的时代背景是（ ）。", "question_type": "single_choice", "options": ["政府财政危机和效率困境", "经济高速增长", "国际和平稳定", "科技快速发展"], "answer": "A", "explanation": "20世纪70-80年代西方福利国家面临财政危机和效率质疑。", "difficulty": "medium", "score": 2},
            {"content": "行政效率的首要前提是（ ）。", "question_type": "single_choice", "options": ["效果保证", "投入减少", "人员精简", "技术先进"], "answer": "A", "explanation": "效率必须以效果为前提，无效果的效率没有意义。", "difficulty": "medium", "score": 2},
            {"content": "行政程序的首要特征是（ ）。", "question_type": "single_choice", "options": ["法定性", "灵活性", "随意性", "保密性"], "answer": "A", "explanation": "行政程序必须由法律规定和保障。", "difficulty": "easy", "score": 2},
            {"content": "行政责任的核心内容是（ ）。", "question_type": "single_choice", "options": ["行政机关及其公务人员因违法或不当行使权力应承担的否定性后果", "获得行政奖励", "享有行政特权", "扩大行政权限"], "answer": "A", "explanation": "行政责任是违法或不当行政的法律后果。", "difficulty": "easy", "score": 2},
            {"content": "我国最高国家行政监察机关是（ ）。", "question_type": "single_choice", "options": ["国家监察委员会", "最高人民检察院", "中纪委", "国务院"], "answer": "A", "explanation": "2018年后国家监察委为最高监察机关。", "difficulty": "easy", "score": 2},
            {"content": "电子政务的核心价值在于（ ）。", "question_type": "single_choice", "options": ["提高政府服务效率和便民水平", "增加政府人员", "扩大政府权力", "减少法律约束"], "answer": "A", "explanation": "电子政务根本目的是便民高效。", "difficulty": "easy", "score": 2},
            {"content": "行政文化的核心要素是（ ）。", "question_type": "single_choice", "options": ["行政价值观", "行政建筑", "行政设备", "行政档案"], "answer": "A", "explanation": "行政文化以行政价值观为核心。", "difficulty": "easy", "score": 2},
            {"content": "机关管理的首要任务是（ ）。", "question_type": "single_choice", "options": ["为行政决策和管理提供服务保障", "获取利润", "扩大规模", "招聘人员"], "answer": "A", "explanation": "机关管理是行政管理的辅助和后勤保障。", "difficulty": "easy", "score": 2},
            {"content": "我国行政体制的根本原则是（ ）。", "question_type": "single_choice", "options": ["民主集中制", "三权分立", "议行合一", "司法独立"], "answer": "A", "explanation": "我国行政体制遵循民主集中制原则。", "difficulty": "easy", "score": 2},
            {"content": "里格斯的行政生态理论将发展中国家的行政模式称为（ ）。", "question_type": "single_choice", "options": ["棱柱形行政模式", "融合型行政模式", "衍射型行政模式", "集中型行政模式"], "answer": "A", "explanation": "里格斯用棱柱形比喻过渡社会的行政特征。", "difficulty": "medium", "score": 2},
            {"content": "行政决策中的'满意原则'由（ ）提出。", "question_type": "single_choice", "options": ["西蒙", "林德布洛姆", "德洛尔", "拉斯韦尔"], "answer": "A", "explanation": "赫伯特·西蒙提出有限理性和满意原则。", "difficulty": "medium", "score": 2},
            {"content": "行政发展的终极目标是（ ）。", "question_type": "single_choice", "options": ["实现公共利益最大化", "扩大政府规模", "增加税收", "控制社会"], "answer": "A", "explanation": "行政发展最终为实现公共利益服务。", "difficulty": "easy", "score": 2},
            # 多选题 5题×4分
            {"content": "行政权力的特征包括（ ）。", "question_type": "multiple_choice", "options": ["公共性", "强制性", "执行性", "有限性"], "answer": "ABCD", "explanation": "行政权力具有公共性、强制性、执行性和有限性。", "difficulty": "medium", "score": 4},
            {"content": "行政组织的构成要素有（ ）。", "question_type": "multiple_choice", "options": ["人员", "目标", "经费", "法规制度"], "answer": "ABCD", "explanation": "行政组织由人员、目标、经费、制度等要素构成。", "difficulty": "medium", "score": 4},
            {"content": "行政决策的类型按决策层次分为（ ）。", "question_type": "multiple_choice", "options": ["战略决策", "战术决策", "业务决策", "确定型决策"], "answer": "ABC", "explanation": "确定型决策是按条件分类，不是按层次分类。", "difficulty": "medium", "score": 4},
            {"content": "行政执行的原则包括（ ）。", "question_type": "multiple_choice", "options": ["忠实执行与灵活运用相结合", "果断迅速与注重效益相结合", "发扬民主与强调集中相结合", "追求利润最大化"], "answer": "ABC", "explanation": "追求利润不是行政执行的原则。", "difficulty": "medium", "score": 4},
            {"content": "我国行政改革的基本经验包括（ ）。", "question_type": "multiple_choice", "options": ["坚持正确的指导思想", "坚持从国情出发", "坚持渐进式改革", "加强法制保障"], "answer": "ABCD", "explanation": "四条基本经验均正确。", "difficulty": "medium", "score": 4},
            # 填空题 5题×2分
            {"content": "威尔逊在______年发表了《行政学研究》。", "question_type": "fill_blank", "options": [], "answer": "1887", "explanation": "1887年，标志行政学诞生。", "difficulty": "easy", "score": 2},
            {"content": "行政领导的方式按领导作风分为专断型、民主型和______。", "question_type": "fill_blank", "options": [], "answer": "放任型", "explanation": "三种基本领导风格。", "difficulty": "easy", "score": 2},
            {"content": "行政沟通按方向分为上行沟通、下行沟通和______。", "question_type": "fill_blank", "options": [], "answer": "平行沟通", "explanation": "三个方向的信息传递。", "difficulty": "easy", "score": 2},
            {"content": "PPBS是指______预算制度。", "question_type": "fill_blank", "options": [], "answer": "计划规划预算", "explanation": "Planning Programming Budgeting System。", "difficulty": "medium", "score": 2},
            {"content": "行政改革的阻力主要来自利益因素、______和习惯因素。", "question_type": "fill_blank", "options": [], "answer": "观念因素", "explanation": "三大阻力来源。", "difficulty": "medium", "score": 2},
            # 简答题 4题×6分
            {"content": "简述行政权力与行政责任的关系。", "question_type": "short_answer", "options": [], "answer": "（1）行政权力与行政责任是对等统一的——有权必有责，用权必担责；（2）行政权力是行政责任的前提——没有权力则无从谈责任；（3）行政责任是行政权力的制约——责任机制防止权力滥用；（4）二者统一于依法行政的实践中。", "explanation": "四层关系：对等、前提、制约、统一。", "difficulty": "medium", "score": 6},
            {"content": "简述行政执行中的控制手段。", "question_type": "short_answer", "options": [], "answer": "（1）行政指导——通过指示、命令引导执行方向；（2）行政协调——解决执行中的矛盾冲突；（3）行政沟通——确保信息畅通、上下衔接；（4）行政监督——检查执行情况、纠正偏差；（5）行政奖惩——激励和约束执行人员。", "explanation": "五种控制手段。", "difficulty": "medium", "score": 6},
            {"content": "简述西方新公共管理运动的主要主张。", "question_type": "short_answer", "options": [], "answer": "（1）引入市场竞争机制——打破政府垄断；（2）以顾客为导向——关注公民需求和满意度；（3）推行绩效管理——注重结果而非过程；（4）分权化管理——赋予基层更大自主权；（5）政府再造——流程重组、组织精简。", "explanation": "五大主张。", "difficulty": "medium", "score": 6},
            {"content": "简述依法行政的基本要求。", "question_type": "short_answer", "options": [], "answer": "（1）合法行政——行政机关必须在法律授权范围内活动；（2）合理行政——行政行为应符合比例原则和公平正义；（3）程序正当——遵循法定程序保障当事人权利；（4）高效便民——提高办事效率、方便群众；（5）诚实守信——保护当事人信赖利益；（6）权责统一——有权必有责。", "explanation": "六项基本要求。", "difficulty": "medium", "score": 6},
            # 论述题 2题×10分
            {"content": "试论行政组织理论的发展及其对我国行政改革的启示。", "question_type": "essay", "options": [], "answer": "（1）古典组织理论：韦伯科层制强调规则和层级，泰勒科学管理强调效率——启示：规范化和标准化建设；（2）行为科学理论：梅奥人际关系学派强调人的因素——启示：关注公务人员积极性和组织文化；（3）系统权变理论：强调组织与环境互动——启示：行政组织须适应外部环境变化；（4）新公共管理理论：强调市场化和结果导向——启示：引入竞争机制和绩效评估。对我国的综合启示：既要借鉴西方经验，又要立足国情，走中国特色行政改革之路。", "explanation": "按理论发展脉络分阶段论述，每阶段结合我国启示。", "difficulty": "hard", "score": 10},
            {"content": "试论行政决策民主化与科学化的关系。", "question_type": "essay", "options": [], "answer": "（1）民主化含义：扩大公民参与、集中群众智慧、接受社会监督；（2）科学化含义：运用科学方法、遵循客观规律、建立科学体制；（3）二者关系：互相促进、互为补充——民主化为科学化提供信息基础和合法性保障，科学化使民主化的成果得以有效转化为正确决策；（4）统一途径：完善公众参与制度、建立专家咨询系统、推进决策信息公开、健全决策责任追究制度。", "explanation": "分别定义→阐述关系→统一途径。", "difficulty": "hard", "score": 10},
        ],
    },
    # ================================================================
    # 数据结构 (02331) — 2024年10月
    # ================================================================
    {
        "subject_code": "02331",
        "year": 2024,
        "month": 10,
        "source": "河北省2024年10月高等教育自学考试真题",
        "questions": [
            # 单选题 20题×2分
            {"content": "数据结构研究的三个方面是数据的逻辑结构、存储结构和（ ）。", "question_type": "single_choice", "options": ["数据的运算", "数据的类型", "数据的规模", "数据的来源"], "answer": "A", "explanation": "数据结构=逻辑结构+存储结构+运算。", "difficulty": "easy", "score": 2},
            {"content": "线性表的顺序存储结构的最大优点是（ ）。", "question_type": "single_choice", "options": ["可以随机访问表中任一元素", "插入操作方便", "删除操作方便", "不需要连续空间"], "answer": "A", "explanation": "顺序存储支持O(1)随机访问。", "difficulty": "easy", "score": 2},
            {"content": "在单链表中，增加头结点的目的是（ ）。", "question_type": "single_choice", "options": ["使运算统一和方便", "节省存储空间", "提高访问速度", "使链表至少有一个结点"], "answer": "A", "explanation": "头结点统一了空表和非空表的操作。", "difficulty": "easy", "score": 2},
            {"content": "栈和队列的共同特点是（ ）。", "question_type": "single_choice", "options": ["只允许在端点处插入和删除", "都是先进先出", "都是后进先出", "没有任何限制"], "answer": "A", "explanation": "栈和队列都是操作受限的线性表。", "difficulty": "easy", "score": 2},
            {"content": "递归算法转换为非递归算法通常使用的数据结构是（ ）。", "question_type": "single_choice", "options": ["栈", "队列", "数组", "链表"], "answer": "A", "explanation": "栈可以模拟递归调用的行为。", "difficulty": "easy", "score": 2},
            {"content": "一棵完全二叉树有100个结点，则其叶子结点数为（ ）。", "question_type": "single_choice", "options": ["50", "49", "51", "48"], "answer": "A", "explanation": "n=100，n0=⌈n/2⌉=50。", "difficulty": "medium", "score": 2},
            {"content": "二叉树的前序遍历序列为ABDECFG，中序遍历序列为DBEAFCG，则后序遍历序列为（ ）。", "question_type": "single_choice", "options": ["DEBFGCA", "DEBGFCA", "DEAFGCB", "DBEFGCA"], "answer": "A", "explanation": "根据前序和中序还原树结构再求后序。", "difficulty": "hard", "score": 2},
            {"content": "哈夫曼树中没有度为（ ）的结点。", "question_type": "single_choice", "options": ["1", "0", "2", "3"], "answer": "A", "explanation": "哈夫曼树是严格的二叉树，只有度0和度2的结点。", "difficulty": "medium", "score": 2},
            {"content": "图的广度优先搜索(BFS)使用的辅助数据结构是（ ）。", "question_type": "single_choice", "options": ["队列", "栈", "堆", "数组"], "answer": "A", "explanation": "BFS按层遍历，使用队列辅助。", "difficulty": "easy", "score": 2},
            {"content": "在一个有向图中，所有顶点的入度之和等于所有顶点的出度之和，这个和等于（ ）。", "question_type": "single_choice", "options": ["边数", "顶点数", "顶点数-1", "边数×2"], "answer": "A", "explanation": "每条边贡献一个入度和一个出度。", "difficulty": "medium", "score": 2},
            {"content": "Dijkstra算法用于求解（ ）。", "question_type": "single_choice", "options": ["单源最短路径", "所有顶点间最短路径", "最小生成树", "拓扑排序"], "answer": "A", "explanation": "Dijkstra求从一个源点到其他所有顶点的最短路径。", "difficulty": "easy", "score": 2},
            {"content": "拓扑排序适用于（ ）。", "question_type": "single_choice", "options": ["有向无环图", "无向图", "有向有环图", "完全图"], "answer": "A", "explanation": "拓扑排序要求DAG（有向无环图）。", "difficulty": "easy", "score": 2},
            {"content": "折半查找的平均时间复杂度为（ ）。", "question_type": "single_choice", "options": ["O(log₂n)", "O(n)", "O(n²)", "O(1)"], "answer": "A", "explanation": "折半查找每次将搜索范围缩小一半。", "difficulty": "easy", "score": 2},
            {"content": "哈希函数设计的基本要求是（ ）。", "question_type": "single_choice", "options": ["计算简单且地址分布均匀", "只要计算简单", "只要地址唯一", "不产生冲突"], "answer": "A", "explanation": "好的哈希函数应简单且均匀分散。", "difficulty": "easy", "score": 2},
            {"content": "稳定排序中，相等元素的相对位置（ ）。", "question_type": "single_choice", "options": ["不变", "一定改变", "随机变化", "无法确定"], "answer": "A", "explanation": "稳定排序保持相等元素的原始相对顺序。", "difficulty": "easy", "score": 2},
            {"content": "直接插入排序在最好情况下的时间复杂度是（ ）。", "question_type": "single_choice", "options": ["O(n)", "O(n²)", "O(nlogn)", "O(1)"], "answer": "A", "explanation": "已排序序列只需n-1次比较，无移动。", "difficulty": "easy", "score": 2},
            {"content": "堆排序的时间复杂度为（ ）。", "question_type": "single_choice", "options": ["O(nlogn)", "O(n²)", "O(n)", "O(logn)"], "answer": "A", "explanation": "堆排序最好、最坏、平均都是O(nlogn)。", "difficulty": "easy", "score": 2},
            {"content": "归并排序的空间复杂度为（ ）。", "question_type": "single_choice", "options": ["O(n)", "O(1)", "O(logn)", "O(n²)"], "answer": "A", "explanation": "归并排序需要O(n)辅助空间。", "difficulty": "medium", "score": 2},
            {"content": "B树是一种（ ）查找结构。", "question_type": "single_choice", "options": ["多路平衡", "二叉", "线性", "散列"], "answer": "A", "explanation": "B树是多路平衡搜索树，适合磁盘存储。", "difficulty": "easy", "score": 2},
            {"content": "串的模式匹配中，KMP算法的优势是（ ）。", "question_type": "single_choice", "options": ["主串指针不回溯", "不需要预处理", "空间复杂度为O(1)", "适用于任何数据类型"], "answer": "A", "explanation": "KMP利用next数组避免主串指针回退。", "difficulty": "medium", "score": 2},
            # 多选题 5题×4分
            {"content": "线性表可采用的存储结构有（ ）。", "question_type": "multiple_choice", "options": ["顺序存储", "链式存储", "索引存储", "散列存储"], "answer": "ABCD", "explanation": "四种都是数据的基本存储结构。", "difficulty": "medium", "score": 4},
            {"content": "下列排序算法中属于稳定排序的有（ ）。", "question_type": "multiple_choice", "options": ["冒泡排序", "直接插入排序", "归并排序", "基数排序"], "answer": "ABCD", "explanation": "快排、堆排、选择排序不稳定。", "difficulty": "medium", "score": 4},
            {"content": "图的存储方式包括（ ）。", "question_type": "multiple_choice", "options": ["邻接矩阵", "邻接表", "十字链表", "邻接多重表"], "answer": "ABCD", "explanation": "图的四种常用存储结构。", "difficulty": "medium", "score": 4},
            {"content": "二叉树的遍历方式有（ ）。", "question_type": "multiple_choice", "options": ["前序遍历", "中序遍历", "后序遍历", "层次遍历"], "answer": "ABCD", "explanation": "四种标准遍历方式。", "difficulty": "easy", "score": 4},
            {"content": "解决哈希冲突的方法有（ ）。", "question_type": "multiple_choice", "options": ["开放定址法", "链地址法", "再散列法", "公共溢出区法"], "answer": "ABCD", "explanation": "四种冲突处理方法。", "difficulty": "medium", "score": 4},
            # 填空题 5题×2分
            {"content": "n个结点的无向完全图有______条边。", "question_type": "fill_blank", "options": [], "answer": "n(n-1)/2", "explanation": "每对顶点间有一条边。", "difficulty": "easy", "score": 2},
            {"content": "具有n个顶点的连通图至少有______条边。", "question_type": "fill_blank", "options": [], "answer": "n-1", "explanation": "连通图至少是一棵树。", "difficulty": "easy", "score": 2},
            {"content": "长度为n的有序表进行折半查找，最多比较______次。", "question_type": "fill_blank", "options": [], "answer": "⌊log₂n⌋+1", "explanation": "折半查找判定树高度。", "difficulty": "medium", "score": 2},
            {"content": "快速排序的平均时间复杂度为______。", "question_type": "fill_blank", "options": [], "answer": "O(nlogn)", "explanation": "平均和最好都是O(nlogn)。", "difficulty": "easy", "score": 2},
            {"content": "在一棵二叉树中，叶子结点数n0与度为2的结点数n2的关系为n0=______。", "question_type": "fill_blank", "options": [], "answer": "n2+1", "explanation": "二叉树性质：n0=n2+1。", "difficulty": "easy", "score": 2},
            # 简答题 4题×6分
            {"content": "简述顺序存储和链式存储的优缺点比较。", "question_type": "short_answer", "options": [], "answer": "顺序存储：优点——随机访问O(1)、存储密度大；缺点——插入删除需移动大量元素O(n)、需要预分配连续空间。链式存储：优点——插入删除仅需修改指针O(1)、动态分配空间；缺点——不支持随机访问需顺序遍历O(n)、每个结点需额外存储指针域。", "explanation": "从访问、增删、空间三方面对比。", "difficulty": "medium", "score": 6},
            {"content": "简述Prim算法和Kruskal算法的基本思想。", "question_type": "short_answer", "options": [], "answer": "Prim算法：从任一顶点出发，每次将与当前生成树距离最近的顶点加入，直到所有顶点加入。适合稠密图，时间O(n²)。Kruskal算法：按边权值从小到大排序，依次加入不构成回路的边，直到n-1条边。适合稀疏图，时间O(eloge)。", "explanation": "分别说明思想、适用场景和复杂度。", "difficulty": "medium", "score": 6},
            {"content": "简述快速排序的基本思想及其时间复杂度分析。", "question_type": "short_answer", "options": [], "answer": "基本思想：选取一个基准元素（pivot），将序列分为比基准小和比基准大的两部分，对两部分递归排序。时间复杂度：最好O(nlogn)——每次平均分割；平均O(nlogn)；最坏O(n²)——序列已有序且每次选首元素为基准。", "explanation": "思想+三种复杂度情况。", "difficulty": "medium", "score": 6},
            {"content": "简述AVL树的定义及其旋转操作的类型。", "question_type": "short_answer", "options": [], "answer": "AVL树定义：任一结点的左右子树高度差（平衡因子）绝对值不超过1的二叉查找树。旋转类型：（1）LL旋转——左子树的左子树插入导致不平衡，右旋；（2）RR旋转——右子树的右子树插入，左旋；（3）LR旋转——左子树的右子树插入，先左旋再右旋；（4）RL旋转——右子树的左子树插入，先右旋再左旋。", "explanation": "定义+四种旋转。", "difficulty": "hard", "score": 6},
            # 论述题 2题×10分
            {"content": "试论述图的深度优先搜索(DFS)和广度优先搜索(BFS)算法，并比较二者的异同。", "question_type": "essay", "options": [], "answer": "DFS：从某顶点出发，沿一条路径尽可能深入，无法继续时回溯到最近的岔路口继续。使用栈（递归调用栈）辅助，时间O(n+e)。BFS：从某顶点出发，先访问所有邻接顶点，再依次访问邻接顶点的邻接顶点。使用队列辅助，时间O(n+e)。相同点：都能遍历图的所有顶点，时间复杂度相同，都需要标记已访问。不同点：DFS更深入（适合路径问题），BFS更广泛（适合最短路径）；DFS空间与深度成正比，BFS空间与宽度成正比；DFS产生深度优先生成树，BFS产生广度优先生成树。", "explanation": "分别描述算法+辅助结构+复杂度，再比较异同。", "difficulty": "hard", "score": 10},
            {"content": "试论述哈希表的基本原理、常用哈希函数的构造方法和冲突处理策略。", "question_type": "essay", "options": [], "answer": "基本原理：通过哈希函数将关键字映射到存储地址，实现O(1)平均查找。哈希函数构造：（1）除留余数法H(k)=k mod p（p取不大于表长的最大质数）；（2）直接定址法H(k)=ak+b；（3）数字分析法；（4）平方取中法。冲突处理：（1）开放定址法——线性探测H(k)+di、二次探测±i²、双重散列；（2）链地址法——同义词链表；（3）再哈希法——使用第二个哈希函数。性能分析：装填因子α=n/m越小冲突越少，查找效率越高。", "explanation": "原理→构造方法(4种)→冲突处理(3类)→性能因素。", "difficulty": "hard", "score": 10},
        ],
    },
    # ================================================================
    # 计算机网络原理 (04741) — 2024年4月
    # ================================================================
    {
        "subject_code": "04741",
        "year": 2024,
        "month": 4,
        "source": "河北省2024年4月高等教育自学考试真题",
        "questions": [
            # 单选题 20题×2分
            {"content": "计算机网络最基本的功能是（ ）。", "question_type": "single_choice", "options": ["数据通信", "资源共享", "分布式处理", "远程登录"], "answer": "A", "explanation": "数据通信是计算机网络最基本的功能。", "difficulty": "easy", "score": 2},
            {"content": "OSI参考模型中负责数据传输路径选择的是（ ）。", "question_type": "single_choice", "options": ["网络层", "传输层", "数据链路层", "物理层"], "answer": "A", "explanation": "网络层负责路由选择和分组转发。", "difficulty": "easy", "score": 2},
            {"content": "TCP/IP体系结构分为（ ）层。", "question_type": "single_choice", "options": ["4", "5", "7", "3"], "answer": "A", "explanation": "TCP/IP四层：网络接口层、网际层、传输层、应用层。", "difficulty": "easy", "score": 2},
            {"content": "以太网使用的介质访问控制方法是（ ）。", "question_type": "single_choice", "options": ["CSMA/CD", "令牌环", "CSMA/CA", "FDDI"], "answer": "A", "explanation": "以太网使用CSMA/CD载波监听多路访问/冲突检测。", "difficulty": "easy", "score": 2},
            {"content": "IPv4地址长度为（ ）位。", "question_type": "single_choice", "options": ["32", "48", "64", "128"], "answer": "A", "explanation": "IPv4为32位，IPv6为128位。", "difficulty": "easy", "score": 2},
            {"content": "UDP协议的主要特点是（ ）。", "question_type": "single_choice", "options": ["无连接、不可靠", "面向连接、可靠", "面向连接、不可靠", "无连接、可靠"], "answer": "A", "explanation": "UDP提供无连接的不可靠传输服务。", "difficulty": "easy", "score": 2},
            {"content": "域名系统DNS的主要功能是（ ）。", "question_type": "single_choice", "options": ["域名到IP地址的映射", "IP地址分配", "路由选择", "数据加密"], "answer": "A", "explanation": "DNS将域名解析为IP地址。", "difficulty": "easy", "score": 2},
            {"content": "TCP使用的流量控制机制是（ ）。", "question_type": "single_choice", "options": ["滑动窗口", "令牌桶", "漏桶", "优先级队列"], "answer": "A", "explanation": "TCP通过滑动窗口实现流量控制。", "difficulty": "easy", "score": 2},
            {"content": "电子邮件发送使用的协议是（ ）。", "question_type": "single_choice", "options": ["SMTP", "POP3", "IMAP", "FTP"], "answer": "A", "explanation": "SMTP负责发送，POP3/IMAP负责接收。", "difficulty": "easy", "score": 2},
            {"content": "子网掩码的作用是（ ）。", "question_type": "single_choice", "options": ["区分网络号和主机号", "加密数据", "路由转发", "域名解析"], "answer": "A", "explanation": "子网掩码用于划分IP地址的网络部分和主机部分。", "difficulty": "easy", "score": 2},
            {"content": "ARP协议的功能是（ ）。", "question_type": "single_choice", "options": ["将IP地址解析为MAC地址", "将MAC地址解析为IP地址", "将域名解析为IP地址", "分配IP地址"], "answer": "A", "explanation": "ARP解决同一网段IP到MAC的映射。", "difficulty": "easy", "score": 2},
            {"content": "HTTPS使用的默认端口号是（ ）。", "question_type": "single_choice", "options": ["443", "80", "21", "25"], "answer": "A", "explanation": "HTTPS默认443端口。", "difficulty": "easy", "score": 2},
            {"content": "网络拓扑结构中可靠性最高的是（ ）。", "question_type": "single_choice", "options": ["网状型", "星型", "环型", "总线型"], "answer": "A", "explanation": "网状结构冗余路径多，可靠性最高。", "difficulty": "easy", "score": 2},
            {"content": "交换机工作在OSI模型的（ ）。", "question_type": "single_choice", "options": ["数据链路层", "物理层", "网络层", "传输层"], "answer": "A", "explanation": "二层交换机基于MAC地址转发，工作在数据链路层。", "difficulty": "easy", "score": 2},
            {"content": "TCP三次握手的第二个报文段的标志位是（ ）。", "question_type": "single_choice", "options": ["SYN+ACK", "SYN", "ACK", "FIN"], "answer": "A", "explanation": "第二次握手：服务器回复SYN+ACK。", "difficulty": "medium", "score": 2},
            {"content": "CIDR的主要目的是（ ）。", "question_type": "single_choice", "options": ["减缓IP地址耗尽和路由表膨胀", "加密网络流量", "提高传输速度", "简化DNS配置"], "answer": "A", "explanation": "CIDR通过路由聚合减少路由表项。", "difficulty": "medium", "score": 2},
            {"content": "数据链路层的主要功能不包括（ ）。", "question_type": "single_choice", "options": ["路由选择", "成帧", "差错控制", "流量控制"], "answer": "A", "explanation": "路由选择是网络层的功能。", "difficulty": "easy", "score": 2},
            {"content": "WWW的核心协议是（ ）。", "question_type": "single_choice", "options": ["HTTP", "FTP", "SMTP", "SNMP"], "answer": "A", "explanation": "HTTP是万维网的基础协议。", "difficulty": "easy", "score": 2},
            {"content": "NAT技术的主要作用是（ ）。", "question_type": "single_choice", "options": ["将私有IP地址转换为公有IP地址", "加密数据", "加速传输", "域名解析"], "answer": "A", "explanation": "NAT实现内网私有地址到公网地址的转换。", "difficulty": "easy", "score": 2},
            {"content": "VLAN的主要优点是（ ）。", "question_type": "single_choice", "options": ["隔离广播域", "加密数据", "加速路由", "压缩数据"], "answer": "A", "explanation": "VLAN将物理网络划分为多个逻辑广播域。", "difficulty": "easy", "score": 2},
            # 多选题 5题×4分
            {"content": "TCP协议提供的服务包括（ ）。", "question_type": "multiple_choice", "options": ["面向连接", "可靠传输", "流量控制", "拥塞控制"], "answer": "ABCD", "explanation": "TCP的四大核心服务特征。", "difficulty": "easy", "score": 4},
            {"content": "应用层协议包括（ ）。", "question_type": "multiple_choice", "options": ["HTTP", "FTP", "SMTP", "DNS"], "answer": "ABCD", "explanation": "四个都是常见的应用层协议。", "difficulty": "easy", "score": 4},
            {"content": "网络安全威胁包括（ ）。", "question_type": "multiple_choice", "options": ["截获", "篡改", "伪造", "中断"], "answer": "ABCD", "explanation": "四种基本安全威胁。", "difficulty": "medium", "score": 4},
            {"content": "路由算法分类包括（ ）。", "question_type": "multiple_choice", "options": ["距离向量算法", "链路状态算法", "静态路由", "动态路由"], "answer": "ABCD", "explanation": "按不同维度的分类。", "difficulty": "medium", "score": 4},
            {"content": "数据编码方式包括（ ）。", "question_type": "multiple_choice", "options": ["不归零编码NRZ", "曼彻斯特编码", "差分曼彻斯特编码", "归零编码RZ"], "answer": "ABCD", "explanation": "四种常见的数字编码方式。", "difficulty": "medium", "score": 4},
            # 填空题 5题×2分
            {"content": "TCP建立连接需要进行______次握手。", "question_type": "fill_blank", "options": [], "answer": "3", "explanation": "三次握手建立连接。", "difficulty": "easy", "score": 2},
            {"content": "IPv6地址长度为______位。", "question_type": "fill_blank", "options": [], "answer": "128", "explanation": "IPv6采用128位地址。", "difficulty": "easy", "score": 2},
            {"content": "以太网的最小帧长为______字节。", "question_type": "fill_blank", "options": [], "answer": "64", "explanation": "以太网帧最小64字节，最大1518字节。", "difficulty": "medium", "score": 2},
            {"content": "TCP释放连接需要______次挥手。", "question_type": "fill_blank", "options": [], "answer": "4", "explanation": "四次挥手释放连接。", "difficulty": "easy", "score": 2},
            {"content": "FTP协议使用______和______两个端口号。", "question_type": "fill_blank", "options": [], "answer": "20和21", "explanation": "20数据传输，21控制命令。", "difficulty": "easy", "score": 2},
            # 简答题 4题×6分
            {"content": "简述TCP可靠传输的实现机制。", "question_type": "short_answer", "options": [], "answer": "（1）序号和确认号——对每个字节编号，接收方确认；（2）超时重传——未收到确认则重发；（3）滑动窗口——控制发送速率；（4）校验和——检测数据损坏；（5）连接管理——三次握手确保双方就绪。", "explanation": "五种机制保证可靠性。", "difficulty": "medium", "score": 6},
            {"content": "简述IP地址的分类及各类地址范围。", "question_type": "short_answer", "options": [], "answer": "（1）A类：0.0.0.0~127.255.255.255，前8位网络号；（2）B类：128.0.0.0~191.255.255.255，前16位网络号；（3）C类：192.0.0.0~223.255.255.255，前24位网络号；（4）D类：224.0.0.0~239.255.255.255，多播地址；（5）E类：240.0.0.0~255.255.255.255，保留实验。", "explanation": "五类地址的范围和用途。", "difficulty": "medium", "score": 6},
            {"content": "简述交换机和路由器的主要区别。", "question_type": "short_answer", "options": [], "answer": "（1）工作层次不同：交换机在数据链路层（二层），路由器在网络层（三层）；（2）转发依据不同：交换机基于MAC地址，路由器基于IP地址；（3）功能不同：交换机连接同一网络内设备，路由器连接不同网络；（4）广播域：交换机不隔离广播域（VLAN除外），路由器隔离广播域。", "explanation": "从层次、依据、功能、广播四方面对比。", "difficulty": "medium", "score": 6},
            {"content": "简述网络拥塞控制的四种算法。", "question_type": "short_answer", "options": [], "answer": "（1）慢开始——拥塞窗口从1开始指数增长；（2）拥塞避免——达到阈值后线性增长；（3）快重传——收到3个重复ACK立即重传；（4）快恢复——快重传后将阈值减半并从新阈值开始拥塞避免（而非慢开始）。", "explanation": "TCP拥塞控制的四个阶段/算法。", "difficulty": "medium", "score": 6},
            # 论述题 2题×10分
            {"content": "试论述OSI参考模型各层的名称、主要功能和典型协议。", "question_type": "essay", "options": [], "answer": "七层从下到上：（1）物理层——透明传输比特流，RS-232、RJ-45；（2）数据链路层——帧传输和差错检测，PPP、Ethernet；（3）网络层——路由选择和分组转发，IP、ICMP；（4）传输层——端到端可靠传输，TCP、UDP；（5）会话层——建立管理会话，RPC；（6）表示层——数据格式转换、加密，JPEG、SSL；（7）应用层——提供用户服务，HTTP、FTP、SMTP。", "explanation": "逐层说明名称、功能、协议示例。", "difficulty": "hard", "score": 10},
            {"content": "试论述TCP三次握手和四次挥手的过程及其设计原因。", "question_type": "essay", "options": [], "answer": "三次握手：（1）客户端→服务器：SYN=1,seq=x；（2）服务器→客户端：SYN=1,ACK=1,seq=y,ack=x+1；（3）客户端→服务器：ACK=1,seq=x+1,ack=y+1。原因：防止已失效的连接请求到达服务器造成错误。四次挥手：（1）客户端→服务器：FIN=1,seq=u；（2）服务器→客户端：ACK=1,ack=u+1；（3）服务器→客户端：FIN=1,seq=w；（4）客户端→服务器：ACK=1,ack=w+1。原因：TCP是全双工的，关闭每个方向需要独立完成（半关闭），所以需要四次。", "explanation": "详细描述每步报文内容和设计理由。", "difficulty": "hard", "score": 10},
        ],
    },
]


def seed() -> None:
    """Insert past paper data."""
    db = SessionLocal()
    try:
        # Get province
        province = db.query(Province).filter(Province.code == "13").first()
        province_id = province.id if province else None

        papers_created = 0
        questions_inserted = 0

        for paper_data in PAPERS:
            subject = db.query(Subject).filter(Subject.code == paper_data["subject_code"]).first()
            if not subject:
                print(f"  WARNING: Subject '{paper_data['subject_code']}' not found, skipping")
                continue

            # Check if paper already exists
            existing = (
                db.query(PastPaper)
                .filter(
                    PastPaper.subject_id == subject.id,
                    PastPaper.year == paper_data["year"],
                    PastPaper.month == paper_data["month"],
                )
                .first()
            )
            if existing:
                print(f"  SKIP: {paper_data['year']}年{paper_data['month']}月 {subject.name} 已存在")
                continue

            # Insert questions and collect IDs
            question_ids = []
            chapters = (
                db.query(Chapter)
                .filter(Chapter.subject_id == subject.id)
                .order_by(Chapter.order)
                .all()
            )

            for idx, q_data in enumerate(paper_data["questions"]):
                # Check duplicate
                existing_q = (
                    db.query(Question)
                    .filter(
                        Question.subject_id == subject.id,
                        Question.content == q_data["content"],
                    )
                    .first()
                )
                if existing_q:
                    question_ids.append(existing_q.id)
                    continue

                # Determine chapter
                chapter_id = chapters[idx % len(chapters)].id if chapters else None

                options_val = json.dumps(q_data["options"], ensure_ascii=False) if q_data["options"] else "[]"

                question = Question(
                    subject_id=subject.id,
                    content=q_data["content"],
                    question_type=q_data["question_type"],
                    options=options_val,
                    answer=q_data["answer"],
                    explanation=q_data.get("explanation", ""),
                    year=paper_data["year"],
                    month=paper_data["month"],
                    chapter_id=chapter_id,
                    difficulty=q_data.get("difficulty", "medium"),
                    frequency=5,
                    score=q_data.get("score", 2),
                    source=paper_data["source"],
                )
                db.add(question)
                db.flush()
                question_ids.append(question.id)
                questions_inserted += 1

            # Calculate total score
            total_score = sum(q.get("score", 2) for q in paper_data["questions"])

            # Build paper_config
            from collections import Counter
            type_counter = Counter(q["question_type"] for q in paper_data["questions"])
            paper_config = {
                "structure": [
                    {"type": qt, "count": cnt}
                    for qt, cnt in type_counter.items()
                ]
            }

            # Create PastPaper record
            paper_name = f"{paper_data['year']}年{paper_data['month']}月 {subject.name} 真题"
            paper = PastPaper(
                subject_id=subject.id,
                name=paper_name,
                year=paper_data["year"],
                month=paper_data["month"],
                province_id=province_id,
                total_score=total_score,
                duration=150,
                question_ids=question_ids,
                paper_config=paper_config,
                source=paper_data["source"],
                is_published=True,
            )
            db.add(paper)
            papers_created += 1
            print(f"  OK: {paper_name} ({len(question_ids)}题, {total_score}分)")

        db.commit()
        print()
        print("[OK] 历年真题数据填充完成!")
        print(f"   真题试卷: {papers_created} 套")
        print(f"   新增题目: {questions_inserted} 道")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] 填充失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
