import argparse
import difflib
import token
import tokenize
from contextlib import suppress

from brm import NoLineTransposer, TokenTransformer, get_type_from_name, pattern

dot_name = "(name( dot name)*)"


class ImportFixer(TokenTransformer):
    def __init__(self, modules, names):
        self.modules = modules
        self.names = names

    # import foo
    # import foo, bar
    # import foo, foo.bar
    # import foo.bar, bar.foo
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

        removeds, remove_offset = 0, 0
        first_import_removed = tuple(modules.keys())[0] in self.modules
        fixed_tokens = []
        for module, module_tokens in modules.items():
            if commas.get(module):
                comma = commas[module]
            else:
                comma = None

            if module in self.modules:
                removeds += 1
                remove_offset += self.directional_length(module_tokens)
                if comma:
                    remove_offset += self.directional_length([comma])
                continue
            fixed_tokens.extend(module_tokens)
            if comma:
                fixed_tokens.append(comma)

        any_imports = removeds < len(modules)
        if any_imports:
            fixed_tokens.insert(0, stmt)

        if fixed_tokens and self._get_type(fixed_tokens[-1]) == token.COMMA:
            remove_offset -= self.directional_length([fixed_tokens[-1]]) + 2
            fixed_tokens.pop()

        if any_imports:
            fixed_tokens.append(newline)
        else:
            raise NoLineTransposer

        # pad first import
        if first_import_removed:
            first_import = []
            imports = iter(fixed_tokens[1:])
            with suppress(StopIteration):
                while self._get_type(current := next(imports)) != token.COMMA:
                    first_import.append(current)

            difference = self.directional_length(
                fixed_tokens[len(first_import) :]
            )
            fixed_tokens = self.shift_after(
                1, fixed_tokens, x_offset=-difference
            )

        return self.shift_after(1, fixed_tokens, x_offset=-remove_offset)

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
    parser.add_argument("-n", type=int, default=2)
    parser.add_argument("path")
    namespace = parser.parse_args()
    fixer = ImportFixer(namespace.remove_modules or [], [])
    with open(namespace.path) as f:
        content = f.read()
        result = fixer.transform(content)

    for line in difflib.unified_diff(
        content.splitlines(), result.splitlines(), n=namespace.n
    ):
        print(line)


if __name__ == "__main__":
    main()
