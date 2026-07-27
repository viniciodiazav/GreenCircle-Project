-- Los hashes fueron generados con bcrypt fuera de este archivo
-- (backend/venv, bcrypt.hashpw) para no versionar contraseñas en texto plano.

-- Usuarios de desarrollo (2026-07-27) -- contraseña "pass1234" para los tres,
-- solo para pruebas locales/CI, nunca usar en producción real.
-- admin (administrador), op1 y op2 (operador).
INSERT INTO usuarios (usuario, password_hash, rol) VALUES
    ('admin', '$2b$12$8PBvzqx7qNo5I1yUPPgsSeiam6OLgzUY6ra0wO2Hw.bsjkxEVFM2G', 'administrador'),
    ('op1', '$2b$12$BaMDAHPfoW96JAAzH1J63uXhmfwsZiZLh5E9T7DyvknCCOxEIxtdK', 'operador'),
    ('op2', '$2b$12$r6U9ycVbcYtjtDGRVwtBKuy1LzHNHnNW0MuQIkbfyMN3Ee3loYELu', 'operador')
ON CONFLICT (usuario) DO NOTHING;
