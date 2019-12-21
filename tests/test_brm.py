import tokenize

from brm import TokenTransformer, pattern

REAL_CODE = """
class X:
    if foo $ 1:
        def baz():
            pass
"""

EXPECTED_CODE = """
class X:
    if foo == 3:
        def baz():
            pass
"""


def test_token_transformer_new_syntax():
    class FooTokenTransformer(TokenTransformer):
        def visit_number(self, token):
            return token._replace(string="3")

        def visit_dolar(self, token):
            return token._replace(string="==", type=tokenize.OP)

        def register_dolar(self):
            return "$"

    foo = FooTokenTransformer()
    new = foo.transform(REAL_CODE)
    assert new == EXPECTED_CODE


def test_token_transformer_patternization():
    class Foo(TokenTransformer):
        @pattern("lsqb", "number", "colon", "number", "rsqb")
        def replace_to_threee(self, *tokens):
            _, n1, __, n2, ___ = tokens
            return _, n1._replace(string="3"), __, n2, ___

    foo = Foo()
    assert foo.transform("[1:10]") == "[3:10]"


def test_token_transformer_wildcarded_pattern():
    class Foo(TokenTransformer):
        @pattern("name", "*name", "newline")
        def replace_all_names_with_foo_bar(self, *tokens):
            name, *names, newline = tokens
            names = [name._replace(string="foobar") for name in names]
            return [name, *names, newline]

    foo = Foo()
    assert foo.transform("name1 name2 name3") == "name1 foobar foobar"
    assert (
        foo.transform("name1 name2 name3 name4 name5")
        == "name1 foobar foobar foobar foobar"
    )


def test_token_transformer_regex_pattern():
    class Foo(TokenTransformer):
        @pattern("name", "{2}name", "newline")
        def replace_all_names_with_foo_bar(self, *tokens):
            name, *names, newline = tokens
            names = [name._replace(string="foobar") for name in names]
            return [name, *names, newline]

    foo = Foo()
    assert (
        foo.transform("name1 name2 name3 name4") == "name1 name2 foobar foobar"
    )
