import argparse
import difflib
import token
import tokenize
from contextlib import suppress

from brm import NO_LINE, TokenTransformer, get_type_from_name, pattern

dot_name = "(name( dot name)*)"


class ImportFixer(TokenTransformer):
    def __init__(self, modules, names):
        self.modules = modules
        self.names = names

    # import foo
    # import foo, bar
    @pattern("name", f"({dot_name}( comma {dot_name})*)", "(newline|nl)")
    def fix_import_stmt(self, stmt, *tokens):
        if stmt.string != "import":
            return

        module = []
        commas = {}
        modules = {}
        token_info = iter(tokens)

        def add_module(comma):
            pretty_name = "".join(
                token_info.string
                for token_info in module
                if self._get_type(token_info) != token.COMMA
            )
            modules[pretty_name] = module.copy()
            commas[pretty_name] = comma
            module.clear()

        with suppress(StopIteration):
            while (current := next(token_info)).type not in {
                token.NEWLINE,
                token.NL,
            }:
                token_type = self._get_type(current)
                if token_type == token.COMMA:
                    add_module(current)
                else:
                    module.append(current)

            else:
                add_module(None)
                newline = current

        removeds = 0
        fixed_tokens = []
        for module, module_tokens in modules.items():
            if module in self.modules:
                removeds += 1
                continue
            fixed_tokens.extend(module_tokens)
            if commas.get(module):
                fixed_tokens.append(commas[module])

        any_imports = removeds < len(modules)
        if any_imports:
            fixed_tokens.insert(0, stmt)

        if fixed_tokens and self._get_type(fixed_tokens[-1]) == token.COMMA:
            fixed_tokens.pop()

        if any_imports:
            fixed_tokens.append(newline)
        else:
            fixed_tokens.append(NO_LINE)

        return fixed_tokens

    # from foo import bar
    # from foo import bar, baz
    # from foo import (
    #   foo,
    #   bar,
    #   baz
    # )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove-modules", nargs="*")
    namespace = parser.parse_args()
    fixer = ImportFixer(namespace.remove_modules or [], [])
    with open("test.py") as f:
        content = f.read()
        result = fixer.transform(content)

    for line in difflib.unified_diff(
        content.splitlines(), result.splitlines(), n=1
    ):
        print(line)


if __name__ == "__main__":
    main()
