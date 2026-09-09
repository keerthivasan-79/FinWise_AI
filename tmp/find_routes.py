import re

def get_routes(filepath):
    content = open(filepath, encoding='utf-8').read()
    # Find decorators like @app.get('/path'), @app.route('/path', methods=['GET', 'POST']), etc.
    pattern = r'@(app|enhancements)\.(route|get|post|delete|put|patch)\(\'([^\'\s]+)\'(?:,\s*methods=\[([^\]\s]+)\])?\)'
    matches = re.findall(pattern, content)
    results = []
    for app_var, method_var, path, methods_list in matches:
        if method_var == 'route':
            methods = [m.replace("'", "").replace('"', "").strip() for m in methods_list.split(',')]
            methods_str = '/'.join(methods)
        else:
            methods_str = method_var.upper()
        results.append((methods_str, path))
    return results

routes = get_routes('backend/app.py') + get_routes('backend/enhancements.py')
print(f"Found {len(routes)} routes:")
for m, p in routes:
    print(f"| {m} | {p} |")
