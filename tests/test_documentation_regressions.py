"""项目文档与构建入口回归测试。"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_script_is_at_repository_root_and_uses_its_directory_as_root():
    source = (ROOT / "build.sh").read_text(encoding="utf-8")

    assert 'PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"' in source
    assert not (ROOT / "pastelabel" / "build.sh").exists()


def test_documentation_uses_pastelabel_log_without_a_leading_dot():
    for path in (ROOT / "README.md", ROOT / "docs" / "user_guide.md", ROOT / "docs" / "project_structure.md"):
        source = path.read_text(encoding="utf-8")
        assert "pastelabel.log" in source
        assert ".pastelabel.log" not in source


def test_build_script_does_not_list_removed_hidden_imports():
    source = (ROOT / "build.sh").read_text(encoding="utf-8")

    assert "pastelabel.ui.widgets" not in source
    assert "pastelabel.ui.styles" not in source
    assert "pastelabel.core.models" not in source


def test_documentation_describes_stats_color_replacement_and_separate_wheel_steps():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "user_guide.md").read_text(encoding="utf-8")

    for source in (readme, guide):
        assert "颜色替换" in source
        assert "HTML色值" in source
        assert "检测框缩放步长" in source
        assert "贴图缩放步长" in source
        assert "检测框滚轮缩放" in source
        assert "贴图滚轮缩放" in source
