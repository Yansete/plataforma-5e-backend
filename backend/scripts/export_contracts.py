"""
Script de exportación y compilación de esquemas JSON Schema.
"""

import json
from pathlib import Path

from plataforma5e.adapters.inbound.contratos.solicitud import GenerationRequestModel
from plataforma5e.adapters.inbound.contratos.engage import ResourceEngageItemModel
from plataforma5e.adapters.inbound.contratos.explore import ResourceExploreItemModel
from plataforma5e.adapters.inbound.contratos.explain import ResourceExplainItemModel
from plataforma5e.adapters.inbound.contratos.elaborate import ResourceElaborateItemModel
from plataforma5e.adapters.inbound.contratos.evaluate import ResourceEvaluateItemModel

# Determina la raíz del repositorio y el directorio de documentación compartido
ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "docs" / "api" / "contracts"


def exportar_todos_los_contratos() -> None:
    """Serializa cada contrato de datos en un archivo JSON Schema versionado."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    catalogo_contratos = {
        "generation-request.v1.json": GenerationRequestModel.model_json_schema(),
        "resource-engage.v1.json": ResourceEngageItemModel.model_json_schema(),
        "resource-explore.v1.json": ResourceExploreItemModel.model_json_schema(),
        "resource-explain.v1.json": ResourceExplainItemModel.model_json_schema(),
        "resource-elaborate.v1.json": ResourceElaborateItemModel.model_json_schema(),
        "resource-evaluate.v1.json": ResourceEvaluateItemModel.model_json_schema()
    }
    
    for nombre_archivo, esquema_json in catalogo_contratos.items():
        ruta_salida = OUTPUT_DIR / nombre_archivo
        with open(ruta_salida, "w", encoding="utf-8") as archivo:
            json.dump(esquema_json, archivo, indent=2, ensure_ascii=False)
        print(f"Esquema exportado exitosamente: {nombre_archivo}")


if __name__ == "__main__":
    exportar_todos_los_contratos()