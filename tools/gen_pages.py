#!/usr/bin/env python3
"""Generates the built-in coloring pages for Color Studio.

Every page is authored as SVG (black strokes, white fills so nearer shapes hide
the lines behind them), rendered with cairosvg, then converted to a transparent
PNG whose alpha channel is the line darkness.  The app uses that alpha channel
both for drawing the outlines and as the barrier for the paint bucket.

Usage: gen_pages.py [out_dir] [--only id1,id2]
"""
import io, json, math, os, random, sys
import cairosvg
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, '..', 'app', 'src', 'main', 'assets', 'pages')
ONLY = None
args = sys.argv[1:]
while args:
    a = args.pop(0)
    if a == '--only':
        ONLY = set(args.pop(0).split(','))
    else:
        OUT_DIR = a

PW, PH = 1500, 2000   # portrait pages
SQ = 1800             # square pages


def f(v):
    if isinstance(v, float):
        s = '%.2f' % v
        s = s.rstrip('0').rstrip('.')
        return s if s not in ('-0', '') else '0'
    return str(v)


def P(x, y):
    return f'{f(x)},{f(y)}'


class Svg:
    def __init__(self, w, h, sw=6):
        self.w, self.h, self.sw = w, h, sw
        self.parts, self.defs = [], []
        self._ids = 0

    @staticmethod
    def attrs(kw):
        out = []
        for k, v in kw.items():
            if v is None:
                continue
            out.append(f'{k.replace("_", "-")}="{v}"')
        return ' '.join(out)

    def add(self, s):
        self.parts.append(s)

    def circle(self, cx, cy, r, **kw):
        self.add(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" {self.attrs(kw)}/>')

    def ellipse(self, cx, cy, rx, ry, rot=0, **kw):
        t = f'rotate({f(rot)} {f(cx)} {f(cy)})' if rot else None
        self.add(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" {self.attrs(dict(transform=t, **kw))}/>')

    def rect(self, x, y, w, h, rx=0, **kw):
        self.add(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" {self.attrs(kw)}/>')

    def polygon(self, pts, **kw):
        self.add(f'<polygon points="{" ".join(P(x, y) for x, y in pts)}" {self.attrs(kw)}/>')

    def polyline(self, pts, **kw):
        kw.setdefault('fill', 'none')
        self.add(f'<polyline points="{" ".join(P(x, y) for x, y in pts)}" {self.attrs(kw)}/>')

    def path(self, d, **kw):
        self.add(f'<path d="{d}" {self.attrs(kw)}/>')

    def line(self, x1, y1, x2, y2, **kw):
        kw.setdefault('fill', 'none')
        self.add(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" {self.attrs(kw)}/>')

    def text(self, x, y, txt, size, weight='bold', italic=False, **kw):
        style = 'italic' if italic else 'normal'
        self.add(f'<text x="{f(x)}" y="{f(y)}" font-family="DejaVu Sans, Arial, sans-serif" font-weight="{weight}" '
                 f'font-style="{style}" font-size="{f(size)}" text-anchor="middle" {self.attrs(kw)}>{txt}</text>')

    def clip(self, d):
        self._ids += 1
        cid = f'c{self._ids}'
        self.defs.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
        return cid

    def begin(self, transform=None, clip=None, **kw):
        cp = f'url(#{clip})' if clip else None
        self.add(f'<g {self.attrs(dict(transform=transform, clip_path=cp, **kw))}>')

    def end(self):
        self.add('</g>')

    def render(self, path):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}"><defs>{"".join(self.defs)}</defs>'
               f'<rect width="{self.w}" height="{self.h}" fill="white"/>'
               f'<g fill="white" stroke="black" stroke-width="{self.sw}" stroke-linejoin="round" stroke-linecap="round">'
               f'{"".join(self.parts)}</g></svg>')
        png = cairosvg.svg2png(bytestring=svg.encode('utf-8'))
        im = Image.open(io.BytesIO(png)).convert('L')
        alpha = im.point(lambda v: 255 - v)
        out = Image.new('RGBA', im.size, (0, 0, 0, 0))
        out.putalpha(alpha)
        out.save(path, optimize=True)


# ----------------------------------------------------------------- geometry helpers

def pol(cx, cy, r, ang):
    a = math.radians(ang)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def petal_d(cx, cy, ang, r_in, r_out, width, bulge=0.5):
    """Closed petal pointing outward from (cx,cy) along angle ang (degrees)."""
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    bx, by = cx + ux * r_in, cy + uy * r_in
    tx, ty = cx + ux * r_out, cy + uy * r_out
    ln = r_out - r_in
    w = width / 2
    c1 = (bx + ux * ln * 0.15 + nx * w, by + uy * ln * 0.15 + ny * w)
    c2 = (bx + ux * ln * (0.35 + bulge * 0.5) + nx * w, by + uy * ln * (0.35 + bulge * 0.5) + ny * w)
    c3 = (bx + ux * ln * (0.35 + bulge * 0.5) - nx * w, by + uy * ln * (0.35 + bulge * 0.5) - ny * w)
    c4 = (bx + ux * ln * 0.15 - nx * w, by + uy * ln * 0.15 - ny * w)
    return (f'M{P(bx, by)} C{P(*c1)} {P(*c2)} {P(tx, ty)} C{P(*c3)} {P(*c4)} {P(bx, by)} Z')


def leaf_d(x1, y1, x2, y2, width):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    w = width
    return (f'M{P(x1, y1)} Q{P(mx + nx * w, my + ny * w)} {P(x2, y2)} '
            f'Q{P(mx - nx * w, my - ny * w)} {P(x1, y1)} Z')


def star_pts(cx, cy, n, r1, r2, rot=-90):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        pts.append(pol(cx, cy, r, rot + i * 180 / n))
    return pts


def heart_d(cx, cy, s):
    def q(x, y):
        return P(cx + x * s, cy + y * s)
    return (f'M{q(0, 0.35)} C{q(-0.1, 0.1)} {q(-0.5, 0.05)} {q(-0.5, -0.3)} '
            f'C{q(-0.5, -0.6)} {q(-0.2, -0.7)} {q(0, -0.45)} '
            f'C{q(0.2, -0.7)} {q(0.5, -0.6)} {q(0.5, -0.3)} '
            f'C{q(0.5, 0.05)} {q(0.1, 0.1)} {q(0, 0.35)} Z')


def polar_d(cx, cy, rfn, steps=360, start=0, end=360, close=True):
    pts = []
    for i in range(steps + 1):
        ang = start + (end - start) * i / steps
        pts.append(pol(cx, cy, rfn(ang), ang))
    d = 'M' + ' L'.join(P(x, y) for x, y in pts)
    return d + (' Z' if close else '')


def wave_pts(x0, x1, y, amp, wl, phase=0, n=None):
    n = n or max(8, int((x1 - x0) / 10))
    return [(x0 + (x1 - x0) * i / n, y + amp * math.sin(phase + 2 * math.pi * (x1 - x0) * i / n / wl)) for i in range(n + 1)]


def wave_band_d(x0, x1, y, amp, wl, bottom, phase=0):
    pts = wave_pts(x0, x1, y, amp, wl, phase)
    return 'M' + ' L'.join(P(x, y) for x, y in pts) + f' L{P(x1, bottom)} L{P(x0, bottom)} Z'


def cloud(svg, cx, cy, w, sw=None):
    """A puffy cloud drawn as a union of circles."""
    rs = [(0, 0.05, 0.3), (-0.3, 0.12, 0.22), (0.3, 0.12, 0.22), (-0.15, -0.12, 0.2), (0.15, -0.1, 0.24)]
    cs = [(cx + dx * w, cy + dy * w, r * w) for dx, dy, r in rs]
    for x, y, r in cs:
        svg.circle(x, y, r)
    inner = (sw or svg.sw) / 2 + 1
    for x, y, r in cs:
        svg.circle(x, y, r - inner, stroke='none')
    # flat base
    svg.rect(cx - 0.52 * w, cy + 0.12 * w, 1.04 * w, 0.15 * w, stroke='none')
    svg.line(cx - 0.52 * w, cy + 0.27 * w, cx + 0.52 * w, cy + 0.27 * w)


def union_circles(svg, circles):
    for x, y, r in circles:
        svg.circle(x, y, r)
    inner = svg.sw / 2 + 1
    for x, y, r in circles:
        svg.circle(x, y, r - inner, stroke='none')


def sun(svg, cx, cy, r, rays=12, ray_len=None, ray_w=None):
    ray_len = ray_len or r * 0.9
    ray_w = ray_w or r * 0.45
    for i in range(rays):
        svg.path(petal_d(cx, cy, i * 360 / rays, r * 0.9, r + ray_len, ray_w, bulge=0.3))
    svg.circle(cx, cy, r)


def flower_simple(svg, cx, cy, r, n=5, petal_w=None):
    petal_w = petal_w or r * 0.9
    for i in range(n):
        svg.path(petal_d(cx, cy, -90 + i * 360 / n, r * 0.3, r, petal_w, bulge=0.7))
    svg.circle(cx, cy, r * 0.32)


def daisy(svg, cx, cy, r, n=16, center=0.3, petal_w=None, double=False):
    petal_w = petal_w or (2 * math.pi * r * 0.55 / n) * 1.6
    if double:
        for i in range(n):
            svg.path(petal_d(cx, cy, i * 360 / n + 180 / n, r * center * 0.9, r * 0.92, petal_w, bulge=0.6))
    for i in range(n):
        svg.path(petal_d(cx, cy, i * 360 / n, r * center * 0.9, r, petal_w, bulge=0.6))
    svg.circle(cx, cy, r * center)
    svg.circle(cx, cy, r * center * 0.55)


def stem(svg, x1, y1, x2, y2, w=14, curve=0.0):
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    mx, my = (x1 + x2) / 2 + nx * curve, (y1 + y2) / 2 + ny * curve
    svg.path(f'M{P(x1 + nx * w / 2, y1 + ny * w / 2)} Q{P(mx + nx * w / 2, my + ny * w / 2)} {P(x2 + nx * w / 2, y2 + ny * w / 2)} '
             f'L{P(x2 - nx * w / 2, y2 - ny * w / 2)} Q{P(mx - nx * w / 2, my - ny * w / 2)} {P(x1 - nx * w / 2, y1 - ny * w / 2)} Z')


def leaf(svg, x1, y1, x2, y2, width, vein=True):
    svg.path(leaf_d(x1, y1, x2, y2, width))
    if vein:
        svg.line(x1, y1, x2, y2)


def star(svg, cx, cy, r, n=5, inner=0.45, rot=-90):
    svg.polygon(star_pts(cx, cy, n, r, r * inner, rot))


def bird(svg, cx, cy, w):
    svg.path(f'M{P(cx - w, cy)} Q{P(cx - w / 2, cy - w * 0.7)} {P(cx, cy)} Q{P(cx + w / 2, cy - w * 0.7)} {P(cx + w, cy)}', fill='none')


def hills(svg, y, bumps):
    """bumps: list of (cx, rx, ry) drawn back to front."""
    for cx, rx, ry in bumps:
        svg.path(f'M{P(cx - rx, y + 5)} A{f(rx)} {f(ry)} 0 0 1 {P(cx + rx, y + 5)} L{P(cx + rx, svg.h + 20)} L{P(cx - rx, svg.h + 20)} Z')


def ground(svg, y):
    svg.rect(-10, y, svg.w + 20, svg.h - y + 20)


# ----------------------------------------------------------------- pages

PAGES = []


def page(pid, title, category, difficulty=2, tags=''):
    def deco(fn):
        PAGES.append(dict(id=pid, title=title, category=category, difficulty=difficulty, tags=tags, fn=fn))
        return fn
    return deco


def frame_square(svg, margin=60, r=40):
    svg.rect(margin, margin, svg.w - 2 * margin, svg.h - 2 * margin, rx=r)


@page('mandala_bloom', 'Blooming Mandala', 'Mandalas', 3, 'mandala flower circle')
def mandala_bloom():
    s = Svg(SQ, SQ, 5)
    cx = cy = SQ / 2
    frame_square(s, 50, 60)
    # corner ornaments
    for ax, ay in [(50, 50), (SQ - 50, 50), (50, SQ - 50), (SQ - 50, SQ - 50)]:
        base = math.degrees(math.atan2(cy - ay, cx - ax))
        for k in (-30, 0, 30):
            s.path(petal_d(ax, ay, base + k, 40, 260, 90, 0.6))
        s.circle(ax, ay, 60)
    s.circle(cx, cy, 820)
    s.circle(cx, cy, 790)
    for i in range(36):
        s.path(petal_d(cx, cy, i * 10, 640, 795, 70, 0.5))
    for i in range(24):
        s.path(petal_d(cx, cy, i * 15 + 7.5, 500, 690, 120, 0.7))
    s.circle(cx, cy, 505)
    for i in range(24):
        x, y = pol(cx, cy, 460, i * 15)
        s.circle(x, y, 36)
    s.circle(cx, cy, 420)
    for i in range(16):
        s.path(petal_d(cx, cy, i * 22.5, 250, 425, 120, 0.8))
    for i in range(16):
        s.path(petal_d(cx, cy, i * 22.5 + 11.25, 150, 330, 90, 0.6))
    s.circle(cx, cy, 160)
    for i in range(8):
        s.path(petal_d(cx, cy, i * 45, 40, 160, 80, 0.8))
    s.circle(cx, cy, 45)
    return s


@page('mandala_lace', 'Lace Mandala', 'Mandalas', 4, 'mandala lace detailed')
def mandala_lace():
    s = Svg(SQ, SQ, 4)
    cx = cy = SQ / 2
    s.circle(cx, cy, 860)
    # scalloped edge
    n = 48
    for i in range(n):
        x, y = pol(cx, cy, 830, i * 360 / n)
        s.circle(x, y, 60)
    s.circle(cx, cy, 790)
    s.circle(cx, cy, 760)
    for i in range(n):
        x, y = pol(cx, cy, 775, i * 360 / n + 180 / n)
        s.circle(x, y, 9)
    for i in range(32):
        s.path(petal_d(cx, cy, i * 11.25, 560, 760, 60, 0.4))
    s.circle(cx, cy, 565)
    s.polygon(star_pts(cx, cy, 12, 560, 430), fill='none')
    s.polygon(star_pts(cx, cy, 12, 560, 430, -90 + 15), fill='none')
    s.circle(cx, cy, 430)
    for i in range(24):
        x, y = pol(cx, cy, 400, i * 15)
        s.circle(x, y, 28)
    s.circle(cx, cy, 370)
    for i in range(12):
        s.path(petal_d(cx, cy, i * 30, 180, 372, 130, 0.7))
        s.path(petal_d(cx, cy, i * 30, 200, 300, 50, 0.4))
    s.circle(cx, cy, 185)
    for i in range(6):
        s.path(petal_d(cx, cy, i * 60 + 30, 60, 185, 90, 0.9))
    s.circle(cx, cy, 65)
    s.circle(cx, cy, 30)
    return s


@page('mandala_star', 'Star Mandala', 'Mandalas', 3, 'mandala star geometric')
def mandala_star():
    s = Svg(SQ, SQ, 5)
    cx = cy = SQ / 2
    s.circle(cx, cy, 870)
    s.circle(cx, cy, 840)
    for i in range(72):
        if i % 2 == 0:
            x, y = pol(cx, cy, 855, i * 5)
            s.circle(x, y, 7)
    s.polygon(star_pts(cx, cy, 8, 840, 560))
    s.polygon(star_pts(cx, cy, 8, 840, 560, -90 + 22.5))
    s.circle(cx, cy, 560)
    s.polygon(star_pts(cx, cy, 16, 555, 440), fill='none')
    s.circle(cx, cy, 440)
    s.polygon(star_pts(cx, cy, 6, 440, 300))
    s.polygon(star_pts(cx, cy, 6, 440, 300, -90 + 30))
    s.circle(cx, cy, 300)
    for i in range(12):
        s.path(petal_d(cx, cy, i * 30, 120, 300, 90, 0.7))
    s.circle(cx, cy, 125)
    s.polygon(star_pts(cx, cy, 5, 120, 55))
    return s


@page('mandala_lotus', 'Lotus Mandala', 'Mandalas', 3, 'mandala lotus petals')
def mandala_lotus():
    s = Svg(SQ, SQ, 5)
    cx = cy = SQ / 2
    frame_square(s, 60, 200)
    s.circle(cx, cy, 800)
    for ring, (n, r0, r1, w) in enumerate([(20, 540, 800, 180), (20, 400, 640, 150), (14, 260, 470, 150), (10, 130, 300, 130)]):
        off = 180 / n if ring % 2 else 0
        for i in range(n):
            s.path(petal_d(cx, cy, i * 360 / n + off, r0, r1, w, 0.9))
    s.circle(cx, cy, 140)
    for i in range(12):
        x, y = pol(cx, cy, 95, i * 30)
        s.circle(x, y, 22)
    s.circle(cx, cy, 45)
    return s


@page('kaleidoscope', 'Kaleidoscope', 'Patterns', 4, 'geometric star overlapping')
def kaleidoscope():
    s = Svg(SQ, SQ, 5)
    cx = cy = SQ / 2
    s.circle(cx, cy, 880, fill='none')
    for k in range(3):
        s.polygon(star_pts(cx, cy, 8, 870, 620, -90 + k * 15), fill='none')
    for k in range(2):
        s.polygon(star_pts(cx, cy, 6, 620, 380, -90 + k * 30), fill='none')
    for r in (700, 500, 380, 220, 110):
        s.circle(cx, cy, r, fill='none')
    for i in range(12):
        x1, y1 = pol(cx, cy, 110, i * 30)
        x2, y2 = pol(cx, cy, 870, i * 30)
        s.line(x1, y1, x2, y2)
    for i in range(12):
        x, y = pol(cx, cy, 300, i * 30 + 15)
        s.circle(x, y, 60, fill='none')
    s.circle(cx, cy, 50)
    return s


@page('honeycomb', 'Honeycomb & Bees', 'Patterns', 2, 'bee hexagon honey')
def honeycomb():
    s = Svg(PW, PH, 6)
    r = 110
    dx = r * math.sqrt(3)
    dy = r * 1.5
    row = 0
    y = 80
    while y < PH + r:
        x = 60 + (dx / 2 if row % 2 else 0)
        while x < PW + r:
            s.polygon([pol(x, y, r, 30 + 60 * k) for k in range(6)], fill='none')
            x += dx
        y += dy
        row += 1
    # honey drops in a few cells
    rnd = random.Random(7)
    for _ in range(10):
        row = rnd.randrange(1, 11)
        col = rnd.randrange(1, 7)
        x = 60 + col * dx + (dx / 2 if row % 2 else 0)
        yy = 80 + row * dy
        s.path(f'M{P(x, yy - 55)} C{P(x + 50, yy + 5)} {P(x + 40, yy + 45)} {P(x, yy + 45)} C{P(x - 40, yy + 45)} {P(x - 50, yy + 5)} {P(x, yy - 55)} Z')

    def bee(cx, cy, sc, flip=1):
        s.begin(transform=f'translate({f(cx)} {f(cy)}) scale({f(sc * flip)} {f(sc)})', stroke_width=f(6 / sc))
        s.ellipse(-20, -70, 45, 28, rot=-20)
        s.ellipse(35, -70, 45, 28, rot=20)
        s.ellipse(0, 0, 90, 60)
        cid = s.clip(f'M-90,0 a90,60 0 1,0 180,0 a90,60 0 1,0 -180,0 Z')
        s.begin(clip=cid)
        for xx in (-45, -5, 35):
            s.rect(xx, -70, 22, 140)
        s.end()
        s.circle(100, -5, 40)
        s.circle(112, -15, 9)
        s.line(115, -40, 135, -75)
        s.line(125, -38, 155, -62)
        s.circle(137, -79, 6)
        s.circle(158, -65, 6)
        s.path('M-95,0 Q-125,0 -140,15', fill='none')
        s.end()

    bee(380, 520, 1.1)
    bee(1120, 1250, 1.0, -1)
    bee(700, 1750, 0.9)
    return s


@page('bouquet', 'Sunny Bouquet', 'Nature', 3, 'flowers vase sunflower daisy fruit')
def bouquet():
    s = Svg(PW, PH, 6)
    # table
    s.path(f'M-10,1500 Q400,1470 750,1500 T1510,1500 L1510,2010 L-10,2010 Z')
    s.path(f'M-10,1560 Q400,1540 750,1560 T1510,1560', fill='none')
    # vase (behind flowers? stems are inside; draw vase first, flowers after)
    vase_d = ('M620,1120 C620,1200 420,1250 420,1520 C420,1760 560,1850 750,1850 '
              'C940,1850 1080,1760 1080,1520 C1080,1250 880,1200 880,1120 Z')
    s.path(vase_d)
    s.path('M620,1120 Q750,1160 880,1120', fill='none')
    s.path('M440,1420 Q750,1480 1060,1420', fill='none')   # water line
    # stems inside the vase
    cid = s.clip(vase_d)
    s.begin(clip=cid)
    for x1, x2 in [(690, 560), (730, 650), (760, 760), (790, 850), (820, 940)]:
        stem(s, x1, 1130, x2, 1800, 16)
    s.end()
    s.path('M490,1330 Q440,1500 500,1660 Q520,1500 490,1330 Z')   # highlights
    s.path('M980,1380 Q1040,1500 990,1640 Q990,1500 980,1380 Z')
    # stems rising from vase to flowers
    flowers = [(430, 700, 'daisy', 150), (1080, 780, 'daisy', 150), (760, 520, 'sun', 210),
               (520, 1000, 'sun', 160), (1000, 1050, 'daisy', 130), (760, 850, 'sun', 180)]
    for fx, fy, kind, r in flowers:
        stem(s, 750, 1140, fx, fy, 14, curve=(fx - 750) * 0.15)
    # leaves
    leaf(s, 700, 1100, 330, 820, 170)
    leaf(s, 720, 1120, 280, 1030, 150)
    leaf(s, 790, 1110, 1190, 760, 170)
    leaf(s, 800, 1130, 1250, 1070, 150)
    leaf(s, 740, 1100, 560, 420, 150)
    leaf(s, 770, 1090, 1000, 400, 150)
    leaf(s, 745, 1120, 900, 1260, 120)
    leaf(s, 760, 1110, 580, 1250, 120)
    # flowers back to front
    for fx, fy, kind, r in flowers:
        if kind == 'daisy':
            daisy(s, fx, fy, r, n=18, center=0.3)
        else:
            daisy(s, fx, fy, r, n=22, center=0.42, double=True)
            s.circle(fx, fy, r * 0.42 * 0.3)
    # fruit on the table
    s.path('M180,1760 C110,1670 110,1550 190,1550 C230,1550 250,1570 260,1580 C270,1570 290,1550 330,1550 C410,1550 410,1670 340,1760 C300,1810 220,1810 180,1760 Z')
    s.line(260, 1580, 268, 1500)
    leaf(s, 268, 1500, 370, 1450, 30)
    s.path('M1130,1740 C1080,1690 1090,1600 1150,1540 C1170,1500 1200,1480 1230,1480 C1260,1480 1290,1500 1310,1540 C1370,1600 1380,1690 1330,1740 C1280,1790 1180,1790 1130,1740 Z')
    s.line(1230, 1480, 1240, 1420)
    s.path('M1160,1690 Q1140,1730 1180,1760 Q1150,1720 1160,1690 Z')
    return s


@page('butterfly', 'Garden Butterfly', 'Animals', 3, 'butterfly insect wings flowers')
def butterfly():
    s = Svg(PW, PH, 6)
    cx = 750
    # background flowers at the bottom
    for fx, h, r in [(150, 1500, 70), (330, 1650, 60), (1360, 1550, 70), (1180, 1700, 55), (750, 1800, 65)]:
        stem(s, fx, PH + 10, fx, h, 12)
        leaf(s, fx, h + 140, fx + 90, h + 60, 30)
        leaf(s, fx, h + 220, fx - 90, h + 150, 30)
        flower_simple(s, fx, h, r, 6)
    sun(s, 1380, 160, 110, 12, 90, 55)
    # wings
    for sgn in (-1, 1):
        def X(dx):
            return cx + sgn * dx
        upper = (f'M{P(X(20), 820)} C{P(X(200), 300)} {P(X(650), 180)} {P(X(690), 560)} '
                 f'C{P(X(710), 800)} {P(X(520), 960)} {P(X(30), 960)} Z')
        lower = (f'M{P(X(30), 980)} C{P(X(520), 960)} {P(X(640), 1150)} {P(X(520), 1420)} '
                 f'C{P(X(420), 1640)} {P(X(120), 1620)} {P(X(25), 1200)} Z')
        for wd in (lower, upper):
            s.path(wd)
            cid = s.clip(wd)
            s.begin(clip=cid)
            if wd is upper:
                for ang in (-75, -55, -35, -15, 5):
                    x2, y2 = pol(X(40), 900, 900, -90 + sgn * (ang + 90) if sgn > 0 else -90 - (ang + 90))
                    s.line(X(40), 900, x2, y2)
                s.circle(X(430), 500, 95)
                s.circle(X(430), 500, 55)
                s.circle(X(430), 500, 22)
                s.ellipse(X(560), 800, 70, 45, rot=-20 * sgn)
            else:
                for ang in (10, 35, 60, 85):
                    x2, y2 = pol(X(40), 1000, 800, ang if sgn > 0 else 180 - ang)
                    s.line(X(40), 1000, x2, y2)
                s.circle(X(380), 1250, 80)
                s.circle(X(380), 1250, 40)
                s.circle(X(220), 1480, 45)
            s.end()
        # scalloped edge dots
        for t in range(6):
            s.circle(X(560 + 20 * math.sin(t)), 350 + t * 100, 18)
    # body
    s.ellipse(cx, 1000, 42, 230)
    for yy in (900, 980, 1060, 1140):
        s.line(cx - 40, yy, cx + 40, yy)
    s.circle(cx, 760, 50)
    s.circle(cx - 20, 745, 10)
    s.circle(cx + 20, 745, 10)
    s.path(f'M{P(cx - 20, 720)} Q{P(cx - 120, 600)} {P(cx - 180, 580)}', fill='none')
    s.path(f'M{P(cx + 20, 720)} Q{P(cx + 120, 600)} {P(cx + 180, 580)}', fill='none')
    s.circle(cx - 185, 578, 14)
    s.circle(cx + 185, 578, 14)
    return s


@page('aquarium', 'Under the Sea', 'Animals', 3, 'fish ocean sea bubbles')
def aquarium():
    s = Svg(PW, PH, 6)
    # water surface
    s.path(wave_band_d(-10, PW + 10, 150, 25, 300, -20))
    s.path('M' + ' L'.join(P(x, y) for x, y in wave_pts(-10, PW + 10, 215, 20, 260, 1.0)), fill='none')
    # sand
    s.path(wave_band_d(-10, PW + 10, 1720, 20, 500, PH + 10, 2.0))
    for x, y, rx, ry in [(200, 1850, 60, 35), (420, 1920, 40, 25), (900, 1880, 70, 40), (1250, 1830, 50, 30), (1380, 1930, 35, 22)]:
        s.ellipse(x, y, rx, ry)
    # seaweed
    def weed(x, h, amp, w):
        pts_l, pts_r = [], []
        n = 30
        for i in range(n + 1):
            t = i / n
            y = PH - 10 - h * t
            off = amp * math.sin(t * 6) * (1 - t * 0.3)
            ww = w * (1 - t * 0.85)
            pts_l.append((x + off - ww, y))
            pts_r.append((x + off + ww, y))
        d = 'M' + ' L'.join(P(a, b) for a, b in pts_l) + ' ' + ' L'.join(P(a, b) for a, b in reversed(pts_r)) + ' Z'
        s.path(d)
    weed(120, 900, 60, 45)
    weed(260, 650, 40, 35)
    weed(1400, 1000, 70, 50)
    weed(1280, 600, 45, 35)
    weed(700, 450, 35, 30)

    def fish(cx, cy, ln, flip=1, stripes=False):
        s.begin(transform=f'translate({f(cx)} {f(cy)}) scale({f(flip)} 1)')
        # tail
        s.path(f'M{P(-ln * 0.45, 0)} L{P(-ln * 0.85, -ln * 0.3)} Q{P(-ln * 0.7, 0)} {P(-ln * 0.85, ln * 0.3)} Z')
        # fins
        s.path(f'M{P(-ln * 0.1, -ln * 0.28)} Q{P(0, -ln * 0.6)} {P(ln * 0.25, -ln * 0.3)} Z')
        s.path(f'M{P(-ln * 0.05, ln * 0.28)} Q{P(0.05 * ln, ln * 0.55)} {P(ln * 0.25, ln * 0.3)} Z')
        body = (f'M{P(-ln * 0.5, 0)} C{P(-ln * 0.4, -ln * 0.45)} {P(ln * 0.2, -ln * 0.45)} {P(ln * 0.5, 0)} '
                f'C{P(ln * 0.2, ln * 0.45)} {P(-ln * 0.4, ln * 0.45)} {P(-ln * 0.5, 0)} Z')
        s.path(body)
        cid = s.clip(body)
        s.begin(clip=cid)
        if stripes:
            for xx in (-ln * 0.3, -ln * 0.1, ln * 0.1):
                s.path(f'M{P(xx, -ln)} Q{P(xx - ln * 0.08, 0)} {P(xx, ln)} L{P(xx + ln * 0.09, ln)} Q{P(xx + ln * 0.01, 0)} {P(xx + ln * 0.09, -ln)} Z')
        else:
            rr = ln * 0.09
            for row in range(-3, 4):
                for col in range(-2, 2):
                    s.circle(-ln * 0.05 + col * rr * 2 + (rr if row % 2 else 0), row * rr * 1.6, rr * 1.1)
        s.end()
        s.path(f'M{P(ln * 0.22, -ln * 0.3)} Q{P(ln * 0.1, 0)} {P(ln * 0.22, ln * 0.3)}', fill='none')
        s.circle(ln * 0.33, -ln * 0.08, ln * 0.07)
        s.circle(ln * 0.35, -ln * 0.08, ln * 0.03)
        s.path(f'M{P(ln * 0.45, ln * 0.08)} Q{P(ln * 0.5, ln * 0.12)} {P(ln * 0.46, ln * 0.16)}', fill='none')
        s.end()
        # bubbles
        bx = cx + flip * ln * 0.6
        for k in range(3):
            s.circle(bx + flip * k * 15, cy - 40 - k * 55, 10 + k * 7)

    fish(450, 520, 380, 1)
    fish(1050, 800, 440, -1, stripes=True)
    fish(560, 1150, 300, -1, stripes=True)
    fish(1000, 1400, 360, 1)
    fish(350, 1500, 240, 1, stripes=True)
    # starfish & shell on the sand
    s.polygon(star_pts(1150, 1800, 5, 110, 55, -90))
    s.circle(1150, 1800, 18)
    for i in range(5):
        for k in (1, 2):
            x, y = pol(1150, 1800, 30 + k * 28, -90 + i * 72)
            s.circle(x, y, 7)
    # scallop shell
    shell = 'M560,1860 L470,1760 A110,110 0 0 1 650,1760 Z'
    s.path(shell)
    cid = s.clip(shell)
    s.begin(clip=cid)
    for ang in range(-155, -20, 22):
        x2, y2 = pol(560, 1860, 160, ang)
        s.line(560, 1860, x2, y2)
    s.end()
    # stray bubbles
    for x, y, r in [(900, 330, 22), (1220, 420, 16), (300, 1000, 20), (1300, 1250, 14), (780, 1650, 18)]:
        s.circle(x, y, r)
    return s


@page('owl', 'Night Owl', 'Animals', 3, 'owl bird moon stars night')
def owl():
    s = Svg(PW, PH, 6)
    # moon
    s.circle(300, 320, 190)
    cid = s.clip('M300,320 m-190,0 a190,190 0 1,0 380,0 a190,190 0 1,0 -380,0 Z')
    s.begin(clip=cid)
    s.circle(400, 280, 170)
    s.end()
    for x, y, r in [(900, 180, 40), (1200, 320, 55), (1380, 150, 30), (700, 420, 28), (1300, 600, 35), (150, 700, 32)]:
        star(s, x, y, r)
    # branch
    s.path('M-10,1700 C300,1660 600,1740 900,1700 C1200,1660 1400,1720 1510,1700 L1510,1780 C1300,1800 1100,1760 900,1780 C600,1820 300,1760 -10,1790 Z')
    for x, y in [(200, 1690), (1250, 1690)]:
        stem(s, x, y, x + 60, y - 140, 10)
        leaf(s, x + 60, y - 140, x + 150, y - 230, 35)
        leaf(s, x + 60, y - 140, x - 40, y - 230, 35)
    # body
    body = 'M750,660 C440,660 330,1000 330,1300 C330,1600 520,1720 750,1720 C980,1720 1170,1600 1170,1300 C1170,1000 1060,660 750,660 Z'
    s.path(body)
    # belly feathers (scallops)
    belly = 'M750,1000 C620,1000 520,1150 520,1350 C520,1560 630,1680 750,1680 C870,1680 980,1560 980,1350 C980,1150 880,1000 750,1000 Z'
    s.path(belly)
    cid = s.clip(belly)
    s.begin(clip=cid)
    for row in range(8):
        yy = 1060 + row * 85
        for col in range(-4, 5):
            xx = 750 + col * 85 + (42 if row % 2 else 0)
            s.path(f'M{P(xx - 42, yy)} A42,42 0 0 0 {P(xx + 42, yy)}', fill='none')
    s.end()
    # wings
    s.path('M400,900 C330,1100 330,1400 450,1560 C520,1400 560,1100 400,900 Z')
    s.path('M1100,900 C1170,1100 1170,1400 1050,1560 C980,1400 940,1100 1100,900 Z')
    # ear tufts
    s.path('M470,700 L420,520 L600,660 Z')
    s.path('M1030,700 L1080,520 L900,660 Z')
    # face disc and eyes
    s.path('M750,640 C560,640 470,780 470,900 C470,980 600,1000 750,1000 C900,1000 1030,980 1030,900 C1030,780 940,640 750,640 Z')
    for ex in (620, 880):
        s.circle(ex, 850, 120)
        s.circle(ex, 850, 85)
        s.circle(ex, 850, 45)
        s.circle(ex + 15, 830, 14)
    s.path('M750,900 L705,930 L750,1030 L795,930 Z')
    # feet
    for fx in (650, 850):
        for k in (-1, 0, 1):
            s.ellipse(fx + k * 32, 1725, 16, 40)
    return s


@page('kitten', 'Playful Kitten', 'Animals', 2, 'cat kitten yarn cute')
def kitten():
    s = Svg(PW, PH, 7)
    ground(s, 1720)
    # yarn ball
    s.circle(1180, 1620, 150)
    cid = s.clip('M1180,1620 m-150,0 a150,150 0 1,0 300,0 a150,150 0 1,0 -300,0 Z')
    s.begin(clip=cid)
    for k in range(-3, 4):
        s.path(f'M{P(1030, 1620 + k * 55)} Q{P(1180, 1560 + k * 55)} {P(1330, 1620 + k * 55)}', fill='none')
    for k in range(-2, 3):
        s.path(f'M{P(1180 + k * 60, 1470)} Q{P(1120 + k * 60, 1620)} {P(1180 + k * 60, 1770)}', fill='none')
    s.end()
    s.path('M1040,1700 Q900,1760 980,1740 Q1060,1720 1000,1780', fill='none')
    # tail
    s.path('M980,1500 C1150,1450 1200,1250 1080,1150 C1050,1130 1010,1150 1020,1190 C1080,1250 1060,1380 940,1430 Z')
    # body
    s.path('M750,1000 C520,1000 420,1250 420,1480 C420,1660 560,1730 750,1730 C940,1730 1080,1660 1080,1480 C1080,1250 980,1000 750,1000 Z')
    # belly
    s.path('M750,1300 C640,1300 600,1450 600,1560 C600,1680 680,1730 750,1730 C820,1730 900,1680 900,1560 C900,1450 860,1300 750,1300 Z')
    # paws
    for px in (640, 860):
        s.ellipse(px, 1720, 85, 45)
        s.line(px - 25, 1700, px - 25, 1760)
        s.line(px + 25, 1700, px + 25, 1760)
    # head
    s.path('M750,560 C530,560 400,720 400,900 C400,1080 560,1180 750,1180 C940,1180 1100,1080 1100,900 C1100,720 970,560 750,560 Z')
    # ears
    s.path('M470,730 L420,470 L650,600 Z')
    s.path('M1030,730 L1080,470 L850,600 Z')
    s.path('M510,700 L480,540 L620,620 Z')
    s.path('M990,700 L1020,540 L880,620 Z')
    # eyes
    for ex in (630, 870):
        s.path(f'M{P(ex - 80, 880)} Q{P(ex, 760)} {P(ex + 80, 880)} Q{P(ex, 990)} {P(ex - 80, 880)} Z')
        s.ellipse(ex, 880, 30, 50)
        s.circle(ex + 12, 855, 10)
    # nose & mouth
    s.path('M700,1000 L800,1000 L750,1060 Z')
    s.path('M750,1060 Q740,1110 690,1110', fill='none')
    s.path('M750,1060 Q760,1110 810,1110', fill='none')
    # whiskers
    for sgn in (-1, 1):
        for dy in (-20, 20, 60):
            s.line(750 + sgn * 120, 1030 + dy, 750 + sgn * 330, 1000 + dy * 2)
    # collar
    s.path('M520,1090 Q750,1240 980,1090 Q750,1300 520,1090 Z')
    s.circle(750, 1230, 40)
    s.line(750, 1230, 750, 1265)
    return s


@page('balloons', 'Hot Air Balloons', 'Nature', 2, 'balloon sky clouds hills')
def balloons():
    s = Svg(PW, PH, 6)
    sun(s, 1320, 200, 110, 12, 90, 55)
    cloud(s, 300, 350, 320)
    cloud(s, 1150, 650, 260)
    cloud(s, 250, 1150, 220)
    hills(s, 1700, [(200, 700, 260), (1300, 700, 300), (750, 650, 220)])
    for x, y in [(120, 1850), (420, 1900), (1300, 1880), (900, 1950)]:
        stem(s, x, PH + 10, x, y, 10)
        flower_simple(s, x, y, 35, 5)

    def balloon(cx, cy, sc):
        s.begin(transform=f'translate({f(cx)} {f(cy)}) scale({f(sc)})', stroke_width=f(6 / sc))
        env = 'M0,-300 C-200,-300 -300,-150 -300,0 C-300,160 -120,280 -60,360 L60,360 C120,280 300,160 300,0 C300,-150 200,-300 0,-300 Z'
        # ropes
        for xx in (-60, -20, 20, 60):
            s.line(xx, 360, xx * 0.8, 450)
        s.path(env)
        cid = s.clip(env)
        s.begin(clip=cid)
        for xx in (-200, -100, 100, 200):
            s.path(f'M{P(xx * 0.0, -320)} C{P(xx * 1.5, -150)} {P(xx * 1.5, 150)} {P(xx * 0.25, 400)}', fill='none')
        s.path('M-320,120 Q0,200 320,120', fill='none')
        s.path('M-320,180 Q0,260 320,180', fill='none')
        s.end()
        s.rect(-80, 450, 160, 110, rx=12)
        cid = s.clip('M-80,450 h160 v110 h-160 Z')
        s.begin(clip=cid)
        for xx in range(-60, 80, 30):
            s.line(xx, 440, xx, 580)
        for yy in (490, 525):
            s.line(-90, yy, 90, yy)
        s.end()
        s.end()

    balloon(1000, 1050, 1.0)
    balloon(420, 700, 0.8)
    balloon(1200, 350, 0.45)
    bird(s, 700, 300, 40)
    bird(s, 780, 260, 30)
    bird(s, 640, 450, 28)
    return s


@page('rocket', 'Rocket to the Stars', 'Space', 2, 'rocket space planet stars moon')
def rocket():
    s = Svg(PW, PH, 6)
    for x, y, r in [(150, 200, 45), (500, 120, 30), (1300, 250, 50), (1400, 900, 35), (200, 1300, 40), (1350, 1500, 45), (650, 1900, 30), (1100, 1950, 28)]:
        star(s, x, y, r)
    for x, y, r in [(900, 420, 12), (350, 600, 10), (1200, 1250, 12), (500, 1700, 10), (1000, 1600, 9)]:
        s.circle(x, y, r)
    # moon with craters
    s.circle(260, 820, 180)
    for x, y, r in [(200, 760, 40), (300, 880, 55), (320, 740, 22), (190, 900, 25)]:
        s.circle(x, y, r)
    # ringed planet
    s.ellipse(1180, 650, 260, 70, rot=-20, fill='none')
    s.circle(1180, 650, 150)
    cid = s.clip('M1180,650 m-150,0 a150,150 0 1,0 300,0 a150,150 0 1,0 -300,0 Z')
    s.begin(clip=cid)
    s.path('M1010,600 Q1180,540 1350,600', fill='none')
    s.path('M1000,700 Q1180,760 1360,700', fill='none')
    s.end()
    # comet
    s.circle(1250, 1800, 60)
    s.path('M1300,1770 Q1450,1650 1500,1500 Q1420,1680 1310,1810 Z')
    s.path('M1250,1740 Q1350,1600 1440,1480 Q1330,1640 1240,1745 Z')
    # rocket
    s.begin(transform='translate(700 1100) rotate(-25)')
    # flame
    s.path('M-70,320 Q-40,420 0,520 Q40,420 70,320 Z')
    s.path('M-35,320 Q-15,380 0,430 Q15,380 35,320 Z')
    # fins
    s.path('M-120,300 L-210,420 L-120,420 L-100,330 Z')
    s.path('M120,300 L210,420 L120,420 L100,330 Z')
    body = 'M0,-380 C110,-280 130,-100 130,100 L130,320 L-130,320 L-130,100 C-130,-100 -110,-280 0,-380 Z'
    s.path(body)
    s.path('M-130,320 L130,320 L110,370 L-110,370 Z')
    cid = s.clip(body)
    s.begin(clip=cid)
    s.path('M-140,-120 Q0,-170 140,-120 L140,-80 Q0,-130 -140,-80 Z')
    s.line(-140, 220, 140, 220)
    s.end()
    s.circle(0, 0, 70)
    s.circle(0, 0, 45)
    s.circle(0, 150, 32)
    s.end()
    return s


@page('cupcake', 'Sweet Cupcake', 'Food', 1, 'cupcake dessert sweet cherry')
def cupcake():
    s = Svg(PW, PH, 7)
    rnd = random.Random(3)
    for _ in range(26):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(60, PH - 60)
        if 300 < x < 1200 and 350 < y < 1800:
            continue
        s.path(heart_d(x, y, rnd.uniform(50, 90)))
    # plate
    s.ellipse(750, 1760, 560, 110)
    s.ellipse(750, 1760, 470, 80)
    # liner
    liner = 'M400,1250 L470,1720 L1030,1720 L1100,1250 Z'
    s.path(liner)
    cid = s.clip(liner)
    s.begin(clip=cid)
    for xx in range(430, 1100, 70):
        s.path(f'M{P(xx, 1240)} L{P(xx + 20, 1730)}', fill='none')
    s.end()
    s.path('M380,1250 Q750,1180 1120,1250 Q750,1320 380,1250 Z')
    # cake
    s.path('M400,1250 C400,1120 520,1060 750,1060 C980,1060 1100,1120 1100,1250 Z')
    # frosting swirl: three tiers of wavy blobs
    def tier(cy, w, h):
        pts = []
        n = 9
        for i in range(n + 1):
            x = 750 - w / 2 + w * i / n
            pts.append((x, cy + (h if i % 2 else 0)))
        d = f'M{P(750 - w / 2, cy - h * 1.6)} '
        d += f'C{P(750 - w / 2, cy - h * 3)} {P(750 + w / 2, cy - h * 3)} {P(750 + w / 2, cy - h * 1.6)} '
        d += f'L{P(750 + w / 2, cy)} '
        for i in range(n, -1, -1):
            x, y = pts[i]
            if i < n:
                px = pts[i + 1][0]
                d += f'Q{P((x + px) / 2, cy + h * 1.3)} {P(x, cy)} '
        d += 'Z'
        s.path(d)
    tier(1150, 720, 55)
    tier(950, 540, 50)
    tier(790, 360, 45)
    s.path('M750,640 C560,640 620,760 750,720 C880,760 940,640 750,640 Z')
    # cherry
    s.circle(750, 560, 70)
    s.path('M760,495 Q780,380 880,350', fill='none')
    s.ellipse(725, 540, 18, 10, rot=-40)
    # sprinkles
    for cx, cy, a in [(600, 880, 30), (680, 1000, -20), (820, 880, 60), (900, 1010, 10), (740, 1200, -40), (560, 1130, 70), (950, 1150, -60), (660, 760, 20), (850, 760, -30)]:
        s.rect(cx - 25, cy - 8, 50, 16, rx=8, transform=f'rotate({a} {cx} {cy})')
    return s


@page('fruit_basket', 'Fruit Basket', 'Food', 3, 'fruit basket apple grapes banana pear')
def fruit_basket():
    s = Svg(PW, PH, 6)
    s.rect(-10, 1750, PW + 20, 300)
    s.path('M-10,1750 Q750,1700 1510,1750', fill='none')
    # handle
    s.path('M330,1250 C330,500 1170,500 1170,1250 L1110,1250 C1110,600 390,600 390,1250 Z')
    cid = s.clip('M330,1250 C330,500 1170,500 1170,1250 L1110,1250 C1110,600 390,600 390,1250 Z')
    s.begin(clip=cid)
    for t in range(0, 40):
        a = 180 + t * 180 / 39
        x1, y1 = pol(750, 1250, 300, a)
        x2, y2 = pol(750, 1250, 460, a + 6)
        s.line(x1, y1, x2, y2)
    s.end()
    # fruits (behind the basket front)
    s.circle(520, 1180, 150)   # orange
    cid = s.clip('M520,1180 m-150,0 a150,150 0 1,0 300,0 a150,150 0 1,0 -300,0 Z')
    s.begin(clip=cid)
    s.circle(480, 1130, 25)
    s.end()
    # apple
    s.path('M820,1250 C740,1150 760,1010 860,1010 C890,1010 910,1030 920,1040 C930,1030 950,1010 980,1010 C1080,1010 1100,1150 1020,1250 C980,1300 860,1300 820,1250 Z')
    s.line(920, 1040, 930, 960)
    leaf(s, 930, 960, 1030, 920, 30)
    # pear
    s.path('M1100,1270 C1040,1220 1060,1120 1120,1060 C1140,1010 1160,990 1190,990 C1220,990 1240,1010 1260,1060 C1320,1120 1340,1220 1280,1270 Z')
    s.line(1190, 990, 1200, 930)
    # grapes
    gx, gy = 320, 1150
    for row, cnt in enumerate([5, 4, 3, 2, 1]):
        for i in range(cnt):
            s.circle(gx + (i - (cnt - 1) / 2) * 62, gy + row * 56, 36)
    s.line(gx, gy - 40, gx + 20, gy - 130)
    leaf(s, gx + 20, gy - 130, gx + 140, gy - 180, 35)
    # banana
    s.path('M560,1020 C700,860 950,860 1080,940 C1040,900 820,920 680,1040 C620,1090 580,1060 560,1020 Z')
    # basket body (front)
    body = 'M250,1250 L330,1760 L1170,1760 L1250,1250 Z'
    s.path(body)
    cid = s.clip(body)
    s.begin(clip=cid)
    for xx in range(-400, 1700, 80):
        s.line(xx, 1250, xx + 400, 1800)
        s.line(xx + 400, 1250, xx, 1800)
    s.end()
    s.rect(230, 1210, 1040, 80, rx=20)
    cid = s.clip('M230,1210 h1040 v80 h-1040 Z')
    s.begin(clip=cid)
    for xx in range(240, 1280, 52):
        s.line(xx, 1200, xx + 20, 1300)
    s.end()
    s.rect(300, 1740, 900, 50, rx=20)
    return s


@page('big_tree', 'The Big Tree', 'Nature', 2, 'tree landscape sun clouds fence')
def big_tree():
    s = Svg(PW, PH, 6)
    sun(s, 220, 220, 120, 14, 90, 55)
    cloud(s, 1150, 300, 320)
    cloud(s, 800, 180, 200)
    hills(s, 1500, [(1300, 900, 320), (200, 800, 260)])
    ground(s, 1650)
    # path
    s.path('M700,1650 C600,1750 950,1800 800,1900 C700,1960 600,2000 650,2020 L1050,2020 C1000,1950 1150,1860 1000,1800 C850,1740 1050,1700 950,1650 Z')
    # fence
    for i in range(6):
        x = 40 + i * 70
        s.path(f'M{P(x, 1700)} L{P(x, 1560)} L{P(x + 25, 1530)} L{P(x + 50, 1560)} L{P(x + 50, 1700)} Z')
    s.rect(20, 1580, 420, 28)
    s.rect(20, 1650, 420, 28)
    # trunk
    s.path('M660,1700 C680,1500 690,1300 700,1100 L820,1100 C830,1300 840,1500 860,1700 C900,1720 920,1740 940,1760 L580,1760 C600,1740 620,1720 660,1700 Z')
    s.path('M700,1100 L740,1250 L700,1400', fill='none')
    s.path('M820,1100 L790,1230', fill='none')
    # foliage
    union_circles(s, [(760, 700, 330), (500, 850, 240), (1020, 850, 240), (560, 600, 200), (960, 600, 200), (760, 450, 230), (640, 1000, 170), (880, 1000, 170)])
    for x, y in [(600, 700), (900, 650), (760, 850), (520, 920), (1000, 950), (700, 540), (880, 480)]:
        s.circle(x, y, 32)
        s.line(x, y - 32, x + 6, y - 60)
    # flowers and grass
    for x in (1200, 1300, 1420):
        stem(s, x, 1850, x, 1760, 8)
        flower_simple(s, x, 1760, 32, 5)
    for x in (150, 300, 1100, 1350):
        for k in (-1, 0, 1):
            s.path(f'M{P(x + k * 20, 1900)} Q{P(x + k * 35, 1850)} {P(x + k * 45, 1800)}', fill='none')
    bird(s, 1200, 700, 35)
    bird(s, 1280, 660, 28)
    return s


@page('snowflake', 'Snowflake', 'Patterns', 3, 'snow winter crystal')
def snowflake():
    s = Svg(SQ, SQ, 5)
    cx = cy = SQ / 2
    rnd = random.Random(11)
    for _ in range(40):
        x, y = rnd.uniform(40, SQ - 40), rnd.uniform(40, SQ - 40)
        if math.hypot(x - cx, y - cy) < 820:
            continue
        s.circle(x, y, rnd.uniform(8, 20))
    for i in range(6):
        a = i * 60 - 90
        # side branches first (behind)
        for dist, ln in [(300, 220), (480, 180), (640, 120)]:
            bx, by = pol(cx, cy, dist, a)
            for side in (-1, 1):
                ex, ey = pol(bx, by, ln, a + side * 60)
                s.path(leaf_d(bx, by, ex, ey, ln * 0.18))
        # main arm
        ex, ey = pol(cx, cy, 800, a)
        s.path(leaf_d(cx, cy, ex, ey, 70))
        s.circle(ex, ey, 40)
        for dist in (300, 480, 640):
            bx, by = pol(cx, cy, dist, a)
            s.circle(bx, by, 26)
    s.polygon([pol(cx, cy, 170, 30 + 60 * k) for k in range(6)])
    s.polygon([pol(cx, cy, 100, 60 * k) for k in range(6)])
    s.circle(cx, cy, 40)
    return s


@page('paisley', 'Paisley Garden', 'Patterns', 4, 'paisley boho pattern')
def paisley():
    s = Svg(PW, PH, 5)
    unit = ('M0,-100 C60,-100 100,-40 100,20 C100,80 70,120 30,150 C0,175 -40,180 -60,160 '
            'C-40,150 -20,130 -30,110 C-50,80 -100,40 -100,-20 C-100,-70 -50,-100 0,-100 Z')

    def paisley_at(cx, cy, sc, rot):
        s.begin(transform=f'translate({f(cx)} {f(cy)}) rotate({rot}) scale({f(sc)})', stroke_width=f(5 / sc))
        s.path(unit)
        s.begin(transform='scale(0.72)')
        s.path(unit)
        s.end()
        s.begin(transform='scale(0.45)')
        s.path(unit)
        s.end()
        for k in range(8):
            x, y = pol(0, -5, 38, k * 45)
            s.circle(x, y, 10)
        s.circle(0, -5, 12)
        # dots around outside
        for k in range(14):
            x, y = pol(0, 10, 128, -160 + k * 20)
            s.circle(x, y, 7)
        s.end()

    paisley_at(400, 450, 2.6, 20)
    paisley_at(1100, 700, 2.2, -150)
    paisley_at(500, 1250, 2.4, 160)
    paisley_at(1100, 1500, 2.6, 10)
    paisley_at(1250, 200, 1.1, 60)
    paisley_at(180, 900, 1.1, -40)
    paisley_at(250, 1750, 1.3, 120)
    paisley_at(800, 1900, 1.0, -90)
    paisley_at(820, 950, 0.9, 200)
    rnd = random.Random(5)
    for _ in range(40):
        s.circle(rnd.uniform(40, PW - 40), rnd.uniform(40, PH - 40), rnd.uniform(8, 16))
    return s


@page('hearts', 'Hearts & Dots', 'Patterns', 1, 'heart love valentine')
def hearts():
    s = Svg(PW, PH, 7)
    rnd = random.Random(21)
    for _ in range(50):
        s.circle(rnd.uniform(40, PW - 40), rnd.uniform(40, PH - 40), rnd.uniform(10, 24))
    for cx, cy, sz in [(400, 450, 450), (1100, 1000, 520), (450, 1500, 480), (1150, 350, 260), (1200, 1650, 300), (850, 1850, 200)]:
        for k in (1.0, 0.72, 0.45):
            s.path(heart_d(cx, cy, sz * k))
    for cx, cy, sz in [(150, 1050, 140), (850, 150, 150), (800, 1250, 120), (1380, 1300, 110), (200, 1900, 120)]:
        s.path(heart_d(cx, cy, sz))
    return s


@page('peacock', 'Peacock Feathers', 'Patterns', 4, 'peacock feather eye')
def peacock():
    s = Svg(PW, PH, 5)

    def feather(cx, cy, sc, rot):
        s.begin(transform=f'translate({f(cx)} {f(cy)}) rotate({rot}) scale({f(sc)})', stroke_width=f(5 / sc))
        outline = 'M0,-300 C110,-300 130,-150 130,0 C130,120 60,250 0,330 C-60,250 -130,120 -130,0 C-130,-150 -110,-300 0,-300 Z'
        s.path(outline)
        cid = s.clip(outline)
        s.begin(clip=cid)
        for yy in range(-280, 340, 40):
            s.path(f'M0,{yy} Q-70,{yy - 30} -140,{yy + 10}', fill='none')
            s.path(f'M0,{yy} Q70,{yy - 30} 140,{yy + 10}', fill='none')
        s.end()
        s.line(0, -300, 0, 330)
        s.ellipse(0, -60, 95, 125)
        s.ellipse(0, -70, 60, 85)
        s.circle(0, -80, 32)
        s.end()

    for row in range(4):
        for col in range(3):
            x = 260 + col * 490 + (245 if row % 2 else 0)
            y = 300 + row * 480
            if x > PW - 100:
                x -= 490 * 3
            feather(x, y, 0.72, (col - 1) * 8)
    return s


@page('sunburst', 'Sunburst Rings', 'Patterns', 3, 'sun rays rings spiral abstract')
def sunburst():
    s = Svg(SQ, SQ, 5)
    cx = cy = SQ / 2
    s.circle(cx, cy, 880, fill='none')
    for i in range(24):
        x1, y1 = pol(cx, cy, 120, i * 15)
        x2, y2 = pol(cx, cy, 880, i * 15)
        s.line(x1, y1, x2, y2)
    for r, k, amp in [(800, 12, 30), (660, 10, 28), (540, 9, 24), (420, 8, 20), (310, 7, 16), (210, 6, 12)]:
        s.path(polar_d(cx, cy, lambda a, r=r, k=k, amp=amp: r + amp * math.sin(math.radians(a) * k), 360), fill='none')
    s.circle(cx, cy, 120)
    for i in range(8):
        s.path(petal_d(cx, cy, i * 45, 30, 118, 50, 0.7))
    return s


@page('lotus_pond', 'Lotus Pond', 'Nature', 3, 'lotus water lily pond')
def lotus_pond():
    s = Svg(PW, PH, 6)
    # ripples
    for ry in range(1, 6):
        s.ellipse(750, 1450, 200 + ry * 160, 80 + ry * 60, fill='none')
    # lily pads
    for px, py, r in [(300, 1250, 150), (1200, 1300, 170), (1050, 1750, 140), (350, 1800, 130)]:
        s.path(f'M{P(px, py)} L{P(*pol(px, py, r, -60))} A{f(r)} {f(r)} 0 1 1 {P(*pol(px, py, r, -100))} Z', transform=f'scale(1 0.55) translate(0 {f(py / 0.55 - py)})')
    # lotus layers
    cx, base = 750, 1380
    rows = [(260, 15, 170, 5), (330, 25, 130, 4), (370, 45, 95, 3)]
    for ln, spread, w, n in [(420, 72, 230, 7), (520, 52, 220, 6), (590, 32, 200, 5), (580, 0, 210, 3)]:
        for i in range(n):
            ang = -90 + (i - (n - 1) / 2) * (spread * 2 / max(n - 1, 1)) if n > 1 else -90
            ang = -90 + (i - (n - 1) / 2) * (2 * spread / max(n - 1, 1)) if n > 1 else -90
            s.path(petal_d(cx, base, ang, 0, ln, w, 0.9))
    s.ellipse(cx, base + 50, 330, 90)
    # dragonfly
    s.ellipse(1150, 500, 14, 150, rot=30)
    s.circle(1215, 370, 30)
    for rot in (-20, 20):
        s.ellipse(1150, 500, 130, 24, rot=rot - 60)
    for rot in (-20, 20):
        s.ellipse(1150, 500, 110, 20, rot=rot + 60)
    # reeds
    for x in (120, 180, 1400, 1450):
        stem(s, x, PH + 10, x + 20, 900 + (x % 100) * 2, 10)
        s.ellipse(x + 22, 880 + (x % 100) * 2, 18, 60)
    return s


@page('flower_of_life', 'Flower of Life', 'Mandalas', 2, 'sacred geometry circles')
def flower_of_life():
    s = Svg(SQ, SQ, 5)
    cx = cy = SQ / 2
    r = 180
    s.circle(cx, cy, 800, fill='none')
    s.circle(cx, cy, 760, fill='none')
    cid = s.clip(f'M{P(cx, cy)} m-760,0 a760,760 0 1,0 1520,0 a760,760 0 1,0 -1520,0 Z')
    s.begin(clip=cid)
    pts = set()
    for q in range(-4, 5):
        for rr in range(-4, 5):
            x = cx + r * (q + rr / 2)
            y = cy + r * rr * math.sqrt(3) / 2
            if math.hypot(x - cx, y - cy) <= r * 3.1:
                pts.add((round(x, 1), round(y, 1)))
    for x, y in pts:
        s.circle(x, y, r, fill='none')
    s.end()
    for ax, ay in [(0, 0), (SQ, 0), (0, SQ), (SQ, SQ)]:
        base = math.degrees(math.atan2(cy - ay, cx - ax))
        for k in (-25, 0, 25):
            s.path(petal_d(ax, ay, base + k, 60, 330, 100, 0.6))
        s.circle(ax, ay, 90)
    return s


@page('iso_cubes', 'Tumbling Blocks', 'Patterns', 2, 'cubes isometric geometric')
def iso_cubes():
    s = Svg(SQ, SQ, 6)
    a = 150
    h = a * math.sqrt(3) / 2
    y = -a
    row = 0
    while y < SQ + a:
        x = -a if row % 2 == 0 else -a + h
        while x < SQ + a:
            # cube: top rhombus, left, right faces
            s.polygon([(x, y - a), (x + h, y - a / 2), (x, y), (x - h, y - a / 2)])
            s.polygon([(x - h, y - a / 2), (x, y), (x, y + a), (x - h, y + a / 2)])
            s.polygon([(x + h, y - a / 2), (x, y), (x, y + a), (x + h, y + a / 2)])
            x += 2 * h
        y += a * 1.5
        row += 1
    return s


@page('zentangle', 'Doodle Tiles', 'Patterns', 4, 'zentangle doodle tiles')
def zentangle():
    s = Svg(PW, PH, 5)
    rnd = random.Random(42)
    cw, ch = 350, 350
    cols, rows = 4, 5
    ox = (PW - cols * cw) / 2
    oy = (PH - rows * ch) / 2
    kinds = ['stripes', 'dots', 'scallop', 'chevron', 'spiral', 'checker', 'wave', 'petals', 'rings', 'grid']
    k = 0
    for r in range(rows):
        for c in range(cols):
            x0, y0 = ox + c * cw, oy + r * ch
            kind = kinds[k % len(kinds)]
            k += 1
            cid = s.clip(f'M{P(x0, y0)} h{cw} v{ch} h-{cw} Z')
            s.begin(clip=cid)
            if kind == 'stripes':
                for t in range(-10, 12):
                    s.line(x0 + t * 60, y0, x0 + t * 60 + ch, y0 + ch)
            elif kind == 'dots':
                for i in range(1, 5):
                    for j in range(1, 5):
                        s.circle(x0 + i * cw / 5, y0 + j * ch / 5, 28)
            elif kind == 'scallop':
                for j in range(7):
                    for i in range(-1, 6):
                        s.circle(x0 + i * 70 + (35 if j % 2 else 0), y0 + ch - j * 45, 42)
            elif kind == 'chevron':
                for j in range(-2, 8):
                    pts = [(x0 + i * cw / 4, y0 + j * 60 + (40 if i % 2 else 0)) for i in range(5)]
                    s.polyline(pts)
            elif kind == 'spiral':
                pts = []
                for t in range(0, 720, 6):
                    rr = 10 + t * 0.32
                    pts.append(pol(x0 + cw / 2, y0 + ch / 2, rr, t))
                s.polyline(pts)
            elif kind == 'checker':
                for i in range(5):
                    for j in range(5):
                        if (i + j) % 2 == 0:
                            s.rect(x0 + i * cw / 5, y0 + j * ch / 5, cw / 5, ch / 5)
            elif kind == 'wave':
                for j in range(8):
                    s.polyline(wave_pts(x0 - 10, x0 + cw + 10, y0 + 20 + j * 46, 16, 120, j * 0.8))
            elif kind == 'petals':
                for i in range(12):
                    s.path(petal_d(x0 + cw / 2, y0 + ch / 2, i * 30, 20, 170, 55, 0.7))
                s.circle(x0 + cw / 2, y0 + ch / 2, 25)
            elif kind == 'rings':
                for i in range(2):
                    for j in range(2):
                        ccx, ccy = x0 + cw / 4 + i * cw / 2, y0 + ch / 4 + j * ch / 2
                        for rr in (75, 50, 25):
                            s.circle(ccx, ccy, rr)
            elif kind == 'grid':
                for i in range(1, 6):
                    s.line(x0 + i * cw / 6, y0, x0 + i * cw / 6, y0 + ch)
                    s.line(x0, y0 + i * ch / 6, x0 + cw, y0 + i * ch / 6)
                for i in range(6):
                    for j in range(6):
                        if (i + j) % 2:
                            s.circle(x0 + (i + 0.5) * cw / 6, y0 + (j + 0.5) * ch / 6, 14)
            s.end()
            s.rect(x0, y0, cw, ch, fill='none')
    s.rect(ox - 25, oy - 25, cols * cw + 50, rows * ch + 50, rx=20, fill='none')
    return s


@page('seashells', 'Seashells', 'Nature', 3, 'beach shell nautilus starfish')
def seashells():
    s = Svg(PW, PH, 6)
    s.path(wave_band_d(-10, PW + 10, 260, 30, 350, -20, 0.5))
    s.path('M' + ' L'.join(P(x, y) for x, y in wave_pts(-10, PW + 10, 330, 22, 300, 2.0)), fill='none')
    s.path(wave_band_d(-10, PW + 10, 480, 40, 600, 330, 1.0))
    # nautilus
    cx, cy = 560, 900
    pts = []
    for t in range(0, 900, 5):
        rr = 12 * math.exp(0.0048 * t)
        pts.append(pol(cx, cy, rr, t))
    outer = 'M' + ' L'.join(P(x, y) for x, y in pts)
    # close the shell with the final sweep back to the center
    shell_d = outer + f' L{P(cx, cy)} Z'
    s.path(shell_d)
    cid = s.clip(shell_d)
    s.begin(clip=cid)
    inner = []
    for t in range(0, 900, 5):
        rr = 12 * math.exp(0.0048 * (t - 360)) if t >= 360 else 0
        if rr:
            inner.append(pol(cx, cy, rr, t))
    for t in range(380, 900, 30):
        r1 = 12 * math.exp(0.0048 * t)
        r0 = 12 * math.exp(0.0048 * (t - 360))
        x1, y1 = pol(cx, cy, r1, t)
        x0, y0 = pol(cx, cy, r0, t)
        s.path(f'M{P(x0, y0)} Q{P(*pol(cx, cy, (r0 + r1) / 2, t - 12))} {P(x1, y1)}', fill='none')
    s.end()
    # scallops
    def scallop(cx, cy, r, rot=0):
        s.begin(transform=f'translate({f(cx)} {f(cy)}) rotate({rot})')
        d = f'M0,0 L{P(*pol(0, 0, r, -150))} A{f(r)} {f(r)} 0 1 1 {P(*pol(0, 0, r, -30))} Z'
        s.path(d)
        cid = s.clip(d)
        s.begin(clip=cid)
        for ang in range(-150, -29, 15):
            x2, y2 = pol(0, 0, r * 1.2, ang)
            s.line(0, 0, x2, y2)
        s.end()
        s.rect(-r * 0.3, -r * 0.1, r * 0.6, r * 0.25, rx=10)
        s.end()
    scallop(1150, 1050, 220, 10)
    scallop(350, 1500, 160, -15)
    scallop(1250, 1700, 140, 25)
    # starfish
    s.polygon(star_pts(850, 1550, 5, 200, 95, -80))
    for i in range(5):
        for k in (1, 2, 3):
            x, y = pol(850, 1550, 40 + k * 45, -80 + i * 72)
            s.circle(x, y, 10 + (3 - k) * 3)
    s.circle(850, 1550, 25)
    # sand dollar
    s.circle(1100, 1400, 110)
    for i in range(5):
        s.path(petal_d(1100, 1400, -90 + i * 72, 10, 85, 45, 0.9))
    # pebbles
    for x, y, rx, ry in [(150, 1850, 45, 25), (600, 1900, 35, 20), (1400, 1250, 30, 18), (700, 1250, 28, 16), (300, 1150, 30, 16)]:
        s.ellipse(x, y, rx, ry)
    return s


@page('easy_house', 'Little House', 'Easy', 1, 'house home sun tree kids')
def easy_house():
    s = Svg(PW, PH, 10)
    sun(s, 230, 230, 130, 10, 110, 70)
    cloud(s, 1100, 280, 340, 10)
    ground(s, 1600)
    # tree
    s.rect(1180, 1300, 90, 320)
    union_circles(s, [(1225, 1050, 200), (1100, 1200, 140), (1350, 1200, 140)])
    # house
    s.rect(300, 950, 700, 650)
    s.polygon([(250, 950), (650, 600), (1050, 950)])
    s.rect(820, 650, 90, 180)
    s.rect(560, 1250, 180, 350, rx=10)
    s.circle(700, 1430, 15)
    for wx in (380, 800):
        s.rect(wx, 1050, 160, 160)
        s.line(wx + 80, 1050, wx + 80, 1210)
        s.line(wx, 1130, wx + 160, 1130)
    # path
    s.path('M580,1600 Q450,1800 350,2010 L1050,2010 Q900,1800 720,1600 Z')
    for x in (150, 1400):
        stem(s, x, 1800, x, 1680, 12)
        flower_simple(s, x, 1680, 45, 5)
    return s


@page('easy_car', 'Zoom Car', 'Easy', 1, 'car vehicle road kids')
def easy_car():
    s = Svg(PW, PH, 10)
    sun(s, 1280, 230, 120, 10, 100, 65)
    cloud(s, 350, 300, 320, 10)
    cloud(s, 850, 450, 220, 10)
    hills(s, 1250, [(300, 700, 250), (1200, 700, 300)])
    s.rect(-10, 1250, PW + 20, 800)
    s.rect(-10, 1250, PW + 20, 500)
    for x in range(60, PW, 240):
        s.rect(x, 1480, 120, 30)
    # car
    s.path('M200,1300 L200,1100 Q200,1040 260,1040 L420,1040 L560,820 L1000,820 L1140,1040 L1240,1040 Q1300,1040 1300,1100 L1300,1300 Z')
    s.path('M470,1030 L580,870 L740,870 L740,1030 Z')
    s.path('M800,870 L960,870 L1070,1030 L800,1030 Z')
    s.rect(1180, 1100, 90, 60, rx=20)
    s.rect(230, 1100, 90, 60, rx=20)
    for wx in (420, 1080):
        s.circle(wx, 1300, 130)
        s.circle(wx, 1300, 70)
        s.circle(wx, 1300, 25)
    s.rect(400, 1110, 700, 60, rx=30)
    return s


@page('easy_icecream', 'Ice Cream Cone', 'Easy', 1, 'ice cream dessert sweet kids')
def easy_icecream():
    s = Svg(PW, PH, 10)
    rnd = random.Random(8)
    for _ in range(18):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(60, PH - 60)
        if 350 < x < 1150 and 250 < y < 1900:
            continue
        star(s, x, y, rnd.uniform(35, 60))
    cone = 'M450,1050 L750,1900 L1050,1050 Z'
    s.path(cone)
    cid = s.clip(cone)
    s.begin(clip=cid)
    for t in range(-6, 10):
        s.line(300 + t * 110, 1000, 700 + t * 110, 1950)
        s.line(1200 - t * 110, 1000, 800 - t * 110, 1950)
    s.end()
    union_circles(s, [(750, 950, 320), (600, 1020, 200), (900, 1020, 200)])
    s.circle(750, 520, 230)
    s.circle(750, 950, 320)
    s.path('M430,980 Q500,1100 560,1000 Q620,1120 690,1010 Q760,1130 820,1010 Q890,1120 950,1000 Q1010,1100 1070,980', fill='none')
    s.circle(750, 520, 230)
    s.circle(750, 270, 60)
    s.path('M760,215 Q790,130 870,110', fill='none')
    for cx, cy, a in [(650, 450, 30), (820, 420, -20), (720, 600, 60), (870, 560, 10), (620, 580, -40)]:
        s.rect(cx - 28, cy - 9, 56, 18, rx=9, transform=f'rotate({a} {cx} {cy})')
    return s


@page('easy_sailboat', 'Sailboat', 'Easy', 1, 'boat sea sail kids')
def easy_sailboat():
    s = Svg(PW, PH, 10)
    sun(s, 250, 250, 120, 10, 100, 65)
    cloud(s, 1100, 300, 300, 10)
    bird(s, 800, 400, 45)
    bird(s, 900, 350, 35)
    s.path(wave_band_d(-10, PW + 10, 1450, 30, 280, PH + 10))
    s.path(wave_band_d(-10, PW + 10, 1620, 30, 240, PH + 10, 1.5))
    s.path(wave_band_d(-10, PW + 10, 1800, 30, 300, PH + 10, 3.0))
    # boat
    s.path('M300,1400 L1200,1400 L1050,1560 L450,1560 Z')
    s.rect(730, 600, 30, 800)
    s.polygon([(760, 620), (1150, 1360), (760, 1360)])
    s.polygon([(715, 700), (380, 1360), (715, 1360)])
    s.polygon([(760, 600), (900, 650), (760, 700)])
    s.circle(850, 1480, 25)
    s.circle(950, 1480, 25)
    # fish
    s.path('M300,1700 C350,1640 450,1640 500,1700 C450,1760 350,1760 300,1700 Z')
    s.path('M300,1700 L250,1660 L250,1740 Z')
    s.circle(460, 1690, 8)
    return s


@page('easy_whale', 'Happy Whale', 'Easy', 1, 'whale ocean sea kids')
def easy_whale():
    s = Svg(PW, PH, 10)
    sun(s, 1280, 230, 120, 10, 100, 65)
    cloud(s, 350, 300, 320, 10)
    s.path(wave_band_d(-10, PW + 10, 1500, 30, 300, PH + 10))
    s.path(wave_band_d(-10, PW + 10, 1700, 30, 260, PH + 10, 2.0))
    # spout
    s.path('M700,700 Q650,500 500,450', fill='none')
    s.path('M700,700 Q750,500 900,450', fill='none')
    s.path('M700,700 L700,480', fill='none')
    for x, y in [(480, 420), (700, 440), (920, 420)]:
        s.path(f'M{P(x, y - 40)} C{P(x + 35, y)} {P(x + 30, y + 30)} {P(x, y + 30)} C{P(x - 30, y + 30)} {P(x - 35, y)} {P(x, y - 40)} Z')
    # tail
    s.path('M1100,1200 C1200,1050 1300,1000 1400,1050 C1350,1100 1340,1150 1360,1200 C1300,1180 1200,1230 1100,1320 Z')
    # body
    s.path('M700,700 C350,700 200,950 250,1250 C300,1500 600,1600 900,1550 C1150,1500 1250,1300 1150,1150 C1050,1000 1000,800 700,700 Z')
    s.path('M300,1000 Q500,1300 800,1500', fill='none')
    s.circle(400, 1000, 35)
    s.circle(412, 990, 12)
    s.path('M300,1150 Q400,1250 550,1230', fill='none')
    s.path('M650,1200 C750,1150 900,1200 950,1300 C850,1300 700,1300 650,1200 Z')
    for x, y, r in [(1050, 800, 25), (1150, 650, 18), (1000, 620, 15)]:
        s.circle(x, y, r)
    return s


@page('easy_dino', 'Friendly Dino', 'Easy', 1, 'dinosaur dino kids')
def easy_dino():
    s = Svg(PW, PH, 10)
    sun(s, 250, 250, 120, 10, 100, 65)
    cloud(s, 1100, 320, 300, 10)
    hills(s, 1500, [(1200, 700, 250), (300, 600, 200)])
    ground(s, 1650)
    # volcano
    s.path('M900,1500 L1100,1000 L1300,1500 Z')
    s.path('M1060,1000 Q1100,960 1140,1000 Q1120,1050 1060,1000 Z')
    # legs back
    s.rect(560, 1400, 110, 260, rx=40)
    s.rect(900, 1400, 110, 260, rx=40)
    # tail
    s.path('M400,1250 C250,1200 100,1300 150,1450 C200,1350 300,1350 420,1380 Z')
    # body
    s.ellipse(680, 1300, 330, 200)
    # neck + head
    s.path('M820,1150 C850,900 900,700 1000,600 L1080,660 C1000,800 950,1000 950,1200 Z')
    s.ellipse(1050, 580, 140, 100)
    s.circle(1100, 560, 22)
    s.circle(1108, 552, 8)
    s.path('M1120,620 Q1150,640 1180,620', fill='none')
    # legs front
    s.rect(500, 1420, 110, 260, rx=40)
    s.rect(840, 1420, 110, 260, rx=40)
    # spots
    for x, y, r in [(600, 1250, 40), (720, 1350, 35), (800, 1230, 28), (560, 1360, 22)]:
        s.circle(x, y, r)
    # back plates
    for x, y in [(500, 1130), (640, 1090), (780, 1090)]:
        s.path(f'M{P(x - 50, y + 20)} L{P(x, y - 90)} L{P(x + 50, y + 20)} Z')
    for x in (200, 1400):
        stem(s, x, 1800, x, 1700, 10)
        flower_simple(s, x, 1700, 40, 5)
    return s


@page('easy_rainbow', 'Rainbow Sky', 'Easy', 1, 'rainbow clouds sun kids')
def easy_rainbow():
    s = Svg(PW, PH, 10)
    cx, cy = 750, 1500
    for r in (680, 600, 520, 440, 360, 280):
        s.path(f'M{P(cx - r, cy)} A{r} {r} 0 0 1 {P(cx + r, cy)} L{P(cx + r - 80, cy)} A{r - 80} {r - 80} 0 0 0 {P(cx - r + 80, cy)} Z')
    s.rect(-10, 1500, PW + 20, 520)
    cloud(s, 150, 1480, 300, 10)
    cloud(s, 1350, 1480, 300, 10)
    sun(s, 750, 320, 140, 12, 100, 70)
    for x, y in [(300, 500, ), (1200, 450), (250, 950), (1250, 1000)]:
        s.path(heart_d(x, y, 130))
    for x in (400, 750, 1100):
        stem(s, x, 1800, x, 1680, 12)
        flower_simple(s, x, 1680, 45, 6)
    return s


@page('stained_glass', 'Stained Glass', 'Patterns', 2, 'glass window mosaic')
def stained_glass():
    s = Svg(PW, PH, 8)
    rnd = random.Random(99)
    sites = [(rnd.uniform(80, PW - 80), rnd.uniform(80, PH - 80)) for _ in range(70)]

    def clip_poly(poly, ax, ay, bx, by):
        # keep points closer to a than b
        mx, my = (ax + bx) / 2, (ay + by) / 2
        nx, ny = bx - ax, by - ay
        out = []
        n = len(poly)
        for i in range(n):
            p, q = poly[i], poly[(i + 1) % n]
            dp = (p[0] - mx) * nx + (p[1] - my) * ny
            dq = (q[0] - mx) * nx + (q[1] - my) * ny
            if dp <= 0:
                out.append(p)
            if (dp <= 0) != (dq <= 0):
                t = dp / (dp - dq)
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        return out

    # arch window outline
    arch = [(60, PH - 60), (60, 700)]
    for k in range(0, 61):
        arch.append(pol(PW / 2, 700, PW / 2 - 60, 180 + k * 3))
    arch.append((PW - 60, PH - 60))
    for i, (sx, sy) in enumerate(sites):
        poly = arch[:]
        for j, (tx, ty) in enumerate(sites):
            if i == j:
                continue
            poly = clip_poly(poly, sx, sy, tx, ty)
            if not poly:
                break
        if len(poly) >= 3:
            s.polygon(poly)
    s.path('M' + ' L'.join(P(x, y) for x, y in arch) + ' Z', fill='none')
    s.rect(20, 20, PW - 40, PH - 40, rx=30, fill='none')
    return s


@page('rose_window', 'Rose Window', 'Mandalas', 3, 'glass circle window cathedral')
def rose_window():
    s = Svg(SQ, SQ, 6)
    cx = cy = SQ / 2
    s.circle(cx, cy, 860)
    s.circle(cx, cy, 800)
    for i in range(24):
        x, y = pol(cx, cy, 830, i * 15)
        s.circle(x, y, 18)
    for i in range(12):
        s.path(petal_d(cx, cy, i * 30, 420, 800, 230, 0.9))
        s.path(petal_d(cx, cy, i * 30, 460, 720, 110, 0.7))
        x, y = pol(cx, cy, 560, i * 30)
        s.circle(x, y, 40)
    for i in range(12):
        x, y = pol(cx, cy, 730, i * 30 + 15)
        s.circle(x, y, 55)
    s.circle(cx, cy, 430)
    for i in range(8):
        s.path(petal_d(cx, cy, i * 45, 160, 430, 190, 0.9))
        s.path(petal_d(cx, cy, i * 45, 190, 360, 80, 0.7))
    s.circle(cx, cy, 170)
    s.polygon(star_pts(cx, cy, 8, 165, 90))
    s.circle(cx, cy, 55)
    return s



# ----------------------------------------------------------------- extra helpers (anime & nature)

def quad_pts(p0, p1, p2, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        out.append((mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0], mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]))
    return out


def cubic_pts(p0, p1, p2, p3, n=30):
    out = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        out.append((mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                    mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def ribbon_d(pts, w0, w1):
    """Closed outline around a polyline whose half-width tapers from w0 to w1."""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        ax, ay = pts[max(i - 1, 0)]
        bx, by = pts[min(i + 1, n - 1)]
        dx, dy = bx - ax, by - ay
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        w = w0 + (w1 - w0) * i / (n - 1)
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return 'M' + ' L'.join(P(x, y) for x, y in left) + ' ' + ' L'.join(P(x, y) for x, y in reversed(right)) + ' Z'


def spike_d(cx, cy, ang, r_in, r_out, width, curl=0.0):
    """Pointed hair spike / leaf blade from radius r_in to r_out around (cx, cy)."""
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    w = width / 2
    bx, by = cx + ux * r_in, cy + uy * r_in
    tx, ty = cx + ux * r_out + nx * curl, cy + uy * r_out + ny * curl
    mid = r_in + (r_out - r_in) * 0.5
    c1 = (cx + ux * mid + nx * (w * 0.9 + curl * 0.3), cy + uy * mid + ny * (w * 0.9 + curl * 0.3))
    c2 = (cx + ux * mid - nx * (w * 0.9 - curl * 0.3), cy + uy * mid - ny * (w * 0.9 - curl * 0.3))
    return (f'M{P(bx + nx * w, by + ny * w)} Q{P(*c1)} {P(tx, ty)} Q{P(*c2)} {P(bx - nx * w, by - ny * w)} Z')


def anime_eye(s, cx, cy, w, h, sharp=False, lash_out=1):
    """Big anime eye: white, thick upper lash, iris, pupil and two highlights."""
    top = 0.42 if sharp else 0.5
    white = (f'M{P(cx - w / 2, cy - h * 0.05)} C{P(cx - w / 2, cy - h * top)} {P(cx + w / 2, cy - h * top)} {P(cx + w / 2, cy - h * 0.05)} '
             f'C{P(cx + w / 2, cy + h * 0.35)} {P(cx + w * 0.25, cy + h * 0.5)} {P(cx, cy + h * 0.5)} '
             f'C{P(cx - w * 0.25, cy + h * 0.5)} {P(cx - w / 2, cy + h * 0.35)} {P(cx - w / 2, cy - h * 0.05)} Z')
    s.path(white)
    cid = s.clip(white)
    s.begin(clip=cid)
    s.ellipse(cx, cy + h * 0.06, w * 0.34, h * 0.4)
    s.ellipse(cx, cy + h * 0.1, w * 0.15, h * 0.2)
    s.end()
    s.circle(cx - w * 0.14, cy - h * 0.14, w * 0.11)
    s.circle(cx + w * 0.16, cy + h * 0.22, w * 0.05)
    # upper lash as a crescent, thicker toward the outer corner
    ox = cx + lash_out * w * 0.08
    lash = (f'M{P(cx - w / 2 - 10, cy - h * 0.02)} C{P(cx - w / 2 - 6, cy - h * (top + 0.16))} {P(ox + w / 2 + 6, cy - h * (top + 0.2))} {P(cx + w / 2 + 12, cy - h * 0.02)} '
            f'C{P(cx + w / 2, cy - h * top)} {P(cx - w / 2, cy - h * top)} {P(cx - w / 2 - 10, cy - h * 0.02)} Z')
    s.path(lash)
    # lower lash hint
    s.path(f'M{P(cx + w * 0.2, cy + h * 0.5)} Q{P(cx + w * 0.45, cy + h * 0.47)} {P(cx + w * 0.55, cy + h * 0.36)}', fill='none')


def hair_fringe_d(x0, x1, top_y, tips, valley_y):
    """Front hair: an arc over the head from (x0, y) to (x1, y) and a zig-zag fringe of pointed strands back."""
    y_side = tips[0][1] - 40
    d = f'M{P(x0, y_side)} C{P(x0, top_y)} {P(x1, top_y)} {P(x1, y_side)} '
    prev = (x1, y_side)
    for tx, ty in reversed(tips):
        vx = (prev[0] + tx) / 2
        d += f'Q{P(vx, valley_y)} {P(tx, ty)} '
        prev = (tx, ty)
    d += f'Q{P((prev[0] + x0) / 2, valley_y)} {P(x0, y_side)} Z'
    return d


def pine(s, x, y, h, w):
    s.rect(x - w * 0.08, y - h * 0.15, w * 0.16, h * 0.2)
    for i in range(3):
        top = y - h + i * h * 0.22
        base = y - h * 0.62 + i * h * 0.24
        hw = w * (0.45 + i * 0.25)
        s.path(f'M{P(x, top)} L{P(x + hw, base)} Q{P(x, base - h * 0.04)} {P(x - hw, base)} Z')


def mountain(s, left, peak, right, snow=0.22, zig=4):
    s.polygon([left, peak, right])
    if snow:
        lp = (peak[0] + (left[0] - peak[0]) * snow, peak[1] + (left[1] - peak[1]) * snow)
        rp = (peak[0] + (right[0] - peak[0]) * snow, peak[1] + (right[1] - peak[1]) * snow)
        pts = [lp]
        for i in range(1, zig * 2):
            t = i / (zig * 2)
            x = lp[0] + (rp[0] - lp[0]) * t
            y = lp[1] + (rp[1] - lp[1]) * t + (28 if i % 2 else -22)
            pts.append((x, y))
        pts.append(rp)
        s.polygon(pts + [peak])


def rock(s, cx, cy, rx, ry, seed=0):
    rnd = random.Random(seed)
    pts = []
    n = 9
    for i in range(n):
        a = i * 360 / n
        r = rnd.uniform(0.8, 1.1)
        pts.append(pol(cx, cy, 1, a))
        pts[-1] = (cx + (pts[-1][0] - cx) * rx * r, cy + (pts[-1][1] - cy) * ry * r)
    s.polygon(pts)


def bush(s, cx, cy, w, n=5, seed=0):
    rnd = random.Random(seed)
    cs = [(cx + (i - (n - 1) / 2) * w / (n - 1) * 0.9, cy - rnd.uniform(0, w * 0.12), w * rnd.uniform(0.2, 0.3)) for i in range(n)]
    union_circles(s, cs)


def fern(s, x, y, ang, ln, side=1):
    tip = pol(x, y, ln, ang)
    s.path(leaf_d(x, y, tip[0], tip[1], ln * 0.22))
    cid = s.clip(leaf_d(x, y, tip[0], tip[1], ln * 0.22))
    s.begin(clip=cid)
    s.line(x, y, tip[0], tip[1])
    for i in range(1, 7):
        t = i / 7
        px, py = x + (tip[0] - x) * t, y + (tip[1] - y) * t
        for sg in (-1, 1):
            e = pol(px, py, ln * 0.2, ang + sg * 55)
            s.line(px, py, e[0], e[1])
    s.end()


def tulip(s, x, y, h, w):
    stem(s, x, y + h, x, y, 10)
    leaf(s, x, y + h * 0.7, x - w * 1.2, y + h * 0.25, w * 0.35)
    s.path(f'M{P(x - w / 2, y)} C{P(x - w * 0.6, y - h * 0.25)} {P(x - w * 0.4, y - h * 0.45)} {P(x - w * 0.45, y - h * 0.5)} '
           f'Q{P(x - w * 0.15, y - h * 0.3)} {P(x, y - h * 0.55)} Q{P(x + w * 0.15, y - h * 0.3)} {P(x + w * 0.45, y - h * 0.5)} '
           f'C{P(x + w * 0.4, y - h * 0.45)} {P(x + w * 0.6, y - h * 0.25)} {P(x + w / 2, y)} Z')


def rose(s, x, y, r):
    s.circle(x, y, r)
    cid = s.clip(f'M{P(x, y)} m{f(-r)},0 a{f(r)},{f(r)} 0 1,0 {f(2 * r)},0 a{f(r)},{f(r)} 0 1,0 {f(-2 * r)},0 Z')
    s.begin(clip=cid)
    for k, rr in enumerate([r * 0.78, r * 0.56, r * 0.36, r * 0.18]):
        s.circle(x + (rr * 0.25 if k % 2 else -rr * 0.2), y - rr * 0.15, rr)
    s.end()
    for ang in (120, 60):
        tipx, tipy = pol(x, y + r * 0.6, r * 1.3, ang)
        s.path(leaf_d(x, y + r * 0.8, tipx, tipy, r * 0.4))


def bluebell(s, x, y, h):
    stem(s, x, y + h, x + 20, y, 8, curve=-20)
    for i in range(4):
        by = y + h * 0.15 + i * h * 0.2
        bx = x + 12 + (i % 2) * 30 - 15
        s.line(bx, by, bx + 25, by + 8)
        s.path(f'M{P(bx + 25, by + 8)} C{P(bx + 50, by)} {P(bx + 60, by + 30)} {P(bx + 62, by + 45)} '
               f'L{P(bx + 50, by + 40)} L{P(bx + 40, by + 50)} L{P(bx + 30, by + 40)} L{P(bx + 20, by + 48)} '
               f'C{P(bx + 15, by + 30)} {P(bx + 10, by + 10)} {P(bx + 25, by + 8)} Z')


def butterfly_small(s, cx, cy, sz, rot=0):
    s.begin(transform=f'translate({f(cx)} {f(cy)}) rotate({rot})')
    for sg in (-1, 1):
        s.ellipse(sg * sz * 0.55, -sz * 0.35, sz * 0.5, sz * 0.4, rot=sg * -25)
        s.ellipse(sg * sz * 0.45, sz * 0.35, sz * 0.38, sz * 0.32, rot=sg * 20)
    s.ellipse(0, 0, sz * 0.1, sz * 0.5)
    s.line(-sz * 0.05, -sz * 0.5, -sz * 0.3, -sz * 0.9)
    s.line(sz * 0.05, -sz * 0.5, sz * 0.3, -sz * 0.9)
    s.end()


def maple_leaf_d(cx, cy, sc, rot=0):
    pts = [(0, -100), (12, -70), (40, -85), (35, -55), (70, -60), (55, -30), (95, -25), (70, 0), (85, 30), (50, 22),
           (55, 55), (25, 35), (15, 70), (0, 45), (-15, 70), (-25, 35), (-55, 55), (-50, 22), (-85, 30), (-70, 0),
           (-95, -25), (-55, -30), (-70, -60), (-35, -55), (-40, -85), (-12, -70)]
    a = math.radians(rot)
    out = []
    for x, y in pts:
        xr = x * math.cos(a) - y * math.sin(a)
        yr = x * math.sin(a) + y * math.cos(a)
        out.append((cx + xr * sc, cy + yr * sc))
    return 'M' + ' L'.join(P(x, y) for x, y in out) + ' Z'


def kawaii_face(s, cx, cy, w, mouth='smile'):
    s.circle(cx - w * 0.28, cy, w * 0.06, fill='black')
    s.circle(cx + w * 0.28, cy, w * 0.06, fill='black')
    s.ellipse(cx - w * 0.45, cy + w * 0.18, w * 0.12, w * 0.06)
    s.ellipse(cx + w * 0.45, cy + w * 0.18, w * 0.12, w * 0.06)
    if mouth == 'smile':
        s.path(f'M{P(cx - w * 0.1, cy + w * 0.12)} Q{P(cx, cy + w * 0.26)} {P(cx + w * 0.1, cy + w * 0.12)}', fill='none')
    elif mouth == 'cat':
        s.path(f'M{P(cx - w * 0.14, cy + w * 0.12)} Q{P(cx - w * 0.07, cy + w * 0.24)} {P(cx, cy + w * 0.14)} Q{P(cx + w * 0.07, cy + w * 0.24)} {P(cx + w * 0.14, cy + w * 0.12)}', fill='none')
    else:
        s.ellipse(cx, cy + w * 0.17, w * 0.07, w * 0.09)


# ----------------------------------------------------------------- anime pages

@page('anime_girl', 'Sakura Dreams', 'Anime', 3, 'anime girl manga portrait sakura blossom')
def anime_girl():
    s = Svg(PW, PH, 6)
    rnd = random.Random(12)
    for _ in range(16):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(60, PH - 60)
        if 330 < x < 1170 and 280 < y < 1750:
            continue
        flower_simple(s, x, y, rnd.uniform(28, 55), 5)
    for _ in range(12):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(60, 1900)
        if 330 < x < 1170 and 280 < y < 1750:
            continue
        star(s, x, y, rnd.uniform(18, 40), 4, 0.35)
    # back hair
    tips = [(300, 1480), (430, 1600), (560, 1660), (690, 1620), (820, 1660), (950, 1600), (1080, 1560), (1200, 1480)]
    d = f'M{P(1060, 760)} C{P(1060, 440)} {P(440, 440)} {P(440, 760)} C{P(420, 950)} {P(360, 1200)} {P(300, 1480)} '
    prev = tips[0]
    for tx, ty in tips[1:]:
        d += f'Q{P((prev[0] + tx) / 2, min(prev[1], ty) - 170)} {P(tx, ty)} '
        prev = (tx, ty)
    d += f'C{P(1140, 1200)} {P(1080, 950)} {P(1060, 760)} Z'
    s.path(d)
    for sx, ex, ey in [(560, 440, 1560), (640, 600, 1600), (860, 900, 1600), (940, 1060, 1520)]:
        s.path(f'M{P(sx, 520)} C{P(sx - 60, 900)} {P(ex + 40, 1200)} {P(ex, ey)}', fill='none')
    # body and uniform
    s.path('M400,1440 C440,1330 600,1290 700,1290 L800,1290 C900,1290 1060,1330 1100,1440 L1150,2010 L350,2010 Z')
    s.path('M700,1290 L540,1340 L690,1540 Z')
    s.path('M800,1290 L960,1340 L810,1540 Z')
    s.path('M700,1290 Q750,1380 800,1290 L810,1540 L690,1540 Z')
    s.path('M690,1540 L580,1480 L590,1600 Z')
    s.path('M810,1540 L920,1480 L910,1600 Z')
    s.ellipse(750, 1545, 34, 28)
    s.path('M730,1570 L690,1740 L745,1700 Z')
    s.path('M770,1570 L810,1740 L755,1700 Z')
    # neck and face
    s.path('M698,1140 L706,1330 L794,1330 L802,1140 Z')
    s.path('M520,740 C515,960 600,1150 750,1190 C900,1150 985,960 980,740 C980,520 870,440 750,440 C630,440 520,520 520,740 Z')
    s.ellipse(518, 900, 22, 40)
    s.ellipse(982, 900, 22, 40)
    anime_eye(s, 652, 905, 140, 150, lash_out=-1)
    anime_eye(s, 848, 905, 140, 150, lash_out=1)
    s.path(leaf_d(582, 792, 712, 772, 9))
    s.path(leaf_d(788, 772, 918, 792, 9))
    s.path('M757,1010 Q773,1034 756,1048', fill='none')
    s.path('M712,1092 Q750,1130 788,1092 Q750,1112 712,1092 Z')
    s.ellipse(585, 1000, 40, 18)
    s.ellipse(915, 1000, 40, 18)
    # front hair
    fringe = hair_fringe_d(470, 1030, 470, [(530, 840), (610, 870), (690, 810), (770, 880), (850, 830), (940, 870)], 700)
    s.path(fringe)
    s.path('M760,480 C700,600 640,720 612,860', fill='none')
    s.path('M790,480 C820,620 870,720 935,860', fill='none')
    s.path(ribbon_d(cubic_pts((490, 720), (430, 900), (470, 1100), (430, 1280)), 44, 6))
    s.path(ribbon_d(cubic_pts((1010, 720), (1070, 900), (1030, 1100), (1070, 1280)), 44, 6))
    # hair bow
    s.ellipse(960, 560, 62, 36, rot=-30)
    s.ellipse(1062, 560, 62, 36, rot=30)
    s.path('M1000,590 L950,720 L1010,700 Z')
    s.path('M1022,590 L1072,720 L1012,700 Z')
    s.circle(1011, 578, 22)
    return s


@page('anime_boy', 'Hero Spirit', 'Anime', 3, 'anime boy manga hero headband spiky hair')
def anime_boy():
    s = Svg(PW, PH, 6)
    cx, cy = 750, 900
    for ang in range(0, 360, 12):
        x1, y1 = pol(cx, cy, 720, ang)
        x2, y2 = pol(cx, cy, 1400, ang)
        s.line(x1, y1, x2, y2)
    # back spikes
    rnd = random.Random(5)
    for ang in list(range(195, 350, 14)):
        s.path(spike_d(750, 700, ang, 200, rnd.uniform(430, 560), 130, curl=rnd.uniform(-30, 30)))
    for ang in (160, 176, 4, 20):
        s.path(spike_d(750, 760, ang, 200, 380, 110))
    # body
    s.path('M380,1470 C430,1340 600,1300 700,1300 L800,1300 C900,1300 1070,1340 1120,1470 L1160,2010 L340,2010 Z')
    s.path('M700,1300 L630,1230 L540,1420 L700,1480 Z')
    s.path('M800,1300 L870,1230 L960,1420 L800,1480 Z')
    s.rect(740, 1480, 20, 540)
    s.path('M698,1140 L706,1330 L794,1330 L802,1140 Z')
    # face
    s.path('M530,760 C525,980 615,1170 750,1200 C885,1170 975,980 970,760 C970,540 870,450 750,450 C630,450 530,540 530,760 Z')
    s.ellipse(528, 900, 22, 40)
    s.ellipse(972, 900, 22, 40)
    anime_eye(s, 652, 910, 130, 120, sharp=True, lash_out=-1)
    anime_eye(s, 848, 910, 130, 120, sharp=True, lash_out=1)
    s.path(leaf_d(585, 790, 720, 822, 16))
    s.path(leaf_d(780, 822, 915, 790, 16))
    s.path('M757,1010 Q773,1034 756,1048', fill='none')
    s.path('M700,1090 Q752,1142 812,1082 Q760,1110 700,1090 Z')
    # front spikes
    fringe = hair_fringe_d(480, 1020, 460, [(540, 860), (620, 900), (700, 840), (780, 910), (860, 850), (940, 890)], 640)
    s.path(fringe)
    s.path('M720,470 C690,600 650,720 625,890', fill='none')
    s.path('M800,470 C830,620 850,740 858,840', fill='none')
    # headband over the fringe
    s.path('M500,700 C600,640 900,640 1000,700 L1000,772 C900,712 600,712 500,772 Z')
    s.path(ribbon_d(cubic_pts((1000, 735), (1120, 700), (1180, 800), (1300, 760)), 30, 8))
    s.path(ribbon_d(cubic_pts((1000, 745), (1100, 820), (1130, 900), (1250, 950)), 30, 8))
    s.circle(1000, 735, 26)
    for tx, ty in [(620, 760), (760, 790), (900, 760)]:
        s.path(spike_d(tx, 640, 90, 0, ty - 640 + 60, 70))
    return s


@page('chibi_cat', 'Chibi Cat Girl', 'Anime', 2, 'chibi cat girl kawaii anime cute neko')
def chibi_cat():
    s = Svg(PW, PH, 6)
    rnd = random.Random(3)
    for _ in range(18):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(60, PH - 60)
        if 380 < x < 1120 and 220 < y < 1600:
            continue
        if rnd.random() < 0.6:
            s.path(heart_d(x, y, rnd.uniform(50, 90)))
        else:
            s.circle(x, y, rnd.uniform(28, 40))
            for k in range(4):
                px, py = pol(x, y - 10, rnd.uniform(28, 40) + 24, 200 + k * 45)
                s.circle(px, py, 11)
    # tail
    s.path(ribbon_d(cubic_pts((930, 1330), (1180, 1300), (1260, 1050), (1120, 920)), 34, 20))
    s.circle(1120, 920, 30)
    # legs and shoes
    for lx in (690, 810):
        s.rect(lx - 42, 1340, 84, 170, rx=30)
        s.ellipse(lx, 1530, 62, 34)
    # dress
    s.path('M640,1030 L590,1370 L910,1370 L860,1030 Z')
    s.path('M590,1370 Q750,1410 910,1370 Q750,1440 590,1370 Z')
    s.path('M690,1030 Q750,1120 810,1030 Z')
    # arms up with paws
    s.path(ribbon_d(cubic_pts((655, 1080), (580, 1050), (530, 980), (520, 920)), 30, 24))
    s.path(ribbon_d(cubic_pts((845, 1080), (920, 1050), (970, 980), (980, 920)), 30, 24))
    for px in (515, 985):
        s.circle(px, 890, 48)
        for k in (-1, 0, 1):
            s.circle(px + k * 30, 850, 15)
        s.ellipse(px, 905, 22, 16)
    # head
    s.path('M460,520 L410,280 L640,420 Z')
    s.path('M1040,520 L1090,280 L860,420 Z')
    s.path('M490,500 L460,350 L610,440 Z')
    s.path('M1010,500 L1040,350 L890,440 Z')
    s.path('M450,700 C450,950 600,1050 750,1050 C900,1050 1050,950 1050,700 C1050,480 920,400 750,400 C580,400 450,480 450,700 Z')
    anime_eye(s, 640, 770, 175, 190, lash_out=-1)
    anime_eye(s, 860, 770, 175, 190, lash_out=1)
    s.path('M740,900 L760,900 L750,915 Z')
    s.path('M690,930 Q720,975 750,935 Q780,975 810,930', fill='none')
    s.ellipse(560, 880, 45, 20)
    s.ellipse(940, 880, 45, 20)
    for sg in (-1, 1):
        for dy in (-15, 15):
            s.line(750 + sg * 330, 860 + dy, 750 + sg * 400, 850 + dy * 2.2)
    fringe = hair_fringe_d(440, 1060, 400, [(500, 640), (590, 700), (680, 640), (770, 720), (860, 650), (960, 700)], 540)
    s.path(fringe)
    s.path('M700,430 C660,520 630,600 600,690', fill='none')
    s.path('M820,430 C850,540 870,620 880,650', fill='none')
    s.path(ribbon_d(cubic_pts((470, 620), (420, 760), (440, 880), (420, 1000)), 40, 8))
    s.path(ribbon_d(cubic_pts((1030, 620), (1080, 760), (1060, 880), (1080, 1000)), 40, 8))
    # collar with bell
    s.path('M560,1040 Q750,1120 940,1040 Q750,1160 560,1040 Z')
    s.circle(750, 1130, 34)
    s.line(750, 1130, 750, 1160)
    return s


@page('magical_girl', 'Starlight Magic', 'Anime', 3, 'anime magical girl wand stars moon')
def magical_girl():
    s = Svg(PW, PH, 6)
    rnd = random.Random(9)
    for _ in range(16):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(60, PH - 60)
        if 330 < x < 1170 and 250 < y < 1850:
            continue
        star(s, x, y, rnd.uniform(18, 45), rnd.choice([4, 5]), 0.4)
    s.circle(300, 330, 170)
    cid = s.clip('M300,330 m-170,0 a170,170 0 1,0 340,0 a170,170 0 1,0 -340,0 Z')
    s.begin(clip=cid)
    s.circle(380, 290, 150)
    s.end()
    # magic circle behind
    s.circle(750, 1050, 560, fill='none')
    s.circle(750, 1050, 520, fill='none')
    s.polygon(star_pts(750, 1050, 5, 520, 200), fill='none')
    # twin tails
    s.path(ribbon_d(cubic_pts((560, 520), (380, 600), (330, 900), (390, 1180)), 60, 10))
    s.path(ribbon_d(cubic_pts((940, 520), (1120, 600), (1170, 900), (1110, 1180)), 60, 10))
    # legs & boots
    for lx in (700, 800):
        s.rect(lx - 36, 1380, 72, 220, rx=25)
        s.path(f'M{P(lx - 42, 1560)} L{P(lx - 42, 1700)} Q{P(lx, 1740)} {P(lx + 60, 1700)} L{P(lx + 42, 1560)} Z')
    # skirt
    s.path('M650,960 Q520,1180 440,1400 Q750,1470 1060,1400 Q980,1180 850,960 Z')
    pts = [(440 + i * 62, 1400 + (18 if i % 2 else 0) + 30 * math.sin(i * 0.3)) for i in range(11)]
    s.path('M' + ' L'.join(P(x, y) for x, y in pts), fill='none')
    for k in (-2, -1, 0, 1, 2):
        s.path(f'M{P(750 + k * 45, 980)} Q{P(750 + k * 110, 1200)} {P(750 + k * 140, 1400)}', fill='none')
    # bodice
    s.path('M680,760 L650,980 L850,980 L820,760 Z')
    s.path('M680,800 Q750,880 820,800', fill='none')
    s.path(heart_d(750, 880, 60))
    # arms
    s.path(ribbon_d(cubic_pts((690, 800), (600, 760), (540, 680), (510, 600)), 26, 22))
    s.path(ribbon_d(cubic_pts((810, 800), (880, 900), (900, 1000), (880, 1100)), 26, 22))
    s.circle(505, 585, 34)
    s.circle(882, 1115, 34)
    # wand
    s.path(ribbon_d([(505, 600), (420, 330)], 12, 12))
    star(s, 400, 270, 80, 5, 0.45)
    s.circle(400, 270, 18)
    for k in range(3):
        px, py = pol(400, 270, 130, -30 + k * 70)
        star(s, px, py, 20, 4, 0.35)
    # head
    s.path('M700,660 L706,790 L794,790 L800,660 Z')
    s.path('M520,560 C520,740 620,830 750,830 C880,830 980,740 980,560 C980,400 880,320 750,320 C620,320 520,400 520,560 Z')
    anime_eye(s, 665, 600, 130, 140, lash_out=-1)
    anime_eye(s, 835, 600, 130, 140, lash_out=1)
    s.path('M722,700 Q750,735 778,700 Q750,718 722,700 Z')
    s.ellipse(600, 680, 36, 16)
    s.ellipse(900, 680, 36, 16)
    fringe = hair_fringe_d(500, 1000, 290, [(560, 520), (640, 560), (720, 500), (800, 570), (880, 520), (950, 560)], 430)
    s.path(fringe)
    s.path('M700,330 C670,420 640,480 622,550', fill='none')
    for bx in (560, 940):
        s.ellipse(bx - 30, 500, 36, 22, rot=-30)
        s.ellipse(bx + 30, 500, 36, 22, rot=30)
        s.circle(bx, 505, 14)
    return s


@page('kawaii_food', 'Kawaii Snacks', 'Anime', 1, 'kawaii food cute faces sushi boba onigiri')
def kawaii_food():
    s = Svg(PW, PH, 7)
    rnd = random.Random(2)
    for _ in range(30):
        s.circle(rnd.uniform(40, PW - 40), rnd.uniform(40, PH - 40), rnd.uniform(6, 14))
    # onigiri
    s.path('M300,300 C330,300 440,460 440,520 C440,560 400,570 300,570 C200,570 160,560 160,520 C160,460 270,300 300,300 Z')
    s.rect(250, 470, 100, 100, rx=8)
    kawaii_face(s, 300, 420, 150)
    # boba tea
    s.path('M660,330 L690,620 L810,620 L840,330 Z')
    s.path('M650,300 L850,300 Q850,340 650,340 Z')
    s.rect(776, 180, 24, 300, rx=8, transform='rotate(12 788 330)')
    for k in range(6):
        s.circle(700 + (k % 3) * 45, 570 + (k // 3) * -40, 17)
    kawaii_face(s, 750, 440, 130)
    # dango
    s.rect(1190, 260, 20, 420, rx=10)
    for i in range(3):
        s.circle(1200, 320 + i * 110, 60)
    kawaii_face(s, 1200, 320, 90, 'o')
    kawaii_face(s, 1200, 430, 90)
    kawaii_face(s, 1200, 540, 90, 'cat')
    # sushi
    s.ellipse(300, 1060, 150, 70)
    s.path('M150,1010 C200,940 400,940 450,1010 C400,1040 200,1040 150,1010 Z')
    for k in range(3):
        s.path(f'M{P(190 + k * 70, 960)} Q{P(220 + k * 70, 990)} {P(190 + k * 70, 1020)}', fill='none')
    kawaii_face(s, 300, 1070, 140)
    # ramen
    s.path('M560,1000 Q750,1030 940,1000 L900,1180 Q750,1220 600,1180 Z')
    s.ellipse(750, 1000, 190, 45)
    cid = s.clip('M750,1000 m-190,0 a190,45 0 1,0 380,0 a190,45 0 1,0 -380,0 Z')
    s.begin(clip=cid)
    for k in range(6):
        s.polyline(wave_pts(560, 940, 985 + k * 8, 6, 60, k))
    s.end()
    s.ellipse(700, 990, 40, 22)
    s.circle(700, 990, 14)
    s.rect(800, 760, 14, 260, rx=6, transform='rotate(-20 807 890)')
    s.rect(840, 760, 14, 260, rx=6, transform='rotate(-15 847 890)')
    kawaii_face(s, 750, 1100, 160)
    # macaron
    s.ellipse(1200, 1010, 150, 60)
    s.ellipse(1200, 1070, 140, 40)
    s.ellipse(1200, 1120, 150, 60)
    s.path('M1050,1010 Q1200,1110 1350,1010', fill='none')
    kawaii_face(s, 1200, 1000, 140)
    # strawberry
    s.path('M300,1500 C400,1500 470,1560 450,1680 C430,1790 340,1880 300,1900 C260,1880 170,1790 150,1680 C130,1560 200,1500 300,1500 Z')
    for k in range(5):
        s.path(leaf_d(300, 1500, *pol(300, 1500, 90, -150 + k * 30), 30))
    for x, y in [(240, 1620), (320, 1600), (380, 1680), (280, 1740), (350, 1780), (220, 1700)]:
        s.ellipse(x, y, 9, 14)
    kawaii_face(s, 300, 1660, 150)
    # pudding
    s.ellipse(750, 1830, 190, 50)
    s.path('M620,1560 L580,1820 L920,1820 L880,1560 Z')
    s.path('M620,1560 Q750,1540 880,1560 L870,1640 Q820,1680 790,1620 Q750,1690 700,1630 Q650,1690 630,1640 Z')
    s.circle(750, 1535, 30)
    kawaii_face(s, 750, 1720, 150)
    # milk carton
    s.path('M1090,1560 L1090,1900 L1310,1900 L1310,1560 L1200,1470 Z')
    s.path('M1090,1560 L1310,1560', fill='none')
    s.path('M1120,1560 L1200,1470 L1280,1560', fill='none')
    s.rect(1180, 1450, 40, 24, rx=6)
    kawaii_face(s, 1200, 1700, 140)
    return s


@page('mecha', 'Mecha Pilot', 'Anime', 3, 'mecha robot anime armor')
def mecha():
    s = Svg(PW, PH, 6)
    r = 70
    rnd = random.Random(8)
    for _ in range(14):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(60, PH - 60)
        if 300 < x < 1200 and 250 < y < 1900:
            continue
        s.polygon([pol(x, y, r * rnd.uniform(0.5, 1), 30 + 60 * k) for k in range(6)], fill='none')
    # shoulders & chest
    for sg in (-1, 1):
        def X(dx):
            return 750 + sg * dx
        s.path(f'M{P(X(300), 1300)} L{P(X(380), 1220)} L{P(X(700), 1300)} L{P(X(740), 1500)} L{P(X(640), 1650)} L{P(X(330), 1560)} Z')
        s.path(f'M{P(X(420), 1320)} L{P(X(650), 1370)} L{P(X(660), 1480)} L{P(X(440), 1430)} Z')
    s.path('M450,1300 L620,1180 L880,1180 L1050,1300 L1000,1700 L900,2010 L600,2010 L500,1700 Z')
    s.path('M560,1700 L940,1700 L880,2010 L620,2010 Z')
    s.circle(750, 1480, 120)
    s.circle(750, 1480, 80)
    s.polygon(star_pts(750, 1480, 3, 60, 25, -90))
    s.path('M520,1360 L640,1360 L680,1600 L560,1600 Z')
    s.path('M980,1360 L860,1360 L820,1600 L940,1600 Z')
    # neck
    s.rect(680, 1080, 140, 130)
    for yy in (1120, 1160):
        s.line(680, yy, 820, yy)
    # helmet
    s.path('M600,520 L560,720 L590,920 L690,1000 L810,1000 L910,920 L940,720 L900,520 L750,460 Z')
    s.path('M750,560 L540,340 L640,580 Z')
    s.path('M750,560 L960,340 L860,580 Z')
    s.path('M700,560 L800,560 L770,640 L730,640 Z')
    s.circle(750, 600, 26)
    s.path('M640,760 L660,920 L750,960 L840,920 L860,760 Z')
    s.path('M655,790 L735,805 L730,845 L660,835 Z')
    s.path('M845,790 L765,805 L770,845 L840,835 Z')
    for yy in (880, 905, 930):
        s.line(700, yy, 800, yy)
    s.path('M690,1000 L750,1060 L810,1000 Z')
    s.path('M560,720 L620,760 L620,880 L590,920 Z')
    s.path('M940,720 L880,760 L880,880 L910,920 Z')
    for sg in (-1, 1):
        s.path(f'M{P(750 + sg * 620, 900)} L{P(750 + sg * 700, 760)} L{P(750 + sg * 760, 1000)} L{P(750 + sg * 690, 1120)} Z')
    return s


# ----------------------------------------------------------------- nature scenes

@page('mountain_lake', 'Mountain Lake', 'Nature', 3, 'mountains lake pine forest canoe')
def mountain_lake():
    s = Svg(PW, PH, 6)
    sun(s, 1230, 250, 90, 12, 70, 45)
    cloud(s, 320, 300, 300)
    cloud(s, 900, 440, 220)
    bird(s, 600, 330, 36)
    bird(s, 680, 290, 28)
    mountain(s, (-100, 1120), (330, 540), (760, 1120))
    mountain(s, (900, 1120), (1250, 640), (1600, 1120))
    mountain(s, (450, 1120), (850, 420), (1250, 1120), zig=5)
    rnd = random.Random(4)
    for row, (y, hmin, hmax) in enumerate([(1130, 150, 220), (1190, 200, 290), (1250, 240, 330)]):
        x = -40 + row * 50
        while x < PW + 60:
            pine(s, x, y, rnd.uniform(hmin, hmax), 110 + row * 15)
            x += rnd.uniform(90, 130)
    # lake with reflections and ripples
    lake = 'M-10,1250 L1510,1250 L1510,1720 L-10,1720 Z'
    s.path(lake)
    cid = s.clip(lake)
    s.begin(clip=cid)
    for left, peak, right in [((-100, 1250), (330, 1250 + 500), (760, 1250)), ((450, 1250), (850, 1250 + 560), (1250, 1250)), ((900, 1250), (1250, 1250 + 420), (1600, 1250))]:
        s.polygon([left, peak, right])
    for k in range(5):
        s.polyline(wave_pts(-10, PW + 10, 1320 + k * 80, 10, 260, k * 1.3))
    s.end()
    s.path('M430,1600 Q620,1700 840,1600 Q630,1650 430,1600 Z')
    s.path('M470,1610 L480,1570 L560,1585', fill='none')
    s.line(600, 1545, 700, 1655)
    s.ellipse(600, 1540, 28, 14, rot=45)
    # foreshore
    s.path(wave_band_d(-10, PW + 10, 1720, 18, 420, PH + 10, 1.0))
    rock(s, 220, 1800, 90, 55, 1)
    rock(s, 1250, 1830, 110, 60, 2)
    rock(s, 1380, 1760, 60, 40, 3)
    for x in (100, 420, 1050, 1150):
        stem(s, x, 1900, x + 10, 1680, 10, curve=15)
        s.ellipse(x + 11, 1665, 16, 50)
    for x in (320, 700, 900, 1450):
        for k in (-1, 0, 1):
            s.path(f'M{P(x + k * 22, 1910)} Q{P(x + k * 38, 1850)} {P(x + k * 50, 1800)}', fill='none')
    return s


@page('forest_path', 'Forest Path', 'Nature', 3, 'forest trees path mushrooms rabbit woods')
def forest_path():
    s = Svg(PW, PH, 6)
    for k in range(3):
        s.path(f'M{P(1150 + k * 130, -10)} L{P(1180 + k * 130, -10)} L{P(620 + k * 170, 1450)} L{P(570 + k * 170, 1450)} Z')
    # background trees
    rnd = random.Random(21)
    for x, h, w in [(450, 1100, 70), (1000, 1200, 80), (650, 900, 55), (1150, 950, 60), (250, 1000, 60)]:
        s.path(ribbon_d([(x, 1450), (x + rnd.uniform(-20, 20), 1450 - h)], w * 0.5, w * 0.3))
        union_circles(s, [(x, 1450 - h, w * 2.4), (x - w * 1.6, 1450 - h + w, w * 1.8), (x + w * 1.6, 1450 - h + w * 0.8, w * 1.8), (x, 1450 - h - w * 1.6, w * 1.8)])
    ground(s, 1450)
    s.path('M700,1450 C600,1600 900,1700 760,1850 C650,1960 520,2000 520,2010 L1120,2010 C1100,1950 1000,1850 940,1780 C800,1650 880,1540 820,1450 Z')
    for x, y, rx, ry in [(700, 1560, 30, 16), (820, 1700, 34, 18), (720, 1820, 28, 14), (900, 1900, 32, 16)]:
        s.ellipse(x, y, rx, ry)
    # foreground trees
    for x, lean in [(170, -40), (1330, 40)]:
        d = ribbon_d(cubic_pts((x, 2010), (x + lean * 0.5, 1300), (x - lean * 0.5, 600), (x + lean, -50)), 110, 70)
        s.path(d)
        cid = s.clip(d)
        s.begin(clip=cid)
        for yy in range(300, 2000, 160):
            s.path(f'M{P(x - 80, yy)} Q{P(x - 20, yy + 50)} {P(x + 20, yy + 100)}', fill='none')
        s.end()
        for by, dirn in [(500, -1), (800, 1), (350, 1)]:
            if (x < 700 and dirn > 0) or (x > 700 and dirn < 0):
                s.path(ribbon_d(cubic_pts((x, by), (x + dirn * 150, by - 60), (x + dirn * 260, by - 90), (x + dirn * 380, by - 200)), 34, 10))
    bush(s, 330, 1460, 260, seed=1)
    bush(s, 1180, 1480, 280, seed=2)
    bush(s, 560, 1480, 180, 4, seed=3)
    fern(s, 1000, 1560, -70, 230)
    fern(s, 1000, 1560, -110, 200)
    fern(s, 1000, 1560, -40, 180)
    fern(s, 330, 1720, -60, 200)
    fern(s, 330, 1720, -120, 180)
    for mx, my, sc in [(470, 1900, 1.0), (560, 1940, 0.7), (1250, 1850, 1.1)]:
        s.rect(mx - 22 * sc, my - 70 * sc, 44 * sc, 80 * sc, rx=12 * sc)
        s.path(f'M{P(mx - 80 * sc, my - 60 * sc)} C{P(mx - 80 * sc, my - 150 * sc)} {P(mx + 80 * sc, my - 150 * sc)} {P(mx + 80 * sc, my - 60 * sc)} Z')
        for dx, dy in [(-35, -100), (10, -120), (40, -85)]:
            s.circle(mx + dx * sc, my + dy * sc, 11 * sc)
    # rabbit
    s.ellipse(1020, 1780, 95, 62)
    s.circle(1105, 1715, 48)
    s.ellipse(1092, 1650, 15, 48, rot=-12)
    s.ellipse(1125, 1652, 15, 48, rot=12)
    s.circle(920, 1770, 22)
    s.circle(1118, 1708, 7)
    s.ellipse(1045, 1830, 30, 14)
    for x in (640, 1120, 1420):
        stem(s, x, 1980, x, 1900, 8)
        flower_simple(s, x, 1900, 30, 5)
    return s


@page('waterfall', 'Hidden Waterfall', 'Nature', 3, 'waterfall jungle cliff rainbow pool')
def waterfall():
    s = Svg(PW, PH, 6)
    sun(s, 230, 230, 100, 12, 80, 50)
    cloud(s, 1100, 260, 260)
    # falls band (trimmed later by the cliffs)
    s.rect(540, 600, 420, 880)
    cid = s.clip('M540,600 h420 v880 h-420 Z')
    s.begin(clip=cid)
    for k in range(7):
        x = 580 + k * 55
        s.path(f'M{P(x, 580)} C{P(x - 20, 900)} {P(x + 25, 1200)} {P(x, 1500)}', fill='none')
    s.end()
    for wall in ('M-10,620 L560,630 L540,800 L590,1000 L540,1200 L600,1400 L-10,1480 Z',
                 'M1510,620 L960,630 L980,800 L930,1000 L990,1200 L930,1400 L1510,1480 Z'):
        s.path(wall)
        cid = s.clip(wall)
        s.begin(clip=cid)
        for k in range(9):
            yy = 680 + k * 95
            s.polyline(wave_pts(-10, PW + 10, yy, 14, 300, k * 0.9))
        for xx in range(100, PW, 230):
            s.path(f'M{P(xx, 640)} Q{P(xx + 40, 900)} {P(xx - 20, 1150)} Q{P(xx + 30, 1300)} {P(xx, 1480)}', fill='none')
        s.end()
    s.path('M-10,620 Q750,560 1510,620 L1510,-10 L-10,-10 Z')
    # rainbow
    for r in (560, 500):
        s.path(f'M{P(750 - r, 1300)} A{r} {r} 0 0 1 {P(750 + r, 1300)} L{P(750 + r - 50, 1300)} A{r - 50} {r - 50} 0 0 0 {P(750 - r + 50, 1300)} Z')
    # pool
    s.path(wave_band_d(-10, PW + 10, 1480, 16, 300, PH + 10))
    union_circles(s, [(560 + k * 70, 1470 + (k % 2) * 18, 40) for k in range(7)])
    for k in range(4):
        s.polyline(wave_pts(-10, PW + 10, 1580 + k * 90, 12, 240, k))
    rock(s, 300, 1600, 120, 60, 7)
    rock(s, 1250, 1620, 130, 60, 8)
    rock(s, 760, 1740, 90, 45, 9)
    # plants
    for x, y, a in [(80, 1480, -60), (80, 1480, -100), (1420, 1480, -120), (1420, 1480, -80), (300, 1540, -75), (1230, 1560, -105)]:
        fern(s, x, y, a, 220)
    for px in (1340, 160):
        for k in range(6):
            tipx, tipy = pol(px, 1900, 260, -150 + k * 24)
            s.path(leaf_d(px, 1900, tipx, tipy, 50))
    cloud(s, 560, 1400, 170)
    cloud(s, 960, 1420, 150)
    return s


@page('beach_sunset', 'Beach Sunset', 'Nature', 2, 'beach palm sunset sea sailboat shells')
def beach_sunset():
    s = Svg(PW, PH, 6)
    s.circle(750, 1080, 240)
    for i in range(12):
        s.path(petal_d(750, 1080, -180 + i * 16.4, 250, 360, 60, 0.3))
    for y, x0, w in [(380, 120, 480), (470, 760, 560), (620, 300, 420), (760, 900, 500)]:
        s.path(f'M{P(x0, y)} Q{P(x0 + w / 2, y - 40)} {P(x0 + w, y)} Q{P(x0 + w / 2, y + 40)} {P(x0, y)} Z')
    s.rect(-10, 1080, PW + 20, 540)
    for k in range(5):
        s.polyline(wave_pts(-10, PW + 10, 1160 + k * 90, 10 + k * 3, 240, k * 0.7))
    # sailboat
    s.path('M980,1230 L1140,1230 L1115,1265 L1005,1265 Z')
    s.rect(1056, 1080, 8, 150)
    s.polygon([(1064, 1090), (1130, 1225), (1064, 1225)])
    s.polygon([(1052, 1110), (1000, 1225), (1052, 1225)])
    bird(s, 300, 500, 40)
    bird(s, 380, 460, 30)
    bird(s, 1250, 300, 38)
    # sand
    s.path(wave_band_d(-10, PW + 10, 1600, 20, 500, PH + 10, 1.5))
    # palm tree
    trunk = ribbon_d(cubic_pts((1250, 2010), (1230, 1500), (1120, 900), (1080, 560)), 55, 30)
    s.path(trunk)
    cid = s.clip(trunk)
    s.begin(clip=cid)
    for t in range(1, 14):
        pt = cubic_pts((1250, 2010), (1230, 1500), (1120, 900), (1080, 560), 14)[t]
        s.path(f'M{P(pt[0] - 70, pt[1])} Q{P(pt[0], pt[1] + 25)} {P(pt[0] + 70, pt[1])}', fill='none')
    s.end()
    for ang, ln in [(-150, 420), (-115, 440), (-70, 400), (-30, 430), (10, 380), (170, 360), (40, 300)]:
        tipx, tipy = pol(1080, 560, ln, ang)
        d = leaf_d(1080, 560, tipx, tipy, ln * 0.2)
        s.path(d)
        s.line(1080, 560, tipx, tipy)
    for cx, cy in [(1050, 600), (1100, 620), (1075, 650)]:
        s.circle(cx, cy, 26)
    # beach things
    s.polygon(star_pts(380, 1800, 5, 110, 55, -90))
    s.circle(380, 1800, 18)
    sh = 'M700,1880 L620,1790 A95,95 0 0 1 780,1790 Z'
    s.path(sh)
    cid = s.clip(sh)
    s.begin(clip=cid)
    for ang in range(-160, -15, 20):
        x2, y2 = pol(700, 1880, 140, ang)
        s.line(700, 1880, x2, y2)
    s.end()
    s.circle(160, 1760, 90)
    cid = s.clip('M160,1760 m-90,0 a90,90 0 1,0 180,0 a90,90 0 1,0 -180,0 Z')
    s.begin(clip=cid)
    for k in (-1, 0, 1):
        s.path(f'M{P(160 + k * 50, 1660)} Q{P(160 + k * 90, 1760)} {P(160 + k * 50, 1860)}', fill='none')
    s.end()
    for x, y, rx, ry in [(950, 1900, 22, 14), (1300, 1950, 28, 16), (560, 1960, 18, 11)]:
        s.ellipse(x, y, rx, ry)
    return s


@page('flower_meadow', 'Flower Meadow', 'Nature', 3, 'flowers garden meadow butterfly bee watering can')
def flower_meadow():
    s = Svg(PW, PH, 6)
    sun(s, 250, 240, 110, 12, 85, 55)
    cloud(s, 900, 300, 300)
    cloud(s, 1300, 520, 200)
    hills(s, 1250, [(300, 700, 220), (1200, 800, 260)])
    ground(s, 1400)
    # fence
    for i in range(9):
        x = 60 + i * 175
        s.path(f'M{P(x, 1420)} L{P(x, 1190)} L{P(x + 28, 1160)} L{P(x + 56, 1190)} L{P(x + 56, 1420)} Z')
    s.rect(30, 1220, 1440, 30)
    s.rect(30, 1320, 1440, 30)
    # bird on the fence
    s.ellipse(760, 1130, 50, 34)
    s.circle(805, 1105, 24)
    s.path('M826,1100 L850,1108 L826,1114 Z')
    s.circle(812, 1100, 5)
    s.path('M712,1120 L660,1095 L705,1140 Z')
    # flowers (back to front)
    for x, h in [(140, 320), (300, 280), (1250, 300), (1400, 260)]:
        stem(s, x, 1750, x, 1750 - h, 12)
        daisy(s, x, 1750 - h, 70, 20, 0.4, double=True)
    for x in (480, 620):
        tulip(s, x, 1520, 230, 90)
    for x in (1080, 1180):
        tulip(s, x, 1560, 200, 80)
    for x, y in [(850, 1480), (960, 1540)]:
        stem(s, x, 1800, x, y + 60, 10)
        rose(s, x, y, 60)
    bluebell(s, 380, 1540, 260)
    bluebell(s, 1320, 1580, 240)
    for x, y, r in [(200, 1700, 45), (560, 1760, 40), (720, 1720, 48), (1000, 1760, 42), (1440, 1740, 38)]:
        stem(s, x, 1960, x, y + 20, 8)
        daisy(s, x, y, r, 12, 0.35)
    for x in (260, 690, 1140, 1360):
        for k in (-1, 0, 1):
            s.path(f'M{P(x + k * 24, 1990)} Q{P(x + k * 40, 1920)} {P(x + k * 50, 1860)}', fill='none')
    butterfly_small(s, 560, 1060, 90, -15)
    butterfly_small(s, 1150, 950, 70, 20)
    # bee
    s.begin(transform='translate(420 980) rotate(-15)')
    s.ellipse(-20, -40, 36, 20, rot=-20)
    s.ellipse(25, -40, 36, 20, rot=20)
    s.ellipse(0, 0, 64, 42)
    cid = s.clip('M-64,0 a64,42 0 1,0 128,0 a64,42 0 1,0 -128,0 Z')
    s.begin(clip=cid)
    for xx in (-35, -5, 25):
        s.rect(xx, -50, 16, 100)
    s.end()
    s.circle(72, -4, 28)
    s.circle(80, -10, 6)
    s.end()
    # watering can
    s.path('M1120,1960 L1120,1760 Q1240,1740 1360,1760 L1360,1960 Z')
    s.path('M1120,1780 Q1240,1760 1360,1780', fill='none')
    s.path(ribbon_d(cubic_pts((1130, 1800), (1060, 1760), (1000, 1700), (960, 1640)), 14, 22))
    s.ellipse(955, 1630, 40, 24, rot=-35)
    s.path('M1200,1760 C1200,1660 1300,1660 1300,1760', fill='none')
    s.path('M1360,1820 C1440,1800 1440,1900 1360,1900', fill='none')
    for dx, dy in [(-40, 30), (-70, 60), (-30, 80)]:
        s.path(f'M{P(930 + dx, 1600 + dy)} C{P(945 + dx, 1625 + dy)} {P(940 + dx, 1640 + dy)} {P(925 + dx, 1640 + dy)} C{P(910 + dx, 1640 + dy)} {P(905 + dx, 1625 + dy)} {P(930 + dx, 1600 + dy)} Z')
    # ladybug on the ground
    s.ellipse(880, 1900, 50, 36)
    s.line(880, 1864, 880, 1936)
    s.circle(926, 1895, 18)
    for x, y in [(858, 1890), (900, 1885), (865, 1915), (905, 1915)]:
        s.circle(x, y, 6)
    return s


@page('cherry_blossom', 'Cherry Blossom Bridge', 'Nature', 3, 'sakura cherry blossom bridge pond fuji japan')
def cherry_blossom():
    s = Svg(PW, PH, 6)
    sun(s, 1250, 230, 80, 10, 60, 40)
    mountain(s, (560, 1050), (1130, 480), (1700, 1050), snow=0.3, zig=6)
    cloud(s, 300, 380, 240)
    hills(s, 1050, [(1200, 800, 160), (200, 700, 140)])
    ground(s, 1150)
    # pond
    s.path('M-10,1500 Q400,1420 750,1500 T1510,1480 L1510,1760 Q1100,1820 750,1760 T-10,1800 Z')
    for k in range(3):
        s.ellipse(400 + k * 350, 1600 + (k % 2) * 60, 90 + k * 20, 26, fill='none')
    # bridge
    s.path('M280,1500 C400,1300 1100,1300 1220,1500 L1220,1560 C1100,1380 400,1380 280,1560 Z')
    for i in range(11):
        t = i / 10
        x = 290 + t * 920
        yb = 1500 - 190 * (1 - (2 * t - 1) ** 2) * 0.95
        s.rect(x - 6, yb - 90, 12, 90 + 10)
    s.path('M284,1410 C400,1215 1100,1215 1216,1410', fill='none')
    for i in range(11):
        t = i / 10
        x = 290 + t * 920
        yb = 1500 - 190 * (1 - (2 * t - 1) ** 2) * 0.95
        s.line(x - 20, yb + 30, x + 20, yb + 30)
    # cherry tree
    s.path(ribbon_d(cubic_pts((230, 2010), (260, 1600), (180, 1200), (260, 980)), 90, 50))
    for p1, p2, p3 in [((500, 760), (760, 660), (960, 720)), ((420, 820), (520, 560), (700, 430)), ((300, 820), (150, 650), (80, 450)), ((450, 900), (650, 900), (820, 980))]:
        s.path(ribbon_d(cubic_pts((260, 980), p1, p2, p3), 40, 10))
    rnd = random.Random(31)
    centers = [(80, 450), (700, 430), (960, 720), (820, 980), (380, 600), (600, 700), (250, 760), (860, 560), (520, 420), (720, 820), (350, 900), (150, 600)]
    for cx, cy in centers:
        for _ in range(7):
            x, y = cx + rnd.uniform(-110, 110), cy + rnd.uniform(-90, 90)
            flower_simple(s, x, y, rnd.uniform(26, 44), 5)
    for _ in range(26):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(1000, PH - 40)
        a = rnd.uniform(0, 360)
        tip = pol(x, y, rnd.uniform(26, 40), a)
        s.path(leaf_d(x, y, tip[0], tip[1], 10))
    # lantern
    s.rect(1340, 1180, 60, 20)
    s.rect(1320, 1200, 100, 140, rx=30)
    s.rect(1340, 1340, 60, 20)
    s.line(1370, 1360, 1370, 1420)
    for yy in (1240, 1280, 1310):
        s.line(1322, yy, 1418, yy)
    return s


@page('autumn_woods', 'Autumn Woods', 'Nature', 3, 'autumn fall leaves squirrel pumpkin maple')
def autumn_woods():
    s = Svg(PW, PH, 6)
    sun(s, 1280, 230, 90, 12, 70, 45)
    cloud(s, 400, 300, 260)
    hills(s, 1300, [(300, 700, 200), (1250, 750, 240)])
    ground(s, 1450)
    # trees
    for x, h, w in [(320, 900, 90), (1150, 1000, 100)]:
        s.path(ribbon_d(cubic_pts((x, 1500), (x + 10, 1200), (x - 10, 900), (x, 1450 - h)), w * 0.5, w * 0.3))
        s.path(ribbon_d(cubic_pts((x, 1450 - h * 0.6), (x + w, 1450 - h * 0.7), (x + w * 1.6, 1450 - h * 0.9), (x + w * 2.2, 1450 - h * 1.1)), 22, 6))
        s.path(ribbon_d(cubic_pts((x, 1450 - h * 0.7), (x - w, 1450 - h * 0.8), (x - w * 1.5, 1450 - h), (x - w * 2.2, 1450 - h * 1.25)), 22, 6))
        union_circles(s, [(x, 1450 - h - w * 0.8, w * 2.2), (x - w * 2, 1450 - h - w * 0.2, w * 1.7), (x + w * 2, 1450 - h - w * 0.3, w * 1.7), (x - w, 1450 - h - w * 2, w * 1.6), (x + w, 1450 - h - w * 2, w * 1.6), (x, 1450 - h - w * 3, w * 1.5)])
    rnd = random.Random(44)
    for _ in range(18):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(60, PH - 60)
        if (y < 1450 and (abs(x - 320) < 300 or abs(x - 1150) < 320) and y < 1300) or (y > 1450 and 500 < x < 1000 and y > 1650):
            if rnd.random() < 0.6:
                continue
        sc = rnd.uniform(0.5, 0.8)
        s.path(maple_leaf_d(x, y, sc, rnd.uniform(0, 360)))
        s.line(x, y, x + 10 * sc, y + 50 * sc)
    # log and squirrel
    s.path('M500,1650 L1000,1650 L1000,1760 L500,1760 Z')
    s.ellipse(1000, 1705, 30, 55)
    s.ellipse(1000, 1705, 16, 30)
    s.ellipse(500, 1705, 30, 55)
    for xx in (600, 720, 850):
        s.path(f'M{P(xx, 1650)} Q{P(xx + 20, 1700)} {P(xx, 1760)}', fill='none')
    s.path(ribbon_d(cubic_pts((640, 1620), (560, 1620), (520, 1480), (600, 1400)), 20, 60))
    s.circle(600, 1400, 55)
    s.ellipse(700, 1590, 70, 55)
    s.circle(770, 1545, 38)
    s.ellipse(755, 1505, 10, 20, rot=-15)
    s.ellipse(790, 1505, 10, 20, rot=15)
    s.circle(785, 1538, 6)
    s.circle(690, 1560, 22)
    s.ellipse(680, 1640, 30, 12)
    s.ellipse(730, 1640, 30, 12)
    # pumpkins and acorns
    for px, py, sc in [(240, 1880, 1.0), (380, 1920, 0.7), (1280, 1890, 1.1)]:
        for k in (-2, -1, 0, 1, 2):
            s.ellipse(px + k * 30 * sc, py, 60 * sc, 85 * sc)
        s.ellipse(px, py, 60 * sc, 85 * sc)
        s.rect(px - 10 * sc, py - 120 * sc, 20 * sc, 45 * sc, rx=8)
    for ax, ay in [(1050, 1900), (1110, 1950), (640, 1900)]:
        s.ellipse(ax, ay + 20, 24, 30)
        s.path(f'M{P(ax - 30, ay)} Q{P(ax, ay - 30)} {P(ax + 30, ay)} Q{P(ax, ay + 10)} {P(ax - 30, ay)} Z')
        s.line(ax, ay - 20, ax + 8, ay - 40)
    for x in (120, 900, 1450):
        for k in (-1, 0, 1):
            s.path(f'M{P(x + k * 22, 1990)} Q{P(x + k * 38, 1920)} {P(x + k * 50, 1860)}', fill='none')
    return s


@page('desert', 'Desert Noon', 'Nature', 2, 'desert cactus mesa sun lizard')
def desert():
    s = Svg(PW, PH, 7)
    sun(s, 1150, 300, 150, 14, 110, 70)
    cloud(s, 300, 350, 220)
    for pts in [[(-10, 1150), (150, 900), (450, 900), (560, 1150)], [(900, 1150), (1000, 980), (1350, 980), (1510, 1150)]]:
        s.polygon(pts)
        s.line(pts[1][0] + 30, pts[1][1] + 70, pts[2][0] - 30, pts[2][1] + 70)
    hills(s, 1300, [(400, 900, 150), (1300, 800, 180)])
    hills(s, 1550, [(1000, 900, 120)])
    ground(s, 1700)
    # saguaro
    for x, h, w in [(380, 900, 110), (1150, 650, 90)]:
        base = 1750
        body = f'M{P(x - w / 2, base)} L{P(x - w / 2, base - h + w / 2)} A{f(w / 2)} {f(w / 2)} 0 0 1 {P(x + w / 2, base - h + w / 2)} L{P(x + w / 2, base)} Z'
        for sg, ay, ah in [(-1, base - h * 0.5, h * 0.45), (1, base - h * 0.36, h * 0.32)]:
            pts = cubic_pts((x, ay), (x + sg * w * 1.1, ay + 10), (x + sg * w * 1.35, ay - ah * 0.4), (x + sg * w * 1.25, ay - ah))
            s.path(ribbon_d(pts, w * 0.3, w * 0.3))
            s.circle(pts[-1][0], pts[-1][1], w * 0.3)
            s.polyline(pts[3:])
        s.path(body)
        cid = s.clip(body)
        s.begin(clip=cid)
        for k in (-1.5, -0.5, 0.5, 1.5):
            s.line(x + k * w * 0.22, base - h, x + k * w * 0.22, base)
        s.end()
    # barrel cactus with flower, prickly pear
    s.ellipse(760, 1700, 110, 95)
    cid = s.clip('M760,1700 m-110,0 a110,95 0 1,0 220,0 a110,95 0 1,0 -220,0 Z')
    s.begin(clip=cid)
    for k in range(-3, 4):
        s.path(f'M{P(760 + k * 32, 1600)} Q{P(760 + k * 40, 1700)} {P(760 + k * 32, 1800)}', fill='none')
    s.end()
    flower_simple(s, 760, 1600, 42, 6)
    for cx, cy, rx, ry, rot in [(1400, 1760, 55, 75, 10), (1340, 1660, 45, 65, -25), (1450, 1640, 40, 60, 20), (1390, 1560, 35, 50, 0)]:
        s.ellipse(cx, cy, rx, ry, rot=rot)
    # tumbleweed, rocks, lizard
    s.circle(160, 1800, 80, fill='none')
    for k in range(6):
        a = k * 30
        x1, y1 = pol(160, 1800, 80, a)
        x2, y2 = pol(160, 1800, 80, a + 180 + 40)
        s.path(f'M{P(x1, y1)} Q{P(160 + 20 * (k % 2), 1800)} {P(x2, y2)}', fill='none')
    rock(s, 600, 1860, 70, 40, 2)
    rock(s, 1000, 1900, 90, 45, 3)
    s.ellipse(880, 1820, 70, 26)
    s.circle(950, 1810, 24)
    s.path(ribbon_d(cubic_pts((812, 1820), (740, 1830), (700, 1880), (640, 1900)), 12, 3))
    for lx in (840, 910):
        s.line(lx, 1835, lx - 15, 1870)
        s.line(lx, 1835, lx + 15, 1870)
    s.circle(958, 1804, 5)
    return s


# ----------------------------------------------------------------- advanced pages

AW, AH = 1800, 2400


def hexagon(cx, cy, r, rot=30):
    return [pol(cx, cy, r, rot + 60 * k) for k in range(6)]


def poly_d(pts):
    return 'M' + ' L'.join(P(x, y) for x, y in pts) + ' Z'


def pattern_fill(s, clip_d, kind, cx, cy, size, rnd=None):
    """Draws a zentangle-style texture clipped to a shape."""
    cid = s.clip(clip_d)
    s.begin(clip=cid)
    x0, y0, x1, y1 = cx - size, cy - size, cx + size, cy + size
    if kind == 'dots':
        step = size / 5
        y = y0
        row = 0
        while y < y1:
            x = x0 + (step / 2 if row % 2 else 0)
            while x < x1:
                s.circle(x, y, step * 0.28)
                x += step
            y += step * 0.87
            row += 1
    elif kind == 'scales':
        step = size / 4.5
        y = y0
        row = 0
        while y < y1 + step:
            x = x0 + (step / 2 if row % 2 else 0)
            while x < x1 + step:
                s.circle(x, y, step * 0.55)
                x += step
            y += step * 0.6
            row += 1
    elif kind == 'stripes':
        for k in range(-12, 13):
            s.line(x0 + k * size / 6, y0, x0 + k * size / 6 + size * 2, y1)
    elif kind == 'chevron':
        for j in range(-2, 14):
            pts = [(x0 + i * size / 3, y0 + j * size / 5 + (size / 6 if i % 2 else 0)) for i in range(8)]
            s.polyline(pts)
    elif kind == 'waves':
        for j in range(14):
            s.polyline(wave_pts(x0, x1, y0 + j * size / 6, size / 14, size / 2, j * 0.7))
    elif kind == 'spiral':
        pts = []
        for t in range(0, 1800, 6):
            rr = t * size / 1500
            pts.append(pol(cx, cy, rr, t))
        s.polyline(pts)
    elif kind == 'rings':
        for rr in range(int(size / 8), int(size * 1.5), int(size / 8)):
            s.circle(cx, cy, rr, fill='none')
    elif kind == 'petals':
        for i in range(12):
            s.path(petal_d(cx, cy, i * 30, size * 0.12, size * 1.2, size * 0.32, 0.7))
        s.circle(cx, cy, size * 0.14)
    elif kind == 'triangles':
        step = size / 4
        y = y0
        row = 0
        while y < y1:
            x = x0 + (step / 2 if row % 2 else 0)
            while x < x1:
                s.polygon([(x, y), (x + step, y), (x + step / 2, y + step * 0.87)])
                x += step
            y += step * 0.87
            row += 1
    elif kind == 'hexes':
        r = size / 6
        dx = r * math.sqrt(3)
        y = y0
        row = 0
        while y < y1 + r:
            x = x0 + (dx / 2 if row % 2 else 0)
            while x < x1 + r:
                s.polygon(hexagon(x, y, r), fill='none')
                x += dx
            y += r * 1.5
            row += 1
    elif kind == 'checker':
        step = size / 4
        for i in range(-1, 9):
            for j in range(-1, 9):
                if (i + j) % 2 == 0:
                    s.rect(x0 + i * step, y0 + j * step, step, step)
    elif kind == 'leaves':
        step = size / 3
        for i in range(-1, 7):
            for j in range(-1, 7):
                px, py = x0 + i * step + (step / 2 if j % 2 else 0), y0 + j * step
                s.path(leaf_d(px, py, px + step * 0.8, py + step * 0.5, step * 0.25))
    elif kind == 'bubbles':
        rr = rnd or random.Random(1)
        for _ in range(int(size * size / 900)):
            s.circle(rr.uniform(x0, x1), rr.uniform(y0, y1), rr.uniform(size / 30, size / 9))
    elif kind == 'radial':
        for k in range(24):
            e = pol(cx, cy, size * 2, k * 15)
            s.line(cx, cy, e[0], e[1])
        for rr in (size * 0.35, size * 0.7, size * 1.05):
            s.circle(cx, cy, rr, fill='none')
    s.end()


@page('intricate_mandala', 'Infinite Mandala', 'Advanced', 4, 'mandala intricate detailed adult fine')
def intricate_mandala():
    s = Svg(2000, 2000, 3)
    cx = cy = 1000
    frame_square(s, 40, 30)
    for ax, ay in [(40, 40), (1960, 40), (40, 1960), (1960, 1960)]:
        base = math.degrees(math.atan2(cy - ay, cx - ax))
        for k in (-36, -18, 0, 18, 36):
            s.path(petal_d(ax, ay, base + k, 60, 300, 70, 0.6))
        s.circle(ax, ay, 70)
        s.circle(ax, ay, 40)
    s.circle(cx, cy, 965)
    s.circle(cx, cy, 940)
    for i in range(96):
        x, y = pol(cx, cy, 952, i * 3.75)
        s.circle(x, y, 6)
    for i in range(48):
        s.path(petal_d(cx, cy, i * 7.5, 770, 938, 60, 0.5))
        s.path(petal_d(cx, cy, i * 7.5 + 3.75, 790, 900, 24, 0.4))
    for i in range(48):
        x, y = pol(cx, cy, 760, i * 7.5)
        s.circle(x, y, 24)
    s.circle(cx, cy, 735)
    s.circle(cx, cy, 712)
    for i in range(120):
        x, y = pol(cx, cy, 723, i * 3)
        s.circle(x, y, 4)
    for i in range(32):
        s.path(petal_d(cx, cy, i * 11.25, 560, 710, 95, 0.7))
        s.path(petal_d(cx, cy, i * 11.25, 580, 670, 40, 0.5))
        s.path(petal_d(cx, cy, i * 11.25 + 5.6, 600, 690, 30, 0.5))
    s.circle(cx, cy, 560)
    s.polygon(star_pts(cx, cy, 24, 556, 482), fill='none')
    s.polygon(star_pts(cx, cy, 24, 556, 482, -90 + 7.5), fill='none')
    s.circle(cx, cy, 480)
    for i in range(24):
        s.path(petal_d(cx, cy, i * 15, 350, 478, 105, 0.7))
        s.path(petal_d(cx, cy, i * 15, 370, 440, 42, 0.5))
        x, y = pol(cx, cy, 462, i * 15 + 7.5)
        s.circle(x, y, 9)
    s.circle(cx, cy, 350)
    for i in range(48):
        x, y = pol(cx, cy, 334, i * 7.5)
        s.circle(x, y, 11)
    s.circle(cx, cy, 318)
    for i in range(16):
        s.path(petal_d(cx, cy, i * 22.5, 200, 316, 112, 0.8))
        s.path(petal_d(cx, cy, i * 22.5, 215, 290, 48, 0.6))
        s.path(petal_d(cx, cy, i * 22.5 + 11.25, 230, 300, 30, 0.5))
    s.circle(cx, cy, 200)
    s.polygon(star_pts(cx, cy, 12, 196, 150), fill='none')
    s.circle(cx, cy, 150)
    for i in range(12):
        s.path(petal_d(cx, cy, i * 30, 60, 148, 70, 0.8))
        s.path(petal_d(cx, cy, i * 30, 70, 120, 26, 0.5))
    s.circle(cx, cy, 62)
    for i in range(8):
        x, y = pol(cx, cy, 40, i * 45)
        s.circle(x, y, 12)
    s.circle(cx, cy, 16)
    return s


@page('star_lattice', 'Star Lattice', 'Advanced', 4, 'islamic geometric star pattern tiling moroccan')
def star_lattice():
    s = Svg(2000, 2000, 4)
    sp = 250
    stars = []
    for j in range(-1, 10):
        for i in range(-1, 10):
            stars.append((i * sp + 125, j * sp + 125))
    # connecting lattice first
    for cx, cy in stars:
        for ang in (0, 90):
            x1, y1 = pol(cx, cy, 120, ang)
            x2, y2 = pol(cx, cy, 120, ang + 180)
            s.line(x1, y1, x2, y2)
        for ang in (45, 135):
            x1, y1 = pol(cx, cy, 120, ang)
            x2, y2 = pol(cx, cy, 120, ang + 180)
            s.line(x1, y1, x2, y2)
    for cx, cy in stars:
        s.polygon(star_pts(cx, cy, 8, 118, 118 * 0.62, -90))
        s.polygon(star_pts(cx, cy, 8, 118 * 0.62, 118 * 0.4, -90 + 22.5))
        s.circle(cx, cy, 34)
        for k in range(8):
            s.path(petal_d(cx, cy, k * 45, 12, 34, 18, 0.7))
    # squares between the stars
    for j in range(-1, 10):
        for i in range(-1, 10):
            cx, cy = i * sp + 250, j * sp + 250
            s.polygon([pol(cx, cy, 46, 45 + 90 * k) for k in range(4)])
            s.polygon([pol(cx, cy, 24, 45 + 90 * k) for k in range(4)])
    s.rect(30, 30, 1940, 1940, rx=10, fill='none')
    s.rect(60, 60, 1880, 1880, rx=6, fill='none')
    return s


@page('pattern_owl', 'Pattern Owl', 'Advanced', 4, 'owl zentangle patterns detailed adult')
def pattern_owl():
    s = Svg(AW, AH, 4)
    cx = 900
    # night sky
    s.circle(330, 380, 210)
    cid = s.clip('M330,380 m-210,0 a210,210 0 1,0 420,0 a210,210 0 1,0 -420,0 Z')
    s.begin(clip=cid)
    s.circle(440, 330, 190)
    for x, y, r in [(250, 330, 30), (300, 470, 40), (370, 250, 18)]:
        s.circle(x, y, r)
    s.end()
    rnd = random.Random(6)
    for _ in range(26):
        x, y = rnd.uniform(40, AW - 40), rnd.uniform(40, 1900)
        if 350 < x < 1450 and 600 < y < 2100:
            continue
        star(s, x, y, rnd.uniform(14, 40), rnd.choice([4, 5]), 0.42)
    # branch with wood grain
    br = 'M-10,2040 C300,1990 700,2080 1000,2040 C1300,2000 1600,2060 1810,2030 L1810,2140 C1600,2170 1300,2110 1000,2150 C700,2190 300,2100 -10,2150 Z'
    s.path(br)
    cid = s.clip(br)
    s.begin(clip=cid)
    for k in range(5):
        s.polyline(wave_pts(-10, AW + 10, 2060 + k * 22, 8, 330, k))
    s.end()
    for x, y, dirn in [(250, 2040, 1), (1500, 2040, -1)]:
        s.path(ribbon_d(cubic_pts((x, y), (x + dirn * 40, y - 100), (x + dirn * 20, y - 180), (x + dirn * 90, y - 260)), 12, 5))
        for k in range(3):
            ex, ey = pol(x + dirn * 90, y - 260, 110, -90 + dirn * (20 + k * 45) - (0 if dirn > 0 else 0))
            s.path(leaf_d(x + dirn * 90, y - 260, ex, ey, 34))
            s.line(x + dirn * 90, y - 260, ex, ey)
    # body
    body = 'M900,780 C520,780 400,1200 400,1560 C400,1900 640,2050 900,2050 C1160,2050 1400,1900 1400,1560 C1400,1200 1280,780 900,780 Z'
    s.path(body)
    pattern_fill(s, body, 'scales', 900, 1500, 420)
    wingL = 'M470,1060 C380,1300 380,1650 530,1850 C620,1650 660,1300 470,1060 Z'
    wingR = 'M1330,1060 C1420,1300 1420,1650 1270,1850 C1180,1650 1140,1300 1330,1060 Z'
    for w, cxw in ((wingL, 500), (wingR, 1300)):
        s.path(w)
        pattern_fill(s, w, 'chevron', cxw, 1450, 300)
    belly = 'M900,1180 C740,1180 620,1360 620,1600 C620,1860 760,2000 900,2000 C1040,2000 1180,1860 1180,1600 C1180,1360 1060,1180 900,1180 Z'
    s.path(belly)
    cid = s.clip(belly)
    s.begin(clip=cid)
    for row in range(10):
        yy = 1250 + row * 82
        for col in range(-4, 5):
            xx = 900 + col * 82 + (41 if row % 2 else 0)
            s.path(f'M{P(xx - 41, yy)} A41,41 0 0 0 {P(xx + 41, yy)}', fill='none')
            s.path(f'M{P(xx - 28, yy - 8)} A28,34 0 0 0 {P(xx + 28, yy - 8)}', fill='none')
    s.end()
    # ear tufts
    for sg in (-1, 1):
        tuft = f'M{P(900 + sg * 300, 820)} L{P(900 + sg * 400, 560)} L{P(900 + sg * 160, 760)} Z'
        s.path(tuft)
        pattern_fill(s, tuft, 'stripes', 900 + sg * 300, 700, 200)
    # face disc
    face = 'M900,760 C640,760 540,940 540,1080 C540,1200 700,1240 900,1240 C1100,1240 1260,1200 1260,1080 C1260,940 1160,760 900,760 Z'
    s.path(face)
    pattern_fill(s, face, 'radial', 900, 1000, 400)
    for ex in (720, 1080):
        s.circle(ex, 1010, 150)
        for i in range(16):
            s.path(petal_d(ex, 1010, i * 22.5, 95, 148, 30, 0.6))
        for rr in (95, 70, 48):
            s.circle(ex, 1010, rr)
        s.circle(ex + 18, 985, 16)
    s.path('M900,1060 L850,1095 L900,1210 L950,1095 Z')
    s.line(900, 1060, 900, 1210)
    for fx in (790, 1010):
        for k in (-1, 0, 1):
            s.ellipse(fx + k * 38, 2055, 18, 46)
    return s


@page('sea_turtle', 'Sea Turtle', 'Advanced', 4, 'turtle ocean zentangle shell mandala detailed')
def sea_turtle():
    s = Svg(AW, AH, 4)
    cx, cy = 900, 1260
    for k in range(9):
        s.polyline(wave_pts(-10, AW + 10, 120 + k * 260, 16, 420, k * 1.1))
    rnd = random.Random(10)
    for _ in range(30):
        x, y = rnd.uniform(40, AW - 40), rnd.uniform(40, AH - 40)
        if math.hypot((x - cx) / 760, (y - cy) / 900) < 1:
            continue
        s.circle(x, y, rnd.uniform(10, 36))
    for x, hgt in [(90, 700), (170, 500), (1700, 800), (1640, 550)]:
        pts_l, pts_r = [], []
        for i in range(31):
            t = i / 30
            yv = AH + 10 - hgt * t
            off = 40 * math.sin(t * 7)
            ww = 26 * (1 - t * 0.85)
            pts_l.append((x + off - ww, yv))
            pts_r.append((x + off + ww, yv))
        s.path('M' + ' L'.join(P(a, b) for a, b in pts_l) + ' ' + ' L'.join(P(a, b) for a, b in reversed(pts_r)) + ' Z')
    # flippers
    flippers = [((560, 760), (120, 420), 250), ((1240, 760), (1680, 420), 250), ((560, 1760), (200, 2100), 220), ((1240, 1760), (1600, 2100), 220)]
    for (x1, y1), (x2, y2), w in flippers:
        d = leaf_d(x1, y1, x2, y2, w)
        s.path(d)
        pattern_fill(s, d, 'scales', (x1 + x2) / 2, (y1 + y2) / 2, 320)
    # head and tail
    head = 'M900,560 C780,560 720,650 720,740 C720,800 800,840 900,840 C1000,840 1080,800 1080,740 C1080,650 1020,560 900,560 Z'
    s.path(head)
    pattern_fill(s, head, 'hexes', 900, 700, 240)
    s.circle(800, 690, 30)
    s.circle(1000, 690, 30)
    s.circle(808, 684, 10)
    s.circle(1008, 684, 10)
    s.path('M900,2020 L860,2140 L940,2140 Z')
    # shell
    shell = f'M{P(cx - 540, cy)} a540,640 0 1,0 1080,0 a540,640 0 1,0 -1080,0 Z'
    s.path(shell)
    s.ellipse(cx, cy, 455, 555)
    cid = s.clip(shell)
    s.begin(clip=cid)
    for k in range(24):
        a = k * 15
        x1, y1 = cx + 455 * math.cos(math.radians(a)), cy + 555 * math.sin(math.radians(a))
        x2, y2 = cx + 560 * math.cos(math.radians(a)), cy + 660 * math.sin(math.radians(a))
        s.line(x1, y1, x2, y2)
    s.end()
    scutes = [(cx, cy, 'spiral'), (cx, cy - 330, 'petals'), (cx, cy + 330, 'rings')]
    for k in range(6):
        px, py = pol(cx, cy, 310, 30 + k * 60)
        scutes.append((px, py * 1 if False else py, ['dots', 'waves', 'triangles', 'checker', 'leaves', 'chevron'][k]))
    hexes = []
    for (px, py, kind) in scutes:
        hx = hexagon(px, py, 150 if (px, py) == (cx, cy) else 130, 0)
        hexes.append((hx, kind, px, py))
    for hx, kind, px, py in hexes:
        s.polygon(hx)
        pattern_fill(s, poly_d(hx), kind, px, py, 140)
    return s


@page('royal_peacock', 'Royal Peacock', 'Advanced', 4, 'peacock feathers tail fan detailed bird')
def royal_peacock():
    s = Svg(AW, AH, 4)
    s.rect(30, 30, AW - 60, AH - 60, rx=20, fill='none')
    ox, oy = 900, 1820
    feathers = []
    n = 17
    for i in range(n):
        ang = -172 + i * (164 / (n - 1))
        ln = 1500 - 280 * abs((i - (n - 1) / 2) / ((n - 1) / 2)) ** 1.6
        feathers.append((ang, ln))
    # outer feathers first so the inner ones overlap them
    order = sorted(range(n), key=lambda i: -abs(i - (n - 1) / 2))
    for i in order:
        ang, ln = feathers[i]
        tipx, tipy = pol(ox, oy, ln, ang)
        d = leaf_d(ox, oy, tipx, tipy, 150)
        s.path(d)
        cid = s.clip(d)
        s.begin(clip=cid)
        for t in range(2, 30):
            px, py = ox + (tipx - ox) * t / 30, oy + (tipy - oy) * t / 30
            for sg in (-1, 1):
                e = pol(px, py, 110, ang + sg * 62)
                s.line(px, py, e[0], e[1])
        s.end()
        s.line(ox, oy, tipx, tipy)
        ex, ey = ox + (tipx - ox) * 0.82, oy + (tipy - oy) * 0.82
        s.ellipse(ex, ey, 62, 92, rot=ang + 90)
        s.ellipse(ex, ey, 40, 62, rot=ang + 90)
        s.circle(ex, ey, 22)
    # body
    s.path(f'M{P(ox - 150, oy)} C{P(ox - 170, oy - 300)} {P(ox + 170, oy - 300)} {P(ox + 150, oy)} C{P(ox + 120, oy + 140)} {P(ox - 120, oy + 140)} {P(ox - 150, oy)} Z')
    pattern_fill(s, f'M{P(ox - 150, oy)} C{P(ox - 170, oy - 300)} {P(ox + 170, oy - 300)} {P(ox + 150, oy)} C{P(ox + 120, oy + 140)} {P(ox - 120, oy + 140)} {P(ox - 150, oy)} Z', 'scales', ox, oy - 60, 200)
    neck = ribbon_d(cubic_pts((ox - 20, oy - 230), (ox - 60, oy - 500), (ox - 180, oy - 650), (ox - 190, oy - 850)), 60, 38)
    s.path(neck)
    s.circle(ox - 190, oy - 900, 70)
    s.path(f'M{P(ox - 255, oy - 905)} L{P(ox - 340, oy - 880)} L{P(ox - 255, oy - 870)} Z')
    s.circle(ox - 205, oy - 915, 12)
    for k in range(5):
        ex, ey = pol(ox - 190, oy - 960, 120, -130 + k * 20)
        s.line(ox - 190, oy - 960, ex, ey)
        s.circle(ex, ey, 14)
    for lx in (ox - 50, ox + 50):
        s.path(ribbon_d([(lx, oy + 120), (lx + 10, oy + 300)], 10, 8))
        for k in (-1, 0, 1):
            s.line(lx + 10, oy + 300, lx + 10 + k * 40, oy + 340)
    for x in range(80, AW, 140):
        for k in (-1, 0, 1):
            s.path(f'M{P(x + k * 22, 2370)} Q{P(x + k * 36, 2300)} {P(x + k * 46, 2250)}', fill='none')
    return s


@page('city_lights', 'City Lights', 'Advanced', 4, 'city skyline buildings night windows bridge river')
def city_lights():
    s = Svg(AW, AH, 4)
    rnd = random.Random(14)
    for _ in range(40):
        x, y = rnd.uniform(40, AW - 40), rnd.uniform(40, 1000)
        star(s, x, y, rnd.uniform(10, 26), rnd.choice([4, 5]), 0.4)
    s.circle(1450, 330, 170)
    cid = s.clip('M1450,330 m-170,0 a170,170 0 1,0 340,0 a170,170 0 1,0 -340,0 Z')
    s.begin(clip=cid)
    s.circle(1540, 290, 150)
    s.end()
    cloud(s, 400, 420, 300)
    cloud(s, 1000, 560, 220)

    def building(x, w, top, bottom, win_w, win_h, gap, arch=False, roof=None):
        s.rect(x, top, w, bottom - top)
        if roof == 'point':
            s.polygon([(x, top), (x + w / 2, top - w * 0.6), (x + w, top)])
            s.rect(x + w / 2 - 4, top - w * 0.6 - 90, 8, 90)
        elif roof == 'dome':
            s.path(f'M{P(x, top)} A{f(w / 2)} {f(w / 2)} 0 0 1 {P(x + w, top)} Z')
            s.rect(x + w / 2 - 5, top - w / 2 - 60, 10, 60)
            s.circle(x + w / 2, top - w / 2 - 70, 14)
        elif roof == 'tower':
            s.rect(x + w * 0.3, top - 160, w * 0.4, 160)
            s.circle(x + w / 2, top - 90, w * 0.14)
            s.line(x + w / 2, top - 90, x + w / 2, top - 120)
            s.line(x + w / 2, top - 90, x + w / 2 + 18, top - 90)
        elif roof == 'tank':
            s.rect(x + w * 0.6, top - 70, w * 0.3, 70, rx=8)
            s.polygon([(x + w * 0.58, top - 70), (x + w * 0.75, top - 110), (x + w * 0.92, top - 70)])
        yy = top + 40
        while yy + win_h < bottom - 20:
            xx = x + gap
            while xx + win_w < x + w - gap + 1:
                if arch:
                    s.path(f'M{P(xx, yy + win_h)} L{P(xx, yy + win_w / 2)} A{f(win_w / 2)} {f(win_w / 2)} 0 0 1 {P(xx + win_w, yy + win_w / 2)} L{P(xx + win_w, yy + win_h)} Z')
                else:
                    s.rect(xx, yy, win_w, win_h)
                xx += win_w + gap
            yy += win_h + gap
    horizon = 1760
    # far row
    for (x, w, top, roof) in [(-20, 220, 1100, None), (180, 160, 1250, 'tank'), (330, 260, 950, 'point'), (580, 200, 1200, None), (770, 240, 1050, 'tower'), (1000, 170, 1300, None), (1160, 280, 900, 'dome'), (1430, 190, 1180, 'tank'), (1610, 230, 1020, None)]:
        building(x, w, top, horizon, 28, 36, 18, roof=roof)
    # near row
    for (x, w, top, roof, arch) in [(60, 300, 1380, None, False), (380, 230, 1480, 'tank', True), (640, 340, 1300, 'point', False), (1010, 260, 1420, None, True), (1300, 320, 1340, 'tower', False), (1640, 220, 1500, None, False)]:
        building(x, w, top, horizon + 40, 40, 52, 22, arch=arch, roof=roof)
    # clock on the pointed tower
    s.circle(810, 1420, 60)
    s.circle(810, 1420, 48)
    s.line(810, 1420, 810, 1385)
    s.line(810, 1420, 838, 1430)
    # street and river
    s.rect(-10, horizon + 40, AW + 20, 90)
    for x in range(40, AW, 160):
        s.rect(x, horizon + 80, 60, 10)
    s.rect(-10, horizon + 130, AW + 20, AH - horizon)
    cid = s.clip(f'M-10,{horizon + 130} h{AW + 20} v{AH} h-{AW + 20} Z')
    s.begin(clip=cid)
    for k in range(7):
        s.polyline(wave_pts(-10, AW + 10, horizon + 200 + k * 70, 8, 220, k * 0.8))
    s.end()
    # bridge
    s.rect(-10, horizon + 330, AW + 20, 50)
    for k in range(5):
        bx = -100 + k * 450
        s.path(f'M{P(bx, horizon + 380)} A225 160 0 0 0 {P(bx + 450, horizon + 380)} L{P(bx + 450 - 30, horizon + 380)} A195 130 0 0 1 {P(bx + 30, horizon + 380)} Z')
    for x in range(60, AW, 160):
        s.rect(x - 6, horizon + 230, 12, 100)
        s.circle(x, horizon + 220, 14)
    s.path('M-10,2290 C300,2250 500,2320 800,2290 C1100,2260 1400,2320 1810,2290', fill='none')
    # balloon and plane
    s.circle(300, 760, 110)
    cid = s.clip('M300,760 m-110,0 a110,110 0 1,0 220,0 a110,110 0 1,0 -220,0 Z')
    s.begin(clip=cid)
    for k in (-2, -1, 1, 2):
        s.path(f'M{P(300 + k * 30, 640)} Q{P(300 + k * 75, 760)} {P(300 + k * 30, 880)}', fill='none')
    s.end()
    s.rect(270, 905, 60, 44, rx=6)
    s.line(230, 850, 275, 905)
    s.line(370, 850, 325, 905)
    return s


@page('secret_garden', 'Secret Garden', 'Advanced', 4, 'flowers dense botanical adult detailed garden')
def secret_garden():
    s = Svg(AW, AH, 4)
    rnd = random.Random(77)
    items = []
    for j in range(-1, 12):
        for i in range(-1, 9):
            x = i * 220 + 110 + rnd.uniform(-70, 70) + (110 if j % 2 else 0)
            y = j * 220 + 110 + rnd.uniform(-70, 70)
            kind = rnd.choice(['daisy', 'rose', 'simple5', 'simple8', 'leaf', 'leaf', 'berries', 'tulip', 'swirl', 'sunflower'])
            items.append((y, x, kind, rnd.random()))
    items.sort()
    for y, x, kind, rv in items:
        ang = rv * 360
        if kind == 'leaf':
            for k in range(3):
                tip = pol(x, y, 150 + rv * 60, ang + k * 35 - 35)
                s.path(leaf_d(x, y, tip[0], tip[1], 40))
                s.line(x, y, tip[0], tip[1])
                for t in (0.3, 0.5, 0.7):
                    px, py = x + (tip[0] - x) * t, y + (tip[1] - y) * t
                    for sg in (-1, 1):
                        e = pol(px, py, 30, ang + k * 35 - 35 + sg * 50)
                        s.line(px, py, e[0], e[1])
        elif kind == 'daisy':
            daisy(s, x, y, 90 + rv * 40, 14, 0.35)
        elif kind == 'sunflower':
            daisy(s, x, y, 110 + rv * 40, 20, 0.45, double=True)
            cid = s.clip(f'M{P(x, y)} m-50,0 a50,50 0 1,0 100,0 a50,50 0 1,0 -100,0 Z')
            s.begin(clip=cid)
            for r2 in range(12, 60, 14):
                s.circle(x, y, r2, fill='none')
            s.end()
        elif kind == 'rose':
            rose(s, x, y, 70 + rv * 30)
        elif kind == 'simple5':
            flower_simple(s, x, y, 80 + rv * 30, 5)
        elif kind == 'simple8':
            flower_simple(s, x, y, 85 + rv * 30, 8, petal_w=50)
            s.circle(x, y, 14)
        elif kind == 'berries':
            stem(s, x, y + 120, x + 30, y - 40, 8, curve=20)
            for k in range(6):
                bx, by = pol(x + 30, y - 40, 40 + (k % 2) * 25, k * 60)
                s.circle(bx, by, 22)
        elif kind == 'tulip':
            tulip(s, x, y + 60, 170, 80)
        elif kind == 'swirl':
            pts = []
            for t in range(0, 720, 8):
                rr = 8 + t * 0.14
                pts.append(pol(x, y, rr, t + ang))
            s.polyline(pts)
            for k in range(3):
                px, py = pts[len(pts) - 1 - k * 25]
                s.circle(px, py, 10)
    s.rect(30, 30, AW - 60, AH - 60, rx=16, fill='none')
    return s


@page('clockwork', 'Clockwork', 'Advanced', 4, 'gears steampunk clock mechanical cogs')
def clockwork():
    s = Svg(2000, 2000, 4)

    def gear(cx, cy, r, teeth, spokes=5, hole=0.22, rot=0):
        pts = []
        step = 180 / teeth
        for i in range(teeth):
            a = rot + i * 2 * step
            pts.append(pol(cx, cy, r * 0.84, a - step * 0.55))
            pts.append(pol(cx, cy, r, a - step * 0.3))
            pts.append(pol(cx, cy, r, a + step * 0.3))
            pts.append(pol(cx, cy, r * 0.84, a + step * 0.55))
        s.polygon(pts)
        s.circle(cx, cy, r * 0.72)
        for k in range(spokes):
            a = rot + k * 360 / spokes
            p0 = pol(cx, cy, r * hole + 10, a)
            p1 = pol(cx, cy, r * 0.72, a)
            s.path(ribbon_d([p0, p1], r * 0.07, r * 0.09))
        s.circle(cx, cy, r * hole)
        s.circle(cx, cy, r * hole * 0.5)
        for k in range(teeth):
            px, py = pol(cx, cy, r * 0.62, rot + k * 360 / teeth + 180 / teeth)
            s.circle(px, py, r * 0.035)

    # pipes behind
    for d in ['M-10,300 L600,300 Q660,300 660,360 L660,900', 'M2010,1500 L1500,1500 Q1440,1500 1440,1440 L1440,1100', 'M300,2010 L300,1600 Q300,1540 360,1540 L700,1540']:
        pts = []
        s.path(d, fill='none', stroke_width=60)
        s.path(d, fill='none', stroke_width=46, stroke='white')
    for x, y in [(600, 300), (1440, 1500), (300, 1600), (660, 900), (1440, 1100), (700, 1540)]:
        s.rect(x - 44, y - 44, 88, 88, rx=12)
        for dx, dy in [(-24, -24), (24, -24), (-24, 24), (24, 24)]:
            s.circle(x + dx, y + dy, 8)
    gear(1000, 1000, 430, 24, 6)
    gear(430, 560, 260, 15, 5, rot=12)
    gear(1540, 500, 230, 13, 5, rot=5)
    gear(380, 1450, 240, 14, 5, rot=8)
    gear(1530, 1500, 310, 18, 6, rot=10)
    gear(930, 1680, 190, 11, 4, rot=4)
    gear(720, 260, 130, 9, 4, rot=20)
    gear(1280, 1230, 120, 8, 4, rot=15)
    gear(180, 1000, 150, 10, 4, rot=0)
    gear(1800, 950, 160, 10, 4, rot=18)
    # clock face in the big gear's hub
    s.circle(1000, 1000, 95)
    for k in range(12):
        p0 = pol(1000, 1000, 80, k * 30)
        p1 = pol(1000, 1000, 92, k * 30)
        s.line(p0[0], p0[1], p1[0], p1[1])
    s.path(ribbon_d([(1000, 1000), pol(1000, 1000, 70, -60)], 7, 3))
    s.path(ribbon_d([(1000, 1000), pol(1000, 1000, 50, 30)], 7, 3))
    s.circle(1000, 1000, 10)
    # frame with rivets
    s.rect(30, 30, 1940, 1940, rx=20, fill='none')
    s.rect(70, 70, 1860, 1860, rx=14, fill='none')
    for k in range(0, 1940, 120):
        for x, y in [(50 + k, 50), (50 + k, 1950), (50, 50 + k), (1950, 50 + k)]:
            s.circle(x, y, 9)
    return s


@page('sugar_skull', 'Sugar Skull', 'Advanced', 4, 'sugar skull day of the dead ornate calavera')
def sugar_skull():
    s = Svg(AW, AH, 4)
    cx = 900
    rnd = random.Random(23)
    for _ in range(40):
        x, y = rnd.uniform(40, AW - 40), rnd.uniform(40, AH - 40)
        if 350 < x < 1450 and 300 < y < 2000:
            continue
        if rnd.random() < 0.5:
            flower_simple(s, x, y, rnd.uniform(26, 50), rnd.choice([5, 6, 8]))
        else:
            s.circle(x, y, rnd.uniform(8, 20))
    # flower crown
    for x, y, r in [(560, 560, 110), (760, 470, 130), (1040, 470, 130), (1240, 560, 110)]:
        rose(s, x, y, r)
    for x, y, r in [(450, 680, 70), (660, 560, 60), (900, 440, 70), (1140, 560, 60), (1350, 680, 70)]:
        daisy(s, x, y, r, 12, 0.35)
    for x, y in [(400, 760), (1400, 760), (520, 460), (1280, 460)]:
        for k in range(3):
            tip = pol(x, y, 110, -60 + k * 60 + (180 if x > 900 else 0))
            s.path(leaf_d(x, y, tip[0], tip[1], 30))
            s.line(x, y, tip[0], tip[1])
    # skull
    skull = 'M420,1000 C420,560 1380,560 1380,1000 C1380,1250 1250,1350 1180,1450 L1180,1760 C1180,1880 620,1880 620,1760 L620,1450 C550,1350 420,1250 420,1000 Z'
    s.path(skull)
    # forehead mandala
    s.circle(cx, 780, 130)
    for i in range(16):
        s.path(petal_d(cx, 780, i * 22.5, 70, 128, 36, 0.6))
    for i in range(8):
        s.path(petal_d(cx, 780, i * 45, 20, 70, 34, 0.7))
    s.circle(cx, 780, 22)
    for i in range(24):
        px, py = pol(cx, 780, 160, i * 15)
        s.circle(px, py, 9)
    # swirls on temples
    for sg in (-1, 1):
        pts = []
        for t in range(0, 560, 8):
            rr = 10 + t * 0.2
            pts.append(pol(cx + sg * 330, 960, rr, (t if sg > 0 else -t) + 180))
        s.polyline(pts)
        for k in range(3):
            px, py = pts[-1 - k * 20]
            s.circle(px, py, 8)
    # eye sockets
    for ex in (690, 1110):
        s.circle(ex, 1090, 170)
        for i in range(14):
            s.path(petal_d(ex, 1090, i * 360 / 14, 120, 168, 42, 0.6))
        s.circle(ex, 1090, 120)
        for i in range(10):
            s.path(petal_d(ex, 1090, i * 36 + 18, 60, 118, 36, 0.7))
        s.circle(ex, 1090, 62)
        s.circle(ex, 1090, 30)
        for i in range(18):
            px, py = pol(ex, 1090, 200, i * 20)
            s.circle(px, py, 8)
    # nose
    s.path(f'M{P(cx, 1280)} C{P(cx - 20, 1340)} {P(cx - 70, 1380)} {P(cx - 60, 1430)} C{P(cx - 50, 1470)} {P(cx - 10, 1460)} {P(cx, 1440)} '
           f'C{P(cx + 10, 1460)} {P(cx + 50, 1470)} {P(cx + 60, 1430)} C{P(cx + 70, 1380)} {P(cx + 20, 1340)} {P(cx, 1280)} Z')
    # cheek motifs
    for sg in (-1, 1):
        x = cx + sg * 290
        for k in range(5):
            s.path(petal_d(x, 1380, -90 + sg * (k * 35 - 70), 14, 90, 30, 0.7))
        s.circle(x, 1380, 16)
        for k in range(3):
            s.path(leaf_d(x + sg * 20, 1470 + k * 40, x + sg * 110, 1500 + k * 40, 14))
    # teeth
    s.path('M660,1560 Q900,1510 1140,1560 L1140,1700 Q900,1740 660,1700 Z')
    s.path('M660,1630 Q900,1600 1140,1630', fill='none')
    for k in range(1, 8):
        x = 660 + k * 60
        s.line(x, 1545 + abs(k - 4) * 4, x, 1715 - abs(k - 4) * 4)
    # chin ornaments
    for k in range(5):
        x = 700 + k * 100
        s.path(f'M{P(x, 1740)} C{P(x + 22, 1760)} {P(x + 20, 1800)} {P(x, 1810)} C{P(x - 20, 1800)} {P(x - 22, 1760)} {P(x, 1740)} Z')
    for x, y in [(760, 1790), (1040, 1790)]:
        s.circle(x, y, 10)
    return s


@page('coral_reef', 'Coral Reef', 'Advanced', 4, 'coral reef fish ocean detailed underwater')
def coral_reef():
    s = Svg(AW, AH, 4)
    s.path(wave_band_d(-10, AW + 10, 120, 24, 360, -20))
    for k in range(3):
        s.path(f'M{P(500 + k * 260, 130)} L{P(524 + k * 260, 130)} L{P(290 + k * 300, 1700)} L{P(250 + k * 300, 1700)} Z')
    rnd = random.Random(19)
    for _ in range(34):
        s.circle(rnd.uniform(40, AW - 40), rnd.uniform(200, 1700), rnd.uniform(8, 30))
    # sand
    s.path(wave_band_d(-10, AW + 10, 1980, 22, 500, AH + 10, 1.0))
    for x, y, rx, ry in [(200, 2150, 60, 32), (700, 2250, 40, 22), (1200, 2180, 70, 36), (1600, 2300, 50, 26)]:
        s.ellipse(x, y, rx, ry)

    def branch_coral(x, y, ang, ln, w, depth, seed):
        r = random.Random(seed)
        pts = cubic_pts((x, y), pol(x, y, ln * 0.4, ang + r.uniform(-15, 15)), pol(x, y, ln * 0.7, ang + r.uniform(-15, 15)), pol(x, y, ln, ang))
        s.path(ribbon_d(pts, w, w * 0.7))
        s.circle(pts[-1][0], pts[-1][1], w * 0.7)
        if depth > 0:
            for k, da in enumerate((-35, 30)):
                branch_coral(pts[-1][0], pts[-1][1], ang + da + r.uniform(-10, 10), ln * 0.72, w * 0.72, depth - 1, seed * 7 + k + 1)
    branch_coral(300, 2000, -80, 300, 34, 3, 3)
    branch_coral(1520, 2020, -95, 320, 36, 3, 5)
    # brain coral
    s.ellipse(760, 2000, 230, 130)
    cid = s.clip('M760,2000 m-230,0 a230,130 0 1,0 460,0 a230,130 0 1,0 -460,0 Z')
    s.begin(clip=cid)
    for k in range(9):
        s.polyline(wave_pts(520, 1000, 1880 + k * 30, 12, 90, k * 1.3))
    s.end()
    # fan coral
    fan = 'M1150,2000 L950,1700 A260,260 0 0 1 1350,1700 Z'
    s.path(fan)
    cid = s.clip(fan)
    s.begin(clip=cid)
    for ang in range(-150, -29, 10):
        e = pol(1150, 2000, 340, ang)
        s.line(1150, 2000, e[0], e[1])
    for rr in (100, 170, 240):
        s.circle(1150, 2000, rr, fill='none')
    s.end()
    # tube corals and anemone
    for x, h in [(560, 180), (610, 240), (665, 200), (720, 150)]:
        s.rect(x - 22, 2000 - h, 44, h + 20, rx=16)
        s.ellipse(x, 2000 - h, 22, 9)
    for k in range(13):
        a = -165 + k * 12.5
        pts = cubic_pts((1500, 2000), pol(1500, 2000, 80, a), pol(1500, 2000, 150, a + 12), pol(1500, 2000, 210, a - 8))
        s.path(ribbon_d(pts, 12, 10))
        s.circle(pts[-1][0], pts[-1][1], 14)
    # seaweed
    for x, hgt in [(90, 900), (1720, 700)]:
        pts_l, pts_r = [], []
        for i in range(31):
            t = i / 30
            yv = 2000 - hgt * t
            off = 50 * math.sin(t * 6)
            ww = 30 * (1 - t * 0.85)
            pts_l.append((x + off - ww, yv))
            pts_r.append((x + off + ww, yv))
        s.path('M' + ' L'.join(P(a, b) for a, b in pts_l) + ' ' + ' L'.join(P(a, b) for a, b in reversed(pts_r)) + ' Z')

    def fish(cx, cy, ln, flip=1, kind='stripes'):
        s.begin(transform=f'translate({f(cx)} {f(cy)}) scale({f(flip)} 1)')
        s.path(f'M{P(-ln * 0.45, 0)} L{P(-ln * 0.85, -ln * 0.3)} Q{P(-ln * 0.7, 0)} {P(-ln * 0.85, ln * 0.3)} Z')
        s.path(f'M{P(-ln * 0.1, -ln * 0.28)} Q{P(0, -ln * 0.6)} {P(ln * 0.25, -ln * 0.3)} Z')
        s.path(f'M{P(-ln * 0.05, ln * 0.28)} Q{P(0.05 * ln, ln * 0.55)} {P(ln * 0.25, ln * 0.3)} Z')
        body = (f'M{P(-ln * 0.5, 0)} C{P(-ln * 0.4, -ln * 0.45)} {P(ln * 0.2, -ln * 0.45)} {P(ln * 0.5, 0)} '
                f'C{P(ln * 0.2, ln * 0.45)} {P(-ln * 0.4, ln * 0.45)} {P(-ln * 0.5, 0)} Z')
        s.path(body)
        cid = s.clip(body)
        s.begin(clip=cid)
        if kind == 'stripes':
            for xx in (-ln * 0.3, -ln * 0.05, ln * 0.2):
                s.path(f'M{P(xx, -ln)} Q{P(xx - ln * 0.08, 0)} {P(xx, ln)} L{P(xx + ln * 0.09, ln)} Q{P(xx + ln * 0.01, 0)} {P(xx + ln * 0.09, -ln)} Z')
        elif kind == 'spots':
            for xx, yy, rr in [(-0.25, -0.1, 0.07), (0, 0.12, 0.09), (0.2, -0.12, 0.06), (-0.1, 0.25, 0.05), (0.25, 0.18, 0.05)]:
                s.circle(xx * ln, yy * ln, rr * ln)
        else:
            rr = ln * 0.09
            for row in range(-3, 4):
                for col in range(-2, 2):
                    s.circle(-ln * 0.05 + col * rr * 2 + (rr if row % 2 else 0), row * rr * 1.6, rr * 1.1)
        s.end()
        s.path(f'M{P(ln * 0.22, -ln * 0.3)} Q{P(ln * 0.1, 0)} {P(ln * 0.22, ln * 0.3)}', fill='none')
        s.circle(ln * 0.33, -ln * 0.08, ln * 0.07)
        s.circle(ln * 0.35, -ln * 0.08, ln * 0.03)
        s.end()
    fish(500, 700, 320, 1, 'stripes')
    fish(1250, 900, 380, -1, 'scales')
    fish(900, 1300, 260, 1, 'spots')
    fish(400, 1250, 200, -1, 'stripes')
    fish(1400, 1500, 240, 1, 'spots')
    for k in range(6):
        fish(1000 + k * 95, 480 + (k % 2) * 40, 90, -1, 'spots')
    # jellyfish
    s.path('M300,560 C300,400 620,400 620,560 Q460,600 300,560 Z')
    s.path('M320,540 Q460,570 600,540', fill='none')
    for k in range(6):
        x = 330 + k * 52
        s.path(f'M{P(x, 575)} C{P(x - 30, 680)} {P(x + 30, 760)} {P(x, 860)}', fill='none')
    # sea star and seahorse
    s.polygon(star_pts(1100, 2200, 5, 110, 50, -90))
    for i in range(5):
        for k in (1, 2):
            px, py = pol(1100, 2200, 30 + k * 28, -90 + i * 72)
            s.circle(px, py, 7)
    sh = cubic_pts((1650, 1150), (1760, 1250), (1600, 1450), (1700, 1560))
    s.path(ribbon_d(sh, 40, 10))
    s.circle(1640, 1120, 55)
    s.path(ribbon_d([(1600, 1140), (1500, 1170)], 16, 10))
    s.circle(1655, 1105, 10)
    for k in range(5):
        px, py = sh[3 + k * 5]
        s.path(f'M{P(px - 30, py)} L{P(px - 70, py - 30)} L{P(px - 65, py + 10)} Z')
    return s


@page('tree_of_life', 'Tree of Life', 'Advanced', 4, 'tree of life mandala roots celtic circle')
def tree_of_life():
    s = Svg(2000, 2000, 4)
    cx, cy = 1000, 1000
    s.circle(cx, cy, 960)
    s.circle(cx, cy, 920)
    for i in range(72):
        px, py = pol(cx, cy, 940, i * 5)
        s.circle(px, py, 8)
    s.circle(cx, cy, 880, fill='none')
    rnd = random.Random(8)

    def branch(x, y, ang, ln, w, depth, leaves=True):
        end = pol(x, y, ln, ang)
        ctrl = pol(x, y, ln * 0.5, ang + rnd.uniform(-18, 18))
        pts = quad_pts((x, y), ctrl, end, 10)
        s.path(ribbon_d(pts, w, w * 0.62))
        if depth > 0:
            spread = 28 + rnd.uniform(-6, 6)
            branch(end[0], end[1], ang - spread, ln * 0.74, w * 0.65, depth - 1, leaves)
            branch(end[0], end[1], ang + spread, ln * 0.74, w * 0.65, depth - 1, leaves)
            if depth >= 3 and rnd.random() < 0.6:
                branch(end[0], end[1], ang + rnd.uniform(-8, 8), ln * 0.6, w * 0.5, depth - 2, leaves)
        elif leaves:
            for k in (-1, 1):
                tip = pol(end[0], end[1], 70, ang + k * 40)
                s.path(leaf_d(end[0], end[1], tip[0], tip[1], 22))
                s.line(end[0], end[1], tip[0], tip[1])
            tip = pol(end[0], end[1], 80, ang)
            s.path(leaf_d(end[0], end[1], tip[0], tip[1], 24))
            s.line(end[0], end[1], tip[0], tip[1])
        else:
            s.circle(end[0], end[1], w * 1.2)
    # roots (downward) first, then trunk, then canopy
    for a in (60, 90, 120, 40, 140):
        branch(cx, cy + 120, a, 230, 22, 3, leaves=False)
    s.path(ribbon_d([(cx, cy + 160), (cx, cy - 60)], 70, 48))
    for a in (-90, -55, -125, -30, -150):
        branch(cx, cy - 60, a, 260, 36, 4)
    s.path('M960,1140 Q1000,1090 1040,1140', fill='none')
    for i in range(16):
        px, py = pol(cx, cy, 900, i * 22.5)
        s.circle(px, py, 12)
    return s


@page('sky_dragon', 'Sky Dragon', 'Advanced', 4, 'dragon oriental clouds scales mythical')
def sky_dragon():
    s = Svg(AW, AH, 4)
    rnd = random.Random(17)
    # oriental clouds
    def ocloud(x, y, w):
        union_circles(s, [(x, y, w * 0.3), (x - w * 0.32, y + w * 0.1, w * 0.22), (x + w * 0.32, y + w * 0.1, w * 0.22), (x + w * 0.1, y - w * 0.15, w * 0.2)])
        pts = []
        for t in range(0, 400, 10):
            rr = 4 + t * 0.09
            pts.append(pol(x - w * 0.5, y + w * 0.25, rr, 180 - t))
        s.polyline(pts)
    for x, y, w in [(300, 300, 300), (1500, 500, 260), (250, 1500, 280), (1550, 1900, 320), (900, 2200, 260), (1400, 1200, 200)]:
        ocloud(x, y, w)
    for _ in range(14):
        star(s, rnd.uniform(60, AW - 60), rnd.uniform(60, AH - 60), rnd.uniform(14, 30), 4, 0.4)
    # spine: a long S through the page
    spine = []
    for seg in [((1500, 700), (1700, 1000), (1300, 1250), (900, 1200)), ((900, 1200), (500, 1150), (300, 1500), (600, 1750)), ((600, 1750), (900, 2000), (1250, 1850), (1450, 1650))]:
        spine += cubic_pts(*seg, 40)[:-1]
    n = len(spine)
    widths = [95 * (1 - 0.8 * (i / (n - 1)) ** 1.3) + 8 for i in range(n)]
    # body as a sequence of ribbon pieces (so the width can taper smoothly)
    body_parts = []
    for i in range(0, n - 1, 6):
        seg = spine[i:min(i + 7, n)]
        if len(seg) < 2:
            continue
        body_parts.append((seg, widths[i], widths[min(i + 6, n - 1)]))
    # dorsal spikes along the left normal
    for i in range(0, n - 3, 4):
        x, y = spine[i]
        ax, ay = spine[max(i - 1, 0)]
        bx, by = spine[min(i + 1, n - 1)]
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        w = widths[i]
        base = pol(x, y, w * 0.85, ang - 90)
        tip = pol(x, y, w * 2.0, ang - 110)
        s.path(f'M{P(*pol(x, y, w * 0.8, ang - 90 - 10))} Q{P(tip[0], tip[1])} {P(*pol(x, y, w * 0.8, ang - 90 + 12))} Z')
    for seg, w0, w1 in body_parts:
        d = ribbon_d(seg, w0, w1)
        s.path(d)
        cid = s.clip(d)
        s.begin(clip=cid)
        for j, (x, y) in enumerate(seg):
            ax, ay = seg[max(j - 1, 0)]
            bx, by = seg[min(j + 1, len(seg) - 1)]
            ang = math.degrees(math.atan2(by - ay, bx - ax))
            w = w0 + (w1 - w0) * j / max(len(seg) - 1, 1)
            k = -3
            while k <= 3:
                off = (k + (0.5 if j % 2 else 0)) * w * 0.42
                if abs(off) < w * 1.1:
                    px, py = pol(x, y, off, ang + 90)
                    s.circle(px, py, w * 0.26)
                k += 1
        # belly line
        s.end()
    # legs with claws
    for idx, side in [(22, 1), (58, -1), (84, 1), (104, -1)]:
        x, y = spine[idx]
        ax, ay = spine[idx - 1]
        bx, by = spine[idx + 1]
        ang = math.degrees(math.atan2(by - ay, bx - ax)) + side * 90
        leg = cubic_pts((x, y), pol(x, y, 90, ang + 30), pol(x, y, 150, ang - 10), pol(x, y, 200, ang + 20))
        s.path(ribbon_d(leg, widths[idx] * 0.55, widths[idx] * 0.4))
        ex, ey = leg[-1]
        for k in (-1, 0, 1):
            tip = pol(ex, ey, 70, ang + 20 + k * 35)
            s.path(f'M{P(ex, ey)} Q{P(*pol(ex, ey, 50, ang + 20 + k * 35 + 25))} {P(tip[0], tip[1])} Q{P(*pol(ex, ey, 40, ang + 20 + k * 35 - 10))} {P(ex, ey)} Z')
    # head at the start of the spine
    hx, hy = spine[0]
    s.begin(transform=f'translate({f(hx)} {f(hy)}) rotate(40)')
    for k in range(9):
        s.path(spike_d(0, 0, 150 + k * 15, 60, rnd.uniform(200, 280), 60, curl=20))
    s.path('M-100,-90 C-40,-150 120,-150 240,-110 C330,-80 380,-20 360,30 C330,80 220,70 150,70 C80,120 -20,130 -110,70 C-150,20 -140,-50 -100,-90 Z')
    s.path('M150,70 C200,110 300,120 360,30', fill='none')
    for k in range(5):
        x = 200 + k * 32
        s.path(f'M{P(x, 62)} L{P(x + 10, 95)} L{P(x + 20, 62)} Z')
    s.circle(40, -40, 34)
    s.circle(48, -46, 12)
    s.path('M-10,-80 Q40,-120 90,-80', fill='none')
    s.circle(300, -40, 14)
    s.path(ribbon_d(cubic_pts((-60, -120), (-120, -260), (-30, -330), (-100, -420)), 14, 4))
    s.path(ribbon_d(cubic_pts((20, -130), (0, -280), (90, -330), (60, -430)), 14, 4))
    s.path('M330,-20 C440,-60 520,20 600,-60', fill='none')
    s.path('M340,40 C450,60 520,140 620,110', fill='none')
    s.ellipse(-60, 0, 40, 26, rot=-20)
    s.end()
    # pearl
    px, py = pol(hx, hy, 430, -125)
    s.circle(px, py, 70)
    for k in range(6):
        s.path(petal_d(px, py, -90 + k * 20 - 50, 75, 150 + (k % 2) * 30, 34, 0.5))
    return s


# ----------------------------------------------------------------- hero academy pages


def hero_head(s, cx, cy, sc, hair='spiky', eyes='sharp', mouth='grin', mask=False, back_hair=True):
    """Anime head drawn in a scaled group. Canonical face spans x 520..980, y 440..1200 (centre ~750,820)."""
    s.begin(transform=f'translate({f(cx)} {f(cy)}) scale({f(sc)}) translate(-750 -820)', stroke_width=f(6 / sc))
    rnd = random.Random(int(cx + cy))
    if back_hair and hair == 'spiky':
        for ang in range(190, 355, 15):
            s.path(spike_d(750, 720, ang, 220, rnd.uniform(400, 520), 120, curl=rnd.uniform(-25, 25)))
    elif back_hair and hair == 'ponytail':
        s.path('M520,740 C500,500 1000,500 980,740 L980,900 L520,900 Z')
        s.path(ribbon_d(cubic_pts((1000, 620), (1250, 560), (1300, 900), (1180, 1250)), 70, 14))
    elif back_hair and hair == 'short':
        s.path('M510,760 C500,480 1000,480 990,760 L990,860 L510,860 Z')
    elif back_hair and hair == 'slick':
        s.path('M500,760 C480,420 1020,420 1000,760 L1000,820 L500,820 Z')
        for k in range(5):
            s.path(f'M{P(560 + k * 95, 480)} C{P(600 + k * 95, 600)} {P(540 + k * 95, 700)} {P(560 + k * 95, 790)}', fill='none')
    s.path('M698,1140 L706,1330 L794,1330 L802,1140 Z')
    s.path('M530,760 C525,980 615,1170 750,1200 C885,1170 975,980 970,760 C970,540 870,450 750,450 C630,450 530,540 530,760 Z')
    s.ellipse(528, 900, 22, 40)
    s.ellipse(972, 900, 22, 40)
    if mask:
        s.path('M520,780 C600,700 700,740 750,770 C800,740 900,700 980,780 C965,880 880,920 800,880 L750,860 L700,880 C620,920 535,880 520,780 Z')
    if eyes == 'sharp':
        anime_eye(s, 652, 910, 130, 120, sharp=True, lash_out=-1)
        anime_eye(s, 848, 910, 130, 120, sharp=True, lash_out=1)
        s.path(leaf_d(585, 790, 720, 822, 16))
        s.path(leaf_d(780, 822, 915, 790, 16))
    else:
        anime_eye(s, 652, 905, 140, 150, lash_out=-1)
        anime_eye(s, 848, 905, 140, 150, lash_out=1)
        s.path(leaf_d(582, 792, 712, 772, 9))
        s.path(leaf_d(788, 772, 918, 792, 9))
    s.path('M757,1010 Q773,1034 756,1048', fill='none')
    if mouth == 'grin':
        s.path('M700,1090 Q752,1142 812,1082 Q760,1110 700,1090 Z')
    elif mouth == 'shout':
        s.path('M690,1070 C720,1050 800,1050 820,1075 C815,1150 760,1180 740,1175 C700,1165 685,1110 690,1070 Z')
        s.path('M700,1080 Q755,1095 812,1082', fill='none')
    elif mouth == 'bigsmile':
        s.path('M620,1060 Q750,1200 880,1060 Q750,1120 620,1060 Z')
        s.path('M640,1072 Q750,1110 860,1072', fill='none')
        for k in range(1, 6):
            x = 640 + k * 37
            s.line(x, 1066 + abs(k - 3) * 3, x, 1088 + abs(k - 3) * 4)
    else:
        s.path('M712,1092 Q750,1130 788,1092 Q750,1112 712,1092 Z')
    if hair == 'spiky':
        s.path(hair_fringe_d(480, 1020, 460, [(540, 860), (620, 900), (700, 840), (780, 910), (860, 850), (940, 890)], 640))
        s.path('M720,470 C690,600 650,720 625,890', fill='none')
        s.path('M800,470 C830,620 850,740 858,840', fill='none')
    elif hair == 'ponytail':
        s.path(hair_fringe_d(470, 1030, 470, [(530, 840), (610, 870), (690, 810), (770, 880), (850, 830), (940, 870)], 700))
        s.path(ribbon_d(cubic_pts((490, 720), (430, 900), (470, 1100), (430, 1200)), 44, 6))
        s.path(ribbon_d(cubic_pts((1010, 720), (1070, 900), (1030, 1100), (1070, 1200)), 44, 6))
        s.ellipse(1010, 620, 40, 26, rot=20)
    elif hair == 'short':
        s.path(hair_fringe_d(480, 1020, 470, [(560, 760), (660, 800), (760, 740), (860, 800), (950, 760)], 640))
        s.path('M700,480 C680,580 660,660 650,760', fill='none')
    elif hair == 'slick':
        s.path('M500,780 C470,560 560,400 760,400 C980,400 1060,560 1000,780 C960,700 880,660 760,660 C640,660 560,700 500,780 Z')
        for k in range(4):
            s.path(f'M{P(600 + k * 100, 420 + (k % 2) * 20)} C{P(640 + k * 100, 520)} {P(600 + k * 100, 600)} {P(640 + k * 100, 680)}', fill='none')
    s.end()


def burst_d(cx, cy, n, r1, r2, rnd=None):
    rnd = rnd or random.Random(1)
    pts = []
    for i in range(n * 2):
        r = (r1 if i % 2 == 0 else r2) * rnd.uniform(0.85, 1.15)
        pts.append(pol(cx, cy, r, i * 180 / n))
    return poly_d(pts)


def bolt_d(x, y, ang, ln, w):
    """Zig-zag lightning bolt polygon."""
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    segs = [(0, 0), (0.3, 0.25), (0.45, -0.1), (0.75, 0.3), (1.0, 0.0)]
    left = [(x + ux * ln * t + nx * (off * w + w * 0.5 * (1 - t)), y + uy * ln * t + ny * (off * w + w * 0.5 * (1 - t))) for t, off in segs]
    right = [(x + ux * ln * t + nx * (off * w - w * 0.5 * (1 - t)), y + uy * ln * t + ny * (off * w - w * 0.5 * (1 - t))) for t, off in segs]
    return poly_d(left + list(reversed(right[:-1])))


def fist(s, cx, cy, r, ang=0):
    s.begin(transform=f'translate({f(cx)} {f(cy)}) rotate({ang})')
    s.ellipse(0, r * 0.95, r * 0.9, r * 0.35)
    s.circle(0, 0, r)
    for k in range(4):
        kx = -r * 0.66 + k * r * 0.44
        s.path(f'M{P(kx - r * 0.2, -r * 0.55)} A{f(r * 0.2)} {f(r * 0.2)} 0 0 1 {P(kx + r * 0.2, -r * 0.55)}', fill='none')
        s.line(kx, -r * 0.5, kx, r * 0.1)
    s.path(f'M{P(-r * 0.95, -r * 0.1)} C{P(-r * 1.1, r * 0.3)} {P(-r * 0.6, r * 0.6)} {P(-r * 0.3, r * 0.5)}', fill='none')
    s.end()


def boot(s, x, y, w, h, flip=1):
    s.path(f'M{P(x - w * 0.4, y - h)} L{P(x + w * 0.4, y - h)} L{P(x + w * 0.4, y - h * 0.25)} Q{P(x + flip * w * 0.9, y - h * 0.2)} {P(x + flip * w * 0.9, y)} L{P(x - w * 0.5, y)} Z')
    s.rect(x - w * 0.45, y - h, w * 0.9, h * 0.22, rx=6)


@page('hero_rookie', 'Rookie Hero', 'Hero Academy', 3, 'hero academy anime student punch action go')
def hero_rookie():
    s = Svg(PW, PH, 6)
    fx, fy = 1060, 420
    for ang in range(0, 360, 10):
        x1, y1 = pol(fx, fy, 420, ang)
        x2, y2 = pol(fx, fy, 1500, ang)
        s.line(x1, y1, x2, y2)
    s.path(burst_d(fx, fy, 18, 420, 300, random.Random(3)))
    rnd = random.Random(2)
    for _ in range(12):
        x, y = rnd.uniform(60, PW - 60), rnd.uniform(900, PH - 60)
        rock(s, x, y, rnd.uniform(14, 36), rnd.uniform(10, 26), int(x))
    # back arm
    s.path(ribbon_d(cubic_pts((520, 620), (430, 700), (370, 820), (340, 900)), 40, 32))
    s.circle(330, 930, 46)
    # torso and belt
    s.path('M500,590 C540,560 760,560 790,590 L750,930 L560,930 Z')
    s.path('M560,600 Q645,660 735,600', fill='none')
    s.polygon(star_pts(645, 740, 5, 62, 28, -90))
    s.rect(540, 925, 220, 54, rx=8)
    s.rect(560, 935, 50, 36, rx=6)
    s.rect(700, 935, 50, 36, rx=6)
    s.circle(652, 952, 20)
    # legs: back leg stretched, front knee up
    s.path(ribbon_d(cubic_pts((590, 960), (520, 1080), (470, 1200), (450, 1340)), 48, 36))
    boot(s, 440, 1500, 90, 160, -1)
    s.path(ribbon_d(cubic_pts((720, 960), (820, 1000), (860, 1080), (850, 1140)), 50, 44))
    s.circle(850, 1150, 46)
    s.path(ribbon_d(cubic_pts((850, 1150), (830, 1230), (800, 1290), (790, 1340)), 42, 34))
    boot(s, 790, 1480, 90, 150, 1)
    # head
    hero_head(s, 645, 420, 0.56, hair='spiky', eyes='sharp', mouth='shout')
    # punching arm and big fist
    s.path(ribbon_d(cubic_pts((780, 630), (860, 600), (930, 560), (980, 520)), 46, 52))
    s.ellipse(985, 515, 70, 44, rot=-40)
    fist(s, fx, fy, 135, -20)
    # action text
    s.text(1180, 1800, 'GO!', 230, italic=True, stroke_width=8)
    for k in range(6):
        x1, y1 = pol(1180, 1720, 170, 200 + k * 28)
        x2, y2 = pol(1180, 1720, 260, 200 + k * 28)
        s.line(x1, y1, x2, y2)
    return s


@page('hero_duo', 'Rival Partners', 'Hero Academy', 3, 'hero academy anime students quirk lightning vines uniform')
def hero_duo():
    s = Svg(PW, PH, 6)
    # emblem behind
    s.path('M750,120 L950,190 L930,420 Q750,520 570,420 L550,190 Z')
    s.path('M750,160 L910,215 L895,400 Q750,480 605,400 L590,215 Z')
    s.text(750, 370, 'H', 220, stroke_width=6)
    s.rect(-10, 1760, PW + 20, 260)
    s.ellipse(440, 1770, 180, 30)
    s.ellipse(1060, 1770, 180, 30)

    def figure(cx, girl):
        hy = 560
        # legs
        if girl:
            for lx in (cx - 45, cx + 45):
                s.path(ribbon_d([(lx, 1260), (lx, 1620)], 34, 30))
                s.rect(lx - 36, 1520, 72, 110, rx=10)
                s.ellipse(lx, 1720, 56, 34)
            s.path(f'M{P(cx - 120, 1000)} L{P(cx - 190, 1290)} L{P(cx + 190, 1290)} L{P(cx + 120, 1000)} Z')
            for k in range(-3, 4):
                s.line(cx + k * 40, 1000 + 40, cx + k * 60, 1290)
        else:
            for lx in (cx - 50, cx + 50):
                s.path(ribbon_d([(lx, 1250), (lx + (10 if lx > cx else -10), 1680)], 52, 44))
                s.ellipse(lx + (16 if lx > cx else -16), 1730, 70, 34)
            s.path(f'M{P(cx - 130, 1000)} L{P(cx - 140, 1270)} L{P(cx + 140, 1270)} L{P(cx + 130, 1000)} Z')
        # blazer
        s.path(f'M{P(cx - 160, 720)} C{P(cx - 120, 680)} {P(cx + 120, 680)} {P(cx + 160, 720)} L{P(cx + 140, 1040)} L{P(cx - 140, 1040)} Z')
        s.path(f'M{P(cx - 60, 700)} L{P(cx - 110, 900)} L{P(cx - 40, 870)} L{P(cx, 760)} Z')
        s.path(f'M{P(cx + 60, 700)} L{P(cx + 110, 900)} L{P(cx + 40, 870)} L{P(cx, 760)} Z')
        s.path(f'M{P(cx - 40, 700)} L{P(cx, 760)} L{P(cx + 40, 700)} L{P(cx + 20, 690)} L{P(cx, 720)} L{P(cx - 20, 690)} Z')
        if girl:
            s.path(f'M{P(cx, 770)} L{P(cx - 60, 740)} L{P(cx - 60, 800)} Z')
            s.path(f'M{P(cx, 770)} L{P(cx + 60, 740)} L{P(cx + 60, 800)} Z')
            s.circle(cx, 770, 14)
        else:
            s.path(f'M{P(cx, 760)} L{P(cx - 22, 820)} L{P(cx - 10, 940)} L{P(cx + 10, 940)} L{P(cx + 22, 820)} Z')
        for by in (900, 960):
            s.circle(cx, by, 9)
        s.rect(cx - 150, 940, 70, 70, rx=6)
        # arms
        up = -1 if girl else 1
        s.path(ribbon_d(cubic_pts((cx - up * 150, 740), (cx - up * 230, 800), (cx - up * 240, 950), (cx - up * 230, 1060)), 40, 34))
        s.circle(cx - up * 232, 1095, 40)
        s.path(ribbon_d(cubic_pts((cx + up * 150, 740), (cx + up * 260, 700), (cx + up * 300, 560), (cx + up * 290, 440)), 40, 34))
        s.circle(cx + up * 292, 410, 44)
        hero_head(s, cx, hy, 0.5, hair='ponytail' if girl else 'spiky', eyes='big' if girl else 'sharp', mouth='smile' if girl else 'grin')
        return cx + up * 292, 410

    hx, hy = figure(440, True)
    # vines and flowers around the girl's hand
    for a0, flip in [(200, 1), (330, -1), (90, 1)]:
        pts = []
        for t in range(0, 300, 6):
            rr = 50 + t * 0.55
            pts.append(pol(hx, hy, rr, a0 + flip * t))
        s.path(ribbon_d(pts, 10, 4))
        for i in (8, 22, 36):
            px, py = pts[i]
            tip = pol(px, py, 46, a0 + flip * i * 6 + 90 * flip)
            s.path(leaf_d(px, py, tip[0], tip[1], 14))
        flower_simple(s, pts[-1][0], pts[-1][1], 34, 5)
    bx, by = figure(1060, False)
    rnd = random.Random(5)
    for a in (-120, -60, 0, 60, 150, 210):
        s.path(bolt_d(*pol(bx, by, 60, a), a, rnd.uniform(150, 260), 26))
    for a in (-90, -30, 100, 180):
        px, py = pol(bx, by, 320, a)
        star(s, px, py, 20, 4, 0.35)
    return s


@page('hero_mentor', 'Symbol of Hope', 'Hero Academy', 3, 'hero academy pro hero muscles cape smile mentor')
def hero_mentor():
    s = Svg(PW, PH, 6)
    for ang in range(0, 360, 12):
        x1, y1 = pol(750, 520, 360, ang)
        x2, y2 = pol(750, 520, 1500, ang)
        s.line(x1, y1, x2, y2)
    # city at the bottom
    rnd = random.Random(7)
    x = -20
    while x < PW:
        w = rnd.uniform(90, 180)
        top = rnd.uniform(1550, 1750)
        s.rect(x, top, w, PH - top + 20)
        yy = top + 30
        while yy < PH - 40:
            xx = x + 18
            while xx + 22 < x + w - 10:
                s.rect(xx, yy, 22, 28)
                xx += 36
            yy += 44
        x += w
    # cape
    s.path('M300,760 C250,1000 180,1500 120,1900 Q400,1750 520,1820 L560,1100 L940,1100 L980,1820 Q1100,1750 1380,1900 C1320,1500 1250,1000 1200,760 Q750,650 300,760 Z')
    for k in range(5):
        s.path(f'M{P(330 + k * 50, 800)} C{P(300 + k * 50, 1200)} {P(260 + k * 40, 1500)} {P(220 + k * 40, 1820)}', fill='none')
        s.path(f'M{P(1170 - k * 50, 800)} C{P(1200 - k * 50, 1200)} {P(1240 - k * 40, 1500)} {P(1280 - k * 40, 1820)}', fill='none')
    # legs
    for lx in (640, 860):
        s.path(ribbon_d([(lx, 1420), (lx, 1700)], 80, 70))
        boot(s, lx, 1900, 160, 230, 1 if lx > 750 else -1)
    s.path('M560,1360 Q750,1420 940,1360 L900,1480 Q750,1540 600,1480 Z')
    # torso
    s.path('M330,800 C420,700 1080,700 1170,800 L1050,1100 L990,1400 Q750,1460 510,1400 L450,1100 Z')
    s.path('M470,820 C560,880 720,900 750,1010 C780,900 940,880 1030,820', fill='none')
    s.path('M560,1180 Q750,1240 940,1180', fill='none')
    s.line(750, 1010, 750, 1240)
    s.circle(750, 1120, 120)
    s.polygon(star_pts(750, 1120, 5, 100, 42, -90))
    s.rect(500, 1340, 500, 70, rx=12)
    s.rect(690, 1330, 120, 90, rx=14)
    s.circle(750, 1375, 24)
    # arms on hips
    for sg in (-1, 1):
        s.path(ribbon_d(cubic_pts((750 + sg * 400, 790), (750 + sg * 560, 850), (750 + sg * 600, 1050), (750 + sg * 520, 1250)), 95, 70))
        s.circle(750 + sg * 480, 1300, 80)
        s.ellipse(750 + sg * 500, 1225, 70, 36, rot=sg * 25)
        for k in range(3):
            s.path(f'M{P(750 + sg * (440 + k * 30), 1330)} Q{P(750 + sg * (450 + k * 30), 1300)} {P(750 + sg * (460 + k * 30), 1340)}', fill='none')
    s.path('M690,700 L700,800 L800,800 L810,700 Z')
    hero_head(s, 750, 480, 0.6, hair='slick', eyes='sharp', mouth='bigsmile', mask=True, back_hair=False)
    return s


@page('hero_academy', 'Hero Academy Gates', 'Hero Academy', 3, 'hero academy school gate robot training flying hero')
def hero_academy():
    s = Svg(PW, PH, 6)
    sun(s, 1300, 200, 90, 12, 70, 45)
    cloud(s, 350, 260, 300)
    cloud(s, 900, 180, 200)
    # flying hero with cape
    s.begin(transform='translate(330 520) rotate(-20)')
    for k in range(5):
        s.line(-180 - k * 30, -40 + k * 20, -320 - k * 30, -40 + k * 20)
    s.path('M-120,-10 C-200,40 -280,90 -340,150 Q-230,110 -140,60 Z')
    s.path(ribbon_d([(-110, 0), (90, 0)], 36, 30))
    s.path(ribbon_d([(70, -20), (200, -60)], 16, 12))
    s.path(ribbon_d([(70, 20), (200, 50)], 16, 12))
    s.circle(215, -66, 16)
    s.circle(215, 56, 16)
    s.path(ribbon_d([(-100, -14), (-200, -30)], 16, 12))
    s.path(ribbon_d([(-100, 14), (-200, 40)], 16, 12))
    s.circle(50, -4, 42)
    s.path('M20,-30 Q60,-70 100,-30', fill='none')
    s.end()
    # building
    s.rect(300, 700, 900, 560)
    s.rect(560, 560, 380, 160)
    s.path('M560,560 A190,120 0 0 1 940,560 Z')
    s.rect(745, 400, 10, 60)
    s.polygon([(755, 400), (820, 420), (755, 440)])
    for col in range(9):
        for row in range(5):
            s.rect(340 + col * 96, 740 + row * 96, 52, 60, rx=4)
    for col in range(4):
        s.rect(600 + col * 90, 600, 50, 90, rx=4)
    s.path('M700,1260 L700,1120 A50,50 0 0 1 800,1120 L800,1260 Z')
    s.line(750, 1120, 750, 1260)
    # trees and lawn
    ground(s, 1260)
    for x in (140, 1360):
        s.rect(x - 18, 1120, 36, 150)
        union_circles(s, [(x, 1030, 110), (x - 80, 1110, 80), (x + 80, 1110, 80), (x, 940, 80)])
    # gate pillars and sign
    for x in (420, 1000):
        s.rect(x, 1000, 80, 360)
        s.rect(x - 14, 980, 108, 36, rx=6)
        s.circle(x + 40, 955, 30)
    s.rect(460, 880, 580, 110, rx=14)
    s.text(750, 962, 'HERO ACADEMY', 64, stroke_width=3)
    # path
    s.path('M560,1360 Q500,1700 380,2010 L1120,2010 Q1000,1700 940,1360 Z')
    for y in range(1420, 2000, 90):
        s.line(560 - (y - 1360) * 0.27, y, 940 + (y - 1360) * 0.27, y)
    # training robot
    s.rect(1080, 1480, 260, 240, rx=20)
    s.rect(1120, 1360, 180, 130, rx=16)
    s.circle(1210, 1425, 40)
    s.circle(1210, 1425, 16)
    s.line(1210, 1360, 1210, 1300)
    s.circle(1210, 1288, 14)
    s.rect(1120, 1560, 180, 50, rx=10)
    for k in range(4):
        s.line(1150 + k * 40, 1560, 1150 + k * 40, 1610)
    s.rect(1040, 1700, 340, 90, rx=45)
    for k in range(4):
        s.circle(1090 + k * 80, 1745, 26)
    s.path(ribbon_d(cubic_pts((1080, 1540), (980, 1560), (940, 1640), (960, 1700)), 30, 26))
    s.circle(962, 1715, 36)
    s.path(ribbon_d(cubic_pts((1340, 1540), (1430, 1500), (1470, 1420), (1480, 1360)), 30, 26))
    for k in range(3):
        s.line(1480, 1360, 1465 + k * 20, 1300)
    # waving student
    s.rect(240, 1690, 56, 130, rx=14)
    s.rect(310, 1690, 56, 130, rx=14)
    s.path('M220,1520 C240,1480 360,1480 380,1520 L370,1700 L230,1700 Z')
    s.path(ribbon_d(cubic_pts((230, 1540), (170, 1500), (130, 1420), (140, 1340)), 22, 18))
    s.circle(140, 1320, 24)
    s.path(ribbon_d(cubic_pts((370, 1540), (410, 1600), (420, 1660), (410, 1700)), 22, 18))
    s.circle(412, 1718, 22)
    hero_head(s, 300, 1400, 0.28, hair='short', eyes='big', mouth='smile')
    s.ellipse(268, 1835, 40, 16)
    s.ellipse(338, 1835, 40, 16)
    return s


# ----------------------------------------------------------------- main

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    index = []
    for p in PAGES:
        if ONLY and p['id'] not in ONLY:
            continue
        svg = p['fn']()
        out = os.path.join(OUT_DIR, p['id'] + '.png')
        svg.render(out)
        kb = os.path.getsize(out) // 1024
        print(f"{p['id']:16s} {svg.w}x{svg.h} {kb:5d} KB")
    if not ONLY:
        for p in PAGES:
            index.append({k: p[k] for k in ('id', 'title', 'category', 'difficulty', 'tags')})
        with open(os.path.join(OUT_DIR, 'index.json'), 'w') as fh:
            json.dump(index, fh, indent=1)
        print(f'{len(index)} pages written to {OUT_DIR}')


if __name__ == '__main__':
    main()
