-- Los códigos siguen la misma regla de generación automática que usa el backend
-- (ver app/modules/materiales/codigo.py): primeras 4 letras de la primera palabra
-- (+ "-" + primeras 3 letras de la segunda, si el nombre tiene más de una palabra).
INSERT INTO materiales (nombre, codigo, unidad, precio_actual) VALUES
    ('Cartón',        'CART',     'kg', 1.50),
    ('Plástico PET',  'PLAS-PET', 'kg', 3.20),
    ('Vidrio',        'VIDR',     'kg', 0.80),
    ('Aluminio',      'ALUM',     'kg', 12.00),
    ('Papel',         'PAPE',     'kg', 1.10)
ON CONFLICT (nombre) DO NOTHING;
