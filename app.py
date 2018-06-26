import random
import string

from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.internet import reactor, defer
from txpostgres import txpostgres

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
        conn = yield txpostgres.Connection().connect(
            database='link_shortener',
            user='postgres',
            password='1'
        )
        try:
            rows = yield conn.runQuery("select link from links where code='{}'".format(self.path))
        except Exception as e:
            print(e)
        yield conn.close()
        request.redirect(rows[0][0].encode('utf-8'))
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
        conn = yield txpostgres.Connection().connect(
            database='link_shortener',
            user='postgres',
            password='1'
        )
        while True:
            code = generate_code()
            try:
                yield conn.runOperation(
                    "insert into links (code, link) values ('{}', '{}')".format(code, link)
                )
                break
            except Exception:
                pass
        yield conn.close()
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
