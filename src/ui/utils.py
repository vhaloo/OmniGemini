import re

def rich_to_html(rich_text):
    # Colors
    text = rich_text.replace("[bold green]", "<b style='color: #A6E3A1'>").replace("[/bold green]", "</b>")
    text = text.replace("[green]", "<span style='color: #A6E3A1'>").replace("[/green]", "</span>")
    text = text.replace("[bold red]", "<b style='color: #F38BA8'>").replace("[/bold red]", "</b>")
    text = text.replace("[red]", "<span style='color: #F38BA8'>").replace("[/red]", "</span>")
    text = text.replace("[bold blue]", "<b style='color: #89B4FA'>").replace("[/bold blue]", "</b>")
    text = text.replace("[bold cyan]", "<b style='color: #89DCEB'>").replace("[/bold cyan]", "</b>")
    text = text.replace("[bold magenta]", "<b style='color: #CBA6F7'>").replace("[/bold magenta]", "</b>")
    text = text.replace("[bold white]", "<b style='color: #CDD6F4'>").replace("[/bold white]", "</b>")
    text = text.replace("[yellow]", "<span style='color: #F9E2AF'>").replace("[/yellow]", "</span>")
    text = text.replace("[dim]", "<span style='color: #6C7086'>").replace("[/dim]", "</span>")

    # Markdown-ish
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'`(.+?)`', r'<code style="background-color:#313244; padding:2px 4px; border-radius:4px;">\1</code>', text)

    return text.replace("\n", "<br>")
