import tokenize
from argparse import ArgumentParser
from pathlib import Path

import svgwrite

from brm import TokenTransformer


def create_board(transformer, tokens, highlight, filename):
    drawing = svgwrite.Drawing(filename=filename)
    drawing.add(
        drawing.rect(
            insert=(0, 0),
            size=("500px", "500px"),
            stroke_width="5",
            stroke="black",
            fill="white",
        )
    )
    text = drawing.text("BRM", font_family="monospace")
    cursor = drawing.tspan(
        f"Current token: {transformer._get_name(highlight)}"
    )
    for token in tokens:
        source = token.line[token.start[1] : token.end[1]]
        span = drawing.tspan(
            source, insert=(50 + token.start[1] * 7, 25 + token.start[0] * 25)
        )
        if highlight == token:
            span.stroke(color="red")
        text.add(span)

    drawing.add(text)
    drawing.save()
    return drawing.tostring()


def main():
    parser = ArgumentParser()
    parser.add_argument("file", type=Path, help="file to visualize")
    parser.add_argument("output", type=Path, help="output directory")
    args = parser.parse_args()

    transformer = TokenTransformer()
    with tokenize.open(args.file) as source:
        tokens = transformer.quick_tokenize(source.read())

    if not args.output.is_dir():
        raise ValueError("output should be an existing directory")

    for frame, token in enumerate(tokens):
        create_board(
            transformer, tokens, token, args.output / f"frame_{frame}.svg"
        )


if __name__ == "__main__":
    main()
