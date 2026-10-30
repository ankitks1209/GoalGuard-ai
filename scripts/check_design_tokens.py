"""Reject raw design values in production styles; canonical tokens own literals.

This conservative source guard complements visual review. It checks CSS and
literal JSX style/SVG attributes, not computed JavaScript styling expressions.
SVG path coordinates and business numbers are deliberately outside its scope.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOKEN_FILE = ROOT / 'src/styles/tokens.css'
RAW = re.compile(r'#[\da-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\(|(?<![\w-])-?(?:\d*\.)?\d+(?:px|r?em|ch|ex|v[wh]|vmin|vmax|pt|cm|mm|in)\b', re.I)
COLOR = re.compile(r'(?<![\w-])(?:color|background(?:-color)?|border(?:-\w+)?-color|fill|stroke)\s*:\s*([^;{}]+)')
ALLOWED = {'none', 'transparent', 'currentcolor', 'inherit', 'initial', 'unset', 'revert', 'revert-layer'}
STYLE = re.compile(r'\bstyle\s*=\s*\{\{(.*?)\}\}', re.S)
STYLE_VALUE = re.compile(r'(?:[\w-]+|[\'"][\w-]+[\'"])\s*:\s*([\'"][^\'"]*[\'"]|-?\d+(?:\.\d+)?)')
SVG = re.compile(r'\b(?:fill|stroke|strokeWidth|stroke-width)\s*=\s*(?:([\'"])(.*?)\1|\{(\d+(?:\.\d+)?)\})', re.S)


def _blank(match: re.Match[str]) -> str:
    return re.sub(r'[^\n]', ' ', match.group())


def violations(source: str, suffix: str) -> list[tuple[int, str]]:
    """Return line and offending value; never evaluate source code."""
    clean = re.sub(r'/\*.*?\*/', _blank, source, flags=re.S)
    found: set[tuple[int, str]] = set()

    def add(offset: int, value: str) -> None:
        found.add((clean.count('\n', 0, offset) + 1, value.strip()))

    def css(text: str, offset: int = 0) -> None:
        text = re.sub(r'([\'"])(?:\\.|(?!\1).)*?\1', _blank, text)
        # Token references can contain digits; they are not numeric literals.
        text = re.sub(r'var\(\s*--[\w-]+\s*\)', _blank, text)
        for match in RAW.finditer(text):
            add(offset + match.start(), match.group())
        for match in COLOR.finditer(text):
            value = match.group(1).strip().lower()
            if value and value not in ALLOWED:
                add(offset + match.start(1), value)

    if suffix == '.css':
        css(clean)
    else:
        for block in re.finditer(r'`([^`]*)`', clean, re.S):
            if '{' in block.group(1) and ':' in block.group(1):
                css(block.group(1), block.start(1))
        for block in STYLE.finditer(clean):
            for match in STYLE_VALUE.finditer(block.group(1)):
                value = match.group(1).strip('\'"')
                if value != '0' and value.lower() not in ALLOWED and not re.fullmatch(r'var\(\s*--[\w-]+\s*\)', value):
                    add(block.start(1) + match.start(1), value)
        for match in SVG.finditer(clean):
            value = match.group(2) if match.group(1) else match.group(3)
            if value.lower() not in ALLOWED and not value.startswith('var(--') and value != '0':
                add(match.start(), value)
    return sorted(found)


def main() -> int:
    files = sorted({path for folder in (ROOT / 'frontend/src', ROOT / 'src')
                    for path in folder.rglob('*')
                    if path.suffix in {'.css', '.ts', '.tsx', '.js', '.jsx'}
                    and '.test.' not in path.name and 'test' not in path.parts})
    count = 0
    for path in files:
        if path == TOKEN_FILE:
            continue
        for line, value in violations(path.read_text(), path.suffix):
            print(f'{path.relative_to(ROOT)}:{line}: raw design value {value!r}; use src/styles/tokens.css')
            count += 1
    print(f'Design tokens: {count} violation(s) across {len(files)} files.')
    return int(count > 0)


if __name__ == '__main__':
    sys.exit(main())
