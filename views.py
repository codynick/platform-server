"""Shared branded portal views, matching the original CodyNick tool panel."""
import html
import re
from pathlib import Path
from urllib.parse import urlencode


def frame(title, content, name='', navigation=''):
    name = html.escape(name)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} | CodyNick</title>
<link rel="icon" href="/favicon.ico"><link rel="stylesheet" href="/assets/multi.css"></head>
<body><header class="portal-heading"><img class="brand-logo" src="/assets/logo.png" alt="CodyNick">
<h1>CodyNick</h1><div class="subtitle">{html.escape(title)}</div></header>
<main class="portal"><div class="account-bar"><span>{name}</span>{navigation}</div>{content}</main>
<footer>CodyNick Multi-user</footer></body></html>'''


def design_template():
    return Path(__file__).with_name('panel.html').read_text(encoding='utf-8')


def portal_header(name='', role='student'):
    brand = re.search(r'<a class="brand".*?</a>', design_template(), re.S)[0].replace('href="#top"', 'href="/"')
    account = '<a class="btn btn-primary" href="/login">Sign in</a>'
    if name:
        account = f'''<details class="account-menu"><summary aria-label="Account menu for {html.escape(name)}"><span class="account-label">{html.escape(name)}<small>{'Administrator' if role == 'admin' else 'Student'}</small></span><span class="avatar">{html.escape(name[:2].upper())}</span></summary>
<div class="account-dropdown"><a href="/account/password">Change password</a><form method="post" action="/logout"><button type="submit">Sign out</button></form></div></details>'''
    return f'''<header class="site-header"><div class="container-fluid container-shell px-3 px-lg-4 d-flex align-items-center justify-content-between gap-3">{brand}<nav class="ribbon-nav"><a href="/">Workspace</a><a href="/#tools">Tools</a><a href="/guide.html">Guide</a></nav>{account}</div></header>'''


def portal_document(content, name='', role='student', title='Main Panel'):
    template = design_template()
    head = template[:template.index('<body>')].replace('CodyNick | Main Panel', 'CodyNick | ' + title)
    head = head.replace('</head>', '<link rel="stylesheet" href="/assets/portal.css"></head>')
    return head + '<body>' + portal_header(name, role) + content + '</body></html>'


def welcome_page(version):
    template = design_template()
    content = re.search(r'<main\b.*?</main>', template, re.S)[0]
    content = content[:content.index('>') + 1] + content[content.index('<section class="hero"'):]
    # Account tools belong to the signed-in workspace, not the public welcome.
    content = re.sub(r'<div class="col-12 col-lg-5">.*?</section>', '</section>', content, flags=re.S)
    content = content.replace('col-12 col-lg-7', 'col-12').replace('@@ADMIN@@', '').replace('href="/code/"', 'href="/blocks/"', 1).replace('Start coding', 'Start Creating', 1)
    return portal_document(content + f'<footer class="footer"><div class="container-fluid container-shell px-3 px-lg-4">CodyNick Multi-user {html.escape(version)}</div></footer>', title='Welcome')


def panel_page(name, role, version):
    tools = [('/code/', 'Python IDE', 'Write and run Python'), ('/blocks/', 'Block Coding', 'Build with blocks'),
             ('/simulator/', 'Gadget Simulator', 'Test virtual gadgets'), ('/dashboard/', 'Dashboard', 'View project data')]
    cards = ''.join(f'<div class="col-12 col-sm-6 col-xl-3"><a class="tool-card h-100 d-flex flex-column text-decoration-none" href="{url}"><h3>{label}</h3><p>{description}</p><span class="tool-action mt-auto">Open &#8594;</span></a></div>' for url, label, description in tools)
    admin = '<a class="btn btn-outline-primary" href="/admin/users">Manage students</a>' if role == 'admin' else ''
    photo = re.search(r'<div class="hero-photo"><img src="([^"]+)"', design_template())[1]
    content = f'''<div class="workspace-watermark" aria-hidden="true"><img src="{photo}" alt=""></div><main class="container-fluid container-shell px-3 px-lg-4 practical-workspace"><div class="workspace-top"><div><h1>Workspace</h1><p>Welcome, {html.escape(name)}</p></div><a class="btn btn-primary" href="/blocks/">Start Creating</a></div><section id="tools" aria-label="Tools"><div class="row g-3">{cards}</div></section><div class="workspace-actions"><a class="btn btn-outline-primary" href="/guide.html">Help &amp; getting started</a>{admin}</div><footer class="workspace-version">CodyNick Multi-user {html.escape(version)}</footer></main>'''
    return portal_document(content, name, role)


def users_page(name, accounts, csrf, error='', created='', updated=''):
    rows = ''.join(f'<tr><td>{html.escape(user)}</td><td>{"Administrator" if a.get("role") == "admin" else "Student"}</td><td><a class="button secondary small-button" href="/admin/password?{urlencode({"user": user})}" title="Reset password for {html.escape(user)}">Reset</a></td></tr>'
                   for user, a in sorted(accounts.items(), key=lambda item: item[1]['slot']))
    notice = '<p class="success" role="status">' + html.escape(created) + ' added.</p>' if created in accounts else ''
    if updated in accounts:
        notice = '<p class="success" role="status">Password updated for ' + html.escape(updated) + '.</p>'
    alert = '<p class="error" role="alert">' + html.escape(error) + '</p>' if error else ''
    content = f'''<h2>Users</h2>{notice}<div class="admin-grid"><section class="user-form-area"><h3>Add Student</h3>
<form class="login-form" id="add-student" method="post" action="/admin/users">
<input type="hidden" name="csrf" value="{html.escape(csrf)}">
<label for="username">Username</label><input id="username" name="username" autocomplete="off" pattern="[a-z][a-z0-9_]{{0,19}}" maxlength="20" required>
<label for="password">Password</label><input id="password" type="password" name="password" autocomplete="new-password" minlength="8" maxlength="128" required>
<label for="confirm">Confirm Password</label><input id="confirm" type="password" name="confirm" autocomplete="new-password" minlength="8" maxlength="128" required>
{alert}<button id="create-button" type="submit">Add Student</button></form></section>
<section><h3>Accounts ({len(accounts)})</h3><table><thead><tr><th>Username</th><th>Role</th><th>Password</th></tr></thead><tbody>{rows}</tbody></table></section></div>
<script>document.getElementById('add-student').addEventListener('submit',()=>{{const b=document.getElementById('create-button');b.disabled=true;b.textContent='Creating...';}});</script>'''
    return frame('User Management', content, name, '<a class="button secondary" href="/">&#8592; Main Panel</a>')


def login_page(error='', changed=False, next_path='/'):
    alert = '<p class="error" role="alert">' + html.escape(error) + '</p>' if error else ''
    if changed:
        alert = '<p class="success" role="status">Password changed. Sign in again.</p>'
    photo = re.search(r'<div class="hero-photo"><img src="([^"]+)"', design_template())[1]
    content = f'''<div class="login-background" aria-hidden="true"><img src="{photo}" alt=""></div><main class="login-layout"><section class="login-box"><h1>Sign in</h1><p>Welcome to your CodyNick workspace.</p><form method="post" action="/login"><input type="hidden" name="next" value="{html.escape(next_path)}">
<label class="form-label" for="username">Username</label><input class="form-control mb-3" id="username" name="username" autocomplete="username" maxlength="20" required autofocus>
<label class="form-label" for="password">Password</label><input class="form-control mb-3" id="password" name="password" type="password" autocomplete="current-password" maxlength="1024" required>
{alert}<button class="btn btn-primary w-100" type="submit">Sign In</button></form><a class="back-welcome" href="/">&#8592; Back to welcome</a></section></main>'''
    return portal_document(content, title='Sign In')


def password_page(name, target, csrf, reset=False, error=''):
    title = 'Reset Password' if reset else 'Change Password'
    action = '/admin/password?' + urlencode({'user': target}) if reset else '/account/password'
    current = '' if reset else '<label for="current">Current Password</label><input id="current" name="current_password" type="password" autocomplete="current-password" maxlength="1024" required>'
    alert = '<p class="error" role="alert">' + html.escape(error) + '</p>' if error else ''
    content = f'''<section class="sign-in"><h2>{title}</h2><p>{html.escape(target)}</p>
<form class="login-form" method="post" action="{html.escape(action)}">
<input type="hidden" name="csrf" value="{html.escape(csrf)}">{current}
<label for="password">New Password</label><input id="password" name="password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required>
<label for="confirm">Confirm New Password</label><input id="confirm" name="confirm" type="password" autocomplete="new-password" minlength="8" maxlength="128" required>
{alert}<button type="submit">{title}</button></form></section>'''
    back = '/admin/users' if reset else '/'
    return frame(title, content, name, f'<a class="button secondary" href="{back}">&#8592; Back</a>')
