#!/usr/bin/env python3
"""
启动脚本，使用自定义端点扩展的label-studio-ml服务
"""
import os
import argparse
from custom_api import init_app_with_custom_endpoints
from model import NewModel

def main():
    parser = argparse.ArgumentParser(description='Label Studio ML Backend with custom endpoints')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 9090)), help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    # 创建应用（包含自定义端点）
    app = init_app_with_custom_endpoints(model_class=NewModel)

    print(f"🚀 Starting Label Studio ML Backend with custom endpoints...")
    print(f"🌐 Available endpoints:")
    print(f"   Standard: /setup, /predict, /train, /health, /metrics")
    print(f"   Custom: /versions, /model/info, /health/detailed")
    print(f"📡 Server running on http://{args.host}:{args.port}")

    # 启动服务器
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()