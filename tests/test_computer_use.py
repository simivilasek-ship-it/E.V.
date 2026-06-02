import pytest

from computer_use import UIElement, format_tree, find_by_text

pytestmark = [pytest.mark.unit]


def test_format_tree_and_find():
    root = UIElement(id="root", role="root", name="")
    btn = UIElement(id="1", role="button", name="Settings")
    root.children.append(btn)

    txt = format_tree(root)
    assert "button" in txt
    assert "Settings" in txt

    found = find_by_text(root, "sett")
    assert found is not None
    assert found.id == "1"
