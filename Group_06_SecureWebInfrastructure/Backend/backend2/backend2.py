from http.server import BaseHTTPRequestHandler, HTTPServer

class RqstHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        message = "Welcome to the server 2, of our group the_rooters"

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

        self.wfile.write(message.encode())

server = HTTPServer(("127.0.0.1", 3002), RqstHandler)

print("Server 2 running on 127.0.0.1:3002")

server.serve_forever()

