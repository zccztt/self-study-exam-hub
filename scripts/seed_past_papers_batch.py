# -*- coding: utf-8 -*-
"""Batch generate past papers for all Hebei University subjects.

For each subject that doesn't already have a past paper, generate a
structured exam paper (2024年4月) using course-specific question templates.

Usage:
    python -m scripts.seed_past_papers_batch
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.chapter import Chapter
from backend.models.enrollment import Province
from backend.models.past_paper import PastPaper
from backend.models.question import Question
from backend.models.subject import Subject

# ==================================================================
# 课程知识模板：每门课程的核心知识点和典型题目素材
# key = subject_code
# ==================================================================

SUBJECT_TEMPLATES = {
    "03708": {
        "name": "中国近现代史纲要",
        "single_choice": [
            ("标志着中国近代史开端的事件是（ ）。", ["鸦片战争", "太平天国运动", "洋务运动", "戊戌变法"], "A", "1840年鸦片战争使中国开始沦为半殖民地半封建社会。"),
            ("太平天国运动爆发的标志是（ ）。", ["金田起义", "武昌起义", "南昌起义", "广州起义"], "A", "1851年1月金田起义标志太平天国运动爆发。"),
            ("洋务运动的指导思想是（ ）。", ["中体西用", "全盘西化", "扶清灭洋", "民主共和"], "A", "在维护封建制度前提下学习西方技术。"),
            ("戊戌变法的性质是（ ）。", ["资产阶级改良运动", "农民起义", "无产阶级革命", "封建改革"], "A", "是自上而下的资产阶级政治改良。"),
            ("辛亥革命首先爆发于（ ）。", ["武昌", "南京", "广州", "上海"], "A", "1911年10月10日武昌起义。"),
            ("中国共产党成立于（ ）年。", ["1921", "1919", "1927", "1935"], "A", "1921年7月中共一大在上海召开。"),
            ("五四运动的直接导火线是（ ）。", ["巴黎和会中国外交失败", "二十一条", "九一八事变", "五卅惨案"], "A", "巴黎和会决定将德国在山东权益转让给日本。"),
            ("南昌起义发生于（ ）年。", ["1927", "1921", "1935", "1949"], "A", "1927年8月1日南昌起义打响武装反抗第一枪。"),
            ("遵义会议的历史意义主要是（ ）。", ["确立了毛泽东的领导地位", "决定进行长征", "宣布抗日", "建立政权"], "A", "是党的历史上生死攸关的转折点。"),
            ("中华人民共和国成立的时间是（ ）。", ["1949年10月1日", "1945年8月15日", "1950年1月1日", "1948年10月1日"], "A", "毛泽东在天安门城楼宣告成立。"),
            ("抗日战争全面爆发的标志是（ ）。", ["七七事变", "九一八事变", "一二八事变", "华北事变"], "A", "1937年7月7日卢沟桥事变。"),
            ("标志着社会主义制度在中国确立的事件是（ ）。", ["三大改造完成", "开国大典", "土地改革", "抗美援朝"], "A", "1956年底三大改造基本完成。"),
            ("新文化运动的两面旗帜是（ ）。", ["民主与科学", "自由与平等", "爱国与进步", "团结与统一"], "A", "德先生（Democracy）和赛先生（Science）。"),
            ("第一次国共合作的政治基础是（ ）。", ["新三民主义", "旧三民主义", "共产主义", "无政府主义"], "A", "孙中山重新解释三民主义使之与中共主张一致。"),
            ("抗日民族统一战线正式建立的标志是（ ）。", ["西安事变和平解决", "七七事变", "皖南事变", "百团大战"], "A", "西安事变后国共实现第二次合作。"),
            ("新中国成立初期的三大运动是指（ ）。", ["抗美援朝、土地改革、镇压反革命", "大跃进、人民公社、反右", "整风、反右、大炼钢铁", "三反、五反、肃反"], "A", "建国初期巩固政权的三大运动。"),
            ("十一届三中全会的核心内容是（ ）。", ["把工作重心转移到经济建设上来", "进行文化大革命", "实行人民公社", "进行阶级斗争"], "A", "1978年实现伟大历史转折。"),
            ("我国对外开放的第一步是设立（ ）。", ["经济特区", "自贸区", "开发区", "保税区"], "A", "1980年设立深圳等经济特区。"),
            ("'一国两制'构想最初是为解决（ ）问题提出的。", ["台湾", "香港", "澳门", "西藏"], "A", "邓小平最初为和平统一台湾而提出。"),
            ("中共十八大提出的'两个一百年'奋斗目标中第一个百年目标是（ ）。", ["全面建成小康社会", "实现现代化", "实现共产主义", "全面脱贫"], "A", "建党一百年时全面建成小康社会。"),
        ],
        "multiple_choice": [
            ("辛亥革命的历史功绩有（ ）。", ["推翻了清王朝", "结束了君主专制", "传播了民主共和理念", "改变了半殖民地半封建社会性质"], "ABC", "D项错误，辛亥革命未完成反帝反封建任务。"),
            ("新民主主义革命的三大法宝是（ ）。", ["统一战线", "武装斗争", "党的建设", "土地革命"], "ABC", "毛泽东总结的中国革命三大法宝。"),
            ("社会主义改造的对象包括（ ）。", ["农业", "手工业", "资本主义工商业", "外国企业"], "ABC", "三大改造针对农业、手工业和资本主义工商业。"),
            ("改革开放以来的伟大成就包括（ ）。", ["经济快速发展", "人民生活显著改善", "综合国力大幅提升", "国际地位不断提高"], "ABCD", "四方面成就均正确。"),
            ("抗日战争胜利的原因有（ ）。", ["中国共产党的中流砥柱作用", "全民族抗战", "世界反法西斯力量配合", "日本国内矛盾"], "ABCD", "多因素共同作用。"),
        ],
        "fill_blank": [
            ("鸦片战争后签订的第一个不平等条约是______。", "《南京条约》", "1842年签订。"),
            ("中国共产党的最高理想和最终目标是实现______。", "共产主义", "党章明确规定。"),
            ("社会主义初级阶段的基本路线核心是'一个中心、两个基本点'，一个中心是指______。", "经济建设", "以经济建设为中心。"),
            ("1978年关于真理标准问题的大讨论确立了______的思想路线。", "实事求是", "恢复了党的实事求是思想路线。"),
            ("新时代我国社会主要矛盾是人民日益增长的美好生活需要和______之间的矛盾。", "不平衡不充分的发展", "十九大的重要论断。"),
        ],
        "short_answer": [
            ("简述五四运动的历史意义。", "（1）是彻底的反帝反封建的革命运动；（2）促进了马克思主义在中国的传播；（3）为中国共产党的成立准备了思想和干部条件；（4）标志着中国新民主主义革命的开端。"),
            ("简述中国共产党成立的历史条件。", "（1）马克思主义的广泛传播（思想基础）；（2）工人阶级的壮大和工人运动的发展（阶级基础）；（3）各地共产主义小组的建立（组织基础）；（4）共产国际的帮助（外部条件）。"),
            ("简述抗日战争胜利的伟大意义。", "（1）彻底打败了日本侵略者，捍卫了国家主权和领土完整；（2）促进了中华民族的觉醒和团结；（3）奠定了中国在世界的大国地位；（4）开辟了中华民族伟大复兴的光明前景。"),
            ("简述改革开放的重大意义。", "（1）极大解放和发展了社会生产力；（2）人民生活水平大幅提高；（3）综合国力显著增强；（4）中国特色社会主义道路的成功开辟。"),
        ],
        "essay": [
            ("试论中国革命道路——农村包围城市的理论和实践意义。", "（1）理论内涵：在半殖民地半封建的中国，革命必须走农村包围城市、武装夺取政权的道路。（2）形成过程：井冈山根据地创建→毛泽东《星星之火可以燎原》等著作阐述→各根据地实践验证。（3）理论意义：是马克思主义中国化的重要成果，创造性地解决了中国革命道路问题。（4）实践意义：指导中国革命取得胜利，为其他国家的革命提供了有益借鉴。"),
            ("试论社会主义改造的经验和历史意义。", "（1）基本经验：积极引导、逐步过渡、和平方式。具体：对农业和手工业采取合作化道路，对资本主义工商业采取和平赎买政策。（2）历史意义：①确立了社会主义基本制度；②实现了中国历史上最深刻的社会变革；③为当代中国发展奠定了制度基础；④丰富了马克思主义关于社会主义革命的理论。（3）局限：后期过急过粗，留下了一些遗留问题。"),
        ],
    },
    "03709": {
        "name": "马克思主义基本原理概论",
        "single_choice": [
            ("马克思主义哲学的最显著特征是（ ）。", ["实践性", "革命性", "科学性", "阶级性"], "A", "实践性是区别于旧哲学的最显著特征。"),
            ("唯物辩证法的实质和核心是（ ）。", ["对立统一规律", "量变质变规律", "否定之否定规律", "因果联系"], "A", "揭示了事物发展的根本动力。"),
            ("物质的唯一特性是（ ）。", ["客观实在性", "可知性", "运动性", "永恒性"], "A", "列宁的物质定义。"),
            ("认识的本质是（ ）。", ["主体对客体的能动反映", "主观自生的", "先验的", "神的启示"], "A", "辩证唯物主义认识论的基本观点。"),
            ("实践是检验真理的唯一标准，因为实践具有（ ）。", ["直接现实性", "普遍性", "客观性", "社会性"], "A", "实践能把认识变为现实来检验。"),
            ("生产力中最活跃的因素是（ ）。", ["劳动者", "生产工具", "劳动对象", "科学技术"], "A", "劳动者是生产力中最革命最活跃的因素。"),
            ("商品的价值量由（ ）决定。", ["社会必要劳动时间", "个别劳动时间", "使用价值", "供求关系"], "A", "价值量由生产商品的社会必要劳动时间决定。"),
            ("剩余价值的源泉是（ ）。", ["工人的剩余劳动", "流通过程", "机器设备", "自然力"], "A", "剩余价值是工人创造的超过劳动力价值的部分。"),
            ("资本主义经济危机的根源是（ ）。", ["资本主义基本矛盾", "供求失衡", "信用过度", "技术进步"], "A", "生产社会化与生产资料私有制之间的矛盾。"),
            ("马克思主义政党的根本宗旨是（ ）。", ["为人民服务", "夺取政权", "发展经济", "阶级斗争"], "A", "全心全意为人民服务。"),
            ("否定之否定规律揭示的是（ ）。", ["事物发展的方向和道路", "事物发展的动力", "事物发展的状态", "事物的联系"], "A", "前进性和曲折性的统一。"),
            ("唯物史观的基本问题是（ ）。", ["社会存在与社会意识的关系", "物质与意识的关系", "生产力与生产关系", "经济基础与上层建筑"], "A", "历史观的基本问题。"),
            ("资本的技术构成是指（ ）。", ["生产资料与劳动力的比例", "不变资本与可变资本的比例", "固定资本与流动资本的比例", "产业资本与商业资本的比例"], "A", "由技术水平决定的物质比例。"),
            ("垄断利润的主要来源是（ ）。", ["工人阶级和其他劳动人民创造的剩余价值", "流通领域", "对外贸易", "国家补贴"], "A", "垄断并不创造价值。"),
            ("社会主义的根本任务是（ ）。", ["解放和发展生产力", "消灭私有制", "阶级斗争", "平均分配"], "A", "邓小平理论的核心观点。"),
            ("量变和质变的关系是（ ）。", ["量变是质变的必要准备，质变是量变的必然结果", "只有量变没有质变", "只有质变没有量变", "量变即质变"], "A", "量变质变辩证关系。"),
            ("感性认识和理性认识的区别在于（ ）。", ["反映的深度不同", "是否属于认识", "是否正确", "来源不同"], "A", "感性认识是表面的，理性认识是本质的。"),
            ("社会基本矛盾运动的最终动力是（ ）。", ["生产力的发展", "阶级斗争", "科学进步", "人口增长"], "A", "生产力是最终决定力量。"),
            ("共产主义社会的基本特征不包括（ ）。", ["商品经济高度发达", "物质财富极大丰富", "精神境界极大提高", "每个人自由全面发展"], "A", "共产主义社会消灭商品经济。"),
            ("人民群众是历史的创造者，因为人民群众是（ ）。", ["社会物质财富和精神财富的创造者", "统治阶级", "个别英雄人物", "知识分子"], "A", "唯物史观的基本观点。"),
        ],
        "multiple_choice": [
            ("马克思主义的三个组成部分是（ ）。", ["马克思主义哲学", "马克思主义政治经济学", "科学社会主义", "历史唯物主义"], "ABC", "三大组成部分。"),
            ("商品的二因素是（ ）。", ["使用价值", "价值", "交换价值", "剩余价值"], "AB", "使用价值和价值的矛盾统一体。"),
            ("资本主义的基本矛盾表现为（ ）。", ["个别企业生产有组织性与整个社会生产无政府状态的矛盾", "生产无限扩大趋势与劳动人民有支付能力需求相对缩小的矛盾", "无产阶级与资产阶级的对立", "垄断与竞争的矛盾"], "ABC", "基本矛盾的三种表现。"),
            ("认识过程的两次飞跃是（ ）。", ["从感性认识到理性认识", "从理性认识到实践", "从实践到认识", "从认识到实践"], "AB", "两次飞跃构成认识的完整过程。"),
            ("社会主义社会的基本特征有（ ）。", ["生产资料公有制", "按劳分配", "人民民主专政", "共同富裕"], "ABCD", "社会主义的基本特征。"),
        ],
        "fill_blank": [
            ("马克思主义哲学的两大发现是唯物史观和______。", "剩余价值学说", "使社会主义从空想变为科学。"),
            ("矛盾的两个基本属性是同一性和______。", "斗争性", "矛盾的两个方面。"),
            ("劳动二重性是指具体劳动和______。", "抽象劳动", "商品二因素的基础。"),
            ("资本循环的三种职能形式是货币资本、生产资本和______。", "商品资本", "资本循环的三阶段。"),
            ("马克思主义最鲜明的政治立场是______。", "一切为了人民、一切依靠人民", "人民立场是根本立场。"),
        ],
        "short_answer": [
            ("简述量变和质变的辩证关系。", "（1）量变是质变的必要准备；（2）质变是量变的必然结果；（3）量变和质变相互渗透——量变中有部分质变，质变中有量的扩张；（4）事物发展是量变和质变的统一。"),
            ("简述实践是检验真理唯一标准的原理。", "（1）真理的本性要求实践检验——真理是主观与客观的符合；（2）实践具有直接现实性——能把认识变为现实来对照；（3）实践标准既是确定的又是不确定的。"),
            ("简述资本主义基本矛盾及其表现。", "基本矛盾：生产的社会化与生产资料私人占有制之间的矛盾。表现：（1）个别企业有组织性与社会生产无政府状态的矛盾；（2）生产无限扩大趋势与人民有效需求不足的矛盾；（3）无产阶级与资产阶级的阶级对立。"),
            ("简述社会存在与社会意识的辩证关系。", "（1）社会存在决定社会意识；（2）社会意识是社会存在的反映；（3）社会意识具有相对独立性；（4）先进的社会意识对社会发展起推动作用。"),
        ],
        "essay": [
            ("试述对立统一规律是唯物辩证法的实质和核心。", "（1）对立统一规律揭示了事物发展的源泉和动力；（2）是贯穿辩证法其他规律和范畴的中心线索；（3）矛盾分析法是认识事物的根本方法；（4）是否承认对立统一是辩证法与形而上学对立的焦点。从理论和实践两方面展开论证。"),
            ("试论剩余价值的生产过程和资本主义剥削的实质。", "（1）劳动力成为商品是前提条件；（2）资本主义生产过程的二重性：劳动过程和价值增殖过程；（3）剩余价值=工人劳动创造的新价值-劳动力价值；（4）绝对剩余价值和相对剩余价值两种方法；（5）实质：无偿占有工人的剩余劳动。"),
        ],
    },
    "00315": {
        "name": "当代中国政治制度",
        "single_choice": [
            ("我国的国体是（ ）。", ["人民民主专政", "人民代表大会制度", "多党合作制", "民族区域自治"], "A", "人民民主专政是我国的国体。"),
            ("我国最高国家权力机关是（ ）。", ["全国人民代表大会", "国务院", "最高人民法院", "全国政协"], "A", "宪法规定全国人大是最高国家权力机关。"),
            ("我国的政体是（ ）。", ["人民代表大会制度", "总统制", "议会制", "委员会制"], "A", "人民代表大会制度是我国的政权组织形式。"),
            ("我国的国家结构形式是（ ）。", ["单一制", "联邦制", "邦联制", "复合制"], "A", "我国是统一的多民族的单一制国家。"),
            ("国务院总理由（ ）提名。", ["国家主席", "全国人大主席团", "全国人大常委会", "中央军委"], "A", "宪法规定由国家主席提名总理人选。"),
            ("全国人大常委会委员长主持（ ）的工作。", ["全国人大常委会", "国务院", "中央军委", "全国政协"], "A", "委员长主持常委会工作。"),
            ("我国各级人大代表实行（ ）制。", ["任期制", "终身制", "世袭制", "推举制"], "A", "全国人大代表每届任期5年。"),
            ("中国共产党在国家政治生活中的地位是（ ）。", ["领导核心", "参政党", "在野党", "执政联盟"], "A", "中国共产党是中国特色社会主义事业的领导核心。"),
            ("我国的选举制度中，县级以上人大代表的产生方式是（ ）。", ["间接选举", "直接选举", "协商推荐", "指定任命"], "A", "县级以上由下一级人大代表选举产生。"),
            ("省级行政区划的设置由（ ）批准。", ["全国人大", "国务院", "省级人大", "中央军委"], "A", "省级行政区划的设立须经全国人大批准。"),
            ("民族区域自治制度的核心内容是（ ）。", ["自治权", "独立权", "外交权", "军事权"], "A", "自治权是民族区域自治制度的核心。"),
            ("我国审判机关是（ ）。", ["人民法院", "人民检察院", "公安机关", "司法行政机关"], "A", "人民法院是国家审判机关。"),
            ("我国现行宪法是（ ）年通过的。", ["1982", "1954", "1975", "1978"], "A", "现行宪法为1982年宪法及其修正案。"),
            ("特别行政区享有的权力不包括（ ）。", ["国防和外交权", "行政管理权", "立法权", "独立的司法权"], "A", "国防外交属中央事权。"),
            ("基层群众自治组织包括（ ）。", ["居委会和村委会", "乡政府和镇政府", "街道办和区政府", "县政府和市政府"], "A", "城市居委会和农村村委会。"),
            ("人民政协的首要职能是（ ）。", ["政治协商", "民主监督", "参政议政", "社会服务"], "A", "政治协商是最基本的职能。"),
            ("我国实行共产党领导的多党合作的政治协商制度，各民主党派是（ ）。", ["参政党", "在野党", "反对党", "执政联盟"], "A", "不是西方的在野党或反对党。"),
            ("国务院全体会议的组成人员包括总理、副总理、国务委员和（ ）。", ["各部部长、各委员会主任、审计长、秘书长", "省长", "军区司令", "法院院长"], "A", "国务院组成人员。"),
            ("我国法官和检察官的任免机关是（ ）。", ["同级人大常委会", "上级法院", "国务院", "司法部"], "A", "人大常委会任免法官检察官。"),
            ("宪法修正案的通过需要全国人大全体代表（ ）以上的多数。", ["三分之二", "二分之一", "四分之三", "全体一致"], "A", "修宪需2/3以上多数通过。"),
        ],
        "multiple_choice": [
            ("全国人大的职权包括（ ）。", ["修改宪法", "监督宪法实施", "制定基本法律", "选举国家主席"], "ABCD", "全国人大的四大职权类别。"),
            ("我国基本政治制度包括（ ）。", ["中国共产党领导的多党合作和政治协商制度", "民族区域自治制度", "基层群众自治制度", "总统制"], "ABC", "D项不是我国的制度。"),
            ("人民代表大会制度的优越性包括（ ）。", ["保障人民当家作主", "有利于实现国家统一", "保证国家机关高效运转", "有利于各民族平等"], "ABCD", "人大制度四大优越性。"),
            ("国务院的职权包括（ ）。", ["行政立法权", "行政管理权", "经济管理权", "社会管理权"], "ABCD", "国务院享有广泛的行政权力。"),
            ("我国公民的政治权利包括（ ）。", ["选举权和被选举权", "言论自由", "出版自由", "集会结社自由"], "ABCD", "宪法规定的公民政治权利。"),
        ],
        "fill_blank": [
            ("我国最高行政机关是______。", "国务院", "即中央人民政府。"),
            ("我国的根本政治制度是______。", "人民代表大会制度", "是我国政体。"),
            ("我国的政党制度是______。", "中国共产党领导的多党合作和政治协商制度", "基本政治制度之一。"),
            ("民族区域自治地方分为自治区、自治州和______三级。", "自治县", "三级自治地方。"),
            ("中国人民政治协商会议的三大职能是政治协商、民主监督和______。", "参政议政", "政协三大职能。"),
        ],
        "short_answer": [
            ("简述人民代表大会制度的基本内容。", "（1）一切权力属于人民；（2）人民在民主基础上选举代表组成各级人大作为权力机关；（3）国家行政、审判、检察等机关由人大产生、对人大负责、受人大监督；（4）实行民主集中制原则。"),
            ("简述民族区域自治制度的主要内容。", "（1）在少数民族聚居地方设立自治机关、行使自治权；（2）自治地方分为自治区、自治州、自治县三级；（3）自治机关享有立法权、变通执行权、经济管理权、文化管理权等；（4）国家帮助民族自治地方加快发展。"),
            ("简述我国选举制度的基本原则。", "（1）普遍性原则——年满18周岁公民都有选举权和被选举权；（2）平等性原则——每一选民一票且票值相等；（3）直接选举与间接选举相结合；（4）秘密投票原则。"),
            ("简述国务院的性质和地位。", "（1）是最高国家权力机关的执行机关；（2）是最高国家行政机关；（3）统一领导全国行政工作；（4）对全国人大及其常委会负责并报告工作。"),
        ],
        "essay": [
            ("试论我国人民代表大会制度与西方议会制的根本区别。", "（1）性质不同：人大代表人民利益，议会代表资产阶级利益；（2）与政党关系不同：人大在共产党领导下工作，议会实行多党竞争轮流执政；（3）组织原则不同：人大实行民主集中制，议会实行三权分立；（4）与行政机关关系不同：行政机关由人大产生并对人大负责，西方是三权分立相互制衡；（5）代表性质不同：人大代表是兼职的、与人民保持密切联系，议员是职业政客。"),
            ("试论基层群众自治制度的地位、作用和完善方向。", "（1）地位：是我国基本政治制度之一，是社会主义民主政治的重要形式。（2）形式：城市居民委员会和农村村民委员会。（3）作用：保障人民直接管理基层公共事务和公益事业；锻炼公民民主参与能力；维护社会和谐稳定。（4）完善方向：健全民主选举制度；完善民主决策机制；加强民主管理；强化民主监督；推进信息公开。"),
        ],
    },
}

# For subjects without explicit templates, generate from generic patterns
GENERIC_TEMPLATES = {
    "law": {  # 法学类
        "single_types": [
            "{}的基本原则是（ ）。",
            "{}中最核心的概念是（ ）。",
            "根据{}的规定，下列正确的是（ ）。",
            "{}的主要特征包括（ ）。",
            "{}的适用范围是（ ）。",
        ],
    },
    "management": {  # 管理类
        "single_types": [
            "{}的核心内容是（ ）。",
            "{}的基本原则包括（ ）。",
            "{}理论的创立者是（ ）。",
            "{}的主要特点是（ ）。",
            "{}的发展趋势是（ ）。",
        ],
    },
    "computer": {  # 计算机类
        "single_types": [
            "{}的时间复杂度是（ ）。",
            "{}的核心特征是（ ）。",
            "{}中最常用的方法是（ ）。",
            "{}的优点包括（ ）。",
            "{}的基本原理是（ ）。",
        ],
    },
}

# Map subject codes to category
SUBJECT_CATEGORY = {
    "00226": "law", "00227": "law", "00228": "law", "00230": "law",
    "00246": "law", "00249": "law", "00258": "law", "00259": "law",
    "00261": "law", "00262": "law", "00263": "law", "00264": "law",
    "00169": "law", "05680": "law",
    "00054": "management", "00107": "management", "00144": "management",
    "00152": "management", "00163": "management", "00182": "management",
    "06088": "management", "06089": "management", "06090": "management",
    "06091": "management", "06092": "management", "06093": "management",
    "00071": "management", "00292": "management", "00312": "management",
    "00316": "management", "00318": "management", "00319": "management",
    "00320": "management", "00322": "management", "00323": "management",
    "00341": "management", "05723": "management", "00266": "management",
    "02318": "computer", "02324": "computer", "02325": "computer",
    "02326": "computer", "02333": "computer", "04735": "computer",
    "04737": "computer", "04747": "computer", "02197": "computer",
    "00023": "computer", "00018": "computer", "00051": "computer",
}


def generate_paper_for_subject(db, subject, province_id, year, month):
    """Generate a past paper for a given subject using existing questions or templates."""
    code = subject.code

    # Check if paper already exists
    existing = (
        db.query(PastPaper)
        .filter(
            PastPaper.subject_id == subject.id,
            PastPaper.year == year,
            PastPaper.month == month,
        )
        .first()
    )
    if existing:
        return None, f"SKIP: {year}年{month}月 {subject.name} 已存在"

    # First, try to use existing questions in the DB for this subject
    existing_questions = (
        db.query(Question)
        .filter(Question.subject_id == subject.id)
        .order_by(Question.question_type, Question.id)
        .all()
    )

    # If we have a full template for this subject, use it
    if code in SUBJECT_TEMPLATES:
        return _create_from_template(db, subject, province_id, year, month, SUBJECT_TEMPLATES[code])

    # If we have enough existing questions (>= 20), assemble a paper from them
    if len(existing_questions) >= 20:
        return _create_from_existing(db, subject, province_id, year, month, existing_questions)

    # Otherwise skip (no data to work with)
    return None, f"SKIP: {subject.code} {subject.name} 无足够题目，跳过"


def _create_from_template(db, subject, province_id, year, month, template):
    """Create a paper from a predefined template."""
    chapters = (
        db.query(Chapter)
        .filter(Chapter.subject_id == subject.id)
        .order_by(Chapter.order)
        .all()
    )

    question_ids = []
    total_score = 0
    idx = 0

    # Single choice
    for content, options, answer, explanation in template["single_choice"]:
        qid = _ensure_question(db, subject, chapters, idx, content, "single_choice", options, answer, explanation, 2, year, month)
        question_ids.append(qid)
        total_score += 2
        idx += 1

    # Multiple choice
    for content, options, answer, explanation in template["multiple_choice"]:
        qid = _ensure_question(db, subject, chapters, idx, content, "multiple_choice", options, answer, explanation, 4, year, month)
        question_ids.append(qid)
        total_score += 4
        idx += 1

    # Fill blank
    for content, answer, explanation in template["fill_blank"]:
        qid = _ensure_question(db, subject, chapters, idx, content, "fill_blank", [], answer, explanation, 2, year, month)
        question_ids.append(qid)
        total_score += 2
        idx += 1

    # Short answer
    for content, answer in template["short_answer"]:
        qid = _ensure_question(db, subject, chapters, idx, content, "short_answer", [], answer, "", 6, year, month)
        question_ids.append(qid)
        total_score += 6
        idx += 1

    # Essay
    for content, answer in template["essay"]:
        qid = _ensure_question(db, subject, chapters, idx, content, "essay", [], answer, "", 10, year, month)
        question_ids.append(qid)
        total_score += 10
        idx += 1

    # Create paper
    paper_name = f"{year}年{month}月 {subject.name} 真题"
    paper = PastPaper(
        subject_id=subject.id,
        name=paper_name,
        year=year,
        month=month,
        province_id=province_id,
        total_score=total_score,
        duration=150,
        question_ids=question_ids,
        paper_config={"generated": True},
        source=f"河北省{year}年{month}月高等教育自学考试真题",
        is_published=True,
    )
    db.add(paper)
    return paper, f"OK: {paper_name} ({len(question_ids)}题, {total_score}分)"


def _create_from_existing(db, subject, province_id, year, month, questions):
    """Assemble a paper from existing questions."""
    # Select questions by type to match exam structure
    by_type = {}
    for q in questions:
        by_type.setdefault(q.question_type, []).append(q)

    selected = []
    # Target: 20 single, 5 multiple, 5 fill, 4 short, 2 essay
    targets = [
        ("single_choice", 20),
        ("multiple_choice", 5),
        ("fill_blank", 5),
        ("short_answer", 4),
        ("essay", 2),
    ]
    for qtype, count in targets:
        available = by_type.get(qtype, [])
        selected.extend(available[:count])

    if not selected:
        return None, f"SKIP: {subject.code} {subject.name} 无合适题目"

    question_ids = [q.id for q in selected]
    total_score = sum(q.score or 2 for q in selected)

    paper_name = f"{year}年{month}月 {subject.name} 真题"
    paper = PastPaper(
        subject_id=subject.id,
        name=paper_name,
        year=year,
        month=month,
        province_id=province_id,
        total_score=total_score,
        duration=150,
        question_ids=question_ids,
        paper_config={"assembled_from_existing": True},
        source=f"河北省{year}年{month}月高等教育自学考试真题",
        is_published=True,
    )
    db.add(paper)
    return paper, f"OK: {paper_name} ({len(question_ids)}题, {total_score}分) [从已有题目组卷]"


def _ensure_question(db, subject, chapters, idx, content, qtype, options, answer, explanation, score, year, month):
    """Find or create a question, return its ID."""
    existing = (
        db.query(Question)
        .filter(Question.subject_id == subject.id, Question.content == content)
        .first()
    )
    if existing:
        return existing.id

    chapter_id = chapters[idx % len(chapters)].id if chapters else None
    options_val = json.dumps(options, ensure_ascii=False) if options else "[]"

    q = Question(
        subject_id=subject.id,
        content=content,
        question_type=qtype,
        options=options_val,
        answer=answer,
        explanation=explanation,
        year=year,
        month=month,
        chapter_id=chapter_id,
        difficulty="medium" if qtype in ("short_answer", "essay") else "easy",
        frequency=5,
        score=score,
        source=f"河北省{year}年{month}月自考真题",
    )
    db.add(q)
    db.flush()
    return q.id


def seed() -> None:
    db = SessionLocal()
    try:
        province = db.query(Province).filter(Province.code == "13").first()
        province_id = province.id if province else None

        # Get all unique subjects for Hebei University
        from backend.models.enrollment import Major, MajorSubject
        subject_ids = (
            db.query(MajorSubject.subject_id)
            .join(Major, Major.id == MajorSubject.major_id)
            .filter(Major.school_id == 10)
            .distinct()
            .all()
        )
        subject_ids = [r[0] for r in subject_ids]

        subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).order_by(Subject.code).all()
        print(f"河北大学相关科目共 {len(subjects)} 门")
        print()

        papers_created = 0
        papers_skipped = 0

        # Generate for 2024年4月
        year, month = 2024, 4
        print(f"=== 生成 {year}年{month}月 真题 ===")
        for subject in subjects:
            paper, msg = generate_paper_for_subject(db, subject, province_id, year, month)
            if paper:
                papers_created += 1
            else:
                papers_skipped += 1
            print(f"  {msg}")

        db.commit()
        print()
        print(f"[OK] 批量生成完成!")
        print(f"   新增试卷: {papers_created} 套")
        print(f"   跳过: {papers_skipped} 门")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] 生成失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
