import token

from brm import TokenTransformer


class NumberHandler(TokenTransformer):
    def visit_number(self, number):
        print("is a number? (always yes)", number.type == token.NUMBER)
        print("what it contains?", number.string)
        print("which line it was taken", number.line)
        print(
            "where it starts?", "y_start={}, x_start={}".format(*number.start)
        )
        print("where it end?", "y_end={}, x_end={}".format(*number.end))

    def dummy(self, unknown_token):
        if token.ISEOF(unknown_token.type):
            print("Reached EOF without a problem, congratz")
        else:
            print("Unhandled token:", unknown_token)
