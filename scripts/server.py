#!/usr/bin/env python3
"""河洛天衍 — 本地排盘服务器

启动本地 HTTP 服务器，提供 iztro-py 精确排盘 API。
前端可通过 /api/chart 接口获取精确命盘数据。

用法:
    python3 server.py              # 默认端口 8765
    python3 server.py --port 8080  # 自定义端口
"""

import argparse
import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from calculate_chart import build_chart, chart_to_frontend_format


class ChartAPIHandler(SimpleHTTPRequestHandler):
    """处理排盘 API 请求 + 静态文件服务"""

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/chart":
            self._handle_chart_api(parsed)
        elif parsed.path == "/api/health":
            self._send_json({"status": "ok", "service": "河洛天衍排盘服务"})
        else:
            # 静态文件服务
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/chart":
            self._handle_chart_api_post()
        else:
            self.send_error(404)

    def _handle_chart_api(self, parsed):
        """GET /api/chart?solar=1991-8-15&hour=1&gender=男"""
        params = parse_qs(parsed.query)
        try:
            result = self._calculate(params)
            self._send_json(result)
        except Exception as e:
            self._send_error(str(e))

    def _handle_chart_api_post(self):
        """POST /api/chart with JSON body"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            result = self._calculate(data)
            self._send_json(result)
        except Exception as e:
            self._send_error(str(e))

    def _calculate(self, params: dict) -> dict:
        """执行排盘计算"""
        # 获取参数
        solar = params.get("solar", [None])[0] if isinstance(params.get("solar"), list) else params.get("solar")
        lunar = params.get("lunar", [None])[0] if isinstance(params.get("lunar"), list) else params.get("lunar")
        hour = params.get("hour", [None])[0] if isinstance(params.get("hour"), list) else params.get("hour")
        gender = params.get("gender", [None])[0] if isinstance(params.get("gender"), list) else params.get("gender")
        leap = params.get("leap", [None])[0] if isinstance(params.get("leap"), list) else params.get("leap")
        frontend = params.get("frontend", ["true"])[0] if isinstance(params.get("frontend"), list) else params.get("frontend", "true")

        # 验证参数
        if not solar and not lunar:
            raise ValueError("请提供 solar 或 lunar 参数")
        if hour is None:
            raise ValueError("请提供 hour 参数（0-12）")
        if not gender:
            raise ValueError("请提供 gender 参数（男/女）")

        hour = int(hour)
        is_lunar = lunar is not None
        date_str = lunar if is_lunar else solar
        is_leap = str(leap).lower() in ("true", "1", "yes")

        # 排盘
        chart = build_chart(date_str, hour, gender, is_lunar, is_leap)

        # 返回前端格式
        if frontend != "false":
            return chart_to_frontend_format(chart)
        return chart

    def _send_json(self, data: dict):
        """发送 JSON 响应"""
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str):
        """发送错误响应"""
        self._send_json({"error": message})

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[河洛天衍] {args[0]}")


def main():
    parser = argparse.ArgumentParser(description="河洛天衍本地排盘服务器")
    parser.add_argument("--port", type=int, default=8765, help="服务器端口（默认 8765）")
    parser.add_argument("--dir", default="..", help="静态文件目录（默认项目根目录）")
    args = parser.parse_args()

    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(args.dir)

    server = HTTPServer(("0.0.0.0", args.port), ChartAPIHandler)
    print(f"""
╔══════════════════════════════════════════╗
║          河洛天衍 — 排盘服务器            ║
║                                          ║
║  本地地址: http://localhost:{args.port}      ║
║  API 接口: http://localhost:{args.port}/api/chart ║
║                                          ║
║  示例:                                    ║
║  curl "http://localhost:{args.port}/api/chart?solar=1991-8-15&hour=1&gender=男" ║
║                                          ║
║  按 Ctrl+C 停止服务器                     ║
╚══════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
