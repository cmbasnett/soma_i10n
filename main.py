from typing import Set
from xml.etree import ElementTree
import argparse
import polib
import yaml
import dotenv
import subprocess
import os
from pathlib import Path

# Load the environment variables from the .env file.
dotenv.load_dotenv()

SOMA_PATH = Path(os.getenv('SOMA_PATH'))
SOMA_FONTS_PATH = SOMA_PATH / 'fonts'
SOMA_CONFIG_PATH = SOMA_PATH / 'config'
FONTS_PATH = Path('.') / 'fonts'
BMFONT_PATH = Path('.') / 'bin' / 'bmfont64.exe'


# Find all instances of [uDDDD] in the string and replace them with the corresponding unicode character.
# Note that the unicode identifiers are in decimal format.
# Use regex to find all instances of [uDDDD] in the string.
def parse_unicode_string(string: str):
    import re
    pattern = re.compile(r'\[u(\d+)]')
    while match := pattern.search(string):
        unicode_char = chr(int(match.group(1)))
        # Replace the unicode character in the string in-place using the match.span() method.
        start, end = match.span()
        string = string[:start] + unicode_char + string[end:]
    return string




class LangFile:

    def __init__(self):
        self.categories = []

    class Entry:
        def __init__(self, name: str, value: str):
            self.name = name
            self.value = value

    class Category:
        def __init__(self, name: str):
            self.name = name
            self.entries = []

        def add_entry(self, name: str, value: str):
            entry = LangFile.Entry(name, value)
            self.entries.append(entry)
            return entry

    def add_category(self, category_name) -> Category:
        category = LangFile.Category(category_name)
        self.categories.append(category)
        return category

    def get_or_add_category(self, category_name) -> Category:
        for category in self.categories:
            if category.name == category_name:
                return category
        return self.add_category(category_name)

    def save(self, path: str):
        with open(path, 'w', encoding='utf-8') as file:
            file.write('<?xml version="1.0" encoding="utf-8"?>\n')
            file.write('<LANG>\n')
            for category in self.categories:
                file.write(f'  <CATEGORY Name="{category.name}">\n')
                for entry in category.entries:
                    file.write(f'    <Entry Name="{entry.name}">{entry.value}</Entry>\n')
                file.write('  </CATEGORY>\n')
            file.write('</LANG>\n')

    def get_unique_characters(self) -> Set[str]:
        characters = set()
        for category in self.categories:
            for entry in category.entries:
                for character in entry.value:
                    characters.update(character)
        return characters

def parse_control_chars(string: str):
    string = parse_unicode_string(string)
    line_break = '[br]'
    string = string.replace(line_break, '\n')
    return string

def parse_langfile(path: str) -> LangFile:
    # Parse the lang file as an XML file
    lang_file = LangFile()
    with open(path, 'r', encoding='utf-8') as file:
        data = file.read()
        tree = ElementTree.fromstring(data)
        resources = tree.find('RESOURCES')
        if resources is not None:
            pass
        categories = tree.findall('CATEGORY')
        for category in categories:
            category_name = category.get('Name')
            entries = category.findall('Entry')
            category = lang_file.add_category(category_name)
            for entry in entries:
                entry_name = entry.get('Name')
                if entry.text is not None:
                    category.add_entry(entry_name, parse_control_chars(entry.text))
    return lang_file


def convert_langfile_to_po(filename, langfile: LangFile):
    po = polib.POFile()
    po.metadata = {
        'Language': 'en',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain',
        'Content-Transfer-Encoding': '8bit; charset=UTF-8'
    }

    for category in langfile.categories:
        for entry in category.entries:
            # Escape the double quotes in the string.
            msgid = f'{category.name}/{entry.name}'
            entry = polib.POEntry(msgid=msgid, msgstr=entry.value)
            po.append(entry)

    return po


def potext_to_langtext(text: str):
    # For any characters outside the ASCII range, replace them with the corresponding [uDDDD] format.

    # Convert newlines to [br] tags.
    text = text.replace('\n', '[br]')

    # First, convert the string to a list of characters.
    chars = list(text)

    # Iterate over the characters in the list.
    for i, char in enumerate(chars):
        if ord(char) > 127:
            # Replace the character in the list with the corresponding [uDDDD] format.
            chars[i] = f'[u{ord(char)}]'

    # Join the list of characters back into a string.
    return ''.join(chars)


def convert_po_to_langfile(filename):
    po = polib.pofile(filename)
    langfile = LangFile()
    for entry in po:
        category_name, entry_name = entry.msgid.split('/')
        category = langfile.get_or_add_category(category_name)

        # Replace the unicode characters in the string with the corresponding [uDDDD] format.
        entry.msgstr = entry.msgstr.replace('\n', '[br]')

        value = potext_to_langtext(entry.msgstr)

        category.add_entry(entry_name, value)
    return langfile

def export(input_path: str):
    pass

def import_(input_path: str):
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # Add subparsers for each command.
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    # Add a subparser for the 'export' command.
    lang2po = subparsers.add_parser('lang2po', help='Convert a LANG file to a PO file')
    lang2po.add_argument('path', type=str, help='Path to the LANG file')
    lang2po.add_argument('--output', type=str, help='Path to the output PO file')

    # Add a subparser for the 'import' command.
    po2lang = subparsers.add_parser('po2lang', help='Convert a PO file to a LANG file')
    po2lang.add_argument('path', type=str, help='Path to the PO file')
    po2lang.add_argument('--output', type=str, help='Path to the output LANG file')

    # Add subparser for the 'font' command.
    makefont = subparsers.add_parser('makefont', help='Create a font file from ')
    makefont.add_argument('language', type=str, help='Language code')

    args = parser.parse_args()

    from pathlib import Path

    match args.command:
        case 'makefont':
            # Load the languages.yaml file.
            with open('languages.yaml', 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)

                # Make sure the language code is in the languages.yaml file.
                languages = data['languages']

                # Create a map of language names to language objects.
                languages = {language['name']: language for language in languages}
                language = languages.get(args.language, None)

                if language is None:
                    print(f'Language {args.language} not found in languages.yaml')
                    exit(1)

                characters = set()

                # Read the charsets from the languages files.
                charsets = {charset['name']: charset for charset in data['charsets']}

                # Add the characters from the charsets to the set of characters.
                for charset_name in language['charsets']:
                    charset = charsets.get(charset_name, None)
                    if charset is None:
                        print(f'Charset {charset_name} not found in charsets')
                        exit(1)

                    # Characters can be either individual codepoints or codepoint ranges (as a list)
                    # Note that we are using hex codes.
                    for char in charset['characters']:
                        if isinstance(char, int):
                            characters.add(chr(char))
                        elif isinstance(char, list):
                            start, end = char
                            characters.update(chr(codepoint) for codepoint in range(start, end + 1))

                for langfile in language['lang_files']:
                    langfile_path = SOMA_PATH / langfile

                    if not langfile_path.exists():
                        print(f'Language file {langfile_path} not found')
                        exit(1)

                    langfile = parse_langfile(langfile_path)
                    characters |= langfile.get_unique_characters()

                # Write the characters to a temporary file.
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-16', delete=False) as file:
                    # Get the path to the temporary file.
                    textfile_path = file.name
                    file.write(''.join(characters))

                # Create the font file using the bmfont tool.
                for font in language['fonts']:
                    font_path = FONTS_PATH / f'{font}.bmfc'

                    if not font_path.exists():
                        print(f'Font file {font_path} not found')
                        exit(1)

                    input_path = font_path
                    output_path = SOMA_FONTS_PATH / f'{font}.fnt'

                    bmfont_args = [BMFONT_PATH, '-c', font_path, '-o', output_path, '-t', textfile_path]

                    print(bmfont_args)

                    subprocess.run(bmfont_args)

                # Run the bmfont tool to create the font file.

        case 'lang2po':
            print('Converting LANG file to PO file...')
            langfile = parse_langfile(args.path)
            print('Categories:', len(langfile.categories))
            for category in langfile.categories:
                print(f'  {category.name}: {len(category.entries)} entries')
            print(args.path)
            pofile = convert_langfile_to_po(args.path, langfile)

            # Replace the file extension with '.po' and save the file.
            output_path = Path(args.path).with_suffix('.po')

            pofile.save(output_path)
        case 'po2lang':
            langfile = convert_po_to_langfile(args.path)

            output_path = Path(args.path).with_suffix('.lang')

            langfile.save(output_path)
