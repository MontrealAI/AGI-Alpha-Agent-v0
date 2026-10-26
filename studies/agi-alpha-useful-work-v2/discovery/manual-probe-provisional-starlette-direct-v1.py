# SPDX-License-Identifier: Apache-2.0
"""Development-only consumer observations; no decision or approval is inferred."""
from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import time
import types


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_subject(consumer_dir):
    model_path = consumer_dir / 'models.py'
    spec = importlib.util.spec_from_file_location('alpha_component_models', model_path)
    models = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = models
    spec.loader.exec_module(models)
    api_path = consumer_dir / 'api.py'
    raw = api_path.read_bytes()
    source = raw.decode()
    tree = ast.parse(source)
    names = {'MAX_REQUEST_BYTES', 'BODY_TIMEOUT_SECONDS', 'SECURITY_HEADERS', 'RequestBoundary', 'Review', 'Control'}
    selected = []
    slices = []
    for node in tree.body:
        present = {node.name} if isinstance(node, ast.ClassDef) else {
            target.id for target in node.targets if isinstance(target, ast.Name)
        } if isinstance(node, ast.Assign) else set()
        if present & names:
            selected.append(node)
            piece = ast.get_source_segment(source, node)
            slices.append({'names': sorted(present & names), 'start_line': node.lineno,
                           'end_line': node.end_lineno, 'sha256': sha(piece.encode())})
    if {name for row in slices for name in row['names']} != names:
        raise ValueError('SOURCE_PROJECTION_INCOMPLETE')
    header = ast.parse('from __future__ import annotations\nimport asyncio\nfrom typing import Literal\n'
                       'from pydantic import Field\nfrom starlette.requests import Request\n'
                       'from starlette.responses import JSONResponse\n'
                       'from starlette.types import ASGIApp, Message, Receive, Scope, Send\n').body
    module = types.ModuleType('alpha_component_boundary')
    module.__dict__['StrictModel'] = models.StrictModel
    sys.modules[module.__name__] = module
    compiled = ast.fix_missing_locations(ast.Module(body=header + selected, type_ignores=[]))
    exec(compile(compiled, str(api_path), 'exec'), module.__dict__)
    identity = {'api_sha256': sha(raw), 'models_sha256': sha(model_path.read_bytes()),
                'api_slices': slices, 'projection_imports_sha256': sha(ast.dump(ast.Module(body=header, type_ignores=[])).encode()),
                'original_timeout_seconds': module.BODY_TIMEOUT_SECONDS,
                'original_byte_limit': module.MAX_REQUEST_BYTES,
                'whole_api_imported': False, 'create_app_called': False,
                'journal_created': False, 'credentials_created': False}
    return module, models, identity


def chunks_for(case):
    chunks = []
    for entry in case['input'].get('chunks', []):
        if set(entry) == {'text'}:
            chunks.append(entry['text'].encode('utf-8'))
        elif set(entry) == {'byte', 'count'} and isinstance(entry['count'], int) and 0 <= entry['count'] <= 524289:
            chunks.append(bytes([entry['byte']]) * entry['count'])
        else:
            raise ValueError('UNSUPPORTED_FIXTURE_CHUNK')
    return chunks


async def observe_asgi(case, boundary):
    item = case['input']
    chunks = chunks_for(case)
    headers = [(name.lower().encode('latin1'), value.encode('latin1')) for name, value in item.get('headers', [])]
    if not any(name == b'host' for name, _ in headers):
        headers.append((b'host', b'127.0.0.1:8765'))
    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'scheme': 'http',
             'method': item.get('method', 'POST'), 'path': '/api/missions', 'raw_path': b'/api/missions',
             'query_string': b'', 'root_path': '', 'server': ('127.0.0.1', 8765),
             'client': ('127.0.0.1', 10000), 'headers': headers}
    position = 0
    downstream_calls = 0
    downstream_body = b''
    emitted = []

    async def receive():
        nonlocal position
        delay = item.get('receive_delay_seconds', 0)
        if delay:
            await asyncio.sleep(delay)
        if position >= len(chunks):
            return {'type': 'http.disconnect'}
        current = position
        position += 1
        return {'type': 'http.request', 'body': chunks[current],
                'more_body': position < len(chunks) or item.get('disconnect', False)}

    async def send(message):
        emitted.append(message)

    async def downstream(inner_scope, inner_receive, inner_send):
        nonlocal downstream_calls, downstream_body
        downstream_calls += 1
        while True:
            event = await inner_receive()
            if event['type'] == 'http.disconnect':
                return
            downstream_body += event.get('body', b'')
            if not event.get('more_body', False):
                break
        await inner_send({'type': 'http.response.start', 'status': 200,
                          'headers': [(b'content-type', b'application/json'), (b'cache-control', b'public, max-age=3600')]})
        await inner_send({'type': 'http.response.body', 'body': b'{"component":"accepted"}', 'more_body': False})

    await boundary.RequestBoundary(downstream)(scope, receive, send)
    starts = [event for event in emitted if event['type'] == 'http.response.start']
    response_body = b''.join(event.get('body', b'') for event in emitted if event['type'] == 'http.response.body')
    parsed = json.loads(response_body) if response_body else None
    return {'response_present': bool(starts), 'status': starts[0]['status'] if starts else None,
            'response_starts': len(starts), 'headers': [[k.decode('latin1'), v.decode('latin1')] for k, v in starts[0].get('headers', [])] if starts else [],
            'response_body_utf8': response_body.decode('utf-8'),
            'error': parsed.get('error') if isinstance(parsed, dict) else None,
            'downstream_invocations': downstream_calls, 'input_bytes': sum(map(len, chunks)),
            'input_body_sha256': sha(b''.join(chunks)), 'downstream_body_bytes': len(downstream_body) if downstream_calls else None,
            'downstream_body_sha256': sha(downstream_body) if downstream_calls else None,
            'body_preserved': downstream_body == b''.join(chunks) if downstream_calls == 1 else None,
            'receive_calls': position}


def observe_model(case, boundary, models):
    item = case['input']
    value = json.loads(json.dumps(item['value']))
    materialized = []
    for override in item.get('nonfinite_overrides', []):
        cursor = value
        for part in override['path'][:-1]:
            cursor = cursor[part]
        actual = {'NaN': float('nan'), 'Infinity': float('inf'), '-Infinity': float('-inf')}[override['token']]
        cursor[override['path'][-1]] = actual
        materialized.append({**override, 'actual_type': type(actual).__name__,
                             'actual_repr': repr(actual)})
    target = getattr(boundary if item['model'] in {'Review', 'Control'} else models, item['model'])
    try:
        if item['method'] == 'model_validate':
            result = target.model_validate(value)
        elif item['method'] == 'model_validate_json':
            result = target.model_validate_json(json.dumps(value, allow_nan=False))
        else:
            raise ValueError('UNKNOWN_MODEL_METHOD')
        return {'accepted': True, 'output': result.model_dump(mode='json'), 'materialized_nonfinite': materialized}
    except Exception as exc:
        from pydantic import ValidationError
        if not isinstance(exc, ValidationError):
            raise
        return {'accepted': False, 'error_type': type(exc).__name__,
                'errors': [{'type': e['type'], 'loc': list(e['loc']), 'msg': e['msg']} for e in exc.errors()],
                'materialized_nonfinite': materialized}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--consumer', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('OUTPUT_EXISTS')
    start = time.perf_counter()
    cpu = time.process_time()
    boundary, models, identity = load_subject(args.consumer)
    contract_raw = args.contract.read_bytes()
    contract = json.loads(contract_raw)
    rows = []
    for case in contract['cases']:
        t = time.perf_counter()
        c = time.process_time()
        try:
            observation = asyncio.run(observe_asgi(case, boundary)) if case['kind'] == 'asgi' else observe_model(case, boundary, models)
            error = None
        except Exception as exc:
            observation = None
            error = f'{type(exc).__name__}: {exc}'
        rows.append({'id': case['id'], 'kind': case['kind'], 'observation': observation, 'execution_error': error,
                     'wall_seconds': time.perf_counter() - t, 'cpu_seconds': time.process_time() - c})
    versions = {n: importlib.metadata.version(n) for n in ['starlette', 'anyio', 'pydantic', 'pydantic-core',
                                                         'annotated-types', 'typing-extensions', 'typing-inspection', 'idna']}
    result = {'schema': 'manual-component-observations/v1', 'source_identity': identity,
              'contract_sha256': sha(contract_raw), 'versions': versions, 'observations': rows,
              'wall_seconds': time.perf_counter() - start, 'cpu_seconds': time.process_time() - cpu,
              'runtime_model_calls': 0, 'runtime_network_requests': 0, 'money_usd': None,
              'scope': 'Pure unchanged component definitions; harmless downstream fixture; not full API or release qualification'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'out': str(args.out), 'cases': len(rows), 'errors': sum(bool(r['execution_error']) for r in rows),
                      'wall_seconds': result['wall_seconds'], 'cpu_seconds': result['cpu_seconds']}))


if __name__ == '__main__':
    main()
