"""Flask 应用入口。

职责：
1. 创建 Flask app；
2. 注册 API 蓝图；
3. 启动时初始化数据库表结构。
"""

from flask import Flask

from api import api_bp, setup_app_data


def create_app():
    """应用工厂：用于统一初始化，便于后续测试/扩展。"""
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    setup_app_data()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
