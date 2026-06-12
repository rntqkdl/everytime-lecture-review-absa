# Notebooks

These notebooks are code templates for Colab T4 runs.

Before committing notebook changes, confirm that stored cell outputs are empty and that no raw review text, CSV preview, browser data, token, or local path containing private data is embedded in the notebook JSON.

Recommended check:

```powershell
python -c "import json, pathlib; [print(p, sum(len(c.get('outputs', [])) for c in json.loads(p.read_text(encoding='utf-8')).get('cells', []) if c.get('cell_type') == 'code')) for p in pathlib.Path('notebooks').glob('*.ipynb')]"
```
