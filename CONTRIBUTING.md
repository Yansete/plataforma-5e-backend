# Cómo contribuir

## Ramas
- `main` siempre se puede desplegar: Render publica el backend desde esta rama.
- Una rama por tarea, en inglés y kebab-case: `feature/scorm-export`, `fix/hide-chunk-count`, `docs/api-reference`.
- Mensajes de commit en inglés con Conventional Commits: `feat: add SCORM 1.2 exporter`.

## Pull requests y merges
1. El PR va hacia `main`, con la plantilla completa y el CI en verde.
2. El líder de la semana (rotación en Notion y en `.github/CODEOWNERS`) revisa, baja la rama, la prueba y aprueba.
3. Solo el líder de la semana hace clic en «Merge». Por defecto «Squash and merge»; los PR que mueven o renombran muchos archivos usan «Create a merge commit» para que Git siga el historial de cada archivo.
4. Los PR del propio líder los aprueba el suplente; igual los fusiona el líder.
5. Cada lunes, el líder nuevo abre un PR que pone su usuario en `CODEOWNERS`; lo aprueba el líder saliente.

## Antes de pedir revisión
- Frontend: los cambios y sus comprobaciones se realizan en [su repositorio](https://github.com/Yansete/plataforma-5e-frontend). El workflow End-to-end comprueba su compatibilidad con este backend.
- Backend: ejecutar `python -m pytest` desde la carpeta `backend/`.
- Nombres en inglés; el español queda para comentarios y textos de la interfaz.
