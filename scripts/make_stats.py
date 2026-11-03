#!/usr/bin/env python3
"""
make_stats.py — 从 GitHub API 拉数据，自绘 tokyonight 风格的
GitHub Stats 卡和 Languages 卡（SVG），彻底摆脱 vercel 公共实例限流。

用法: TOKEN=xxx python3 make_stats.py <output_dir>
"""
import json
import os
import sys
import urllib.request

USER = 'ling-ou-pq'

# GitHub Linguist 官方语言色
LANG_COLORS = {
    'Python': '#3572A5', 'MATLAB': '#e16737', 'HTML': '#e34c26',
    'CSS': '#563d7c', 'JavaScript': '#f1e05a', 'TypeScript': '#3178c6',
    'Markdown': '#083fa1', 'Shell': '#89e051', 'C': '#555555',
    'C++': '#f34b7d', 'Java': '#b07219', 'Go': '#00ADD8',
    'Dockerfile': '#384d54', 'Vue': '#41b883', 'Jupyter Notebook': '#DA5B0B',
    'Batchfile': '#C1F12E', 'PowerShell': '#012456', 'SCSS': '#c6538c',
}
PALETTE = ['#7aa2f7', '#9ece6a', '#bb9af7', '#ff9e64', '#73daca', '#e0af68']


def gh(path, token=None):
    req = urllib.request.Request(
        'https://api.github.com' + path,
        headers={'User-Agent': 'stats-gen', 'Accept': 'application/vnd.github+json'})
    if token:
        req.add_header('Authorization', f'token {token}')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fmt(n):
    return f'{n:,}'


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def collect(token):
    user = gh(f'/users/{USER}', token)
    repos = gh(f'/users/{USER}/repos?per_page=100&sort=pushed', token)
    stars = sum(r.get('stargazers_count', 0) for r in repos)
    forks = sum(r.get('forks_count', 0) for r in repos)

    def search(q):
        try:
            return gh(f'/search/issues?q={q}+user:{USER}&per_page=1', token)['total_count']
        except Exception:
            return 0

    commits = 0
    try:
        commits = gh(f'/search/commits?q=author:{USER}&per_page=1', token)['total_count']
    except Exception:
        pass

    langs = {}
    for r in repos:
        try:
            for name, b in gh(f"/repos/{r['full_name']}/languages", token).items():
                langs[name] = langs.get(name, 0) + b
        except Exception:
            pass
    total_b = sum(langs.values()) or 1
    langs = sorted(langs.items(), key=lambda x: -x[1])

    return {
        'stars': stars, 'forks': forks, 'commits': commits,
        'repos': user.get('public_repos', 0), 'followers': user.get('followers', 0),
        'langs': [(n, round(b * 100 / total_b, 1)) for n, b in langs[:6]],
    }


def stats_svg(d):
    rows = [
        ('\u2b50', 'Total Stars', fmt(d['stars'])),
        ('\U0001f4c6', 'Total Commits', fmt(d['commits'])),
        ('\U0001f4e6', 'Repositories', fmt(d['repos'])),
        ('\U0001f465', 'Followers', fmt(d['followers'])),
        ('\U0001f52f', 'Total Forks', fmt(d['forks'])),
    ]
    parts = [
        '<svg width="400" height="210" viewBox="0 0 400 210" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="GitHub Stats">',
        '<rect width="400" height="210" rx="8" fill="#1a1b27" stroke="rgba(255,255,255,0.08)"/>',
        '<text x="25" y="38" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="16" font-weight="600" fill="#ffffff">'
        f"{esc(USER)}'s GitHub Stats</text>",
    ]
    y = 72
    for icon, label, val in rows:
        parts.append(
            f'<text x="25" y="{y}" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="14" fill="#a9b1d6">'
            f'{icon} {label}</text>')
        parts.append(
            f'<text x="375" y="{y}" text-anchor="end" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
            f'font-size="14" font-weight="600" fill="#7aa2f7">{val}</text>')
        y += 28
    parts.append('</svg>')
    return '\n'.join(parts)


def langs_svg(d):
    rows = d['langs']
    h = 58 + len(rows) * 40
    parts = [
        f'<svg width="400" height="{h}" viewBox="0 0 400 {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Top Languages">',
        f'<rect width="400" height="{h}" rx="8" fill="#1a1b27" stroke="rgba(255,255,255,0.08)"/>',
        '<text x="25" y="38" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="16" font-weight="600" fill="#ffffff">Most Used Languages</text>',
    ]
    y = 72
    for i, (name, pct) in enumerate(rows):
        color = LANG_COLORS.get(name, PALETTE[i % len(PALETTE)])
        w = round(pct * 3.5)  # 条最长 350
        parts.append(
            f'<circle cx="30" cy="{y - 4}" r="6" fill="{color}"/>'
            f'<text x="44" y="{y}" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="13" fill="#a9b1d6">{esc(name)}</text>'
            f'<text x="375" y="{y}" text-anchor="end" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="13" fill="#7aa2f7">{pct}%</text>')
        parts.append(
            f'<rect x="25" y="{y + 8}" width="350" height="8" rx="4" fill="rgba(255,255,255,0.06)"/>'
            f'<rect x="25" y="{y + 8}" width="{max(w, 4)}" height="8" rx="4" fill="{color}"/>')
        y += 40
    parts.append('</svg>')
    return '\n'.join(parts)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    token = os.environ.get('TOKEN')
    d = collect(token)
    print('数据:', {k: v for k, v in d.items() if k != 'langs'})
    for name, svg in (('stats.svg', stats_svg(d)), ('langs.svg', langs_svg(d))):
        with open(os.path.join(out, name), 'w', encoding='utf-8') as f:
            f.write(svg)
        print(f'[OK] {name} -> {len(svg)} bytes')


if __name__ == '__main__':
    main()
