"""CLI for compiling a SankeyDefinition to a JSON spec file.

Usage:
    python -m floweaver.compiler my_diagram.py -o spec.json
    python -m floweaver.compiler my_diagram.py::my_var -o spec.json
"""

import argparse
import gzip
import importlib.util
import json
import os
import sys


DEFAULT_VAR = "sankey_definition"


def parse_input(input_str):
    """Parse input string into (filepath, varname).

    Supports FILE::VARNAME notation; defaults to DEFAULT_VAR.
    """
    if "::" in input_str:
        filepath, varname = input_str.rsplit("::", 1)
        return filepath, varname
    return input_str, DEFAULT_VAR


def load_variable(filepath, varname):
    """Load a variable from a Python file by executing it as a module."""
    spec = importlib.util.spec_from_file_location("_user_module", filepath)
    if spec is None or spec.loader is None:
        print(f"Error: cannot load '{filepath}' as a Python module.", file=sys.stderr)
        sys.exit(1)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, varname):
        from ..sankey_definition import SankeyDefinition

        available = [
            n
            for n in dir(module)
            if not n.startswith("_")
            and isinstance(getattr(module, n), SankeyDefinition)
        ]
        msg = f"Error: variable '{varname}' not found in '{filepath}'."
        if available:
            msg += f"\nSankeyDefinition instances found: {', '.join(available)}"
        else:
            msg += "\nNo SankeyDefinition instances found in the file."
        print(msg, file=sys.stderr)
        sys.exit(1)

    return getattr(module, varname)


def parse_color_mapping(value):
    """Parse a --color-mapping value as inline JSON dict or a path to a JSON file."""
    # Try as a file path first
    if os.path.isfile(value):
        with open(value, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print(
                f"Error: color mapping file '{value}' must contain a JSON object.",
                file=sys.stderr,
            )
            sys.exit(1)
        return data

    # Try as inline JSON
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        print(
            f"Error: --color-mapping value is not valid JSON and not a file path: {value}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(data, dict):
        print(
            "Error: --color-mapping must be a JSON object (dict), not a list or scalar.",
            file=sys.stderr,
        )
        sys.exit(1)

    return data


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m floweaver.compiler",
        description=(
            "Compile a SankeyDefinition to a JSON spec file. "
            "WARNING: The input Python file will be executed to load the "
            "SankeyDefinition. Only use trusted files."
        ),
    )

    parser.add_argument(
        "input",
        help=(
            "Path to a Python file containing a SankeyDefinition. "
            "Optionally specify the variable name using FILE::VARNAME "
            f'notation (default variable: "{DEFAULT_VAR}").'
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file path. If not specified, writes to stdout.",
    )

    parser.add_argument(
        "--var",
        default=None,
        help=(
            "Variable name to import from the Python file. Overrides any "
            f'name given via FILE::VARNAME notation. Default: "{DEFAULT_VAR}".'
        ),
    )

    parser.add_argument(
        "--measure",
        action="append",
        dest="measures",
        metavar="MEASURE",
        help='Measure column to aggregate (repeatable). Default: "value".',
    )

    parser.add_argument(
        "--link-width",
        default=None,
        help="Measure to use for link width.",
    )

    parser.add_argument(
        "--link-color",
        default=None,
        help="Measure or dimension to use for link color.",
    )

    parser.add_argument(
        "--palette-name",
        default=None,
        metavar="NAME",
        help="Name of a palettable qualitative palette (e.g. Pastel1_8).",
    )

    parser.add_argument(
        "--color-mapping",
        default=None,
        metavar="JSON_OR_FILE",
        help=(
            "Explicit value-to-color mapping as an inline JSON object "
            '(e.g. \'{"apples": "yellowgreen"}\') or a path to a JSON file '
            "containing an object."
        ),
    )

    parser.add_argument(
        "--no-elsewhere-waypoints",
        action="store_true",
        default=False,
        help="Disable automatic elsewhere waypoints.",
    )

    gzip_group = parser.add_mutually_exclusive_group()
    gzip_group.add_argument(
        "--gzip",
        action="store_true",
        default=None,
        dest="use_gzip",
        help="Force gzip compression of output.",
    )
    gzip_group.add_argument(
        "--no-gzip",
        action="store_false",
        dest="use_gzip",
        help='Disable gzip even if output filename ends with ".gz".',
    )

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    # Resolve input file and variable name
    filepath, varname = parse_input(args.input)
    if args.var is not None:
        varname = args.var

    # Load the SankeyDefinition from the Python file
    sankey_definition = load_variable(filepath, varname)

    # Build compile kwargs
    from . import compile_sankey_definition

    kwargs = {}

    if args.measures:
        kwargs["measures"] = (
            args.measures if len(args.measures) > 1 else args.measures[0]
        )

    if args.link_width is not None:
        kwargs["link_width"] = args.link_width

    if args.link_color is not None:
        kwargs["link_color"] = args.link_color

    # Build palette from --palette-name and/or --color-mapping
    if args.color_mapping is not None:
        kwargs["palette"] = parse_color_mapping(args.color_mapping)
    elif args.palette_name is not None:
        kwargs["palette"] = args.palette_name

    if args.no_elsewhere_waypoints:
        kwargs["add_elsewhere_waypoints"] = False

    # Compile
    spec = compile_sankey_definition(sankey_definition, **kwargs)
    json_data = json.dumps(spec.to_json(), indent=2)

    # Determine whether to gzip
    use_gzip = args.use_gzip
    if use_gzip is None and args.output is not None:
        use_gzip = args.output.endswith(".gz")
    if use_gzip is None:
        use_gzip = False

    # Write output
    if args.output is None:
        sys.stdout.write(json_data)
        sys.stdout.write("\n")
    elif use_gzip:
        with gzip.open(args.output, "wt", encoding="utf-8") as f:
            f.write(json_data)
            f.write("\n")
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_data)
            f.write("\n")


if __name__ == "__main__":
    main()
