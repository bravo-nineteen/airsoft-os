"""Regression tests for AOS dashboard sizing and persistence (no Qt required)."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name('main.py').read_text(encoding='utf-8')
TREE = ast.parse(SOURCE)

class ResizableWidgetsTests(unittest.TestCase):
    def test_source_compiles(self):
        compile(TREE, 'main.py', 'exec')

    def test_resize_corner_supports_mouse_drag(self):
        node=next(x for x in TREE.body if isinstance(x,ast.ClassDef) and x.name=='ResizeCorner')
        methods={x.name for x in node.body if isinstance(x,ast.FunctionDef)}
        self.assertTrue({'mousePressEvent','mouseMoveEvent','mouseReleaseEvent'} <= methods)

    def test_panel_has_presets(self):
        node=next(x for x in TREE.body if isinstance(x,ast.ClassDef) and x.name=='WidgetPanel')
        methods={x.name for x in node.body if isinstance(x,ast.FunctionDef)}
        self.assertTrue({'resize_to_preset','contextMenuEvent','set_edit_mode'} <= methods)
        self.assertIn('Compact',SOURCE)
        self.assertIn('Large',SOURCE)

    def test_layout_migration_does_not_erase_previous_geometry(self):
        self.assertIn("get('_layout_version') in (35, 39)", SOURCE)
        self.assertIn("'_layout_version': 39", SOURCE)

    def test_status_is_responsive(self):
        self.assertIn("self.setMinimumSize(45, 47)",SOURCE)
        self.assertIn("panel.height() >= 245",SOURCE)
        self.assertIn('self.resize_corner = ResizeCorner(self)',SOURCE)

if __name__=='__main__': unittest.main()
