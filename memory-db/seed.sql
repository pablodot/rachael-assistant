-- Rachael – seed de desarrollo
-- Datos mínimos para validar el esquema y probar la integración.

-- Sesión inicial de demo
INSERT INTO sessions (id, title, status)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'Sesión de demo',
    'active'
);

-- Mensajes de ejemplo
INSERT INTO messages (session_id, role, content, tokens)
VALUES
    ('a0000000-0000-0000-0000-000000000001', 'user',      'Hola Rachael, ¿cómo estás?', 8),
    ('a0000000-0000-0000-0000-000000000001', 'assistant', 'Hola, estoy operativa y lista. ¿En qué te puedo ayudar?', 15);

-- Tarea de demo con un plan simple
INSERT INTO tasks (id, session_id, goal, plan_json, status)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    'Buscar hoteles en Valencia',
    '{
        "goal": "Buscar hoteles en Valencia",
        "steps": [
            {"tool": "browser.open",     "args": {"url": "https://booking.com"}, "needs_ok": false},
            {"tool": "browser.navigate", "args": {"query": "Valencia"},          "needs_ok": false},
            {"tool": "browser.extract",  "args": {"selector": ".hotel-list"},    "needs_ok": false}
        ]
    }',
    'pending'
);

-- Approval de demo (paso que requeriría confirmación)
INSERT INTO approvals (task_id, step_index, ok_prompt, status)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    2,
    'A punto de extraer resultados. ¿Continuar?',
    'pending'
);

-- Entidad extraída
INSERT INTO entities (name, entity_type, attributes, source_session_id)
VALUES (
    'Valencia',
    'place',
    '{"country": "España", "type": "city"}',
    'a0000000-0000-0000-0000-000000000001'
);

-- Registro de browser_run
INSERT INTO browser_runs (task_id, url, action, args_json, result_json, status)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'https://booking.com',
    'browser.open',
    '{"url": "https://booking.com"}',
    '{"page_title": "Booking.com", "status_code": 200}',
    'success'
);
