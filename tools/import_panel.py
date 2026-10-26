"""Import the supplied standalone visual design without its preview behavior."""
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding='utf-8')
source = re.sub(r'(?s)<!--.*?-->', '', source)
source = re.sub(r'(?s)<script\b[^>]*>.*?</script>', '', source)
source = source[:source.index('<div class="modal fade"')] + '</body></html>'
source = re.sub(r' data-preview-route="[^"]*"| data-tool="[^"]*"', '', source)
source = source.replace('CodyNick | Main Panel — Bootstrap Design Preview', 'CodyNick | Main Panel')
source = re.sub(r'<span class="preview-chip">.*?</span>', '', source)
source = source.replace('id="account-name">teacher', 'id="account-name">@@NAME@@')
source = source.replace('id="greeting-name">teacher', 'id="greeting-name">@@NAME@@')
source = source.replace('id="account-caption">Administrator', 'id="account-caption">@@ROLE@@')
source = source.replace('id="avatar">TE', 'id="avatar">@@INITIALS@@')
source = re.sub(r'<a class="quick-link" id="admin-link".*?</a>', '@@ADMIN@@', source)
source = re.sub(r'<button type="button" class="btn btn-light.*?</button>', '', source)
source = re.sub(r'<a class="quick-link" id="student-signout".*?</a>', '<form method="post" action="/logout"><button class="quick-link w-100 text-start border-0 bg-transparent" type="submit">Sign out</button></form>', source)
source = re.sub(r'(?s)<footer class="footer">.*?</footer>', '<footer class="footer"><div class="container-fluid container-shell px-3 px-lg-4 footer-inner">CodyNick Multi-user @@VERSION@@</div></footer>', source)
source = source.replace('</head>', '<link rel="icon" href="/favicon.ico"><style>html{scroll-behavior:smooth}button.quick-link{font:inherit}*{letter-spacing:0!important}</style></head>')
source = source.replace('</body>', '''<script>document.querySelector('.mobile-menu').addEventListener('click',function(){const menu=document.getElementById('mobileNav');const open=menu.classList.toggle('show');this.setAttribute('aria-expanded',String(open));});</script></body>''')
Path(__file__).resolve().parents[1].joinpath('panel.html').write_text(source, encoding='utf-8', newline='\n')
