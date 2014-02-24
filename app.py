import io
from markdown import markdown
import os
import werkzeug
import yaml
import itertools
from flask import Flask, Markup, url_for, render_template, abort, render_template_string

app = Flask(__name__)

#platblad
class Pages(object):
    default_language = 'en'
    _cache = {}  # shared cache

    def __init__(self, folder=u'pages', suffix='.md', ):
        self.folder = folder
        self.suffix = suffix

    def root(self):
        return os.path.join(app.root_path, self.folder)

    def all(self, lang=''):
        pagedir = os.path.join(self.root(), lang)
        if not os.path.isdir(pagedir):
            abort(404)
        for filename in os.listdir(pagedir):
            if filename.endswith(self.suffix):
                yield self.get(filename[:-len(self.suffix)], lang)

    def get(self, name, lang=''):
        filepath = os.path.join(self.root(), '' if lang == self.default_language else lang, name+self.suffix)
        if not os.path.isfile(filepath):
            abort(404)
        lang = lang or self.default_language
        mtime = os.path.getmtime(filepath)
        page, old_mtime = self._cache.get(filepath, (None, None))
        if not page or mtime != old_mtime:
            with io.open(filepath, encoding='utf8') as fd:
                head = ''.join(itertools.takewhile(str.strip, fd))
                body = fd.read()
            page = Page(name, head, body, lang)
            self._cache[filepath] = (page, mtime)
        return page


class Page(object):

    def __init__(self, name, head, body, lang):
        self.name = name
        self.head = head
        self.body = body
        self.lang = lang

    @werkzeug.cached_property
    def meta(self):
        return yaml.safe_load(self.head) or {}

    def __getitem__(self, name):
        return self.meta[name]

    @werkzeug.cached_property
    def html(self):
        return markdown(render_template_string(Markup(self.body)), ['codehilite', 'fenced_code'])

    def url(self, **kwargs):
        return url_for(
            'page_detail', name=self.name, **kwargs)

    def updated(self):
        return self.meta.get('lastmod', self['published'])


blog = Pages(u'blog')


def by_date(pages):
    return sorted(pages, reverse=True, key=lambda p: p['published'])


#controllers
@app.route('/test/')
def test():
    return "hallo wereld"

@app.route('/blog/')
@app.route('/blog/<lang>/')
def blogs_list(lang=''):
    blogs = [b for b in by_date(blog.all(lang))]
    return render_template('blog-list.html', **locals())

@app.route('/blog/<lang>/<name>')
def blog_detail(name, lang):
    b = blog.get(name, lang)
    return render_template('blog-detail.html', **locals())


#launch
if __name__ == "__main__":
    app.run(debug=True)