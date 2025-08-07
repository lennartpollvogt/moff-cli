from markdown_to_data import Markdown
from pathlib import Path
from rich import print

markdown_file = Path("moff-cli/collector/tech_collector.md")
markdown_content = markdown_file.read_text()

def main():
    markdown = Markdown(markdown_content)
    print(markdown.md_list)

if __name__ == "__main__":
    main()
