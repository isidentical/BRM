# Bicycle Repair Man
Rewrite python sources, highly experimental

## How?
BRM is based on tokens which can be manipulated easily. Like an `ast.NodeTransformer`, we offer `brm.TokenTransformer`. `TokenTransformer` can do a lot of things starting from registering a new token (via `register_{TOK_NAME}` functions) to finding and replacing token patterns with parser rules.

!!! This project is highly experimental and has tons of bugs !!

## Examples
### Simple Patterns
```py
from brm import TokenTransformer, pattern

class OperatorTransformer(TokenTransformer):

    @pattern("number", "plus", "number")
    def plus_to_minus(self, lhs, operator, rhs):
        operator = operator._replace(string="-")
        return lhs, operator, rhs

opt = OperatorTransformer()
assert opt.transform("2 + 2") == "2 - 2"
```
### Custom Tokens and New Syntaxes
```py
from brm import TokenTransformer, pattern

class SquareRoot(TokenTransformer):

    def register_squareroot(self):
        return "√"

    @pattern("squareroot", "number")
    def remove_varprefix(self, sr, number):
        return self.quick_tokenize(f"int({number.string} ** 0.5)")

sqr = SquareRoot()
assert eval(sqr.transform("√9")) == 3
```
