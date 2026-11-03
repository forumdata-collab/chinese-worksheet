#!/usr/bin/env python3
"""Deploy the staging dir (main site unchanged + /enhanced/ preview) to CF Pages."""
import os, subprocess, sys

ENV_FILE = '/home/ubuntu/.hermes/.env'
env = dict(os.environ)
if os.path.exists(ENV_FILE):
    for line in open(ENV_FILE):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
env['CLOUDFLARE_API_TOKEN'] = env.get('CF_WORKERS_TOKEN') or env.get('CLOUDFLARE_API_TOKEN', '')
env['CLOUDFLARE_ACCOUNT_ID'] = env.get('CF_ACCOUNT_ID') or env.get('CLOUDFLARE_ACCOUNT_ID', '')
env['WRANGLER_CONFIG'] = '/tmp/empty.toml'
open('/tmp/empty.toml', 'w').write('')

cwd = sys.argv[1] if len(sys.argv) > 1 else '/tmp/cwdeploy'
r = subprocess.run(['npx', 'wrangler', 'pages', 'deploy', '.',
                    '--project-name=chineseword-we1co', '--branch=main'],
                   cwd=cwd, env=env, capture_output=True, text=True)
print('rc', r.returncode)
print(r.stdout[-2000:])
if r.returncode:
    print(r.stderr[-2000:])
sys.exit(r.returncode)
