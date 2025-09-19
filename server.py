#!/usr/bin/env python3
import http.server
import socketserver
import os

# Переходим в директорию с файлами
os.chdir('/Users/alekenov/Leken')

PORT = 8888

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Добавляем CORS заголовки
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        # Обрабатываем preflight запросы
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"🌐 HTTP Server running at http://localhost:{PORT}")
        print(f"📂 Serving files from: {os.getcwd()}")
        print(f"🔗 Open: http://localhost:{PORT}/index.html")
        print("📝 Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")
            httpd.shutdown()