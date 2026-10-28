# SPDX-License-Identifier: Apache-2.0
"""Render the exact authored example, without running an experiment."""
from __future__ import annotations
import html
import json
from pathlib import Path


def build(source: Path, target: Path) -> None:
    d = json.loads(source.read_text())
    e = {x['id']: x for x in d['experiments']}
    if d['hypotheses'] != ['H0', 'H1', 'H2', 'H3'] or set(e) != {'screen', 'left', 'right'}:
        raise ValueError('Example figure requires the declared four-hypothesis source')
    expected = {'screen': {'H0':['L','L2'], 'H1':['L','L2'], 'H2':['R','R2'], 'H3':['R','R2']}, 'left':{'H0':['a','a2'], 'H1':['b','b2'], 'H2':['x'], 'H3':['x']}, 'right':{'H0':['x'], 'H1':['x'], 'H2':['c','c2'], 'H3':['d','d2']}}
    if any(e[k]['outcomes'] != expected[k] or not e[k]['allowed'] for k in expected):
        raise ValueError('Example observation model changed; revise the figure explicitly')
    worst = e['screen']['cost'] + max(e['left']['cost'],e['right']['cost'])
    static = e['left']['cost'] + e['right']['cost']
    if worst != 3 or static != 4 or d['max_cost'] != 3 or d['max_experiments'] != 2:
        raise ValueError('Example budget or costs changed; revise caption')
    def obs(probe: str, h: str) -> str:
        return html.escape(' / '.join(e[probe]['outcomes'][h]))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="880" height="310" viewBox="0 0 880 310" role="img" aria-labelledby="ex_title ex_desc">
<title id="ex_title">The executed authored example: pay only for the observed branch</title><desc id="ex_desc">A screen costs one unit. L or L2 leads to the left test; R or R2 leads to the right test. Each branch test costs two units. All possible observations lead to exactly one compatible hypothesis. Worst path cost is three units; purchasing both branch tests statically costs four.</desc>
<defs><marker id="ex_arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#71598b"/></marker></defs>
<rect width="880" height="310" fill="white"/>
<g font-family="DejaVu Sans,sans-serif" fill="#302447" text-anchor="middle">
<rect x="340" y="10" width="200" height="44" rx="7" fill="#302447"/>
<text x="440" y="38" fill="white" font-size="20" font-weight="bold">screen · {e['screen']['cost']} unit</text>
<path d="M440 54V76H220V110M440 76H660V110" stroke="#71598b" stroke-width="2" fill="none" marker-end="url(#ex_arrow)"/>
<text x="220" y="95" font-size="17">{obs('screen','H0')}</text><text x="660" y="95" font-size="17">{obs('screen','H2')}</text>
<rect x="130" y="118" width="180" height="40" rx="7" fill="#edf5f5" stroke="#8db5b9"/>
<rect x="570" y="118" width="180" height="40" rx="7" fill="#f4f0f8" stroke="#cbbddc"/>
<text x="220" y="145" font-size="19" font-weight="bold">left · {e['left']['cost']} units</text><text x="660" y="145" font-size="19" font-weight="bold">right · {e['right']['cost']} units</text>
<path d="M220 158V179H110V215M220 179H330V215M660 158V179H550V215M660 179H770V215" fill="none" stroke="#71598b" stroke-width="2" marker-end="url(#ex_arrow)"/>
<text x="110" y="201" font-size="17">{obs('left','H0')}</text><text x="330" y="201" font-size="17">{obs('left','H1')}</text><text x="550" y="201" font-size="17">{obs('right','H2')}</text><text x="770" y="201" font-size="17">{obs('right','H3')}</text>
'''
    for x, h in zip([110,330,550,770],d['hypotheses']):
        svg += f'<rect x="{x-50}" y="223" width="100" height="39" rx="6" fill="#fff8ed" stroke="#b88a50"/><text x="{x}" y="249" font-size="20" font-weight="bold">{h}</text>\n'
    svg += f'<text x="440" y="296" font-size="17">Worst contingent path: {worst} units · Static left + right: {static} units · Units are not currency</text></g></svg>\n'
    target.write_text(svg)
