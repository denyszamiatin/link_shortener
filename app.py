import random
import string

from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.internet import reactor, defer

import txredisapi as redis

PAGE = '''
<!doctype html>
<html>
<head>
    <meta charset='utf-8'>
    <title>Link shortener</title>
</head>
<body>
    <h1>Link shortener</h1>
    {}
</body>
</html>
'''


def generate_code():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))


class Redirect(Resource):
    def __init__(self, path):
        self.path = path.decode('utf-8')

    @defer.inlineCallbacks
    def redirect(self, request):
        conn = yield redis.Connection()
        link = yield conn.get("link:%s" % self.path)
        yield conn.disconnect()
        request.redirect(link)
        request.finish()

    def render_GET(self, request):
        self.redirect(request)
        return NOT_DONE_YET


class IndexPage(Resource):
    def getChild(self, path, request):
        if path:
            return Redirect(path)
        return self

    def render_GET(self, request):
        form = '''
        <form method='post'>
            <input type='text' name='link' placeholder='Link'>
            <input type='submit' value='Ok'>
        </form>
        '''
        return PAGE.format(form).encode('utf-8')

    @defer.inlineCallbacks
    def add_link(self, link, request):
        conn = yield redis.Connection()
        while True:
            code = generate_code()
            ok = yield conn.setnx("link:%s" % code, link)
            if ok:
                break
        yield conn.disconnect()
        body = '''
        <p>Shortened link: <a href='http://localhost:8000/{0}'>http://localhost:8000/{0}</a>
        '''.format(code)
        request.write(PAGE.format(body).encode('utf-8'))
        request.finish()

    def render_POST(self, request):
        link = request.args[b'link'][0].decode('utf-8')
        self.add_link(link, request)
        return NOT_DONE_YET


resource = IndexPage()
resource.putChild(b'static', File('static'))
factory = Site(resource)

if __name__ == '__main__':
    reactor.listenTCP(8000, factory)
    reactor.run()
