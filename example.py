import argparse
import difflib
import token
import tokenize
from contextlib import suppress

from brm import (
    NoLineTransposer,
    Priority,
    TokenTransformer,
    get_type_from_name,
    pattern,
)

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
    def fix_import_stmt(self, stmt, *tokens, removals=None):
        if stmt.string != "import":
            return

        module = []
        commas = {}
        modules = {}
        token_info = iter(tokens)
        removals = removals or self.modules

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

        removeds, remove_offset, first_import_offset = 0, 0, 0
        first_import = tuple(modules.keys())[0]
        first_import_removed = False
        fixed_tokens = []
        for module, module_tokens in modules.items():
            module_tokens = module_tokens.copy()

            if commas.get(module):
                comma = commas[module]
            else:
                comma = None

            if module in removals:
                if module == first_import:
                    first_import_removed = True
                    first_import_offset = -self.directional_length(
                        [module_tokens[0], stmt]
                    )  # end to start difference
                    # calculates distance between import's end and module name's start
                    # import foo => 1
                    # import  foo => 2
                    # import   foo => 3

                removeds += 1
                remove_offset += self.directional_length(module_tokens)
                if comma:
                    remove_offset += self.directional_length([comma])
                continue

            if comma:
                module_tokens.append(comma)

            fixed_tokens.extend(
                self.shift_all(module_tokens, x_offset=-remove_offset)
            )

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

        # pad the new first import
        if first_import_removed:
            current_offset = -self.directional_length([fixed_tokens[1], stmt])
            current_offset -= first_import_offset
            fixed_tokens = self.shift_after(
                1, fixed_tokens, x_offset=-current_offset
            )

        return self.shift_after(1, fixed_tokens)

    # from foo import bar
    # from foo import bar, baz
    # from foo.bar import bar, bar.baz

    @pattern(
        "name",
        dot_name,
        "name",
        f"({dot_name}( comma {dot_name})*)",
        "(newline|nl)",
    )
    @Priority.CANCEL_PENDING
    def fix_from_import_stmt(self, stmt, *tokens):
        if stmt.string != "from":
            return

        stream_token = iter(tokens)
        module = [next(stream_token)]
        have_dot = False
        try:
            while self._get_type(current := next(stream_token)) == token.DOT:
                module.append(current)
                module.append(next(stream_token))
            else:
                if current.string != "import":
                    return
        except StopIteration:
            return

        if "".join(token.string for token in module) in self.modules:
            raise NoLineTransposer

        new_imports = self.fix_import_stmt(
            current, *stream_token, removals=self.names
        )
        # we are sending the `import y, z` part of `from x import y, z`
        # if both y and z are unused, it will raise NoLineTransposer and
        # we are not going to do anything about it, we'll just pass it through
        # to TokenTransformer and it will remove the rest of the tokens.
        # if there are tokens, we'll get new version of `import y, z`
        return [stmt, *module, *new_imports]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove-modules", nargs="*")
    parser.add_argument("--remove-names", nargs="*")
    parser.add_argument("-n", type=int, default=2)
    parser.add_argument("path")
    namespace = parser.parse_args()
    fixer = ImportFixer(
        namespace.remove_modules or [], namespace.remove_names or []
    )
    with open(namespace.path) as f:
        content = f.read()
        result = fixer.transform(content)

    union_skipper = 0
    for line in difflib.unified_diff(
        content.splitlines(), result.splitlines(), n=namespace.n
    ):
        if union_skipper < 4:
            union_skipper += 1
            continue
        print(line)


if __name__ == "__main__":
    main()
