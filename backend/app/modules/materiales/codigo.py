import unicodedata


def _sin_acentos_mayusculas(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_acentos.upper()


def _segmento(palabra: str, longitud: int) -> str:
    letras = _sin_acentos_mayusculas(palabra)
    return letras[:longitud].ljust(longitud, "0")


def generar_codigo_base(nombre: str) -> str:
    """CART, VIDR, ORO0 (una palabra) o PLAS-PET (dos o más palabras)."""
    palabras = nombre.strip().split()
    primera = _segmento(palabras[0], 4)
    if len(palabras) == 1:
        return primera
    segunda = _segmento(palabras[1], 3)
    return f"{primera}-{segunda}"
