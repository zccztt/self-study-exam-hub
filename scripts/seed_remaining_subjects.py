# -*- coding: utf-8 -*-
"""Batch generate past papers for ALL remaining Hebei University subjects.

Generates 2024年10月 papers for subjects without one.
Each paper: 20 single + 5 multi + 5 fill + 4 short + 2 essay = 36 questions, 114 points.

Usage:
    python -m scripts.seed_remaining_subjects
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.chapter import Chapter
from backend.models.enrollment import Major, MajorSubject, Province
from backend.models.past_paper import PastPaper
from backend.models.question import Question
from backend.models.subject import Subject

# ===================================================================
# Question templates per subject code
# Format: {code: {"singles": [(content, [opts], answer, expl), ...], ...}}
# ===================================================================

def _law_questions(name, code):
    """Generate law-category questions."""
    return {
        "singles": [
            (f"{name}的调整对象是（ ）。", [f"{name}所规定的特定社会关系", "一切社会关系", "经济关系", "行政关系"], "A", f"{name}调整特定领域的法律关系。"),
            (f"{name}的基本原则中最重要的是（ ）。", ["合法性原则", "效率原则", "利润原则", "保密原则"], "A", "合法性是法律制度的首要原则。"),
            (f"{name}中权利主体享有权利的前提是（ ）。", ["具备法定资格", "缴纳费用", "获得批准", "年满30岁"], "A", "权利主体须具备法定资格条件。"),
            (f"{name}规定的法律责任主要包括（ ）。", ["民事责任、行政责任和刑事责任", "仅有民事责任", "仅有刑事责任", "仅有行政责任"], "A", "法律责任体系包含三种基本类型。"),
            (f"{name}的法律渊源中效力最高的是（ ）。", ["宪法", "行政法规", "地方性法规", "部门规章"], "A", "宪法是根本法，效力最高。"),
            (f"{name}中诉讼时效的一般规定是（ ）年。", ["3", "1", "5", "10"], "A", "民法典规定普通诉讼时效为3年。"),
            (f"{name}的立法目的是（ ）。", ["保护合法权益、维护社会秩序", "增加政府收入", "限制公民自由", "扩大行政权力"], "A", "法律的根本目的是保护权益和维护秩序。"),
            (f"关于{name}的适用，下列说法正确的是（ ）。", ["特别法优于一般法", "一般法优于特别法", "旧法优于新法", "下位法优于上位法"], "A", "法律适用的基本规则。"),
            (f"{name}中当事人的基本义务是（ ）。", ["遵守法律规定和诚实信用", "服从行政命令", "放弃权利", "无条件服从"], "A", "诚实信用是基本义务。"),
            (f"{name}的纠纷解决方式不包括（ ）。", ["武力解决", "协商", "调解", "仲裁"], "A", "法律不允许武力解决纠纷。"),
            (f"{name}中法律关系的构成要素包括（ ）。", ["主体、客体和内容", "仅有主体", "仅有客体", "仅有内容"], "A", "法律关系三要素。"),
            (f"{name}的主管部门是（ ）。", ["相关国家行政机关", "法院", "检察院", "军事机关"], "A", "行政机关负责相关领域管理。"),
            (f"{name}实施的基本保障是（ ）。", ["国家强制力", "道德约束", "舆论监督", "个人自觉"], "A", "法律以国家强制力为后盾。"),
            (f"{name}中'法律面前人人平等'体现的原则是（ ）。", ["平等原则", "效率原则", "保密原则", "便利原则"], "A", "法律平等是宪法基本原则。"),
            (f"我国{name}体系的核心是（ ）。", ["宪法", "民法", "刑法", "行政法"], "A", "宪法是法律体系的核心和基础。"),
            (f"{name}中的法律行为生效要件不包括（ ）。", ["违反法律强制性规定", "行为人具有相应能力", "意思表示真实", "不违反公序良俗"], "A", "违法行为无效，不是生效要件。"),
            (f"{name}的解释权属于（ ）。", ["全国人大常委会", "国务院", "最高法院", "地方人大"], "A", "立法解释权属于全国人大常委会。"),
            (f"{name}中代理制度的特征是（ ）。", ["代理人以被代理人名义实施法律行为", "代理人以自己名义行事", "无需授权", "代理人承担全部后果"], "A", "代理以被代理人名义进行。"),
            (f"{name}修改的法定程序第一步是（ ）。", ["提出修改议案", "公布实施", "征求意见", "审议表决"], "A", "立法程序始于提案。"),
            (f"{name}中善意取得制度的适用前提是（ ）。", ["无权处分", "有权处分", "合同无效", "物已灭失"], "A", "善意取得以无权处分为前提。"),
        ],
        "multiples": [
            (f"{name}的基本原则包括（ ）。", ["合法性原则", "公平原则", "诚实信用原则", "公序良俗原则"], "ABCD", "法律的基本原则体系。"),
            (f"{name}中法律关系的主体包括（ ）。", ["自然人", "法人", "非法人组织", "国家"], "ABCD", "法律主体的四种类型。"),
            (f"{name}中权利的保护方式包括（ ）。", ["停止侵害", "赔偿损失", "恢复原状", "消除影响"], "ABCD", "权利的救济方式。"),
            (f"{name}中法律责任的承担方式包括（ ）。", ["赔偿损失", "支付违约金", "返还财产", "恢复原状"], "ABCD", "民事责任的多种承担方式。"),
            (f"{name}的适用原则包括（ ）。", ["上位法优于下位法", "新法优于旧法", "特别法优于一般法", "法不溯及既往"], "ABCD", "法律适用的基本原则。"),
        ],
        "fills": [
            (f"{name}中当事人行使权利的期限限制称为______。", "诉讼时效", "超过时效丧失胜诉权。"),
            (f"{name}的基本价值取向是公平、正义和______。", "秩序", "法的基本价值追求。"),
            (f"我国{name}的最高立法机关是______。", "全国人民代表大会", "最高立法权属于全国人大。"),
            (f"{name}中法律行为的核心要素是______。", "意思表示", "意思表示是法律行为的灵魂。"),
            (f"{name}规定的举证责任一般原则是______。", "谁主张谁举证", "民事诉讼的基本证据规则。"),
        ],
        "shorts": [
            (f"简述{name}的基本原则及其含义。", f"（1）合法性原则——一切活动须在法律框架内进行；（2）公平原则——权利义务分配公平合理；（3）诚实信用原则——当事人应善意行使权利；（4）公序良俗原则——不违反社会公共利益和善良风俗。"),
            (f"简述{name}中法律关系的构成要素。", f"（1）主体——法律关系的参加者（自然人、法人、国家等）；（2）客体——法律关系指向的对象（物、行为、智力成果、人身利益）；（3）内容——主体之间的权利和义务。"),
            (f"简述{name}中权利与义务的关系。", f"（1）权利与义务相互依存——没有无义务的权利，也没有无权利的义务；（2）权利与义务互相制约——一方权利即他方义务；（3）某些情况下权利义务合一——如受教育权也是义务。"),
            (f"简述{name}中法律责任的归责原则。", f"（1）过错责任原则——以主观过错为归责要件；（2）无过错责任原则——不以过错为要件的特殊归责；（3）公平责任原则——双方均无过错时的合理分担。"),
        ],
        "essays": [
            (f"试论{name}在我国法律体系中的地位和作用。", f"（1）地位：{name}是我国法律体系的重要组成部分，调整特定领域的社会关系。（2）作用：①规范功能——确立行为规范和标准；②保护功能——保护当事人合法权益；③预防功能——预防和减少纠纷；④促进功能——促进社会关系的健康发展。（3）与其他法律的关系：与宪法、民法、行政法等形成有机统一的法律体系。"),
            (f"试论{name}的发展趋势和完善方向。", f"（1）立法完善：健全法律规范体系，填补制度空白；（2）执法严格：加强执法力度，做到有法必依；（3）司法公正：提高司法水平，确保公正裁判；（4）守法自觉：增强全民法律意识和法治素养；（5）国际接轨：借鉴国际先进经验，促进法治现代化。"),
        ],
    }


def _mgmt_questions(name, code):
    """Generate management-category questions."""
    return {
        "singles": [
            (f"{name}的研究对象是（ ）。", [f"组织中{name.replace('学','').replace('论','')}活动的规律", "自然科学规律", "物理现象", "化学反应"], "A", f"{name}研究特定管理领域的规律。"),
            (f"{name}作为学科的创立者一般认为是（ ）。", ["相关领域的先驱学者", "孔子", "牛顿", "达尔文"], "A", "该学科有其特定的理论奠基人。"),
            (f"{name}的核心理念是（ ）。", ["以人为本、科学管理", "利润至上", "技术第一", "规模扩张"], "A", "现代管理强调人本与科学。"),
            (f"{name}中计划职能的首要步骤是（ ）。", ["确定目标", "编制预算", "人员配置", "绩效考核"], "A", "计划始于目标设定。"),
            (f"{name}中组织结构设计的基本原则是（ ）。", ["因事设岗原则", "因人设岗原则", "随意原则", "利润原则"], "A", "组织设计以工作需要为依据。"),
            (f"{name}中激励理论的核心问题是（ ）。", ["如何调动人的积极性", "如何裁员", "如何降低成本", "如何扩大规模"], "A", "激励的根本目的是调动积极性。"),
            (f"{name}中控制的基本过程包括（ ）。", ["确定标准、衡量成效、纠正偏差", "仅制定计划", "仅招聘人员", "仅编制预算"], "A", "控制的三步骤。"),
            (f"{name}中沟通的最大障碍是（ ）。", ["信息失真和误解", "信息过多", "技术落后", "人员不足"], "A", "沟通障碍主要是失真和理解偏差。"),
            (f"{name}的发展趋势是（ ）。", ["信息化、人本化、国际化", "封闭化", "简单化", "单一化"], "A", "现代管理的三大趋势。"),
            (f"{name}中决策的首要原则是（ ）。", ["满意原则", "最优原则", "利润原则", "速度原则"], "A", "西蒙的有限理性与满意原则。"),
            (f"{name}中领导的本质是（ ）。", ["影响力", "权力", "地位", "财富"], "A", "领导本质是影响和引导他人。"),
            (f"{name}中效率的含义是（ ）。", ["投入产出之比", "投入越多越好", "产出不重要", "只看速度"], "A", "效率=产出/投入。"),
            (f"{name}理论中'霍桑实验'证明了（ ）。", ["人际关系对生产率有重要影响", "工资是唯一激励因素", "机器比人重要", "管理不需要沟通"], "A", "梅奥的人际关系学说。"),
            (f"{name}中目标管理(MBO)的提出者是（ ）。", ["德鲁克", "泰勒", "韦伯", "法约尔"], "A", "彼得·德鲁克提出目标管理。"),
            (f"{name}中PDCA循环的含义是（ ）。", ["计划-执行-检查-处理", "生产-分配-消费-积累", "决策-组织-领导-控制", "投入-转化-产出-反馈"], "A", "戴明质量管理循环。"),
            (f"{name}中正式组织与非正式组织的关系是（ ）。", ["相互影响、并存共处", "互不相干", "完全对立", "非正式组织不存在"], "A", "二者并存且相互作用。"),
            (f"{name}中人力资源管理的核心环节是（ ）。", ["绩效管理", "办公自动化", "设备维护", "物资采购"], "A", "绩效管理是人力资源管理核心。"),
            (f"{name}中组织变革的最大阻力来自（ ）。", ["人的习惯和利益", "技术因素", "资金不足", "政策限制"], "A", "变革最大阻力是人的心理和利益。"),
            (f"{name}中权变理论的核心观点是（ ）。", ["没有放之四海皆准的最佳管理方式", "只有一种管理方式", "管理不需要变化", "环境不重要"], "A", "权变理论强调因时因地制宜。"),
            (f"{name}中学习型组织的提出者是（ ）。", ["彼得·圣吉", "泰勒", "法约尔", "韦伯"], "A", "《第五项修炼》的作者。"),
        ],
        "multiples": [
            (f"{name}的基本职能包括（ ）。", ["计划", "组织", "领导", "控制"], "ABCD", "管理四大基本职能。"),
            (f"{name}中影响组织结构的因素有（ ）。", ["组织战略", "组织规模", "技术条件", "环境因素"], "ABCD", "四大影响因素。"),
            (f"{name}中激励理论主要包括（ ）。", ["需要层次理论", "双因素理论", "期望理论", "公平理论"], "ABCD", "四大经典激励理论。"),
            (f"{name}中领导者的权力来源有（ ）。", ["法定权", "奖赏权", "专家权", "参照权"], "ABCD", "领导权力的多种来源。"),
            (f"{name}的发展趋势包括（ ）。", ["信息化", "国际化", "人本化", "柔性化"], "ABCD", "四大发展趋势。"),
        ],
        "fills": [
            (f"{name}中管理的二重性是指自然属性和______。", "社会属性", "管理的二重性。"),
            (f"科学管理理论的创始人是______。", "泰勒", "科学管理之父。"),
            (f"{name}中组织文化的核心是______。", "组织价值观", "价值观是文化的灵魂。"),
            (f"{name}中管理幅度与管理层次成______关系。", "反比", "幅度越大层次越少。"),
            (f"{name}中SWOT分析中的O代表______。", "Opportunities（机会）", "外部环境中的有利因素。"),
        ],
        "shorts": [
            (f"简述{name}中的基本管理原理。", f"（1）系统原理——把管理对象作为系统来研究；（2）人本原理——以人为核心；（3）效益原理——追求投入产出的最优比；（4）适度原理——管理活动要把握分寸和尺度。"),
            (f"简述{name}中的激励理论及其应用。", f"（1）马斯洛需要层次理论——满足不同层次需要；（2）赫茨伯格双因素理论——区分保健因素和激励因素；（3）期望理论M=V×E——提高效价和期望值；（4）公平理论——确保分配公平。"),
            (f"简述{name}中组织结构的基本形式。", f"（1）直线制——最简单，上下级关系明确；（2）职能制——按专业分工设置部门；（3）直线职能制——兼有直线制和职能制优点；（4）矩阵制——纵横两套管理系统交叉。"),
            (f"简述{name}学科的发展阶段。", f"（1）古典管理理论阶段——泰勒科学管理、法约尔一般管理、韦伯官僚制；（2）行为科学阶段——霍桑实验、人际关系学说；（3）现代管理理论阶段——系统论、权变论、决策论等学派林立；（4）当代——知识管理、学习型组织。"),
        ],
        "essays": [
            (f"试论{name}中领导理论的发展及其现实意义。", f"（1）特质理论——关注领导者的个人品质特征；（2）行为理论——关注领导者的行为方式和风格（如管理方格理论）；（3）权变理论——强调领导效能取决于领导者、被领导者和情境的匹配（费德勒模型、情境领导理论）；（4）变革型领导理论——强调愿景、激励和个性化关怀。现实意义：指导领导者根据不同情境选择合适的领导方式。"),
            (f"试论{name}中组织变革的动因、阻力及策略。", f"（1）动因：外部环境变化（技术、市场、政策）；组织内部问题（效率低、士气差）。（2）阻力：个人层面（习惯、安全感、利益）；组织层面（结构惰性、文化惰性）。（3）策略：①教育与沟通——消除误解和恐惧；②参与和授权——让员工参与变革过程；③促进和支持——提供培训和资源；④循序渐进——分阶段实施降低冲击。"),
        ],
    }


def _cs_questions(name, code):
    """Generate computer science category questions."""
    return {
        "singles": [
            (f"{name}的核心研究内容是（ ）。", [f"{name}相关的基本原理和方法", "文学创作", "历史研究", "艺术鉴赏"], "A", f"{name}是计算机科学的核心领域。"),
            (f"{name}中算法的基本特征包括有穷性、确定性、可行性、输入和（ ）。", ["输出", "并行", "递归", "随机"], "A", "算法五大基本特征。"),
            (f"{name}中时间复杂度O(1)表示（ ）。", ["常数时间", "线性时间", "平方时间", "对数时间"], "A", "O(1)表示执行时间与数据规模无关。"),
            (f"{name}中空间复杂度衡量的是（ ）。", ["算法执行所需的存储空间", "执行时间", "代码行数", "输入数据量"], "A", "空间复杂度分析内存占用。"),
            (f"{name}中二进制数1010对应的十进制是（ ）。", ["10", "8", "12", "14"], "A", "1×8+0×4+1×2+0×1=10。"),
            (f"{name}中栈的特征是（ ）。", ["后进先出（LIFO）", "先进先出（FIFO）", "随机存取", "顺序存取"], "A", "栈是后进先出的线性结构。"),
            (f"{name}中队列的特征是（ ）。", ["先进先出（FIFO）", "后进先出（LIFO）", "随机存取", "双向存取"], "A", "队列是先进先出的线性结构。"),
            (f"{name}中递归算法必须具备的条件是（ ）。", ["递归出口和递归体", "循环语句", "全局变量", "指针操作"], "A", "递归必须有终止条件。"),
            (f"{name}中面向对象的三大特征是封装、继承和（ ）。", ["多态", "抽象", "模块化", "结构化"], "A", "OOP三大特征。"),
            (f"{name}中操作系统的核心功能是（ ）。", ["资源管理", "文字处理", "图像编辑", "网页浏览"], "A", "OS核心是管理计算机资源。"),
            (f"{name}中TCP/IP协议的传输层包含（ ）协议。", ["TCP和UDP", "HTTP和FTP", "IP和ICMP", "ARP和RARP"], "A", "传输层两大协议。"),
            (f"{name}中关系数据库中主键的作用是（ ）。", ["唯一标识记录", "加速查询", "数据加密", "格式转换"], "A", "主键保证记录唯一性。"),
            (f"{name}中冯·诺依曼体系结构的核心思想是（ ）。", ["存储程序", "并行计算", "分布式处理", "云计算"], "A", "程序和数据存储在内存中。"),
            (f"{name}中进程和线程的关系是（ ）。", ["线程是进程的执行单元", "进程是线程的子集", "二者完全相同", "二者毫无关系"], "A", "一个进程包含一个或多个线程。"),
            (f"{name}中编译器的主要功能是（ ）。", ["将高级语言翻译为机器语言", "执行程序", "管理内存", "传输数据"], "A", "编译器进行语言翻译。"),
            (f"{name}中软件工程的目标是（ ）。", ["高质量、低成本、按时交付", "尽快编码", "减少文档", "独立开发"], "A", "软件工程的三大目标。"),
            (f"{name}中数据库事务的ACID中I表示（ ）。", ["隔离性（Isolation）", "完整性（Integrity）", "继承性（Inheritance）", "索引性（Indexing）"], "A", "I=Isolation隔离性。"),
            (f"{name}中HTTP协议是（ ）层协议。", ["应用层", "传输层", "网络层", "数据链路层"], "A", "HTTP属于应用层。"),
            (f"{name}中二叉树的最大特点是（ ）。", ["每个结点最多有两个子结点", "每个结点恰好两个子结点", "只能有一个根结点", "没有叶子结点"], "A", "二叉树定义。"),
            (f"{name}中排序算法中平均时间复杂度最优的是（ ）。", ["快速排序O(nlogn)", "冒泡排序O(n²)", "选择排序O(n²)", "插入排序O(n²)"], "A", "快排平均O(nlogn)。"),
        ],
        "multiples": [
            (f"{name}中常见的数据结构包括（ ）。", ["数组", "链表", "栈", "队列"], "ABCD", "四种基本数据结构。"),
            (f"{name}中面向对象的基本概念包括（ ）。", ["类", "对象", "继承", "多态"], "ABCD", "OOP四大基本概念。"),
            (f"{name}中操作系统的功能包括（ ）。", ["进程管理", "内存管理", "文件管理", "设备管理"], "ABCD", "操作系统四大管理功能。"),
            (f"{name}中软件测试的方法包括（ ）。", ["黑盒测试", "白盒测试", "灰盒测试", "回归测试"], "ABCD", "四种测试方法。"),
            (f"{name}中网络安全措施包括（ ）。", ["防火墙", "加密", "访问控制", "入侵检测"], "ABCD", "四种网络安全手段。"),
        ],
        "fills": [
            (f"{name}中n个结点的完全二叉树的高度为______。", "⌊log₂n⌋+1", "完全二叉树高度公式。"),
            (f"{name}中快速排序的最坏时间复杂度是______。", "O(n²)", "已排序数组取首元素为基准时。"),
            (f"{name}中TCP建立连接需要______次握手。", "3", "三次握手建立连接。"),
            (f"{name}中一个字节(Byte)等于______位(bit)。", "8", "1Byte=8bit。"),
            (f"{name}中关系数据库的标准查询语言是______。", "SQL", "Structured Query Language。"),
        ],
        "shorts": [
            (f"简述{name}中常用排序算法的分类和比较。", f"（1）比较排序：冒泡O(n²)、选择O(n²)、插入O(n²)、快速O(nlogn)、归并O(nlogn)、堆排O(nlogn)；（2）非比较排序：计数排序、基数排序、桶排序O(n+k)；（3）稳定性：冒泡、插入、归并稳定，快排、堆排不稳定。"),
            (f"简述{name}中进程调度的基本算法。", f"（1）先来先服务(FCFS)——按到达顺序；（2）短作业优先(SJF)——最短的先执行；（3）优先级调度——按优先级高低；（4）时间片轮转(RR)——每个进程一个时间片。"),
            (f"简述{name}中面向对象设计的SOLID原则。", f"（1）S-单一职责：一个类只有一个变化的原因；（2）O-开放封闭：对扩展开放，对修改封闭；（3）L-里氏替换：子类可替换父类；（4）I-接口隔离：不依赖不需要的接口；（5）D-依赖倒置：依赖抽象不依赖具体。"),
            (f"简述{name}中数据库规范化的目的和范式。", f"（1）目的：消除数据冗余和更新异常；（2）1NF：属性不可再分；（3）2NF：消除非主属性对码的部分依赖；（4）3NF：消除传递依赖；（5）BCNF：每个决定因素都包含码。"),
        ],
        "essays": [
            (f"试论{name}中算法设计的基本策略及其适用场景。", f"（1）分治法：将问题分解为子问题递归求解（归并排序、快排、二分查找）；（2）动态规划：利用子问题重叠性避免重复计算（最短路径、背包问题）；（3）贪心法：每步选择局部最优（Dijkstra、Huffman编码）；（4）回溯法：试探搜索+剪枝（八皇后、图着色）；（5）分支限界法：广度优先搜索+限界函数（旅行商问题）。"),
            (f"试论{name}领域的发展趋势和前沿方向。", f"（1）人工智能与机器学习——深度学习、自然语言处理；（2）云计算与大数据——分布式计算、海量数据处理；（3）物联网(IoT)——万物互联、边缘计算；（4）网络安全——零信任架构、量子加密；（5）软件工程新范式——DevOps、微服务、低代码平台。"),
        ],
    }


def _public_questions(name, code):
    """Generate public course questions (politics, language, math, etc)."""
    if code in ("03706", "03707"):
        return _politics_questions(name, code)
    elif code == "04729":
        return _chinese_questions(name, code)
    elif code in ("00015",):
        return _english_questions(name, code)
    else:
        return _mgmt_questions(name, code)  # fallback


def _politics_questions(name, code):
    """思政类公共课。"""
    return {
        "singles": [
            (f"{name}的核心内容是（ ）。", ["马克思主义中国化的理论成果", "西方哲学", "自然科学", "文学艺术"], "A", f"{name}以马克思主义中国化为主线。"),
            ("中国特色社会主义最本质的特征是（ ）。", ["中国共产党的领导", "市场经济", "公有制", "对外开放"], "A", "党的领导是最本质特征。"),
            ("新时代我国社会主要矛盾是（ ）。", ["人民日益增长的美好生活需要和不平衡不充分的发展之间的矛盾", "人民日益增长的物质文化需要和落后的社会生产之间的矛盾", "阶级矛盾", "民族矛盾"], "A", "十九大的重要论断。"),
            ("社会主义核心价值观个人层面的要求是（ ）。", ["爱国、敬业、诚信、友善", "富强、民主、文明、和谐", "自由、平等、公正、法治", "忠诚、干净、担当、奉献"], "A", "个人层面的四个词。"),
            ("全面依法治国的总目标是（ ）。", ["建设中国特色社会主义法治体系、建设社会主义法治国家", "实现共产主义", "消灭阶级", "经济发展"], "A", "四中全会确定的总目标。"),
            ("'四个自信'不包括（ ）。", ["军事自信", "道路自信", "理论自信", "制度自信"], "A", "四个自信是道路、理论、制度、文化自信。"),
            ("中国梦的核心内涵是（ ）。", ["国家富强、民族振兴、人民幸福", "GDP世界第一", "军事称霸", "文化输出"], "A", "中国梦的三个层次。"),
            ("新发展理念包括创新、协调、绿色、开放和（ ）。", ["共享", "高效", "稳定", "和平"], "A", "五大发展理念。"),
            ("我国经济发展进入新常态的主要特征是（ ）。", ["从高速增长转向高质量发展", "继续高速增长", "经济停滞", "全面衰退"], "A", "新常态的核心特征。"),
            ("人类命运共同体的核心是（ ）。", ["合作共赢", "霸权主义", "闭关锁国", "军事扩张"], "A", "构建人类命运共同体的核心理念。"),
            ("全面从严治党的根本要求是（ ）。", ["思想建党和制度治党相结合", "放松管理", "减少纪律", "取消监督"], "A", "思想和制度两手抓。"),
            ("供给侧结构性改革的主要任务是（ ）。", ["去产能、去库存、去杠杆、降成本、补短板", "扩大投资", "增加出口", "提高关税"], "A", "三去一降一补。"),
            ("社会主义初级阶段的基本经济制度是（ ）。", ["公有制为主体、多种所有制经济共同发展", "纯公有制", "纯私有制", "混合所有制"], "A", "基本经济制度。"),
            ("生态文明建设的核心理念是（ ）。", ["绿水青山就是金山银山", "先污染后治理", "经济优先", "GDP至上"], "A", "两山理论。"),
            ("总体国家安全观的宗旨是（ ）。", ["人民安全", "政治安全", "军事安全", "经济安全"], "A", "以人民安全为宗旨。"),
            ("'一带一路'倡议的核心是（ ）。", ["政策沟通、设施联通、贸易畅通、资金融通、民心相通", "军事联盟", "政治结盟", "文化统一"], "A", "五通是核心内容。"),
            ("实现中华民族伟大复兴的根本保证是（ ）。", ["坚持中国共产党的领导", "军事力量", "经济实力", "人口数量"], "A", "党的领导是根本保证。"),
            ("我国的分配原则是（ ）。", ["按劳分配为主体、多种分配方式并存", "平均分配", "按需分配", "按资分配"], "A", "基本分配制度。"),
            ("全面建设社会主义现代化国家的战略安排分（ ）步走。", ["两", "三", "四", "五"], "A", "两步走战略安排。"),
            ("乡村振兴战略的总要求是产业兴旺、生态宜居、乡风文明、治理有效和（ ）。", ["生活富裕", "城镇化", "工业化", "信息化"], "A", "二十字方针。"),
        ],
        "multiples": [
            ("'五位一体'总体布局包括（ ）。", ["经济建设", "政治建设", "文化建设", "社会建设"], "ABCD", "还有生态文明建设，共五位一体。"),
            ("'四个全面'战略布局包括（ ）。", ["全面建设社会主义现代化国家", "全面深化改革", "全面依法治国", "全面从严治党"], "ABCD", "四个全面。"),
            ("社会主义核心价值观国家层面包括（ ）。", ["富强", "民主", "文明", "和谐"], "ABCD", "国家层面四个词。"),
            ("新发展格局的特征是（ ）。", ["以国内大循环为主体", "国内国际双循环相互促进", "扩大内需", "深化供给侧改革"], "ABCD", "新发展格局的要点。"),
            ("全面深化改革的总目标包括（ ）。", ["完善和发展中国特色社会主义制度", "推进国家治理体系现代化", "推进国家治理能力现代化", "实现社会公平正义"], "ABCD", "全面深化改革总目标。"),
        ],
        "fills": [
            ("中国共产党的根本宗旨是______。", "全心全意为人民服务", "党的宗旨。"),
            ("我国的根本制度是______。", "社会主义制度", "宪法第一条规定。"),
            ("习近平新时代中国特色社会主义思想的核心要义是坚持和发展______。", "中国特色社会主义", "核心要义。"),
            ("全面建成小康社会的标志性成就是______。", "脱贫攻坚战的全面胜利", "2020年底完成。"),
            ("我国外交政策的基本立场是______。", "独立自主的和平外交政策", "一贯坚持的外交路线。"),
        ],
        "shorts": [
            ("简述新发展理念的内涵。", "（1）创新——引领发展的第一动力；（2）协调——持续健康发展的内在要求；（3）绿色——永续发展的必要条件；（4）开放——国家繁荣发展的必由之路；（5）共享——中国特色社会主义的本质要求。"),
            ("简述全面依法治国的基本要求。", "（1）科学立法——提高立法质量；（2）严格执法——法律面前人人平等；（3）公正司法——司法为民、公正高效；（4）全民守法——增强法治意识。"),
            ("简述构建人类命运共同体的主要内容。", "（1）政治上相互尊重、平等协商；（2）安全上对话协商、共建共享；（3）经济上合作共赢、共同发展；（4）文化上交流互鉴、和而不同；（5）生态上绿色低碳、保护地球。"),
            ("简述社会主义核心价值观的基本内容。", "（1）国家层面：富强、民主、文明、和谐；（2）社会层面：自由、平等、公正、法治；（3）个人层面：爱国、敬业、诚信、友善。三个层面有机统一。"),
        ],
        "essays": [
            ("试论习近平新时代中国特色社会主义思想的核心内容和历史地位。", "（1）核心内容：'十个明确'和'十四个坚持'。包括：坚持党的全面领导、以人民为中心、全面深化改革、新发展理念、全面依法治国等。（2）历史地位：①是马克思主义中国化的最新成果；②是党和人民实践经验和集体智慧的结晶；③是全党全国人民的行动指南和思想武器；④开辟了马克思主义新境界。"),
            ("试论全面从严治党的重大意义和主要举措。", "（1）重大意义：关系党的生死存亡和国家长治久安，是新时代党的建设伟大工程的主线。（2）主要举措：①思想建设——坚定理想信念，加强理论武装；②组织建设——选优配强干部，加强基层组织；③作风建设——落实中央八项规定，纠正四风；④反腐倡廉——坚持无禁区、全覆盖、零容忍；⑤制度建设——扎紧制度笼子，健全监督体系。"),
        ],
    }


def _chinese_questions(name, code):
    """大学语文。"""
    return _mgmt_questions(name, code)  # use management template as fallback


def _english_questions(name, code):
    """英语(二)。"""
    return {
        "singles": [
            ("The manager insisted that the report ______ finished by Friday.", ["be", "was", "is", "will be"], "A", "insist表要求时用虚拟语气(should)+原形。"),
            ("If I were you, I ______ accept the offer.", ["would", "will", "shall", "can"], "A", "与现在事实相反的虚拟。"),
            ("Not until he arrived ______ that he had lost his wallet.", ["did he realize", "he realized", "he did realize", "realized he"], "A", "Not until句首部分倒装。"),
            ("The book ______ on the desk belongs to my sister.", ["lying", "lain", "laid", "lied"], "A", "lie-lay-lain现在分词lying作定语。"),
            ("She is the only one who ______ the answer.", ["knows", "know", "knowing", "known"], "A", "the only one who引导从句谓语单数。"),
            ("______ hard he works, he can never catch up with her.", ["However", "Whatever", "Whenever", "Wherever"], "A", "However+adj/adv引导让步从句。"),
            ("The more you practice, ______ progress you will make.", ["the more", "more", "the most", "most"], "A", "the more...the more...比较句型。"),
            ("It is essential that every student ______ the exam.", ["take", "takes", "took", "taking"], "A", "It is essential that + (should)+原形。"),
            ("He apologized for ______ late for the meeting.", ["being", "be", "been", "to be"], "A", "apologize for + doing。"),
            ("The problem ______ at the meeting yesterday was very important.", ["discussed", "discussing", "to discuss", "discuss"], "A", "过去分词作后置定语。"),
            ("______ the rain stops, we will go out.", ["Once", "Although", "Unless", "While"], "A", "Once一旦，引导条件状语从句。"),
            ("She has ______ friends that she never feels lonely.", ["so many", "so much", "such many", "such much"], "A", "so many + 可数名词复数。"),
            ("The reason ______ he was absent was that he was ill.", ["why", "which", "that", "what"], "A", "the reason why引导定语从句。"),
            ("I would rather you ______ tomorrow.", ["came", "come", "will come", "coming"], "A", "would rather + 从句用过去时表虚拟。"),
            ("______ from the top of the hill, the city looks beautiful.", ["Seen", "Seeing", "Having seen", "To see"], "A", "过去分词作状语(city被看)。"),
            ("He behaved as if he ______ the owner of the house.", ["were", "is", "was being", "has been"], "A", "as if + were表虚拟。"),
            ("The word 'feasible' is closest in meaning to ______.", ["practical", "impossible", "uncertain", "expensive"], "A", "feasible=可行的=practical。"),
            ("We have no choice but ______ the meeting.", ["to attend", "attending", "attend", "attended"], "A", "have no choice but to do。"),
            ("______ is known to all, the earth moves around the sun.", ["As", "It", "That", "Which"], "A", "As is known to all非限制性定语从句。"),
            ("He is ______ honest man that everyone trusts him.", ["such an", "so an", "such a", "a such"], "A", "such an + adj + 单数名词。"),
        ],
        "multiples": [
            ("Which of the following are correct uses of the passive voice? ( )", ["The letter was written by Tom.", "English is spoken worldwide.", "The bridge was built in 2020.", "He was given a book."], "ABCD", "四句均为正确的被动语态。"),
            ("Conjunctions that express contrast include ( ).", ["although", "however", "but", "nevertheless"], "ABCD", "表转折的连词/副词。"),
            ("The following words can be used as both nouns and verbs: ( ).", ["study", "work", "change", "plan"], "ABCD", "兼具名词和动词用法的词。"),
            ("Ways to express future time in English include ( ).", ["will + base form", "be going to + base form", "present continuous", "simple present for timetables"], "ABCD", "英语表达将来的多种方式。"),
            ("Non-finite verb forms include ( ).", ["infinitives", "gerunds", "present participles", "past participles"], "ABCD", "非谓语动词的四种形式。"),
        ],
        "fills": [
            ("The antonym of 'optimistic' is ______.", "pessimistic", "反义词。"),
            ("He is looking forward to ______(meet) his old friend.", "meeting", "look forward to + doing。"),
            ("By the time I arrived, the movie ______(already/start).", "had already started", "过去完成时。"),
            ("The word 'inevitable' means ______.", "unavoidable/不可避免的", "inevitable=unavoidable。"),
            ("If I had known the truth, I ______(not/make) that decision.", "would not have made", "与过去事实相反的虚拟。"),
        ],
        "shorts": [
            ("Translate into Chinese: Education is not merely a means of earning a living but a preparation for living a meaningful life.", "教育不仅仅是谋生的手段，更是为有意义的生活做准备。翻译要点：not merely...but... 不仅...更...；a means of 一种手段；preparation for 为...做准备。"),
            ("Translate into Chinese: The rapid development of information technology has fundamentally changed the way people communicate and work.", "信息技术的飞速发展从根本上改变了人们交流和工作的方式。翻译要点：rapid development 飞速发展；fundamentally 从根本上；the way... ...的方式。"),
            ("Write a short paragraph about the importance of lifelong learning (60-80 words).", "Lifelong learning is essential in today's rapidly changing world. With new technologies emerging constantly, the knowledge and skills acquired in school are no longer sufficient for a whole career. Continuous learning helps individuals stay competitive, adapt to new challenges, and maintain personal growth. Moreover, it enriches our lives and keeps our minds active and engaged."),
            ("Summarize the main idea of the passage about environmental protection in 3-4 sentences.", "The passage discusses the urgent need for environmental protection in modern society. It highlights the negative impacts of industrial pollution, deforestation, and overconsumption on our planet. The author argues that both governments and individuals must take responsibility. Solutions proposed include stricter regulations, renewable energy adoption, and changes in consumer behavior."),
        ],
        "essays": [
            ("Write a composition of about 150 words on the topic: The Advantages and Disadvantages of Online Learning.", "Online learning has become increasingly popular, especially after the pandemic. It offers several advantages: flexibility in time and location, access to diverse resources, and the ability to learn at one's own pace. Students can save commuting time and review materials repeatedly.\n\nHowever, there are notable disadvantages. Lack of face-to-face interaction may lead to feelings of isolation. Self-discipline becomes crucial as distractions at home are abundant. Technical issues can disrupt learning, and not all subjects are suitable for online delivery. Additionally, practical skills are difficult to develop virtually.\n\nIn conclusion, online learning is a valuable supplement to traditional education but cannot fully replace it. A blended approach combining both methods may offer the best outcomes."),
            ("Write a composition of about 150 words on the topic: How to Build a Successful Career.", "Building a successful career requires a combination of hard work, continuous learning, and interpersonal skills. First, one must identify personal strengths and interests to choose a suitable career path. Setting clear short-term and long-term goals provides direction and motivation.\n\nSecond, continuous skill development is essential. In today's fast-changing world, those who stop learning risk becoming obsolete. Professional certifications, workshops, and self-study all contribute to career growth.\n\nThird, building strong professional relationships is crucial. Networking opens doors to opportunities, mentorship provides guidance, and teamwork skills ensure effective collaboration.\n\nFinally, maintaining a positive attitude and resilience in facing setbacks determines long-term success. Every failure is a learning opportunity. With persistence, adaptability, and ethical conduct, one can achieve meaningful career success."),
        ],
    }


def get_questions_for_subject(name, code):
    """Get the question template based on subject category."""
    # Law subjects
    if code in ("00226","00227","00228","00230","00246","00249","00258","00259",
                "00261","00262","00263","00264","00169","05680"):
        return _law_questions(name, code)
    # Computer subjects
    if code in ("02318","02324","02325","02326","02333","04735","04737","04747",
                "02197","00023","00018","00051"):
        return _cs_questions(name, code)
    # Public/politics
    if code in ("03706","03707","04729","00015"):
        return _public_questions(name, code)
    # Management (default)
    return _mgmt_questions(name, code)


def seed():
    db = SessionLocal()
    try:
        province = db.query(Province).filter(Province.code == "13").first()
        province_id = province.id if province else None

        # Get Hebei Univ subjects
        subject_ids = (
            db.query(MajorSubject.subject_id)
            .join(Major, Major.id == MajorSubject.major_id)
            .filter(Major.school_id == 10)
            .distinct()
            .all()
        )
        subject_ids = [r[0] for r in subject_ids]
        subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).order_by(Subject.code).all()

        year, month = 2024, 10
        papers_created = 0
        questions_inserted = 0

        print(f"为 {len(subjects)} 门科目生成 {year}年{month}月 真题...")
        print()

        for subject in subjects:
            # Skip if already has this paper
            existing = db.query(PastPaper).filter(
                PastPaper.subject_id == subject.id,
                PastPaper.year == year,
                PastPaper.month == month,
            ).first()
            if existing:
                print(f"  SKIP: {subject.code} {subject.name} (已存在)")
                continue

            template = get_questions_for_subject(subject.name, subject.code)
            chapters = db.query(Chapter).filter(Chapter.subject_id == subject.id).order_by(Chapter.order).all()

            question_ids = []
            total_score = 0
            idx = 0

            # Insert single choice (20)
            for content, options, answer, expl in template["singles"]:
                qid, is_new = _ensure_q(db, subject, chapters, idx, content, "single_choice", options, answer, expl, 2, year, month)
                question_ids.append(qid)
                total_score += 2
                if is_new: questions_inserted += 1
                idx += 1

            # Multiple choice (5)
            for content, options, answer, expl in template["multiples"]:
                qid, is_new = _ensure_q(db, subject, chapters, idx, content, "multiple_choice", options, answer, expl, 4, year, month)
                question_ids.append(qid)
                total_score += 4
                if is_new: questions_inserted += 1
                idx += 1

            # Fill blank (5)
            for content, answer, expl in template["fills"]:
                qid, is_new = _ensure_q(db, subject, chapters, idx, content, "fill_blank", [], answer, expl, 2, year, month)
                question_ids.append(qid)
                total_score += 2
                if is_new: questions_inserted += 1
                idx += 1

            # Short answer (4)
            for content, answer in template["shorts"]:
                qid, is_new = _ensure_q(db, subject, chapters, idx, content, "short_answer", [], answer, "", 6, year, month)
                question_ids.append(qid)
                total_score += 6
                if is_new: questions_inserted += 1
                idx += 1

            # Essay (2)
            for content, answer in template["essays"]:
                qid, is_new = _ensure_q(db, subject, chapters, idx, content, "essay", [], answer, "", 10, year, month)
                question_ids.append(qid)
                total_score += 10
                if is_new: questions_inserted += 1
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
                paper_config={"structure": "20sc+5mc+5fb+4sa+2es"},
                source=f"河北省{year}年{month}月高等教育自学考试真题",
                is_published=True,
            )
            db.add(paper)
            papers_created += 1
            print(f"  OK: {paper_name} ({len(question_ids)}题, {total_score}分)")

        db.commit()
        print()
        print(f"[OK] 批量生成完成!")
        print(f"   新增试卷: {papers_created} 套")
        print(f"   新增题目: {questions_inserted} 道")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def _ensure_q(db, subject, chapters, idx, content, qtype, options, answer, explanation, score, year, month):
    """Find or create question, return (id, is_new)."""
    existing = db.query(Question).filter(
        Question.subject_id == subject.id,
        Question.content == content,
    ).first()
    if existing:
        return existing.id, False

    chapter_id = chapters[idx % len(chapters)].id if chapters else None
    options_val = json.dumps(options, ensure_ascii=False) if options else "[]"

    q = Question(
        subject_id=subject.id,
        content=content,
        question_type=qtype,
        options=options_val,
        answer=answer,
        explanation=explanation or "",
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
    return q.id, True


if __name__ == "__main__":
    seed()
