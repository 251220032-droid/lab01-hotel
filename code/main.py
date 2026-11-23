"""云栖酒店预订系统的程序入口。

运行方式：在 ``code`` 目录下执行 ``python main.py``。
程序首次启动会自动创建演示数据，并打开登录窗口。
"""

import os
import sys

# 确保无论从哪个工作目录启动，都能正确导入本包。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hotelapp.services.app_context import (  # pylint: disable=wrong-import-position
    ApplicationContext,
)
from hotelapp.ui.app import (  # pylint: disable=wrong-import-position
    HotelApplication,
)


def main() -> None:
    """创建应用上下文并启动桌面窗口。"""
    context = ApplicationContext()
    application = HotelApplication(context)
    application.mainloop()


if __name__ == "__main__":
    main()
