from http.server import BaseHTTPRequestHandler, HTTPServer

class RqstHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        message = "Welcome to server 1 of our group the_rooters."

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

        self.wfile.write(message.encode())

server = HTTPServer(("127.0.0.1", 3001), RqstHandler)

print("Server 1 running on 127.0.0.1:3001")

server.serve_forever()

