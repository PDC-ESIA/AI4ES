"""Harness confiável da imagem. Só publica contagens, nunca saída do teste."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.request import urlopen


def main():
    job = json.loads(Path('/input/job.json').read_text())
    shutil.copytree('/input/suite', '/work/suite')
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp',
           'PYTHONPATH': '/work/suite:/work/suite/src',
           'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONUTF8': '1',
           'PLAYWRIGHT_BROWSERS_PATH': '/opt/browsers'}
    server = None
    try:
        if job['modo'] == 'pytest':
            argv = ['python', '-P', '-m', 'pytest', '-c', '/opt/qa/pytest.ini',
                    '-p', 'pytest_cov', '-p', 'pytest_jsonreport.plugin',
                    job['teste'], '--cov=.', '--cov-report=json:/tmp/coverage.json',
                    '--json-report', '--json-report-file=/tmp/report.json']
            report = Path('/tmp/report.json')
        else:
            validated = subprocess.run(['node', '/opt/qa/validate-spec.cjs',
                                        '/work/suite/' + job['teste']],
                                       env=env, timeout=10, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
            if validated.returncode:
                raise ValueError('Spec rejected')
            if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*', job['entrypoint']):
                raise ValueError('Invalid entrypoint')
            shutil.copytree('/input/app', '/work/app')
            app_env = dict(env, PYTHONPATH='/work/app:/work/app/src')
            server = subprocess.Popen(['python', '-P', '-m', 'uvicorn', job['entrypoint'],
                                       '--host', '127.0.0.1', '--port', '8765'],
                                      cwd='/work/app', env=app_env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ready = False
            for _ in range(50):
                if server.poll() is not None:
                    break
                try:
                    with urlopen('http://127.0.0.1:8765/openapi.json', timeout=.2):
                        ready = True
                        break
                except OSError:
                    time.sleep(.1)
            if not ready:
                raise RuntimeError('Target unavailable')
            # A resolução de @playwright/test no spec usa apenas o pacote da imagem.
            os.symlink('/opt/qa/node_modules', '/work/suite/node_modules')
            env['QA_SPEC'] = job['teste']
            argv = ['node', '/opt/qa/node_modules/@playwright/test/cli.js', 'test',
                    '--config', '/opt/qa/playwright.config.cjs']
            report = Path('/tmp/playwright.json')
        run = subprocess.run(argv, cwd='/work/suite', env=env, timeout=job['timeout'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if report.stat().st_size > 2_000_000:
            raise ValueError('Report too large')
        data = json.loads(report.read_text())
        if job['modo'] == 'pytest':
            summary = data.get('summary', {})
            result = {key: summary.get(key, 0) for key in ('passed', 'failed', 'skipped')}
            result['errors'] = []
            for test in data.get('tests', [])[:1000]:
                if test.get('outcome') != 'failed':
                    continue
                message = str(test.get('call', {}).get('crash', {}).get('message', ''))
                kind = next((name for name in ('AssertionError', 'ImportError', 'ModuleNotFoundError',
                            'TypeError', 'ValueError', 'RuntimeError', 'TimeoutError')
                             if re.search(r'\b' + name + r'\b', message)), 'TestFailure')
                result['errors'].append({'line': test.get('lineno', 0) + 1, 'type': kind})
                if len(result['errors']) >= 20:
                    break
            coverage = Path('/tmp/coverage.json')
            if coverage.is_file() and coverage.stat().st_size <= 2_000_000:
                totals = json.loads(coverage.read_text()).get('totals', {})
                result.update({key: totals.get(key, 0) for key in ('covered_lines', 'num_statements')})
        else:
            stats = data.get('stats', {})
            result = dict(passed=stats.get('expected', 0),
                          failed=stats.get('unexpected', 0) + stats.get('flaky', 0),
                          skipped=stats.get('skipped', 0))
        result['exit_code'] = run.returncode
        print(json.dumps(result), flush=True)
    finally:
        if server is not None:
            server.kill()
            server.wait(timeout=5)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(json.dumps({'exit_code': 1, 'failed': 0, 'passed': 0, 'skipped': 0}), flush=True)
