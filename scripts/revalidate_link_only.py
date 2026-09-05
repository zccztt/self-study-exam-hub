"""重新校验被误判为 link_only 但有正文的源记录"""
import re
from backend.database import get_db
from backend.models.past_paper_source import PastPaperSource
from scripts.harvest_papers import OPTION_LINE_RE, ANSWER_LINE_RE

QUESTION_MARK_RE = re.compile(r"(?:^|\n)\s*\d{1,2}[\.、．]")

def main():
    db = next(get_db())

    candidates = db.query(PastPaperSource).filter(
        PastPaperSource.status == 'link_only',
        PastPaperSource.content_text.isnot(None),
        PastPaperSource.content_text != ''
    ).all()

    print(f"找到 {len(candidates)} 条待重新校验的源")

    upgraded = 0
    for rec in candidates:
        text = rec.content_text or ""
        questions = len(QUESTION_MARK_RE.findall(text))
        options = len(OPTION_LINE_RE.findall(text))
        answers = len(ANSWER_LINE_RE.findall(text))

        # 真题判定: 试题特征 ≥3 且选项 ≥4
        if questions >= 3 and options >= 4:
            rec.status = 'extracted'
            upgraded += 1
            print(f"[升级] {rec.url[:80]} 题={questions} 选项={options} 答案={answers}")

    if upgraded:
        db.commit()
        print(f"\n✅ {upgraded} 条源从 link_only 升级为 extracted")
    else:
        print("\n无符合条件的源")

    db.close()

if __name__ == "__main__":
    main()
