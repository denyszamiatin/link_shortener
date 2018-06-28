import random
import string

from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.internet import reactor, defer, threads

import txredisapi as redis

import qr_enc

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
        code = yield conn.get('code:%s' % link)
        if code is None:
            while True:
                code = generate_code()
                ok = yield conn.setnx("link:%s" % code, link)
                if ok:
                    break
            yield conn.set('code:%s' % link, code)
        yield conn.disconnect()
        body = '''
        <p>Shortened link: <a href='http://localhost:8000/{0}'>http://localhost:8000/{0}</a></p>
        <p><img src='img/{0}'></p>
        '''.format(code)
        request.write(PAGE.format(body).encode('utf-8'))
        request.finish()

    def render_POST(self, request):
        link = request.args[b'link'][0].decode('utf-8')
        self.add_link(link, request)
        return NOT_DONE_YET


class QRcode(Resource):
    def getChild(self, path, request):
        self.path = path
        return self

    @defer.inlineCallbacks
    def generate_image(self, link, request):
        conn = yield redis.Connection()
        image = yield conn.get('image:%s' % link)
        if image is None:
            image = yield threads.deferToThread(qr_enc.encode_string, link)
            image = image.read()
            yield conn.setnx('image:%s' % link, image)
            yield conn.expire('image:%s' % link, 300)
        request.setHeader('Content-Type', 'image/png')
        request.write(image)
        request.finish()

    def render_GET(self, request):
        link = "http://localhost:8000/%s" % self.path.decode('utf-8')
        self.generate_image(link, request)
        return NOT_DONE_YET


resource = IndexPage()
resource.putChild(b'static', File('static'))
resource.putChild(b'img', QRcode())
factory = Site(resource)

if __name__ == '__main__':
    reactor.listenTCP(8000, factory)
    reactor.run()
