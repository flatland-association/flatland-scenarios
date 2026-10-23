# AGENTS.md

## Git

- Always commit Jupyter notebooks (`.ipynb`) without outputs: every code cell with empty `outputs` and
  `"execution_count": null`. Keep the outputs in the working copy - stage a stripped copy instead, e.g.:

  ```shell
  sha=$(python3 -c '
  import json, sys
  nb = json.load(open(sys.argv[1]))
  for c in nb["cells"]:
      if c["cell_type"] == "code":
          c["outputs"], c["execution_count"] = [], None
  sys.stdout.write(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
  ' "$NB" | git hash-object -w --stdin)
  git update-index --cacheinfo 100644,"$sha","$NB"
  ```
