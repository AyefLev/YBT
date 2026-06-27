def mock_generate(task_type: str, prompt: str) -> str:
    if task_type == "exercise":
        return (
            "课堂练习\n\n"
            "题目 1\n"
            "请概括本节课的核心知识点。\n"
            "A. 只记忆题干\n"
            "B. 提炼概念并说明理由\n"
            "C. 忽略材料信息\n"
            "D. 只背答案\n\n"
            "答案与解析\n"
            "正确答案：B\n"
            "解析：练习应围绕题干和材料信息，提炼关键概念并说明理由。\n\n"
            f"生成依据：{prompt}"
        )

    if task_type == "lesson":
        return (
            "课程设计\n"
            "教学目标：学生能够理解核心概念，并完成迁移应用。\n"
            "教学流程：导入、讲解、练习、反馈。\n"
            f"生成依据：{prompt}"
        )

    return f"AI 生成内容\n任务类型：{task_type}\n内容：{prompt}"
