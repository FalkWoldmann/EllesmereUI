# Lua static analysis

Type-aware linting for EllesmereUI with **lua-language-server (LuaLS)**, the
community WoW API annotations from **[Ketho/vscode-wow-api]** and Blizzard's
FrameXML source with generated annotations from **[NumyAddon/FramexmlAnnotations]**
(retail live branch). Nothing here ships
in the addon zip (`.pkgmeta` ignores it).

## Run it

```sh
.tools/lint/check.sh                    # same gate as CI, ~90s on the full repo
.tools/lint/check.sh --update-baseline  # accept the current findings, then commit the baseline
```

The first run downloads the pinned toolchain into `.tools/cache/` (gitignored).
Versions are pinned in `fetch-tools.sh`; bump them there. The CI cache key follows
that file.

## How the gate works

The codebase predates annotations, so a full check reports ~2.5k existing findings.
`luals_check.py` reduces each finding to a line-independent fingerprint
`(file, code, message)` and compares counts with `luals-baseline.json`:

- **Blocking** (fails CI when above the baseline): diagnostics that don't depend
  on type inference, such as `undefined-global` (typos, APIs that don't exist),
  `lowercase-global` (a missing `local` leaks into `_G`: taint risk),
  `duplicate-index`, `duplicate-set-field` and `unbalanced-assignments`.
- **Advisory** (annotated on the PR, never failing): type-inference findings
  such as `need-check-nil` and `param-type-mismatch`. LuaLS inference can shift
  slightly between runs, so these can't gate reliably.

Fixed a finding? Run `--update-baseline` so it can't come back. Added one on
purpose (false positive)? Same command, and say why in the PR.

## Editor setup

- **VS Code:** install the recommended extensions (`sumneko.lua`, `ketho.wow-api`).
  `.luarc.json` configures Lua 5.1 and the ignores. The WoW extension adds its
  own annotation path.
- **Neovim / Zed / other LSP clients:** point them at lua-language-server. After
  one `fetch-tools.sh` run, `.luarc.json` already references the fetched annotations.
- **EmmyLua (Rust) language server** (`emmylua_ls`, optional): about 5x faster on
  this repo and configured by `.emmyrc.json`. It is *not* the CI gate: it is
  noisier with these annotations. To try its CLI:
  `.tools/lint/fetch-tools.sh --with-emmylua && .tools/cache/emmylua/emmylua_check . -c .emmyrc.json`
  (the `-c` is required, otherwise it reads `.luarc.json`).

## Known gaps / next steps

- **Bump annotations with the game.** After a patch, point `FRAMEXML_COMMIT` in
  `fetch-tools.sh` at the newest `live-mix-into-source` commit, bump
  `WOW_API_COMMIT`, and run `--update-baseline`.
- **Optional third-party addon APIs** (Pawn, Northern Sky, ...) are declared in
  `.luarc.json` `diagnostics.globals`. Add new integrations there, not in code.
- **Formatting:** StyLua was evaluated and not adopted. Any config reformats 213 of
  220 files (+224k/-159k lines), which would conflict with every upstream merge.
- **Annotations:** adding `---@class`/`---@param` to the shared core
  (`EllesmereUI.PP`, the profile serializer, `ADDON_DB_MAP`, per-module settings
  tables) turns many advisory findings into real type checks.

[Ketho/vscode-wow-api]: https://github.com/Ketho/vscode-wow-api
[NumyAddon/FramexmlAnnotations]: https://github.com/NumyAddon/FramexmlAnnotations
