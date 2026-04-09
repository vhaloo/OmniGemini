import sys
from unittest.mock import MagicMock

# Mocking dependencies before importing src.gui
mock_sd = MagicMock()
sys.modules["sounddevice"] = mock_sd

mock_widgets = MagicMock()
sys.modules["PyQt6.QtWidgets"] = mock_widgets
mock_gui = MagicMock()
sys.modules["PyQt6.QtGui"] = mock_gui
mock_core = MagicMock()
sys.modules["PyQt6.QtCore"] = mock_core
mock_pyqt6 = MagicMock()
sys.modules["PyQt6"] = mock_pyqt6

mock_console = MagicMock()
sys.modules["rich.console"] = mock_console
mock_rich = MagicMock()
sys.modules["rich"] = mock_rich

# Mocking config if needed, though it seems safe to import
# but let's be safe to avoid side effects
mock_config = MagicMock()
sys.modules["src.config"] = mock_config

from src.gui import rich_to_html

def test_import():
    assert rich_to_html is not None

def test_color_replacements():
    # Test all 10 color tag pairs
    assert rich_to_html("[bold green]text[/bold green]") == "<b style='color: #A6E3A1'>text</b>"
    assert rich_to_html("[green]text[/green]") == "<span style='color: #A6E3A1'>text</span>"
    assert rich_to_html("[bold red]text[/bold red]") == "<b style='color: #F38BA8'>text</b>"
    assert rich_to_html("[red]text[/red]") == "<span style='color: #F38BA8'>text</span>"
    assert rich_to_html("[bold blue]text[/bold blue]") == "<b style='color: #89B4FA'>text</b>"
    assert rich_to_html("[bold cyan]text[/bold cyan]") == "<b style='color: #89DCEB'>text</b>"
    assert rich_to_html("[bold magenta]text[/bold magenta]") == "<b style='color: #CBA6F7'>text</b>"
    assert rich_to_html("[bold white]text[/bold white]") == "<b style='color: #CDD6F4'>text</b>"
    assert rich_to_html("[yellow]text[/yellow]") == "<span style='color: #F9E2AF'>text</span>"
    assert rich_to_html("[dim]text[/dim]") == "<span style='color: #6C7086'>text</span>"

def test_markdown_and_newlines():
    # Test markdown bold
    assert rich_to_html("**bold text**") == "<b>bold text</b>"
    # Test markdown italic
    assert rich_to_html("*italic text*") == "<i>italic text</i>"
    # Test markdown code
    assert rich_to_html("`code block`") == '<code style="background-color:#313244; padding:2px 4px; border-radius:4px;">code block</code>'
    # Test newlines
    assert rich_to_html("line 1\nline 2") == "line 1<br>line 2"
    # Test combined
    input_text = "[bold green]**Alert**[/bold green]\n`system failure`"
    expected_output = "<b style='color: #A6E3A1'><b>Alert</b></b><br><code style=\"background-color:#313244; padding:2px 4px; border-radius:4px;\">system failure</code>"
    assert rich_to_html(input_text) == expected_output
