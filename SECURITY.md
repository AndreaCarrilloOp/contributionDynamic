# Security policy

Do not open public issues containing credentials or private calendar data. Revoke any exposed token immediately and use GitHub's private vulnerability reporting if enabled, or the repository owner's published contact channel.

The engine reads contribution data through GitHub GraphQL and creates local SVG files. The composite action does not push commits or request additional repository permissions. Use a read-only token with minimum access. Published calendar SVGs expose activity levels, dates and counts; review the intended visibility before publishing.

Pin the action to a reviewed release or commit. Beta versions are supported on a best-effort basis.
