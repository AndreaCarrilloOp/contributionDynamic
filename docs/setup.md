# Set up your animated profile

1. In your own public profile repository (`username/username`), create an Actions repository secret named `CONTRIBUTION_TOKEN` containing a read-only token for the intended public contributions. Never put it in source code. Review whether the token can expose private activity.
2. Add `.github/workflows/contributions.yml` with the following example.
3. Run the workflow manually, then add the picture element to your profile README.

```yaml
name: Contribution animations

on:
  workflow_dispatch:
  schedule:
    - cron: '17 11 * * *'

permissions:
  contents: read

concurrency:
  group: contribution-animations
  cancel-in-progress: false

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      # Replace @main with a verified release or commit SHA before production use.
      - uses: AndreaCarrilloOp/contributionDynamic@main
        with:
          github-user: ${{ github.repository_owner }}
          github-token: ${{ secrets.CONTRIBUTION_TOKEN }}
          scenario: all
          theme: both
          output-dir: generated
      - uses: actions/upload-artifact@v4
        with:
          name: contribution-animations
          path: generated/*.svg
          if-no-files-found: error
  publish:
    needs: generate
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/download-artifact@v4
        with:
          name: contribution-animations
          path: ${{ runner.temp }}/animations
      - shell: bash
        run: |
          set -euo pipefail
          if git show-ref --verify --quiet refs/remotes/origin/contribution-output; then
            git switch -c contribution-output --track origin/contribution-output
          else
            git switch --orphan contribution-output
          fi
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          cp "$RUNNER_TEMP"/animations/*.svg .
          git add -- *.svg
          if ! git diff --cached --quiet; then
            git commit -m "chore: update contribution animations"
            git push origin HEAD:refs/heads/contribution-output
          fi
```

Replace `YOUR_LOGIN` below with your GitHub username, and `factory` with the desired scenario.

```html
<picture>
  <source media="(prefers-color-scheme: dark)"
    srcset="https://raw.githubusercontent.com/YOUR_LOGIN/YOUR_LOGIN/contribution-output/factory-dark.svg">
  <img alt="Animated GitHub contributions"
    src="https://raw.githubusercontent.com/YOUR_LOGIN/YOUR_LOGIN/contribution-output/factory-light.svg">
</picture>
```

The generated image is separate from GitHub's native calendar. GitHub may cache raw SVGs. The workflow updates daily and supports manual runs; scheduled execution can be delayed by GitHub. Write permissions are needed only by the publication job.
