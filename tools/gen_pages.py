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
