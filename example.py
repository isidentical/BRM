from __future__ import annotations

import argparse
import difflib
import token
import tokenize
from contextlib import suppress
from dataclasses import dataclass
from typing import Dict, List

from brm import (
    NoLineTransposer,
    Priority,
    TokenTransformer,
    get_type_from_name,
    pattern,
)

dot_name = "(name( dot name)*)"
newline_group = "(nl|newline)"


@dataclass
class ParseResult:
    commas: Dict[str, TokenInfo]
    modules: Dict[str, List[TokenInfo]]
    newlines: Dict[str, TokenInfo]


class ImportFixer(TokenTransformer):
    def __init__(self, modules, names):
        self.modules = modules
        self.names = names

    # import foo
    # import foo, bar
    # import foo, foo.bar
    # import foo.bar, bar.foo
    @pattern(
        "name",
        f"((nl )?{dot_name}( comma (nl )?{dot_name})*( nl)?)",
        newline_group,
    )
    def fix_import_stmt(self, stmt, *tokens, removals=None):
        if stmt.string != "import":
            return

        module = []
        commas = {}
        modules = {}
        newlines = {}
        token_info = iter(tokens)
        first_module_newline = None
        if removals is None:
            # cant use removals = removals or self.modules
            # because caller might be call this with removals = []
            removals = self.modules

        def add_module(comma):
            pretty_name = "".join(
                token_info.string
                for token_info in module
                if self._get_type(token_info) != token.COMMA
            )
            modules[pretty_name] = module.copy()
            commas[pretty_name] = comma
            module.clear()

        def add_newline(newline):
            last_module = tuple(modules.keys())
            if len(last_module) == 0:
                first_module_newline = newline
            else:
                last_module = last_module[-1]
                # this relies on dicts are preserving insertion order
                # they are, since 3.6 for CPython
                # 3.7 for other implementations
                newlines[last_module] = newline

        *module_tokens, newline = token_info
        for module_token in module_tokens:
            if self._get_type(module_token) == token.COMMA:
                add_module(module_token)
            elif self._get_type(module_token) == token.NL:
                add_newline(module_token)
            else:
                module.append(module_token)
        else:
            add_module(None)

        first_import = tuple(modules.keys())[0]

        if first_module_newline:
            newlines[first_import] = first_module_newline

        if newlines:
            # that means this was just a parse action
            # and we'll return what we got
            return ParseResult(commas, modules, newlines)

        removeds, remove_offset, first_import_offset = 0, 0, 0
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
                    )
                    # end to start difference
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

    def find_module_for_from_import_stmt(self, token_iterator):
        have_dot = False
        module = []
        try:
            while self._get_type(current := next(token_iterator)) == token.DOT:
                module.append(current)
                module.append(next(token_iterator))
        except StopIteration:
            return None
        else:
            return module, current

    # from foo import bar
    # from foo import bar, baz
    # from foo.bar import bar, bar.baz

    @pattern(
        "name",
        dot_name,
        "name",
        f"({dot_name}( comma {dot_name})*)",
        newline_group,
    )
    @Priority.CANCEL_PENDING
    def fix_from_import_stmt(self, stmt, *tokens):
        if stmt.string != "from":
            return

        stream_token = iter(tokens)
        module = [next(stream_token)]
        module_parts, current = self.find_module_for_from_import_stmt(
            stream_token
        )
        module.extend(module_parts)

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

    # name dot_name name lpar \
    # nl? dot_name (comma nl? dot_name)* nl? \
    # rpar newline

    # [<smth>] = optional <smth>
    # from <module> import ([\n] <name>[,[\n]<name>][\n])

    # from (x, y, z)
    # from (x.y, z.q)
    # from (
    #   x,
    #   y,
    #   z
    # )

    @pattern(
        "name",
        dot_name,
        "name",
        "lpar",
        f"((nl )?{dot_name}( comma (nl )?{dot_name})*( nl)?)",
        "rpar",
        newline_group,
    )
    @Priority.CANCEL_PENDING
    def test(self, from_stmt, *tokens):
        if from_stmt.string != "from":
            return

        stream_token = iter(tokens)
        module = [next(stream_token)]
        module_parts, import_stmt = self.find_module_for_from_import_stmt(
            stream_token
        )
        module.extend(module_parts)

        if "".join(token.string for token in module) in self.modules:
            raise NoLineTransposer

        name_part = []
        lpar = next(stream_token)
        while self._get_type(current := next(stream_token)) != token.RPAR:
            name_part.append(current)
        rpar = current
        newline = next(stream_token)

        # now we have
        # from_stmt => from
        # module => <module>
        # import_stmt = import
        # left par => (
        # name_part => <name>, [nl]<name>, ....
        # right par => )

        result = self.fix_import_stmt(
            import_stmt, *name_part, newline, removals=self.names
        )
        if isinstance(result, ParseResult):
            pass
        else:
            result = result[1:-1]
            overflow = self.directional_length(
                name_part
            ) - self.directional_length(result)
            return [
                from_stmt,
                *module,
                import_stmt,
                lpar,
                *result,
                *self.shift_all([rpar, newline], x_offset=-overflow),
            ]


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
        if union_skipper < 3:
            union_skipper += 1
            continue
        print(line)


if __name__ == "__main__":
    main()
