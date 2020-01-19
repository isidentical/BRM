# requirements: svgwrite
import tempfile
import token
import tokenize
import webbrowser
from argparse import ArgumentParser, FileType
from contextlib import contextmanager
from string import Template
from tempfile import NamedTemporaryFile

import svgwrite

from brm import TokenTransformer, pattern


def create_board(transformer, stream_tokens, highlight, pattern=None):
    drawing = svgwrite.Drawing()
    drawing.add(
        drawing.rect(
            insert=(0, 0),
            size=("600px", "600px"),
            stroke_width="5",
            stroke="black",
            fill="white",
        )
    )
    text = drawing.text("BRM", font_family="monospace")
    for stream_token in stream_tokens:
        x_pos = 50 + stream_token.start[1] * 7
        y_pos = 25 + stream_token.start[0] * 25
        source = stream_token.string

        if stream_token in highlight:
            if stream_token.type == token.NEWLINE:
                source = "|"
                x_pos += 7
            elif stream_token.type == token.INDENT:
                source = "*" * len(stream_token.string)

        for extra, line in enumerate(source.splitlines()):
            span = drawing.tspan(line, insert=(x_pos, y_pos + 25 * extra))
            if stream_token in highlight:
                span.stroke(color="red")
            text.add(span)

    if pattern is not None:
        cursor = drawing.tspan(f"Pattern: {pattern}", (100, y_pos + 50))
    else:
        cursor = drawing.tspan(
            f"Current token: {transformer._get_name(*highlight)}",
            (100, y_pos + 50),
        )

    cursor.stroke(color="black")
    text.add(cursor)
    drawing.add(text)
    return drawing.tostring()


@contextmanager
def document(page, transformer, tokens):
    page.write("<html><head><title>BRM Visualizer</title></head><body>")
    yield page
    page.write("</body></html>")


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "file",
        type=FileType(),
        nargs="?",
        default="-",
        help="file to visualize",
    )
    parser.add_argument(
        "pattern",
        nargs="?",
        default=None,
        help="pattern to visualize on board",
    )
    args = parser.parse_args()

    transformer = TokenTransformer()
    source = args.file.read()
    tokens = transformer.quick_tokenize(source)
    args.file.close()
    print("Processing input...")

    if tokens[-1].end[0] > 18:
        raise ValueError("input file should contain less then 15 lines")

    if args.pattern:
        matches = []

        @pattern(args.pattern)
        def set_args(*tokens):
            matches.append(tokens)

        transformer._internal = set_args
        transformer.transform(source)

    page = NamedTemporaryFile("w", delete=False, buffering=1)
    with document(page, transformer, tokens) as doc:
        for frame, token in enumerate(tokens):
            idx = f"frame_{frame}"
            highlight = matches[frame] if args.pattern else {token}
            doc.write(
                f'<div id="frame_{frame}">{create_board(transformer, tokens, highlight, args.pattern)}</div>'
            )
            if args.pattern and frame + 1 == len(matches):
                break

        page.write(STATIC_HTML.substitute({"total_frames": frame + 1}))

    webbrowser.open(page.name)
    page.close()


# I SUCK AT SVGS
# I AM SURE THERE IS A WAY TO
# DO THIS WITHOUT JS BUT I COULDN'T
# FIGURE OUT
# I DONT KNOW JS
# I AM JUST TRYING
# PLEASE HELP ME TO ANIMATE
# IF YOU CAN
STATIC_HTML = Template(
    """
<script>
var i;
for (i = 0; i < ${total_frames}; i++) { 
    var div = document.getElementById("frame_" + i);
    div.style.display = "none";
}

var i = 0, last;
var interval_id = setInterval(function () {
        var div = document.getElementById("frame_" + i);
        div.style.display = "block";
        last && (last.style.display = "none");
        last = div;
        i += 1;
        console.log("showing" + i);
        if (i == ${total_frames}) i = 0;
    },
550);
</script>
"""
)

if __name__ == "__main__":
    main()
