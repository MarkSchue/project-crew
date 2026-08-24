# active-project-repo

A concrete active project instance generated from the pinned
`project-template-repository` template (masterplan section 7.3). Project
facts live in `public/` (accessible to all project agents) and
agent-confidential working data lives in `private/`.

`template.lock` records the exact template version and content hash this
project was generated from. Generated `index.md` files are projections —
regenerate with `mas index rebuild`, do not hand-edit.
