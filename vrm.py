import ast
import token as t
import tokenize
from collections import namedtuple
from copy import deepcopy

import brm

TOKEN_EATS = {ast.operator: 1}

POSITION_INFO = ("lineno", "col_offset", "end_lineno", "end_col_offset")


class Comment(ast.AST):
    __module__ = ast

    _fields = ("comment",)
    _attributes = POSITION_INFO

    @classmethod
    def from_token(cls, token):
        return cls(
            comment=token.string,
            **dict(zip(POSITION_INFO, token.start + token.end))
        )


class Position(namedtuple("Position", POSITION_INFO + ("mod",))):
    @classmethod
    def from_token(cls, token):
        return cls(*token.start, *token.end, token)

    @classmethod
    def from_node(cls, node):
        return cls(
            node.lineno,
            node.col_offset,
            node.end_lineno,
            node.end_col_offset,
            node,
        )

    def can_cover(self, other):
        return (
            self.lineno <= other.lineno
            and self.col_offset <= other.col_offset
            and self.end_lineno >= other.lineno
            and self.end_col_offset >= other.end_col_offset
        )

    def distance_to(self, other):
        return (
            (self.lineno - other.lineno) ** 2
            + (self.end_lineno - other.end_lineno) ** 2
        ) ** 0.5


def has_position(node):
    if set(POSITION_INFO).issubset(set(node._attributes)):
        return True
    return False


def get_token_eats(node, default=1):
    node_type = type(node)
    for base in node_type.mro():
        if base in TOKEN_EATS:
            return TOKEN_EATS[base]
    else:
        return default


class ASTTransformer(ast.NodeTransformer, brm.TokenTransformer):
    def transform(self, source):
        tree = ast.parse(source)
        tokens = self.quick_tokenize(source, strip=False)

        self.insert_comments(tree, tokens)
        self.mark(tree, tokens)
        source = tokenize.untokenize(tokens)
        return source

    def mark(self, tree, tokens):
        tokens = tuple(map(Position.from_token, tokens))
        previous_node = None

        for node in ast.walk(tree):
            if has_position(node):
                node = Position.from_node(node)
                node._tokens = self.search(node, tokens)
            elif previous_node:
                start = tokens.index(previous_node._tokens[-1]) + 1
                amount = get_token_eats(node)
                node._tokens = tokens[start : start + amount]
            else:
                node._tokens = tokens

            previous_node = node

    def search(self, node, tokens):
        matches = []
        for token in tokens:
            if node.can_cover(token):
                matches.append(token)
        return matches

    def insert_comments(self, tree, tokens):
        comments = {}
        for token in tokens:
            if token.type == t.COMMENT:
                comment = Comment.from_token(token)
                comments[comment.lineno] = comment

        if len(tree.body) > 0:
            previous_node = tree.body[0]
            prev_start, prev_end = (
                previous_node.lineno,
                previous_node.end_lineno,
            )
        else:
            return tree.body.extend(comments.values())

        # TODO: calculate comment range
