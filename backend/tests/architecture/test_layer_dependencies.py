"""Dependencias de todas las capas mediante AST, incluidos imports relativos."""

from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path
import pytest

# Ruta base hacia el código fuente de la plataforma
RAIZ = Path(__file__).resolve().parents[2] / 'src' / 'platform5e'

# Matriz de reglas de dependencias prohibidas por capa
REGLAS = {
    'domain': (
        'platform5e.application',
        'platform5e.infrastructure',
        'fastapi',
        'sqlalchemy',
    ),
    'application': (
        'platform5e.infrastructure',
        'fastapi',
        'sqlalchemy',
    ),
    'infrastructure/http': (
        'platform5e.infrastructure.persistence',
    ),
}


def importaciones(fuente: str, paquete: str):
    """Extrae todos los módulos y alias importados a partir del árbol AST del archivo."""
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Import):
            yield from (alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ''
            if nodo.level:
                modulo = resolve_name('.' * nodo.level + modulo, paquete)
            yield modulo
            yield from (modulo + '.' + alias.name for alias in nodo.names)


def infracciones(fuente: str, paquete: str, prohibidos: tuple[str, ...]):
    """Determina si alguna importación viola la frontera arquitectónica establecida."""
    return [
        nombre
        for nombre in importaciones(fuente, paquete)
        if any(nombre == p or nombre.startswith(p + '.') for p in prohibidos)
    ]


@pytest.mark.parametrize('capa,prohibidos', REGLAS.items())
def test_capas_respetan_las_dependencias(capa, prohibidos):
    fallos = []
    archivos = list((RAIZ / capa).rglob('*.py'))
    assert archivos, f'No se encontraron módulos en {capa}'
    for archivo in archivos:
        # Construye la ruta de importación canónica bajo platform5e
        partes_relativas = archivo.relative_to(RAIZ).parent.parts
        paquete = '.'.join(['platform5e', *partes_relativas]) if partes_relativas else 'platform5e'
        errores = infracciones(archivo.read_text(encoding='utf-8'), paquete, prohibidos)
        fallos.extend(f'{archivo.relative_to(RAIZ)}: {nombre}' for nombre in errores)
    assert not fallos, '\n'.join(fallos)


@pytest.mark.parametrize('fuente,paquete,prohibido', [
    ('import fastapi as web', 'platform5e.domain', 'fastapi'),
    ('from sqlalchemy.exc import SQLAlchemyError', 'platform5e.infrastructure.http', 'sqlalchemy'),
    ('from platform5e import infrastructure', 'platform5e.application', 'platform5e.infrastructure'),
    ('from ..application import services', 'platform5e.domain', 'platform5e.application'),
    ('def funcion():\n    from ..infrastructure import http', 'platform5e.application', 'platform5e.infrastructure'),
])
def test_detecta_aliases_imports_relativos_y_dentro_de_funciones(fuente, paquete, prohibido):
    assert infracciones(fuente, paquete, (prohibido,))


def test_comentarios_y_textos_no_son_importaciones():
    assert infracciones('# import fastapi\ntexto = "sqlalchemy"', 'platform5e.domain', ('fastapi', 'sqlalchemy')) == []