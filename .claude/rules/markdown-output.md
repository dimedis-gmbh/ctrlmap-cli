# Markdown Output Rules

- All generated Markdown files must have a maximum line length of 120 characters.
- Wrap paragraphs at word boundaries. Do not break within inline formatting (`**bold**`, `[links](url)`), code spans, or frontmatter values.
- Do not use tables in generated Markdown. Use list-based layouts instead (heading + bullet list per item).
- Each document file has YAML frontmatter with metadata, followed by the converted body content.
- Index files use `##` headings with relative links for each document, followed by metadata bullets.
- Strip soft hyphens (`\u00ad`) and normalize `&nbsp;` to regular spaces during HTML-to-Markdown conversion.
- All generated Markdown must pass `markdownlint-cli2` with the project configuration.
