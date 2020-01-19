import token
import tokenize
from argparse import ArgumentParser
from pathlib import Path
from string import Template

import svgwrite

from brm import TokenTransformer


def create_board(transformer, stream_tokens, highlight, filename):
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
    for stream_token in stream_tokens:
        x_pos = 50 + stream_token.start[1] * 7
        y_pos = 25 + stream_token.start[0] * 25
        source = stream_token.line[
            stream_token.start[1] : stream_token.end[1]
        ]  # single line
        if highlight == stream_token:
            if stream_token.type == token.NEWLINE:
                source = "|"
            elif stream_token.type == token.INDENT:
                source = "*" * len(stream_token.string)

        span = drawing.tspan(source, insert=(x_pos, y_pos))
        if highlight == stream_token:
            span.stroke(color="red")
        text.add(span)

    cursor = drawing.tspan(
        f"Current token: {transformer._get_name(highlight)}", (100, y_pos + 50)
    )
    cursor.stroke(color="black")
    text.add(cursor)
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

    if tokens[-1].end[0] > 15:
        raise ValueError("input file should contain less then 15 lines")
    if not args.output.is_dir():
        raise ValueError("output should be an existing directory")

    index = open(args.output / "index.html", "w")
    for frame, token in enumerate(tokens):
        idx = f"frame_{frame}"
        index.write(f'<div id="{idx}">')
        index.write(
            create_board(
                transformer, tokens, token, args.output / f"{idx}.svg"
            )
        )
        index.write("</div>")

    index.write(STATIC_HTML.substitute({"total_frames": frame + 1}))
    index.close()


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
        if (i == ${total_frames}) clearInterval(interval_id);
    },
    700);
</script>
"""
)

if __name__ == "__main__":
    main()
