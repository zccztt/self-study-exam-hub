# -*- coding: utf-8 -*-
"""Answer template service for subjective question types."""

from typing import Any, Dict, Optional


QUESTION_TYPE_LABELS = {
    "single_choice": "单选题",
    "multiple_choice": "多选题",
    "fill_blank": "填空题",
    "short_answer": "简答题",
    "essay": "论述题",
    "case": "案例题",
}


class AnswerTemplateService:
    """Provides structured answer templates for self-study exam question types."""

    TEMPLATES: Dict[str, Dict[str, Dict[str, Any]]] = {
        "fill_blank": {
            "default": {
                "name": "填空题记忆技巧",
                "structure": "关键词定位 → 精准填写 → 检查搭配",
                "scoring_tips": [
                    "只填核心关键词，不要多写",
                    "注意前后文语境搭配",
                    "专有名词、数字、年份不能有错字",
                    "多空题每空独立得分，不会的也要猜",
                ],
                "example_frame": "根据题干上下文定位概念 → 回忆教材原文 → 填写精确术语",
                "common_mistakes": [
                    "写了多余的修饰词",
                    "错别字导致不得分",
                    "不同概念混淆",
                ],
                "score_range": "每空1-2分",
            },
        },
        "short_answer": {
            "default": {
                "name": "简答题通用模板",
                "structure": "总述(1句) → 分点阐述(3-5点) → 总结(可选)",
                "scoring_tips": [
                    "每个要点2-3分，写满4个要点基本满分",
                    "先写结论，再展开解释",
                    "使用教材原话得分率更高",
                    "分点标序号(1)(2)(3)，阅卷更清晰",
                ],
                "example_frame": "XXX是指______。其主要内容/特征包括：\n(1)______\n(2)______\n(3)______\n(4)______",
                "common_mistakes": [
                    "只写结论不展开",
                    "要点重复无新意",
                    "字数不够（建议150-200字）",
                    "没有分点，写成一段话",
                ],
                "score_range": "4-6分",
            },
            "law": {
                "name": "法学类简答题模板",
                "structure": "概念定义 → 构成要件/特征 → 法律依据",
                "scoring_tips": [
                    "先给概念下定义",
                    "列出构成要件或基本特征",
                    "引用具体法条加分",
                    "使用法律专业术语",
                ],
                "example_frame": "XXX是指______（定义）。\n其构成要件包括：\n(1)______\n(2)______\n(3)______\n法律依据：根据《______》第X条规定……",
                "common_mistakes": [
                    "概念表述不准确",
                    "遗漏关键构成要件",
                    "未引用法条",
                ],
                "score_range": "4-6分",
            },
            "management": {
                "name": "管理类简答题模板",
                "structure": "概念 → 核心要素/原则 → 作用/意义",
                "scoring_tips": [
                    "先定义再展开",
                    "列举核心原则或要素",
                    "结合管理实际说明作用",
                    "使用管理学专业术语",
                ],
                "example_frame": "XXX是指______。\n其核心要素/基本原则包括：\n(1)______\n(2)______\n(3)______\n其主要作用在于______。",
                "common_mistakes": [
                    "定义模糊",
                    "要素列举不全",
                    "缺少实际意义说明",
                ],
                "score_range": "4-6分",
            },
        },
        "essay": {
            "default": {
                "name": "论述题通用模板",
                "structure": "是什么(定义) → 为什么(原因/意义) → 怎么做(措施) → 联系实际",
                "scoring_tips": [
                    "论述题必须展开写，300字以上",
                    "分层清晰：是什么→为什么→怎么做",
                    "最后联系实际加1-2句可多得2-3分",
                    "每层3个以上要点",
                    "字迹工整、段落分明",
                ],
                "example_frame": "一、XXX的含义\n______（概念定义，2-3句）\n\n二、XXX的原因/意义\n(1)______\n(2)______\n(3)______\n\n三、如何实现/做到XXX\n(1)______\n(2)______\n(3)______\n\n四、结合实际\n在当前______背景下，______（1-2句联系实际）",
                "common_mistakes": [
                    "当简答题写，不展开论述",
                    "缺少'怎么做'层次",
                    "无实际联系",
                    "字数不足300字",
                    "层次混乱不分段",
                ],
                "score_range": "10-12分",
            },
            "law": {
                "name": "法学类论述题模板",
                "structure": "法理定义 → 法律规定 → 制度价值 → 完善建议 → 实践意义",
                "scoring_tips": [
                    "从法理层面阐述概念",
                    "引用2-3个具体法条",
                    "分析制度设计的价值和目的",
                    "提出完善建议体现思考深度",
                    "联系法治建设实践",
                ],
                "example_frame": "一、XXX的法理基础\n______\n\n二、我国法律的相关规定\n根据《______》第X条……\n\n三、该制度的价值\n(1)______\n(2)______\n\n四、存在的问题与完善建议\n(1)______\n(2)______\n\n五、实践意义\n______",
                "common_mistakes": [
                    "不引用法条",
                    "只有观点没有论据",
                    "缺少制度价值分析",
                ],
                "score_range": "10-12分",
            },
        },
        "case": {
            "default": {
                "name": "案例分析题通用模板",
                "structure": "案例定性(是什么问题) → 法条/理论依据 → 逐问分析 → 明确结论",
                "scoring_tips": [
                    "先判定案例性质/类型",
                    "每问独立作答，标清题号",
                    "必须引用具体法条或理论原文",
                    "结论要明确：合法/违法、成立/不成立、有效/无效",
                    "分析过程要结合案例事实",
                ],
                "example_frame": "问题1：\n1. 本案涉及______问题。\n2. 根据《______》第X条规定：______\n3. 本案中，______(结合案例事实分析)\n4. 因此，______(明确结论)\n\n问题2：\n1. ______\n2. ______",
                "common_mistakes": [
                    "不引用法条/理论依据",
                    "结论模糊（'可能''或许'）",
                    "漏答子问题",
                    "没有结合案例事实分析",
                    "只有结论没有推理过程",
                ],
                "score_range": "10-15分",
            },
            "law": {
                "name": "法学案例分析模板",
                "structure": "法律关系定性 → 争议焦点 → 法条适用 → 逐项分析 → 裁判结论",
                "scoring_tips": [
                    "首先明确法律关系性质（合同/侵权/物权等）",
                    "找出案例中的争议焦点",
                    "每个焦点对应法条分析",
                    "结论必须明确且有法律依据",
                    "注意时效、管辖、举证等程序问题",
                ],
                "example_frame": "一、法律关系定性\n本案属于______法律关系。\n\n二、争议焦点\n焦点1：______\n焦点2：______\n\n三、法律分析\n关于焦点1：根据《______》第X条，______。本案中______，因此______。\n关于焦点2：______\n\n四、结论\n综上，______（明确结论）。",
                "common_mistakes": [
                    "法律关系定性错误",
                    "引用法条不准确",
                    "分析与结论矛盾",
                    "遗漏重要争议焦点",
                ],
                "score_range": "10-15分",
            },
        },
    }

    # Exam tips applicable across all types
    EXAM_TIPS = {
        "time_management": "150分钟分配：选择题30分钟、填空题15分钟、简答题45分钟、论述题40分钟、检查20分钟",
        "answer_order": "先做选择→填空→简答→论述，确保容易拿的分先到手",
        "key_reminders": [
            "多选题宁少选不多选（多选全错，少选得部分分）",
            "简答题分点作答，每点标序号",
            "论述题字数不低于300字，分层清晰",
            "不留空白，不会的也写相关知识点（按点给分）",
            "注意审题，看清'简述'和'论述'的区别",
            "案例题每问都要有结论性语句",
        ],
    }

    def get_template(self, question_type: str, subject_category: str = "default") -> Dict[str, Any]:
        """Get the answer template for a specific question type and subject category."""
        type_templates = self.TEMPLATES.get(question_type, {})
        template = type_templates.get(subject_category) or type_templates.get("default", {})
        if template:
            template = dict(template)
            template["question_type"] = question_type
            template["question_type_label"] = QUESTION_TYPE_LABELS.get(question_type, question_type)
            template["category"] = subject_category
        return template

    def get_all_templates(self) -> Dict[str, Any]:
        """Get all templates organized by question type."""
        result = {}
        for qtype, categories in self.TEMPLATES.items():
            templates_list = []
            for cat, tmpl in categories.items():
                entry = dict(tmpl)
                entry["category"] = cat
                templates_list.append(entry)
            result[qtype] = {
                "question_type": qtype,
                "label": QUESTION_TYPE_LABELS.get(qtype, qtype),
                "templates": templates_list,
            }
        result["exam_tips"] = self.EXAM_TIPS
        return result

    def get_exam_tips(self) -> Dict[str, Any]:
        """Get general exam-taking tips."""
        return self.EXAM_TIPS
