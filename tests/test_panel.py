import unittest
from html.parser import HTMLParser
from views import panel_page, welcome_page, login_page
from gateway import safe_destination


class Tags(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class PanelTests(unittest.TestCase):
    def test_welcome_and_login(self):
        welcome = welcome_page('0.1.7')
        self.assertIn('Start Creating', welcome)
        self.assertIn('hero-photo', welcome)
        self.assertNotIn('@@', welcome)
        self.assertNotIn('teacher', welcome)
        self.assertNotIn('/admin/users', welcome)
        login = login_page(next_path='/blocks/?test=1&next=2')
        self.assertIn('login-background', login)
        self.assertIn('/blocks/?test=1&amp;next=2', login)

    def test_destination_is_local(self):
        for value in ['https://bad.example', '//bad.example', '/%2fbad.example', '/\\bad.example', '/%0d%0aLocation:evil', '/logout', '/login']:
            self.assertEqual('/', safe_destination(value))
        self.assertEqual('/blocks/?x=1', safe_destination('/blocks/?x=1'))

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
