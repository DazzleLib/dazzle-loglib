"""The sub-command recipe in docs/cli-integration.md, run from the page itself.

The library contains no argparse code, so the doc is the only specification of the wiring an adopter copies
(see the page's opening). These tests execute the page's own code blocks, so the recipe cannot drift from
something that works: the pitfall block must show the lost `-v`, and the recipe block must give one verbosity
whichever side of the sub-command the flags are typed on.
"""
import pathlib
import re

import pytest

from dazzle_loglib import get_output

DOC = pathlib.Path(__file__).resolve().parent.parent / "docs" / "cli-integration.md"
_BLOCK = re.compile(r"```python\n(.*?)```", re.S)


def _blocks():
    text = DOC.read_text(encoding="utf-8")
    canonical = _BLOCK.search(text).group(1)                 # the page's first block: imports, channels, flags
    start = text.index("## Sub-commands")
    section = text[start:text.index("\n## ", start + 1)]
    pitfall, recipe = _BLOCK.findall(section)
    return canonical, pitfall, recipe


@pytest.fixture
def no_env(monkeypatch):
    monkeypatch.delenv("MYAPP_VERBOSITY", raising=False)
    monkeypatch.delenv("MYAPP_SHOW", raising=False)


def test_the_pitfall_block_loses_the_flag_as_the_page_says():
    canonical, pitfall, _ = _blocks()
    ns = {}
    exec(canonical, ns)
    *body, last = pitfall.strip().splitlines()
    exec("\n".join(body), ns)
    assert eval(last.split("#")[0], ns) == 0                  # the page's claim: "0, not 1"


@pytest.mark.parametrize("argv, verbosity", [
    (["run"], 0),
    (["-v", "run"], 1),                                        # the form the pitfall loses
    (["run", "-v"], 1),
    (["-v", "run", "-v"], 2),                                  # one chain: -v on both sides is -vv
    (["-vv", "run", "-q"], 1),                                 # the counts subtract across the sides
    (["-q", "run"], -1),
])
def test_the_recipe_gives_one_verbosity_on_both_sides_of_the_command(no_env, argv, verbosity):
    canonical, _, recipe = _blocks()
    ns = {}
    exec(canonical, ns)
    exec(recipe, ns)
    ns["main"](argv)
    assert get_output().verbosity == verbosity


def test_the_recipe_joins_show_specs_from_both_sides(no_env):
    canonical, _, recipe = _blocks()
    ns = {}
    exec(canonical, ns)
    exec(recipe, ns)
    ns["main"](["--show", "scan:2", "run", "--show", "git:1"])
    overrides = get_output().channel_overrides
    assert overrides.get("scan") == 2 and overrides.get("git") == 1
