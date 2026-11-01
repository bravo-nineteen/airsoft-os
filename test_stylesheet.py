"""Regression test for the startup crash seen in AOS 3.8.1."""
import ast
import pathlib
import unittest
P=pathlib.Path(__file__).with_name('main.py')
class StyleTests(unittest.TestCase):
    def test_fstring_only_has_intended_fields(self):
        tree=ast.parse(P.read_text(encoding='utf-8'))
        style=next(node.value for node in tree.body if isinstance(node,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='STYLE' for t in node.targets))
        self.assertIsInstance(style,ast.JoinedStr)
        self.assertEqual([n.value.id for n in style.values if isinstance(n,ast.FormattedValue)
                and isinstance(n.value,ast.Name)],['TEXT','MUTED'])
        self.assertTrue(all(isinstance(n.value,ast.Name) for n in style.values
            if isinstance(n,ast.FormattedValue)))
    def test_stylesheet_is_valid_css_not_python(self):
        source=P.read_text(encoding='utf-8')
        tree=ast.parse(source)
        code=compile(ast.Module(body=[node for node in tree.body if isinstance(node,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='STYLE' for t in node.targets)],type_ignores=[]),str(P),'exec')
        env={'TEXT':'#e4e9e8','MUTED':'#a3b0ad'}
        exec(code,env)
        css=env['STYLE']
        self.assertIn('QTextEdit, QLineEdit',css)
        self.assertIn('background: #101b1d;',css)
        self.assertNotIn('{{',css)
        self.assertNotIn('}}',css)
        self.assertEqual(css.count('{'),css.count('}'))
    def test_source_compiles(self):
        compile(P.read_text(encoding='utf-8'),str(P),'exec')
if __name__ == '__main__': unittest.main()
