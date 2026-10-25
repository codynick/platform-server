"""Shared branded portal views, matching the original CodyNick tool panel."""
import html
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


def panel_page(name, role, version):
    tools = [('/code/', 'On-Device IDE'), ('/blocks/', 'Block Coding'),
             ('/simulator/', 'Gadget Simulator'), ('/dashboard/', 'On-Device Dashboard'),
             ('/guide.html', 'Guide'), ('/account/password', 'Change Password')]
    if role == 'admin':
        tools.append(('/admin/users', 'Users'))
    links = ''.join(f'<a class="link-card" href="{url}"><span class="link-title">{label}</span><span aria-hidden="true">&#8599;</span></a>'
                    for url, label in tools)
    details = f'''<dl class="account-details"><div><dt>Account</dt><dd>{html.escape(name)}</dd></div>
<div><dt>Role</dt><dd>{'Administrator' if role == 'admin' else 'Student'}</dd></div>
<div><dt>Software Version</dt><dd>{html.escape(version)}</dd></div></dl>'''
    return frame('Main Panel', '<nav class="links">' + links + '</nav>' + details, name,
                 '<form method="post" action="/logout"><button type="submit" class="secondary">Sign Out</button></form>')


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


def login_page(error='', changed=False):
    alert = '<p class="error" role="alert">' + html.escape(error) + '</p>' if error else ''
    if changed:
        alert = '<p class="success" role="status">Password changed. Sign in again.</p>'
    content = f'''<section class="sign-in"><h2>Sign In</h2><form class="login-form" method="post" action="/login">
<label for="username">Username</label><input id="username" name="username" autocomplete="username" maxlength="20" required autofocus>
<label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" maxlength="1024" required>
{alert}<button type="submit">Sign In</button></form></section>'''
    return frame('Multi-user', content)


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
