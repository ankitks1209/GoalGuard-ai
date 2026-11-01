"""Token guard contract: prevent literals without rejecting financial data."""
import unittest
from scripts.check_design_tokens import violations


class DesignTokenTests(unittest.TestCase):
    def test_css_literals_rejected_with_line_numbers(self):
        for value in ('#fff', 'rgb(1 2 3)', 'oklch(50% 0 0)', 'red'):
            with self.subTest(value=value):
                self.assertEqual(violations(f'/* heading */\na {{ color: {value}; }}', '.css')[0][0], 2)
        for rule in ('padding: 12px', 'gap: .5rem', 'border: 1px solid currentColor',
                     '@media (max-width: 800px)', 'border-radius: 4px'):
            with self.subTest(rule=rule):
                self.assertTrue(violations(rule, '.css'))

    def test_variables_keywords_comments_and_layout_ratios_pass(self):
        css = '''/* old red and 12px */
        a { color: var(--color-ink); padding: var(--space-2); margin: 0 auto;
            background: transparent; border-color: currentColor;
            grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); width: 100%; }
        a::after { content: "12px red"; }'''
        self.assertEqual(violations(css, '.css'), [])

    def test_component_style_and_svg_literals_rejected(self):
        for source in ('<div style={{ padding: 12 }} />',
                       '<div style={{ color: "red" }} />',
                       '<svg stroke="#fff" strokeWidth={2} />',
                       '<div style={{ marginTop: "1rem" }} />'):
            with self.subTest(source=source):
                self.assertTrue(violations(source, '.tsx'))

    def test_financial_values_and_svg_geometry_are_not_style_tokens(self):
        source = '''const cents = 1200;
        const item = { amount_cents: 100, color: "blue" };
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M0 0L24 24" /></svg>
        <div style={{ padding: "var(--space-2)", margin: 0 }} />'''
        self.assertEqual(violations(source, '.tsx'), [])

    def test_embedded_css_is_checked(self):
        self.assertTrue(violations('const css = `a { padding: 12px; }`', '.ts'))
