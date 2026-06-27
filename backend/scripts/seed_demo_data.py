from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.auth import models as auth_models  # noqa: F401,E402
from app.compliance import models as compliance_models  # noqa: F401,E402
from app.core.config import get_settings  # noqa: E402
from app.core.database import get_session_local, init_db  # noqa: E402
from app.courses import models as courses_models  # noqa: F401,E402
from app.demo.seed import seed_demo_data  # noqa: E402
from app.exercises import models as exercises_models  # noqa: F401,E402
from app.exports import models as exports_models  # noqa: F401,E402
from app.lessons import models as lessons_models  # noqa: F401,E402
from app.logs import models as logs_models  # noqa: F401,E402
from app.materials import models as materials_models  # noqa: F401,E402
from app.questions import models as questions_models  # noqa: F401,E402


def main() -> None:
    settings = get_settings()
    init_db(settings.database_url)
    session_local = get_session_local(settings.database_url)
    with session_local() as db:
        result = seed_demo_data(db)
        db.commit()

    print("演示数据已初始化。")
    print(f"登录账号：{result['username']}")
    print(f"登录密码：{result['password']}")
    print(f"课程 ID：{result['course_id']}")
    print(f"材料 ID：{result['material_id']}")
    print(f"习题 ID：{result['exercise_id']}")
    print(f"题库题目 ID：{result['question_id']}")


if __name__ == "__main__":
    main()
