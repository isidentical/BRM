# requiurements: svgwrite
import tempfile
import token
import tokenize
import webbrowser
from argparse import ArgumentParser, FileType
from string import Template
from tempfile import NamedTemporaryFile

import svgwrite

from brm import TokenTransformer


def create_board(transformer, stream_tokens, highlight):
    drawing = svgwrite.Drawing()
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
    for stream_token in stream_tokens:
        x_pos = 50 + stream_token.start[1] * 7
        y_pos = 25 + stream_token.start[0] * 25
        source = stream_token.string

        if highlight == stream_token:
            if stream_token.type == token.NEWLINE:
                source = "|"
                x_pos += 7
            elif stream_token.type == token.INDENT:
                source = "*" * len(stream_token.string)

        for extra, line in enumerate(source.splitlines()):
            span = drawing.tspan(line, insert=(x_pos, y_pos + 25 * extra))
            if highlight == stream_token:
                span.stroke(color="red")
            text.add(span)

    cursor = drawing.tspan(
        f"Current token: {transformer._get_name(highlight)}", (100, y_pos + 50)
    )
    cursor.stroke(color="black")
    text.add(cursor)
    drawing.add(text)
    return drawing.tostring()


def write_board(page, transformer, tokens):
    page.write("<html><head><title>BRM Visualizer</title></head><body>")
    for frame, token in enumerate(tokens):
        idx = f"frame_{frame}"
        page.write(
            f'<div id="frame_{frame}">{create_board(transformer, tokens, token)}</div>'
        )
    page.write(STATIC_HTML.substitute({"total_frames": len(tokens)}))
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
    args = parser.parse_args()

    transformer = TokenTransformer()
    tokens = transformer.quick_tokenize(args.file.read())
    args.file.close()
    print("Processing input...")

    if tokens[-1].end[0] > 15:
        raise ValueError("input file should contain less then 15 lines")

    page = NamedTemporaryFile("w", delete=False, buffering=1)
    write_board(page, transformer, tokens)
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
        if (i == ${total_frames}) clearInterval(interval_id);
    },
700);
</script>
"""
)

if __name__ == "__main__":
    main()
