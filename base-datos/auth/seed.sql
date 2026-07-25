-- El hash del admin fue generado con bcrypt fuera de este archivo
-- (backend/venv, bcrypt.hashpw) para no versionar contraseñas en texto plano.

-- Usuario: admin
-- Contraseña: GreenCircle2026i++
INSERT INTO admin (usuario, password_hash) VALUES
    ('admin', '$2b$12$jDhG73fiTXT9i9qy90fJ7e/Ykno7epPg3dVpb1sZhS9VxXhzV4oae')
ON CONFLICT (usuario) DO NOTHING;
