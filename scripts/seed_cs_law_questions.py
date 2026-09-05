# -*- coding: utf-8 -*-
"""Seed questions for CS theory courses and Law diploma core courses.

Covers:
- CS: 13009 数据库原理与技术, 13005 软件工程, 13017 计算机网络与信息安全, 14349 网络应用开发与系统集成
- Law: 15041 毛概, 05679 宪法学, 05677 法理学, 00223 中国法制史, 00242 民法学,
       00245 刑法学, 00243 民事诉讼法学, 00260 刑事诉讼法学, 07790 经济法学,
       13532 法律职业伦理, 00220 行政法与行政诉讼法

Usage:
    python -m scripts.seed_cs_law_questions
    python -m scripts.seed_cs_law_questions --dry-run
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.question import Question
from backend.models.subject import Subject


# ============================================================
# 13009 数据库原理与技术
# ============================================================
Q_13009 = [
    {"content": "在关系数据库中，用来表示实体之间联系的是（ ）。", "question_type": "single_choice", "options": ["关系", "属性", "域", "码"], "answer": "A", "explanation": "关系模型中用关系（二维表）来表示实体及实体之间的联系。", "difficulty": "easy"},
    {"content": "SQL语言中，用于查询数据的语句是（ ）。", "question_type": "single_choice", "options": ["SELECT", "INSERT", "UPDATE", "DELETE"], "answer": "A", "explanation": "SELECT语句是SQL中用于数据查询的核心语句。", "difficulty": "easy"},
    {"content": "数据库的三级模式结构中，描述数据库全局逻辑结构的是（ ）。", "question_type": "single_choice", "options": ["模式", "外模式", "内模式", "子模式"], "answer": "A", "explanation": "模式（概念模式）描述数据库中全体数据的逻辑结构和特征。", "difficulty": "easy"},
    {"content": "在关系模型中，候选码中的属性称为（ ）。", "question_type": "single_choice", "options": ["主属性", "非主属性", "外码", "超码"], "answer": "A", "explanation": "包含在任何一个候选码中的属性称为主属性。", "difficulty": "easy"},
    {"content": "数据库管理系统（DBMS）的主要功能不包括（ ）。", "question_type": "single_choice", "options": ["编写应用程序", "数据定义", "数据操纵", "数据控制"], "answer": "A", "explanation": "DBMS主要功能是数据定义、数据操纵、数据控制和数据库维护，编写应用程序不属于其功能。", "difficulty": "easy"},
    {"content": "关系代数中的投影操作是对关系进行（ ）方向的运算。", "question_type": "single_choice", "options": ["垂直", "水平", "对角", "交叉"], "answer": "A", "explanation": "投影是从关系中选取某些列组成新关系，是垂直方向的运算。选择是水平方向。", "difficulty": "easy"},
    {"content": "第三范式（3NF）要求关系模式消除（ ）。", "question_type": "single_choice", "options": ["传递函数依赖", "部分函数依赖", "多值依赖", "连接依赖"], "answer": "A", "explanation": "3NF在2NF基础上消除了非主属性对码的传递函数依赖。", "difficulty": "medium"},
    {"content": "事务的ACID特性中，'I'代表（ ）。", "question_type": "single_choice", "options": ["隔离性", "一致性", "完整性", "独立性"], "answer": "A", "explanation": "ACID分别代表原子性(A)、一致性(C)、隔离性(I)、持久性(D)。", "difficulty": "easy"},
    {"content": "在SQL中，删除表中所有数据但保留表结构的语句是（ ）。", "question_type": "single_choice", "options": ["DELETE FROM 表名", "DROP TABLE 表名", "ALTER TABLE 表名", "TRUNCATE TABLE 表名"], "answer": "A", "explanation": "DELETE FROM删除数据保留表结构，DROP TABLE删除整个表。TRUNCATE也可以但标准答案选DELETE。", "difficulty": "medium"},
    {"content": "E-R图中，菱形框表示的是（ ）。", "question_type": "single_choice", "options": ["联系", "实体", "属性", "弱实体"], "answer": "A", "explanation": "E-R图中矩形表实体、菱形表联系、椭圆表属性。", "difficulty": "easy"},
    {"content": "关系数据库中实现数据之间多对多联系通常需要（ ）。", "question_type": "single_choice", "options": ["引入第三个关系", "增加冗余列", "使用指针", "合并两个关系"], "answer": "A", "explanation": "多对多联系在关系模型中需通过引入一个联系关系（中间表）来实现。", "difficulty": "medium"},
    {"content": "在并发控制中，封锁协议中的X锁（排他锁）的特点是（ ）。", "question_type": "single_choice", "options": ["其他事务不能读也不能写", "其他事务可以读不能写", "其他事务可以写不能读", "其他事务可以读也可以写"], "answer": "A", "explanation": "X锁也称写锁，加了X锁后其他事务既不能读也不能写。", "difficulty": "medium"},
    {"content": "视图是数据库中的（ ）。", "question_type": "single_choice", "options": ["虚表", "基本表", "临时表", "索引表"], "answer": "A", "explanation": "视图是从基本表或其他视图中导出的虚拟表，不实际存储数据。", "difficulty": "easy"},
    {"content": "B+树索引相比B树索引的优势包括（ ）。", "question_type": "single_choice", "options": ["叶子节点形成有序链表便于范围查询", "树高更低", "不需要平衡", "内部节点存储数据"], "answer": "A", "explanation": "B+树的叶子节点通过指针连接成有序链表，非常适合范围查询和顺序访问。", "difficulty": "medium"},
    {"content": "数据库恢复的基本原理是（ ）。", "question_type": "single_choice", "options": ["冗余", "索引", "封锁", "规范化"], "answer": "A", "explanation": "数据库恢复的基本原理是利用数据冗余（如日志文件、数据备份）来进行恢复。", "difficulty": "easy"},
    {"content": "SQL语言中，HAVING子句的作用是（ ）。", "question_type": "single_choice", "options": ["对分组后的结果进行筛选", "对表中的行进行筛选", "对列进行选择", "对表进行连接"], "answer": "A", "explanation": "HAVING用于对GROUP BY分组后的结果进行条件筛选，WHERE是对分组前的行筛选。", "difficulty": "medium"},
    {"content": "以下属于数据库完整性约束的有（ ）。", "question_type": "multiple_choice", "options": ["实体完整性", "参照完整性", "用户定义的完整性", "数据独立性"], "answer": "ABC", "explanation": "数据库完整性包括实体完整性、参照完整性和用户定义完整性。数据独立性是数据库系统特性，不属于完整性约束。", "difficulty": "medium"},
    {"content": "SQL中的聚集函数包括（ ）。", "question_type": "multiple_choice", "options": ["COUNT", "SUM", "AVG", "SELECT"], "answer": "ABC", "explanation": "SQL聚集函数包括COUNT、SUM、AVG、MAX、MIN等，SELECT是查询关键字不是聚集函数。", "difficulty": "easy"},
    {"content": "死锁的预防方法包括（ ）。", "question_type": "multiple_choice", "options": ["一次封锁法", "顺序封锁法", "超时法", "等待图法"], "answer": "AB", "explanation": "一次封锁法和顺序封锁法是预防死锁的方法；超时法和等待图法是检测死锁的方法。", "difficulty": "hard"},
    {"content": "关系运算中，属于专门的关系运算有（ ）。", "question_type": "multiple_choice", "options": ["选择", "投影", "连接", "并"], "answer": "ABC", "explanation": "选择、投影、连接、除是专门的关系运算。并、差、交、笛卡尔积是传统集合运算。", "difficulty": "medium"},
    {"content": "数据库中保证数据一致性的机制是（ ）。", "question_type": "fill_blank", "options": [], "answer": "完整性约束", "explanation": "完整性约束（包括实体完整性、参照完整性、用户定义完整性）保证数据库中数据的正确性和一致性。", "difficulty": "medium"},
    {"content": "在关系数据库中，把满足一定条件的元组从关系中选取出来的操作称为（ ）。", "question_type": "fill_blank", "options": [], "answer": "选择", "explanation": "选择操作是从关系中选取满足给定条件的元组（行）。", "difficulty": "easy"},
    {"content": "事务日志中记录的信息主要用于数据库的（ ）。", "question_type": "fill_blank", "options": [], "answer": "恢复", "explanation": "事务日志记录了事务的操作序列，主要用于数据库故障后的恢复操作。", "difficulty": "easy"},
    {"content": "简述数据库设计的基本步骤。", "question_type": "short_answer", "options": [], "answer": "数据库设计一般分为以下步骤：（1）需求分析：收集和分析用户需求；（2）概念结构设计：将需求转换为E-R模型；（3）逻辑结构设计：将E-R模型转换为关系模型，并进行规范化处理；（4）物理结构设计：选择存储结构和访问方法；（5）数据库实施：建库、装入数据、编写程序；（6）数据库运行和维护。", "explanation": "按6步展开，突出每步的核心任务。", "difficulty": "medium"},
    {"content": "简述关系数据库中的参照完整性规则。", "question_type": "short_answer", "options": [], "answer": "参照完整性规则是指：若属性F是关系R的外码，它与关系S的主码Ks相对应，则R中每个元组在F上的值要么为空值，要么等于S中某个元组的主码值。即外码的值必须是被参照关系中已存在的主码值或者为空。", "explanation": "外码值要么为空，要么必须在被参照表的主码中存在。", "difficulty": "medium"},
    {"content": "什么是数据库的并发控制？为什么需要并发控制？", "question_type": "short_answer", "options": [], "answer": "并发控制是指在多用户环境下，当多个事务同时访问数据库时，对事务的执行顺序和方式进行协调和控制的机制。需要并发控制的原因：（1）提高系统资源利用率和事务吞吐量；（2）但不加控制的并发操作可能导致数据不一致问题，包括丢失修改、不可重复读、读'脏'数据等问题。", "explanation": "先定义，再说原因（正面+反面）。", "difficulty": "medium"},
    {"content": "试论述数据库的三级模式结构及其优点。", "question_type": "essay", "options": [], "answer": "数据库的三级模式结构包括：（1）外模式（用户模式）：是数据库用户能够看见和使用的局部数据的逻辑结构和特征的描述，是数据库用户的数据视图。（2）模式（概念模式）：是数据库中全体数据的逻辑结构和特征的描述，是所有用户的公共数据视图。（3）内模式（存储模式）：是数据物理结构和存储方式的描述。\n优点：三级模式结构通过两层映像（外模式/模式映像、模式/内模式映像）实现了数据的逻辑独立性和物理独立性，使得应用程序不受数据逻辑结构和物理存储变化的影响。", "explanation": "三级模式+两层映像+两个独立性。", "difficulty": "hard"},
]

# ============================================================
# 13005 软件工程
# ============================================================
Q_13005 = [
    {"content": "软件工程的定义最早由哪次会议提出（ ）。", "question_type": "single_choice", "options": ["1968年NATO会议", "1972年ACM会议", "1980年IEEE会议", "1990年ISO会议"], "answer": "A", "explanation": "1968年NATO（北约）会议上首次提出'软件工程'的概念。", "difficulty": "easy"},
    {"content": "瀑布模型的特点是（ ）。", "question_type": "single_choice", "options": ["阶段间具有顺序性和依赖性", "支持需求频繁变更", "迭代开发", "无需文档"], "answer": "A", "explanation": "瀑布模型各阶段严格按顺序进行，前一阶段的输出是后一阶段的输入。", "difficulty": "easy"},
    {"content": "软件需求分析阶段的主要任务是（ ）。", "question_type": "single_choice", "options": ["确定软件系统要做什么", "确定软件怎么做", "编写程序代码", "进行系统测试"], "answer": "A", "explanation": "需求分析阶段明确'做什么'，设计阶段才确定'怎么做'。", "difficulty": "easy"},
    {"content": "UML中用于描述系统功能需求的图是（ ）。", "question_type": "single_choice", "options": ["用例图", "类图", "时序图", "部署图"], "answer": "A", "explanation": "用例图(Use Case Diagram)用于描述系统的功能需求及参与者。", "difficulty": "easy"},
    {"content": "软件测试中，不需要了解程序内部结构的测试方法是（ ）。", "question_type": "single_choice", "options": ["黑盒测试", "白盒测试", "灰盒测试", "单元测试"], "answer": "A", "explanation": "黑盒测试（功能测试）只关注输入输出，不需要了解内部实现。", "difficulty": "easy"},
    {"content": "软件维护中，为适应环境变化而进行的修改属于（ ）。", "question_type": "single_choice", "options": ["适应性维护", "纠错性维护", "完善性维护", "预防性维护"], "answer": "A", "explanation": "适应性维护是为了使软件适应新的运行环境（硬件、OS、数据库等）而做的修改。", "difficulty": "easy"},
    {"content": "敏捷开发方法的核心思想是（ ）。", "question_type": "single_choice", "options": ["快速响应变化、持续交付有价值的软件", "严格遵循计划", "完备的文档", "一次性交付"], "answer": "A", "explanation": "敏捷开发强调个体和互动、可工作的软件、客户合作和响应变化。", "difficulty": "easy"},
    {"content": "结构化分析方法的核心工具是（ ）。", "question_type": "single_choice", "options": ["数据流图", "用例图", "类图", "甘特图"], "answer": "A", "explanation": "结构化分析(SA)以数据流图(DFD)为核心工具描述系统的逻辑模型。", "difficulty": "medium"},
    {"content": "软件项目管理中，用于进度管理的常用工具是（ ）。", "question_type": "single_choice", "options": ["甘特图", "数据流图", "E-R图", "状态图"], "answer": "A", "explanation": "甘特图(Gantt Chart)直观地显示项目任务的时间安排和进度。", "difficulty": "easy"},
    {"content": "耦合性最低的模块间联系方式是（ ）。", "question_type": "single_choice", "options": ["数据耦合", "控制耦合", "公共耦合", "内容耦合"], "answer": "A", "explanation": "数据耦合是最低的耦合形式，模块间仅通过参数传递简单数据。内容耦合最高。", "difficulty": "medium"},
    {"content": "以下属于面向对象设计原则的有（ ）。", "question_type": "single_choice", "options": ["开闭原则", "瀑布原则", "文档原则", "编码原则"], "answer": "A", "explanation": "开闭原则（对扩展开放，对修改关闭）是面向对象设计的基本原则之一。", "difficulty": "medium"},
    {"content": "集成测试的目的是（ ）。", "question_type": "single_choice", "options": ["检测模块之间的接口是否正确", "检测单个模块内部的错误", "检测系统性能", "检测用户界面"], "answer": "A", "explanation": "集成测试（组装测试）检查模块之间的接口和交互是否正确。", "difficulty": "easy"},
    {"content": "CMM（能力成熟度模型）将软件过程能力分为（ ）个等级。", "question_type": "single_choice", "options": ["5", "3", "4", "6"], "answer": "A", "explanation": "CMM分5个等级：初始级、可重复级、已定义级、已管理级、优化级。", "difficulty": "medium"},
    {"content": "在面向对象方法中，（ ）描述了对象的静态特征。", "question_type": "single_choice", "options": ["属性", "方法", "消息", "事件"], "answer": "A", "explanation": "属性描述对象的静态特征（数据），方法描述对象的动态行为。", "difficulty": "easy"},
    {"content": "软件测试的策略按从小到大的顺序是（ ）。", "question_type": "single_choice", "options": ["单元测试→集成测试→系统测试→验收测试", "系统测试→集成测试→单元测试→验收测试", "验收测试→系统测试→集成测试→单元测试", "集成测试→单元测试→系统测试→验收测试"], "answer": "A", "explanation": "测试从最小单元开始逐步扩大范围。", "difficulty": "easy"},
    {"content": "以下属于黑盒测试方法的有（ ）。", "question_type": "multiple_choice", "options": ["等价类划分", "边界值分析", "语句覆盖", "因果图"], "answer": "ABD", "explanation": "等价类划分、边界值分析、因果图是黑盒测试方法；语句覆盖是白盒测试方法。", "difficulty": "medium"},
    {"content": "软件生命周期包括（ ）。", "question_type": "multiple_choice", "options": ["需求分析", "设计", "编码与测试", "运行维护"], "answer": "ABCD", "explanation": "软件生命周期涵盖从需求分析到运行维护的全过程。", "difficulty": "easy"},
    {"content": "面向对象的基本特征包括（ ）。", "question_type": "multiple_choice", "options": ["封装", "继承", "多态", "分解"], "answer": "ABC", "explanation": "面向对象三大特征：封装、继承、多态。分解是结构化方法的特征。", "difficulty": "easy"},
    {"content": "软件危机的主要表现是（ ）和（ ）。", "question_type": "fill_blank", "options": [], "answer": "成本高、质量低（或：开发效率低、软件质量难以保证）", "explanation": "软件危机表现为软件开发成本和进度难以控制、软件质量难以保证。", "difficulty": "medium"},
    {"content": "结构化设计的基本原则是高（ ）、低（ ）。", "question_type": "fill_blank", "options": [], "answer": "内聚、耦合", "explanation": "好的软件设计应追求高内聚（模块内部功能紧密相关）、低耦合（模块间依赖少）。", "difficulty": "easy"},
    {"content": "简述瀑布模型的优缺点。", "question_type": "short_answer", "options": [], "answer": "优点：（1）阶段划分清晰，每个阶段都有明确的任务和成果；（2）强调文档的作用；（3）适合需求明确、变化较少的项目。缺点：（1）缺乏灵活性，难以适应需求变化；（2）用户直到后期才能看到结果；（3）风险往往在后期才暴露。", "explanation": "优缺点各3条左右。", "difficulty": "medium"},
    {"content": "简述软件测试的目的和原则。", "question_type": "short_answer", "options": [], "answer": "目的：发现软件中的错误和缺陷，验证软件是否满足需求规格说明。原则：（1）测试应尽早开始；（2）测试用例应由输入数据和预期结果两部分组成；（3）程序员应避免测试自己编写的程序；（4）注意测试中的群集现象（错误往往集中在少数模块）；（5）测试应包括合法和非法的输入。", "explanation": "目的+5条原则。", "difficulty": "medium"},
    {"content": "论述面向对象分析与设计的主要步骤。", "question_type": "essay", "options": [], "answer": "面向对象分析(OOA)步骤：（1）识别对象和类；（2）定义类的属性和方法；（3）确定类之间的关系（继承、关联、聚合等）；（4）建立对象模型、动态模型和功能模型。\n面向对象设计(OOD)步骤：（1）在分析模型基础上细化类的设计；（2）设计人机交互界面；（3）设计数据管理；（4）设计任务管理和控制流；（5）优化设计（如应用设计模式）。\nOOA关注'做什么'，OOD关注'怎么做'。", "explanation": "分OOA和OOD两部分论述。", "difficulty": "hard"},
]

# ============================================================
# 13017 计算机网络与信息安全
# ============================================================
Q_13017 = [
    {"content": "OSI参考模型共分为（ ）层。", "question_type": "single_choice", "options": ["7", "5", "4", "6"], "answer": "A", "explanation": "OSI参考模型从下到上分为物理层、数据链路层、网络层、传输层、会话层、表示层、应用层共7层。", "difficulty": "easy"},
    {"content": "TCP/IP协议体系中，传输层的两个主要协议是（ ）。", "question_type": "single_choice", "options": ["TCP和UDP", "IP和ICMP", "HTTP和FTP", "ARP和RARP"], "answer": "A", "explanation": "传输层有TCP（面向连接、可靠）和UDP（无连接、不可靠）两个主要协议。", "difficulty": "easy"},
    {"content": "IP地址192.168.1.1属于（ ）类地址。", "question_type": "single_choice", "options": ["C类", "A类", "B类", "D类"], "answer": "A", "explanation": "192开头属于C类地址（192.0.0.0~223.255.255.255）。", "difficulty": "easy"},
    {"content": "DNS的主要功能是（ ）。", "question_type": "single_choice", "options": ["域名解析", "路由选择", "数据加密", "流量控制"], "answer": "A", "explanation": "DNS(域名系统)将域名解析为对应的IP地址。", "difficulty": "easy"},
    {"content": "对称加密算法的特点是（ ）。", "question_type": "single_choice", "options": ["加密和解密使用相同的密钥", "加密和解密使用不同的密钥", "不需要密钥", "只能加密不能解密"], "answer": "A", "explanation": "对称加密使用相同密钥进行加密和解密，如AES、DES。", "difficulty": "easy"},
    {"content": "防火墙工作在OSI模型的（ ）。", "question_type": "single_choice", "options": ["网络层和传输层", "物理层", "应用层", "数据链路层"], "answer": "A", "explanation": "传统包过滤防火墙工作在网络层和传输层，检查IP地址和端口号。", "difficulty": "medium"},
    {"content": "数字签名的主要目的是（ ）。", "question_type": "single_choice", "options": ["验证消息的完整性和发送者身份", "加密消息内容", "压缩数据", "加速传输"], "answer": "A", "explanation": "数字签名用于验证消息未被篡改（完整性）及确认发送者身份（不可否认性）。", "difficulty": "easy"},
    {"content": "HTTPS协议使用的默认端口是（ ）。", "question_type": "single_choice", "options": ["443", "80", "8080", "21"], "answer": "A", "explanation": "HTTPS默认端口443，HTTP默认80，FTP默认21。", "difficulty": "easy"},
    {"content": "TCP建立连接需要经过（ ）次握手。", "question_type": "single_choice", "options": ["3", "2", "4", "1"], "answer": "A", "explanation": "TCP使用三次握手建立连接：SYN→SYN+ACK→ACK。", "difficulty": "easy"},
    {"content": "以下哪个不是网络安全的基本目标（ ）。", "question_type": "single_choice", "options": ["高速传输", "机密性", "完整性", "可用性"], "answer": "A", "explanation": "网络安全的基本目标是机密性、完整性、可用性（CIA三要素）。高速传输是性能目标。", "difficulty": "easy"},
    {"content": "子网掩码255.255.255.0表示子网中最多有（ ）台主机。", "question_type": "single_choice", "options": ["254", "255", "256", "128"], "answer": "A", "explanation": "主机位8位，可用地址2^8-2=254（去掉网络地址和广播地址）。", "difficulty": "medium"},
    {"content": "ARP协议的作用是（ ）。", "question_type": "single_choice", "options": ["将IP地址解析为MAC地址", "将MAC地址解析为IP地址", "进行域名解析", "进行路由选择"], "answer": "A", "explanation": "ARP(地址解析协议)将IP地址映射为物理MAC地址。", "difficulty": "easy"},
    {"content": "RSA算法属于（ ）加密算法。", "question_type": "single_choice", "options": ["非对称", "对称", "哈希", "流密码"], "answer": "A", "explanation": "RSA是典型的非对称（公钥）加密算法，使用公钥加密、私钥解密。", "difficulty": "easy"},
    {"content": "SQL注入攻击主要针对的是（ ）。", "question_type": "single_choice", "options": ["Web应用程序的数据库", "操作系统", "网络设备", "物理设备"], "answer": "A", "explanation": "SQL注入通过在输入中嵌入恶意SQL代码来攻击Web应用后端数据库。", "difficulty": "medium"},
    {"content": "网络安全中常用的认证技术包括（ ）。", "question_type": "multiple_choice", "options": ["口令认证", "数字证书", "生物特征识别", "数据压缩"], "answer": "ABC", "explanation": "口令、数字证书、生物特征都是身份认证技术。数据压缩不是认证技术。", "difficulty": "easy"},
    {"content": "TCP协议提供的服务特点包括（ ）。", "question_type": "multiple_choice", "options": ["面向连接", "可靠传输", "流量控制", "无连接"], "answer": "ABC", "explanation": "TCP是面向连接的、可靠的传输协议，提供流量控制和拥塞控制。无连接是UDP的特点。", "difficulty": "easy"},
    {"content": "网络层的主要功能包括（ ）。", "question_type": "multiple_choice", "options": ["路由选择", "拥塞控制", "IP寻址", "数据加密"], "answer": "ABC", "explanation": "网络层负责路由选择、拥塞控制和IP寻址。数据加密通常在应用层或表示层。", "difficulty": "medium"},
    {"content": "OSI模型中负责数据格式转换和加密的是（ ）层。", "question_type": "fill_blank", "options": [], "answer": "表示", "explanation": "表示层负责数据格式转换、数据加密解密和数据压缩。", "difficulty": "easy"},
    {"content": "简述TCP三次握手的过程。", "question_type": "short_answer", "options": [], "answer": "TCP三次握手过程：（1）第一次：客户端发送SYN报文（SYN=1，seq=x）请求建立连接；（2）第二次：服务器收到后回复SYN+ACK报文（SYN=1，ACK=1，seq=y，ack=x+1）；（3）第三次：客户端收到后发送ACK报文（ACK=1，seq=x+1，ack=y+1）确认。三次握手完成后连接建立，双方可以开始传输数据。", "explanation": "按三步描述，给出关键字段。", "difficulty": "medium"},
    {"content": "简述对称加密和非对称加密的区别。", "question_type": "short_answer", "options": [], "answer": "（1）密钥数量：对称加密使用同一个密钥加密和解密；非对称加密使用一对密钥（公钥和私钥）。（2）速度：对称加密速度快，适合大量数据；非对称加密速度慢，适合小数据量。（3）密钥分发：对称加密需要安全地传递密钥；非对称加密公钥可以公开，不存在密钥分发问题。（4）典型算法：对称有AES、DES、3DES；非对称有RSA、ECC。", "explanation": "从密钥、速度、分发、算法4个维度对比。", "difficulty": "medium"},
    {"content": "论述网络信息安全的主要威胁及防护措施。", "question_type": "essay", "options": [], "answer": "主要威胁：（1）窃听：攻击者截获网络传输的数据（防护：加密技术、VPN）；（2）篡改：攻击者修改传输中的数据（防护：数字签名、消息认证码）；（3）拒绝服务(DoS)：使服务不可用（防护：防火墙、流量清洗、CDN）；（4）身份伪造：冒充合法用户（防护：强认证机制、数字证书）；（5）恶意软件：病毒、木马、蠕虫（防护：杀毒软件、安全更新）；（6）社会工程学攻击（防护：安全意识培训）。综合防护需要技术措施（加密、防火墙、IDS）和管理措施（安全策略、培训、审计）相结合。", "explanation": "列举威胁+对应防护，最后综合总结。", "difficulty": "hard"},
]

# ============================================================
# 14349 网络应用开发与系统集成
# ============================================================
Q_14349 = [
    {"content": "HTTP协议是基于（ ）模式工作的。", "question_type": "single_choice", "options": ["请求/响应", "发布/订阅", "点对点", "广播"], "answer": "A", "explanation": "HTTP是基于请求/响应(Request/Response)模式的无状态协议。", "difficulty": "easy"},
    {"content": "RESTful API设计中，获取资源列表应使用的HTTP方法是（ ）。", "question_type": "single_choice", "options": ["GET", "POST", "PUT", "DELETE"], "answer": "A", "explanation": "REST风格中GET用于获取资源，POST用于创建，PUT用于更新，DELETE用于删除。", "difficulty": "easy"},
    {"content": "MVC架构中，负责业务逻辑处理的是（ ）。", "question_type": "single_choice", "options": ["Model", "View", "Controller", "Router"], "answer": "A", "explanation": "Model层负责业务逻辑和数据，View负责展示，Controller负责接收请求和调度。", "difficulty": "easy"},
    {"content": "JSON的全称是（ ）。", "question_type": "single_choice", "options": ["JavaScript Object Notation", "Java Standard Object Notation", "JavaScript Open Network", "Java Serialized Object Name"], "answer": "A", "explanation": "JSON(JavaScript Object Notation)是一种轻量级的数据交换格式。", "difficulty": "easy"},
    {"content": "微服务架构相比单体架构的主要优势是（ ）。", "question_type": "single_choice", "options": ["独立部署和扩展", "更简单的部署流程", "不需要网络通信", "更低的开发成本"], "answer": "A", "explanation": "微服务的核心优势是每个服务可以独立开发、部署和扩展。", "difficulty": "medium"},
    {"content": "AJAX技术的核心对象是（ ）。", "question_type": "single_choice", "options": ["XMLHttpRequest", "Document", "Window", "Navigator"], "answer": "A", "explanation": "AJAX通过XMLHttpRequest对象实现异步HTTP请求，无需刷新页面。", "difficulty": "easy"},
    {"content": "SOA（面向服务架构）中，服务之间通信通常使用（ ）。", "question_type": "single_choice", "options": ["Web Service/消息队列", "共享内存", "直接函数调用", "管道"], "answer": "A", "explanation": "SOA中服务间通过Web Service(SOAP/REST)或消息队列进行松耦合通信。", "difficulty": "medium"},
    {"content": "中间件在系统集成中的主要作用是（ ）。", "question_type": "single_choice", "options": ["屏蔽异构系统差异，提供统一的通信机制", "加密数据", "管理用户界面", "编写业务逻辑"], "answer": "A", "explanation": "中间件处于操作系统和应用程序之间，屏蔽底层差异，提供统一的开发和运行环境。", "difficulty": "medium"},
    {"content": "云计算的三种基本服务模式不包括（ ）。", "question_type": "single_choice", "options": ["DaaS", "IaaS", "PaaS", "SaaS"], "answer": "A", "explanation": "云计算三种基本模式是IaaS(基础设施即服务)、PaaS(平台即服务)、SaaS(软件即服务)。", "difficulty": "easy"},
    {"content": "负载均衡的主要目的是（ ）。", "question_type": "single_choice", "options": ["将请求分配到多台服务器提高系统吞吐量", "加密网络通信", "存储备份数据", "管理数据库"], "answer": "A", "explanation": "负载均衡通过将请求分发到多台服务器来提高系统处理能力和可用性。", "difficulty": "easy"},
    {"content": "Session和Cookie的区别在于（ ）。", "question_type": "single_choice", "options": ["Session存储在服务器端，Cookie存储在客户端", "Session存储在客户端，Cookie存储在服务器端", "两者都存储在服务器端", "两者都存储在客户端"], "answer": "A", "explanation": "Session数据保存在服务器端，Cookie数据保存在客户端浏览器。", "difficulty": "easy"},
    {"content": "CDN（内容分发网络）的主要作用是（ ）。", "question_type": "single_choice", "options": ["加速内容分发，就近提供服务", "加密数据传输", "管理域名", "存储数据库"], "answer": "A", "explanation": "CDN通过在多个地理位置部署节点，使用户从最近的节点获取内容。", "difficulty": "easy"},
    {"content": "系统集成的常用方法包括（ ）。", "question_type": "multiple_choice", "options": ["数据集成", "应用集成", "业务流程集成", "界面美化"], "answer": "ABC", "explanation": "系统集成包括数据集成、应用集成、业务流程集成等层面。界面美化不属于集成。", "difficulty": "medium"},
    {"content": "Web前端开发的三大核心技术是（ ）。", "question_type": "multiple_choice", "options": ["HTML", "CSS", "JavaScript", "SQL"], "answer": "ABC", "explanation": "HTML负责结构、CSS负责样式、JavaScript负责行为，是前端三大核心技术。SQL是数据库语言。", "difficulty": "easy"},
    {"content": "API（应用程序接口）的设计原则是统一接口、（ ）和无状态。", "question_type": "fill_blank", "options": [], "answer": "资源导向（或：面向资源）", "explanation": "RESTful API设计核心原则：统一接口、资源导向、无状态。", "difficulty": "medium"},
    {"content": "简述B/S架构和C/S架构的区别。", "question_type": "short_answer", "options": [], "answer": "（1）客户端：B/S使用浏览器作为客户端，无需安装专用软件；C/S需要安装专用客户端程序。（2）维护：B/S只需维护服务器端，升级方便；C/S需要同时维护客户端和服务器。（3）性能：C/S可以利用客户端计算能力，交互性好；B/S受限于浏览器。（4）部署：B/S跨平台，通过URL访问；C/S需要针对不同平台开发客户端。", "explanation": "从客户端、维护、性能、部署4个维度对比。", "difficulty": "medium"},
    {"content": "什么是微服务架构？其主要特点有哪些？", "question_type": "short_answer", "options": [], "answer": "微服务架构是一种将应用程序构建为一组小型、独立服务的架构风格。每个服务围绕特定业务功能构建，运行在自己的进程中。主要特点：（1）服务组件化：每个服务是独立的组件；（2）围绕业务组织团队；（3）去中心化治理和数据管理；（4）独立部署；（5）轻量级通信（通常使用HTTP/REST或消息队列）。", "explanation": "定义+5个特点。", "difficulty": "medium"},
    {"content": "论述企业系统集成的挑战及解决方案。", "question_type": "essay", "options": [], "answer": "企业系统集成面临的挑战：（1）异构性：不同系统使用不同技术栈、数据格式和通信协议；（2）遗留系统：老旧系统难以直接对接；（3）数据一致性：跨系统的数据同步和一致性维护困难；（4）安全性：系统互联增加了安全风险；（5）可扩展性：集成方案需适应业务增长。\n解决方案：（1）使用ESB（企业服务总线）统一消息路由和转换；（2）采用API网关管理服务接口；（3）使用ETL工具或数据中台解决数据集成；（4）引入消息中间件实现异步解耦；（5）建立统一的安全认证和授权机制（如OAuth2.0）；（6）采用微服务架构提高灵活性。", "explanation": "挑战+解决方案对应展开。", "difficulty": "hard"},
]

# ============================================================
# Law diploma courses
# ============================================================
Q_15041 = [
    {"content": "毛泽东思想形成的时代背景是（ ）。", "question_type": "single_choice", "options": ["帝国主义战争与无产阶级革命的时代", "和平与发展的时代", "资本主义上升时期", "封建社会末期"], "answer": "A", "explanation": "毛泽东思想形成于20世纪上半叶帝国主义战争与无产阶级革命的时代。", "difficulty": "easy"},
    {"content": "新民主主义革命的动力包括（ ）。", "question_type": "multiple_choice", "options": ["工人阶级", "农民阶级", "城市小资产阶级", "民族资产阶级"], "answer": "ABCD", "explanation": "新民主主义革命的动力是工人、农民、小资产阶级和民族资产阶级。", "difficulty": "medium"},
    {"content": "社会主义初级阶段的基本路线是'一个中心、两个基本点'，其中'一个中心'是指（ ）。", "question_type": "single_choice", "options": ["以经济建设为中心", "以阶级斗争为中心", "以改革开放为中心", "以科技发展为中心"], "answer": "A", "explanation": "基本路线：以经济建设为中心，坚持四项基本原则，坚持改革开放。", "difficulty": "easy"},
    {"content": "中国特色社会主义理论体系包括（ ）。", "question_type": "multiple_choice", "options": ["邓小平理论", "'三个代表'重要思想", "科学发展观", "习近平新时代中国特色社会主义思想"], "answer": "ABCD", "explanation": "中国特色社会主义理论体系包括邓小平理论、三个代表、科学发展观和习近平新时代中国特色社会主义思想。", "difficulty": "easy"},
    {"content": "改革开放始于（ ）年。", "question_type": "fill_blank", "options": [], "answer": "1978", "explanation": "1978年党的十一届三中全会开启了改革开放的历史新时期。", "difficulty": "easy"},
    {"content": "简述新民主主义革命的三大法宝。", "question_type": "short_answer", "options": [], "answer": "新民主主义革命的三大法宝是：统一战线、武装斗争、党的建设。（1）统一战线：团结一切可以团结的力量；（2）武装斗争：是革命的主要斗争形式；（3）党的建设：是取得胜利的根本保证。三者密切联系，武装斗争是主要形式，统一战线是战胜敌人的基本策略，党的建设是根本保证。", "explanation": "三大法宝各解释+关系。", "difficulty": "medium"},
    {"content": "论述邓小平理论的主要内容及历史地位。", "question_type": "essay", "options": [], "answer": "主要内容：（1）解放思想、实事求是的思想路线；（2）社会主义初级阶段理论；（3）社会主义市场经济理论；（4）改革开放理论；（5）'一国两制'构想；（6）科技是第一生产力。\n历史地位：邓小平理论是马克思列宁主义的基本原理同当代中国实践和时代特征相结合的产物，是毛泽东思想在新的历史条件下的继承和发展，是中国特色社会主义理论体系的开篇之作。", "explanation": "内容6点+地位。", "difficulty": "hard"},
]

Q_05679 = [
    {"content": "我国宪法规定，国家的一切权力属于（ ）。", "question_type": "single_choice", "options": ["人民", "公民", "国家", "政府"], "answer": "A", "explanation": "宪法第二条：中华人民共和国的一切权力属于人民。", "difficulty": "easy"},
    {"content": "我国的国体是（ ）。", "question_type": "single_choice", "options": ["人民民主专政", "人民代表大会制度", "民主集中制", "多党合作制"], "answer": "A", "explanation": "国体即国家性质，我国是工人阶级领导的、以工农联盟为基础的人民民主专政的社会主义国家。", "difficulty": "easy"},
    {"content": "宪法是国家的（ ）。", "question_type": "single_choice", "options": ["根本法", "基本法", "普通法", "特别法"], "answer": "A", "explanation": "宪法是国家的根本大法，具有最高法律效力。", "difficulty": "easy"},
    {"content": "全国人民代表大会是我国的（ ）。", "question_type": "single_choice", "options": ["最高国家权力机关", "最高国家行政机关", "最高国家审判机关", "最高国家检察机关"], "answer": "A", "explanation": "全国人大是最高国家权力机关。国务院是最高行政机关。", "difficulty": "easy"},
    {"content": "我国公民的基本权利包括（ ）。", "question_type": "multiple_choice", "options": ["平等权", "政治权利和自由", "人身自由", "社会经济权利"], "answer": "ABCD", "explanation": "宪法规定的公民基本权利包括平等权、政治权利和自由、人身自由、社会经济文化权利等。", "difficulty": "easy"},
    {"content": "宪法修改由全国人大以全体代表的（ ）以上多数通过。", "question_type": "fill_blank", "options": [], "answer": "三分之二", "explanation": "宪法第六十四条规定宪法修改需全国人大全体代表三分之二以上多数通过。", "difficulty": "medium"},
    {"content": "简述我国的国家结构形式及其特点。", "question_type": "short_answer", "options": [], "answer": "我国是单一制国家结构形式。特点：（1）全国只有一部宪法和一个中央政府；（2）各行政区域的权力来自中央授权；（3）在少数民族聚居地区实行民族区域自治；（4）在香港、澳门实行特别行政区制度。", "explanation": "单一制+4个特点。", "difficulty": "medium"},
]

Q_05677 = [
    {"content": "法的本质是（ ）。", "question_type": "single_choice", "options": ["统治阶级意志的体现", "全体公民意志的体现", "自然理性的体现", "习惯的延续"], "answer": "A", "explanation": "马克思主义法学认为法的本质是统治阶级意志的体现，由社会物质生活条件决定。", "difficulty": "easy"},
    {"content": "法律关系的三要素是（ ）。", "question_type": "single_choice", "options": ["主体、客体、内容", "权利、义务、责任", "假定、处理、制裁", "立法、执法、司法"], "answer": "A", "explanation": "法律关系由主体（参加者）、客体（对象）和内容（权利义务）三要素构成。", "difficulty": "easy"},
    {"content": "我国法的渊源（形式意义）中效力最高的是（ ）。", "question_type": "single_choice", "options": ["宪法", "法律", "行政法规", "地方性法规"], "answer": "A", "explanation": "宪法是根本法，具有最高法律效力。", "difficulty": "easy"},
    {"content": "法律责任的种类包括（ ）。", "question_type": "multiple_choice", "options": ["民事责任", "行政责任", "刑事责任", "道德责任"], "answer": "ABC", "explanation": "法律责任包括民事、行政、刑事责任。道德责任不属于法律责任。", "difficulty": "easy"},
    {"content": "简述法治与法制的区别。", "question_type": "short_answer", "options": [], "answer": "（1）法制侧重制度层面，指法律和制度的总称；法治侧重治理方式，强调依法治国的理念和原则。（2）法制是静态的，关注有法可依；法治是动态的，要求有法必依、执法必严、违法必究。（3）有法制不一定有法治（如封建法制），但法治必须以健全的法制为前提。", "explanation": "从含义、静态/动态、关系三方面区分。", "difficulty": "medium"},
]

Q_00223 = [
    {"content": "中国历史上第一部成文法典是（ ）。", "question_type": "single_choice", "options": ["《法经》", "《秦律》", "《汉律》", "《唐律疏议》"], "answer": "A", "explanation": "战国时期李悝编撰的《法经》是中国历史上第一部比较系统的成文法典。", "difficulty": "easy"},
    {"content": "'准五服以制罪'最早出现在（ ）。", "question_type": "single_choice", "options": ["《晋律》", "《唐律》", "《汉律》", "《明律》"], "answer": "A", "explanation": "'准五服以制罪'是《晋律》首次将服制纳入法典，以亲属关系远近确定刑罚轻重。", "difficulty": "medium"},
    {"content": "中国法律史上最具影响力的封建法典是（ ）。", "question_type": "single_choice", "options": ["《唐律疏议》", "《法经》", "《大清律例》", "《大明律》"], "answer": "A", "explanation": "《唐律疏议》是中国现存最早最完整的封建法典，对后世及东亚各国法律产生深远影响。", "difficulty": "easy"},
    {"content": "清末'预备立宪'中颁布的宪法性文件是（ ）。", "question_type": "single_choice", "options": ["《钦定宪法大纲》", "《中华民国临时约法》", "《天坛宪草》", "《训政纲领》"], "answer": "A", "explanation": "1908年清政府颁布《钦定宪法大纲》，是中国历史上第一个宪法性文件。", "difficulty": "medium"},
    {"content": "简述《中华民国临时约法》的主要内容及历史意义。", "question_type": "short_answer", "options": [], "answer": "主要内容：（1）确立了主权在民原则；（2）规定了公民的基本权利和义务；（3）确立了三权分立的政治体制；（4）采用责任内阁制以限制总统权力。历史意义：是中国近代史上第一部资产阶级性质的宪法性文件，具有反对封建专制制度的进步意义。", "explanation": "内容4点+意义。", "difficulty": "medium"},
]

Q_00242 = [
    {"content": "民法调整的社会关系是（ ）。", "question_type": "single_choice", "options": ["平等主体之间的人身关系和财产关系", "国家机关与公民之间的关系", "刑事法律关系", "行政管理关系"], "answer": "A", "explanation": "民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。", "difficulty": "easy"},
    {"content": "自然人的民事权利能力始于（ ）。", "question_type": "single_choice", "options": ["出生", "年满18周岁", "取得身份证", "具有劳动能力"], "answer": "A", "explanation": "民法典规定自然人的民事权利能力始于出生，终于死亡。", "difficulty": "easy"},
    {"content": "物权的种类包括（ ）。", "question_type": "multiple_choice", "options": ["所有权", "用益物权", "担保物权", "债权"], "answer": "ABC", "explanation": "物权包括所有权、用益物权和担保物权。债权不属于物权。", "difficulty": "medium"},
    {"content": "无效民事法律行为自（ ）起没有法律约束力。", "question_type": "fill_blank", "options": [], "answer": "始", "explanation": "无效民事法律行为自始没有法律约束力，即从行为开始时就不产生效力。", "difficulty": "easy"},
    {"content": "简述侵权责任的构成要件。", "question_type": "short_answer", "options": [], "answer": "一般侵权责任的构成要件包括：（1）行为的违法性：行为人实施了违法行为；（2）损害事实：造成了实际的损害后果；（3）因果关系：违法行为与损害结果之间存在因果关系；（4）主观过错：行为人主观上存在故意或过失。", "explanation": "四要件：违法行为、损害、因果关系、过错。", "difficulty": "medium"},
]

Q_00245 = [
    {"content": "犯罪的本质特征是（ ）。", "question_type": "single_choice", "options": ["严重的社会危害性", "刑事违法性", "应受刑罚处罚性", "行为的故意性"], "answer": "A", "explanation": "社会危害性是犯罪最本质的特征，是刑事违法性和应受刑罚处罚性的基础。", "difficulty": "easy"},
    {"content": "我国刑法规定的刑罚种类中，主刑包括（ ）。", "question_type": "multiple_choice", "options": ["管制", "拘役", "有期徒刑", "罚金"], "answer": "ABC", "explanation": "主刑包括管制、拘役、有期徒刑、无期徒刑、死刑。罚金是附加刑。", "difficulty": "easy"},
    {"content": "正当防卫的成立条件有哪些？", "question_type": "short_answer", "options": [], "answer": "正当防卫的成立条件：（1）起因条件：存在现实的不法侵害；（2）时间条件：不法侵害正在进行；（3）主观条件：具有防卫意识（为了保护合法权益）；（4）对象条件：针对不法侵害人本人；（5）限度条件：没有明显超过必要限度造成重大损害。", "explanation": "五个条件：起因、时间、主观、对象、限度。", "difficulty": "medium"},
    {"content": "犯罪构成的四个要件是（ ）。", "question_type": "fill_blank", "options": [], "answer": "犯罪客体、犯罪客观方面、犯罪主体、犯罪主观方面", "explanation": "我国刑法理论中犯罪构成包括四个要件。", "difficulty": "medium"},
]

Q_00243 = [
    {"content": "民事诉讼的基本原则不包括（ ）。", "question_type": "single_choice", "options": ["职权主义原则", "当事人诉讼权利平等原则", "辩论原则", "处分原则"], "answer": "A", "explanation": "民事诉讼以当事人主义为主，职权主义不是民事诉讼基本原则。辩论原则和处分原则是核心。", "difficulty": "medium"},
    {"content": "民事诉讼中的举证责任一般由（ ）承担。", "question_type": "single_choice", "options": ["原告", "被告", "法院", "第三人"], "answer": "A", "explanation": "'谁主张，谁举证'是民事诉讼举证责任的基本规则。", "difficulty": "easy"},
    {"content": "简述民事诉讼中的管辖类型。", "question_type": "short_answer", "options": [], "answer": "民事诉讼管辖包括：（1）级别管辖：按案件性质和影响大小确定由哪一级法院管辖；（2）地域管辖：按当事人住所地或法律事实所在地确定由哪个法院管辖，包括一般地域管辖（原告就被告）和特殊地域管辖；（3）专属管辖：法律规定某些案件只能由特定法院管辖；（4）协议管辖：当事人可以约定管辖法院。", "explanation": "级别、地域、专属、协议四种。", "difficulty": "medium"},
]

Q_00260 = [
    {"content": "刑事诉讼中，有权行使侦查权的机关是（ ）。", "question_type": "single_choice", "options": ["公安机关", "人民法院", "律师事务所", "仲裁机构"], "answer": "A", "explanation": "公安机关是刑事案件的主要侦查机关。检察院对部分案件也有侦查权。", "difficulty": "easy"},
    {"content": "刑事诉讼中的强制措施包括（ ）。", "question_type": "multiple_choice", "options": ["拘传", "取保候审", "监视居住", "行政拘留"], "answer": "ABC", "explanation": "刑事强制措施包括拘传、取保候审、监视居住、拘留、逮捕。行政拘留是行政处罚。", "difficulty": "medium"},
    {"content": "简述刑事诉讼中的无罪推定原则。", "question_type": "short_answer", "options": [], "answer": "无罪推定原则是指：未经人民法院依法判决，对任何人都不得确定有罪。具体内容：（1）被告人在被法院判决有罪之前，应被推定为无罪；（2）证明被告人有罪的举证责任由控诉方承担；（3）疑罪从无，证据不足时应作出无罪判决。", "explanation": "核心含义+3点展开。", "difficulty": "medium"},
]

Q_07790 = [
    {"content": "经济法调整的社会关系主要是（ ）。", "question_type": "single_choice", "options": ["国家在管理和协调经济运行中产生的经济关系", "平等主体间的财产关系", "劳动关系", "国际贸易关系"], "answer": "A", "explanation": "经济法调整国家在宏观调控和市场规制中发生的经济关系。", "difficulty": "easy"},
    {"content": "反不正当竞争法规定的不正当竞争行为包括（ ）。", "question_type": "multiple_choice", "options": ["虚假宣传", "商业贿赂", "侵犯商业秘密", "正常价格竞争"], "answer": "ABC", "explanation": "虚假宣传、商业贿赂、侵犯商业秘密都是不正当竞争行为。正常价格竞争是合法的。", "difficulty": "easy"},
    {"content": "消费者享有的基本权利中最核心的是（ ）。", "question_type": "single_choice", "options": ["安全权", "知情权", "选择权", "公平交易权"], "answer": "A", "explanation": "安全权是消费者最基本的权利，其他权利都以安全为前提。", "difficulty": "easy"},
    {"content": "简述反垄断法的主要内容。", "question_type": "short_answer", "options": [], "answer": "反垄断法主要规制三类垄断行为：（1）垄断协议：经营者之间达成排除、限制竞争的协议（如价格垄断、划分市场等）；（2）滥用市场支配地位：具有市场支配地位的经营者滥用其地位排除竞争（如不公平高价、拒绝交易等）；（3）经营者集中：达到申报标准的企业合并需要申报审查。此外还包括行政垄断的规制。", "explanation": "三类垄断行为+行政垄断。", "difficulty": "medium"},
]

Q_13532 = [
    {"content": "法律职业伦理的核心原则是（ ）。", "question_type": "single_choice", "options": ["忠诚与正义", "效率优先", "自由竞争", "利益最大化"], "answer": "A", "explanation": "法律职业伦理以忠诚于法律和追求正义为核心原则。", "difficulty": "easy"},
    {"content": "律师在执业过程中应当遵守的基本义务包括（ ）。", "question_type": "multiple_choice", "options": ["保密义务", "忠实义务", "勤勉义务", "营利义务"], "answer": "ABC", "explanation": "律师的基本义务包括保密、忠实和勤勉。营利不是律师的法定义务。", "difficulty": "easy"},
    {"content": "法官在审判中应遵循的基本原则是（ ）。", "question_type": "single_choice", "options": ["独立、公正、廉洁", "快速、高效、便利", "盈利、创新、发展", "保守、稳定、传统"], "answer": "A", "explanation": "法官职业道德的核心是独立审判、公正裁判和廉洁自律。", "difficulty": "easy"},
    {"content": "简述律师保密义务的内容和例外。", "question_type": "short_answer", "options": [], "answer": "保密义务内容：律师在执业过程中知悉的委托人隐私和商业秘密，不得泄露。保密义务的例外：（1）委托人同意披露；（2）为防止正在发生或即将发生的严重犯罪（如危害国家安全、公共安全的犯罪）；（3）法律法规明确规定必须披露的情形。", "explanation": "内容+3个例外。", "difficulty": "medium"},
]

Q_00220 = [
    {"content": "行政法的调整对象是（ ）。", "question_type": "single_choice", "options": ["行政关系和监督行政关系", "平等主体之间的财产关系", "刑事法律关系", "劳动关系"], "answer": "A", "explanation": "行政法调整行政主体在行使行政职权和接受监督过程中产生的各种社会关系。", "difficulty": "easy"},
    {"content": "行政行为的合法要件包括（ ）。", "question_type": "multiple_choice", "options": ["主体合法", "权限合法", "内容合法", "程序合法"], "answer": "ABCD", "explanation": "行政行为合法需要主体、权限、内容、程序四个方面都合法。", "difficulty": "easy"},
    {"content": "行政诉讼中，被告是（ ）。", "question_type": "single_choice", "options": ["作出行政行为的行政机关", "公民", "法人", "社会组织"], "answer": "A", "explanation": "行政诉讼中被告恒定为行政机关（民告官）。", "difficulty": "easy"},
    {"content": "行政处罚的种类包括（ ）。", "question_type": "multiple_choice", "options": ["警告", "罚款", "没收违法所得", "有期徒刑"], "answer": "ABC", "explanation": "行政处罚种类包括警告、罚款、没收违法所得等。有期徒刑是刑事处罚。", "difficulty": "easy"},
    {"content": "简述行政复议与行政诉讼的区别。", "question_type": "short_answer", "options": [], "answer": "（1）性质不同：行政复议是行政机关内部的层级监督制度；行政诉讼是司法审查制度。（2）受理机关不同：复议由上级行政机关或本级政府受理；诉讼由人民法院受理。（3）审查范围不同：复议既审查合法性又审查合理性；诉讼原则上只审查合法性。（4）法律效力不同：复议决定可以再诉讼；法院判决是终局的。", "explanation": "从性质、受理机关、审查范围、法律效力4方面比较。", "difficulty": "medium"},
]

# ============================================================
# 汇总
# ============================================================
ALL_QUESTIONS = {
    "13009": Q_13009,
    "13005": Q_13005,
    "13017": Q_13017,
    "14349": Q_14349,
    "15041": Q_15041,
    "05679": Q_05679,
    "05677": Q_05677,
    "00223": Q_00223,
    "00242": Q_00242,
    "00245": Q_00245,
    "00243": Q_00243,
    "00260": Q_00260,
    "07790": Q_07790,
    "13532": Q_13532,
    "00220": Q_00220,
}


def seed(dry_run=False):
    db = SessionLocal()
    try:
        total_inserted = 0
        for code, questions in ALL_QUESTIONS.items():
            subject = db.query(Subject).filter(Subject.code == code).first()
            if not subject:
                print('  [SKIP] Subject %s not found in DB' % code)
                continue

            # Check existing question count
            existing = db.query(Question).filter(Question.subject_id == subject.id).count()
            if existing > 0:
                print('  [SKIP] %s %s already has %d questions' % (code, subject.name, existing))
                continue

            inserted = 0
            for q in questions:
                opts = q.get('options', [])
                options_dict = None
                if opts and q['question_type'] in ('single_choice', 'multiple_choice'):
                    letters = 'ABCDEFGH'
                    options_dict = {letters[i]: opt for i, opt in enumerate(opts)}

                obj = Question(
                    subject_id=subject.id,
                    question_type=q['question_type'],
                    content=q['content'],
                    options=options_dict,
                    answer=q.get('answer', ''),
                    explanation=q.get('explanation', ''),
                    year=q.get('year', 2026),
                    difficulty=q.get('difficulty', 'medium'),
                    score=q.get('score', 2),
                    source='seed_generated',
                )
                if not dry_run:
                    db.add(obj)
                inserted += 1

            if not dry_run:
                db.flush()
            total_inserted += inserted
            print('  [OK] %s %s: %d questions' % (code, subject.name, inserted))

        if not dry_run:
            db.commit()
            print('\n[OK] Total inserted: %d questions' % total_inserted)
        else:
            print('\n[dry-run] Would insert: %d questions' % total_inserted)

    except Exception as e:
        db.rollback()
        print('[FAIL] %s' % e)
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Seed CS + Law questions')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print('=== Seed CS Theory + Law Diploma Questions ===')
    print()
    for code, qs in ALL_QUESTIONS.items():
        types = {}
        for q in qs:
            t = q['question_type']
            types[t] = types.get(t, 0) + 1
        print('  %s: %d questions (%s)' % (code, len(qs), ', '.join('%s:%d' % (k, v) for k, v in sorted(types.items()))))
    print()

    seed(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
