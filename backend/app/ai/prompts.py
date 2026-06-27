LESSON_LABELS = {
    "subject": "学科",
    "chapter": "章节",
    "stage": "阶段",
    "duration_minutes": "课时分钟",
    "student_level": "学情",
    "teaching_goal": "教学目标",
    "teaching_context": "课程树上下文",
    "output_format": "输出格式要求",
    "prompt_template": "教师补充提示词",
    "web_search_note": "网络检索",
    "retrieval_note": "资料引用策略",
}

EXERCISE_LABELS = {
    "title": "标题",
    "subject": "学科",
    "knowledge_point": "知识点",
    "question_type": "题型",
    "difficulty": "难度",
    "count": "题量",
    "teaching_context": "课程树上下文",
    "lesson_context": "关联教案",
    "output_format": "输出格式要求",
    "prompt_template": "教师补充提示词",
    "retrieval_note": "资料引用策略",
}


def build_lesson_prompt(form: dict, references: list[str] | None = None) -> str:
    reference_text = _format_references(references)
    form_text = _format_form(form, LESSON_LABELS)
    return (
        "请生成一份可直接给教师使用的中文教案。\n"
        "要求：\n"
        "1. 不要输出 Title、Subject、Content 等英文元信息。\n"
        "2. 不要使用 Markdown 井号标题或分隔线。\n"
        "3. 用清晰的中文小标题组织：教学目标、重点难点、教学流程、课堂练习、课后建议。\n"
        "4. 内容要完整、可编辑、适合成人考研机构教研场景。\n"
        "5. 如果提供了课程树上下文，必须围绕对应课程、章节、课次和知识点展开。\n"
        "6. 如果提供了教师补充提示词或输出格式要求，应优先遵循。\n\n"
        f"备课信息：\n{form_text}\n\n"
        f"参考资料：\n{reference_text}"
    )


def build_exercise_prompt(form: dict, references: list[str] | None = None) -> str:
    reference_text = _format_references(references)
    form_text = _format_form(form, EXERCISE_LABELS)
    type_rules = _exercise_type_rules(str(form.get("question_type") or ""))
    alignment_rules = _subject_alignment_rules(form)
    return (
        "请生成一份可直接发给学生练习的中文习题资料。\n"
        "要求：\n"
        "1. 不要输出 Title、Subject、Knowledge point、Content 等英文元信息。\n"
        "2. 不要使用 Markdown 井号标题、粗体标记或分隔线。\n"
        "3. 严格按照表单中的题型生成，不要擅自改成其他题型。\n"
        f"4. 题型格式规则：{type_rules}\n"
        f"5. 学科与知识点约束：{alignment_rules}\n"
        "6. 每道题必须紧扣表单中的学科和知识点，不得生成与学科或知识点无关的题目。\n"
        "7. 不要禁止必要的公式、表格、示意图或题图；数学、物理、统计等题目可以包含公式、矩阵、表格和示意图。\n"
        "8. 公式请优先使用 LaTeX 块，格式为 [公式]...[/公式]。\n"
        "9. 简单题图可使用 SVG 块，格式为 [SVG]...[/SVG]；SVG 只允许静态图形，不要包含脚本、事件属性或外部链接。\n"
        "10. 表格请使用 Markdown 表格或普通文本表格。\n"
        "11. 如题目需要真实照片、复杂插画或识别已有图片，请在题干中标注“需要图片素材”，并说明图片需求，不要假装已经看到了图片。\n"
        "12. 题目数量必须符合表单要求。\n"
        "13. 如果提供了关联教案、课程树上下文或教师补充提示词，必须优先围绕这些内容出题。\n\n"
        f"习题信息：\n{form_text}\n\n"
        f"参考资料：\n{reference_text}"
    )


def build_review_prompt(task_type: str, content: str) -> str:
    return (
        "You are the reviewer in a multi-AI teaching content workflow.\n"
        "Review the generated Chinese teaching content for factual issues, missing structure, "
        "format problems, and compliance concerns.\n"
        "Return concise Chinese feedback with three sections: Status, Warnings, Suggestions.\n\n"
        f"Task type: {task_type}\n"
        f"Generated content:\n{content}"
    )


def build_revise_prompt(task_type: str, content: str, review_feedback: str) -> str:
    return (
        "You are the reviser in a multi-AI teaching content workflow.\n"
        "Revise the generated Chinese teaching content according to the reviewer feedback.\n"
        "Keep the original task type and teaching intent. Output only the revised final content, "
        "without meta commentary about the revision process.\n\n"
        f"Task type: {task_type}\n"
        f"Reviewer feedback:\n{review_feedback}\n\n"
        f"Original content:\n{content}"
    )


def _format_form(form: dict, labels: dict[str, str]) -> str:
    lines: list[str] = []
    for key, label in labels.items():
        value = form.get(key)
        if value not in (None, "", [], False):
            lines.append(f"{label}：{value}")
    return "\n".join(lines)


def _exercise_type_rules(question_type: str) -> str:
    if "综合" in question_type:
        return (
            "综合题必须包含材料、情境、表格、公式或示意图之一，并围绕同一材料设置2到3个递进小问；"
            "不要把综合题拆成单选题，不要给每个小问都生成A/B/C/D选项；"
            "答案与解析应按小问编号逐条说明。"
        )
    if "选择" in question_type:
        return "选择题需要提供A/B/C/D选项，并给出正确答案与解析。"
    if "填空" in question_type:
        return "填空题使用横线或括号表示空缺，不要生成A/B/C/D选项，并给出答案与解析。"
    if "判断" in question_type:
        return "判断题只需判断正确或错误，不要生成A/B/C/D选项，并给出理由。"
    if "简答" in question_type:
        return "简答题应提出开放性问题，不要生成A/B/C/D选项，并给出参考答案与评分要点。"
    if "计算" in question_type:
        return "计算题应给出必要公式、代入过程和结果，矩阵或分式请使用 LaTeX 公式块。"
    if "证明" in question_type:
        return "证明题应按步骤展示条件、推导和结论，不要生成A/B/C/D选项。"
    return "按题型名称组织题目，只有选择题才生成A/B/C/D选项。"


def _subject_alignment_rules(form: dict) -> str:
    subject = str(form.get("subject") or "").strip()
    knowledge_point = str(form.get("knowledge_point") or "").strip()
    base = f"所有题目都要围绕“{subject}”学科和“{knowledge_point}”知识点展开。"
    if "数学" in subject:
        return (
            base
            + "数学题目必须体现数学概念、计算、推导或建模，不能只写常识、语文、英语或纯阅读理解内容。"
            f"如果知识点是“{knowledge_point}”，每道题的材料、小问、答案与解析都要直接服务于该知识点。"
        )
    return (
        base
        + "题干、材料、小问、答案与解析都要体现该学科的核心能力，不能只生成泛泛的学习建议或常识问答。"
    )


def _format_references(references: list[str] | None) -> str:
    if not references:
        return "无"
    return "\n".join(f"{index}. {content}" for index, content in enumerate(references, start=1))
