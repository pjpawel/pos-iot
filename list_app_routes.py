from pot.http import app


# /info       &   GET             &   \\\hline
for rule in app.url_map.iter_rules():
    end = rule.endpoint.replace('_', '')
    print(f"{rule.rule} & {list(rule.methods)[0]} & {end}\\\\")

