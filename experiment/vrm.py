import ast
import token
import tokenize
from collections import namedtuple
from copy import deepcopy

import brm

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


ast._Unparser.visit_Comment = lambda self, node: self.write(node.comment)


class ASTTransformer(ast.NodeTransformer, brm.TokenTransformer):
    def transform(self, source):
        tree = ast.parse(source)
        tokens = self.quick_tokenize(source, strip=False)
        self.set_parents(tree)
        self.insert_comments(tree, tokens)
        source = tokenize.untokenize(tokens)
        return source

    def set_parents(self, tree):
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

    def fetch_comments(self, stream_tokens):
        comments = []
        for stream_token in stream_tokens:
            if stream_token.type == token.COMMENT:
                comment = Comment.from_token(stream_token)
                comments.append(
                    Position.from_node(Comment.from_token(stream_token))
                )
        return comments

    def insert_comments(self, tree, tokens):
        nodes = [
            Position.from_node(node)
            for node in ast.walk(tree)
            if has_position(node)
        ]
        comments = self.fetch_comments(tokens)
        connected_nodes = {}

        for comment in comments:
            node = min(*nodes, key=lambda node: node.distance_to(comment)).mod
            after = comment.lineno >= node.lineno
            if comment.lineno != node.lineno:
                comment = comment._replace(
                    mod=ast.copy_location(ast.Expr, comment.mod)
                )
            while not hasattr(node.parent, "body"):
                node = node.parent

            if node in node.parent.body:
                index = node.parent.body.index(node) + int(after)
            else:
                index = 0
            node.parent.body.insert(0, comment.mod)
