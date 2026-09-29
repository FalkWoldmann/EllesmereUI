# Agent notes for EllesmereUI

- WoW retail addon suite, Lua 5.1 (the WoW runtime). No build step: the `.toc`
  files define load order. `Libs/` is fetched by the packager from `.pkgmeta`
  externals and is not in the repo.
- **Lint before finishing any Lua change:** `.tools/lint/check.sh` (~80s). It must
  report no new blocking findings. Never "fix" a finding by adding a global. If a
  finding is a genuine false positive, run `.tools/lint/check.sh --update-baseline`
  and explain why in the PR. Details: `.tools/lint/README.md`.
- WoW API signatures: the annotations fetched into
  `.tools/cache/wow-api/Annotations/Core` (after one `check.sh` run) are the
  quickest local reference.
