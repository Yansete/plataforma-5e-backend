# Guía de ramas commits y pull requests

## Ramas

`main` conserva entregas revisadas. Usar `feature/nombre` para funcionalidades y `fix/nombre` para
correcciones; si el equipo mantiene `develop`, integrar allí el trabajo habitual. Para esta limpieza
la base acordada es `main` y la rama es `fix/limpieza-arquitectura`.

Antes de actualizar, revisar `git status` y conservar cualquier cambio local. Con la copia limpia:

```bash
git switch main
git pull origin main
git switch -c fix/limpieza-arquitectura
```

No crear ramas permanentes por integrante. Mantener un grupo de cambios por commit.

## Convención de commits

Formato: `tipo: descripción breve en español`.

| Tipo | Uso |
|---|---|
| `feat` | Funcionalidad nueva |
| `fix` | Corrección de un error |
| `refactor` | Reorganización del código |
| `docs` | Documentación |
| `test` | Pruebas |

```bash
git status
git diff
git add ruta/del/archivo
git diff --cached
git commit -m "fix: rechazar decisiones inválidas"
```

Usar únicamente la identidad de quien realiza el trabajo y no añadir `Co-Authored-By`.
Capturas, informes y evidencias van a Notion; `test-results/` queda fuera del repositorio.

## Abrir un pull request

Ejecutar las verificaciones de [overview.md](architecture/overview.md) y revisar el diff antes de publicar.
El push y la apertura del PR los realiza la autora después de revisar los resultados:

```bash
git push -u origin fix/limpieza-arquitectura
```

En GitHub, abrir **Compare & pull request**, con base `main` y compare `fix/limpieza-arquitectura`
para esta tarea. Describir el problema corregido, alcance y resultados de pruebas, enlazar la evidencia
registrada en Notion y solicitar revisión. No integrar antes de la aprobación del responsable.
