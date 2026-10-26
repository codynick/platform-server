import unittest
from html.parser import HTMLParser
from views import panel_page


class Tags(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class PanelTests(unittest.TestCase):
    def test_real_links_and_post_logout(self):
        page = panel_page('teacher', 'admin', '0.1.6')
        tags = Tags(page).tags
        links = [attrs.get('href') for tag, attrs in tags if tag == 'a']
        for target in ['/code/', '/blocks/', '/simulator/', '/dashboard/', '/guide.html', '/account/password', '/admin/users']:
            self.assertIn(target, links)
        self.assertNotIn('/logout', links)
        self.assertTrue(any(tag == 'form' and attrs.get('action') == '/logout' and attrs.get('method') == 'post' for tag, attrs in tags))
        self.assertIn('Multi-user 0.1.6', page)
        self.assertNotIn('data-preview-route', page)
        self.assertNotIn('previewModal', page)

    def test_student_and_escaping(self):
        page = panel_page('<student>', 'student', 'test')
        self.assertNotIn('/admin/users', page)
        self.assertIn('&lt;student&gt;', page)
        self.assertNotIn('@@', page)
        for tag, attrs in Tags(page).tags:
            for key in ['href', 'src']:
                self.assertFalse(attrs.get(key, '').startswith(('https:', 'http:', '//')))
