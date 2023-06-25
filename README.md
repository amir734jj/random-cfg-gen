# random-cfg-gen

Random context free grammar generator

```bash
# 2^4 non-terminals
echo "2^4" | bc | xargs -I {} bash -c "./App {}" > ~/Downloads/cfg.txt

# additional options
echo "2^10" | bc | xargs -I {} bash -c "./App {}  --DisallowEpsilon --DisallowAlternative" > ~/Downloads/cfg.txt
```
