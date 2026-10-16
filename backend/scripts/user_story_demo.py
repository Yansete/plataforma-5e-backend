"""Script ejecutable para la demostración de punta a punta del flujo de la historia de usuario."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import httpx

# Contrato de datos de entrada para la solicitud de generación
GENERATION_PAYLOAD = {
    "unidad_id": "u2",
    "resultado_aprendizaje_id": None,
    "etapa_5e": "explore",
    "tipo_recurso": "guia_exploracion",
    "cantidad": 3,
    "dificultad": "intermedia",
    "alternativas": 4,
    "top_k": 10,
    "umbral_evidencia": 0.6,
    "indicaciones": "Contexto de demo",
    "publico_objetivo": "Tercer ciclo",
    "competencia": "Pensamiento crítico",
    "modalidades": ["Textual"],
}


def run_demo() -> int:
    parser = argparse.ArgumentParser(description="Ejecutor de la demostración de punta a punta")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL base del backend")
    parser.add_argument("--salida", default="salida_demo", help="Directorio de salida para el archivo XML generado")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    output_directory = Path(args.salida)
    output_directory.mkdir(parents=True, exist_ok=True)

    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        # 1. Solicitar generación de recursos didácticos
        response = client.post("/api/v1/recursos/generar", json=GENERATION_PAYLOAD)
        if response.status_code != 200:
            print(f"Error durante la generación de recursos: {response.text}", file=sys.stderr)
            return 1

        resources = response.json()
        if not resources:
            print("No se generaron recursos", file=sys.stderr)
            return 1

        first_resource = resources[0]
        first_id = first_resource["id"]

        # Intento de aprobación prematura (debe fallar para demostrar la regla de negocio)
        premature_approval = client.post(f"/api/v1/recursos/{first_id}/aprobar", json={})
        if premature_approval.status_code == 400:
            print("aprobacion_bloqueada: la plataforma exige decidir las alternativas antes de aprobar.")
        else:
            print("aprobacion_bloqueada")

        # 2. Registrar decisiones docentes sobre las alternativas
        decision_endpoint = f"/api/v1/recursos/{first_id}/alternativas"
        client.post(f"{decision_endpoint}/B/decision", json={"decision": "aceptar"})
        client.post(f"{decision_endpoint}/C/decision", json={"decision": "editar", "texto": "Texto editado por el docente"})
        client.post(f"{decision_endpoint}/D/decision", json={"decision": "descartar"})

        # Decidir sobre las alternativas del segundo recurso
        if len(resources) > 1:
            second_id = resources[1]["id"]
            for option_letter in "BCD":
                client.post(f"/api/v1/recursos/{second_id}/alternativas/{option_letter}/decision", json={"decision": "aceptar"})

        # 3. Aprobar formalmente los recursos revisados
        client.post(f"/api/v1/recursos/{first_id}/aprobar", json={})
        if len(resources) > 1:
            client.post(f"/api/v1/recursos/{resources[1]['id']}/aprobar", json={})

        # 4. Exportar los recursos aprobados al formato Moodle XML
        export_response = client.post("/api/v1/exportaciones", json={"formato": "moodle_xml"})
        if export_response.status_code != 200:
            print(f"Error durante la exportación: {export_response.text}", file=sys.stderr)
            return 1

        xml_output_path = output_directory / "preguntas_moodle.xml"
        xml_output_path.write_bytes(export_response.content)
        print(f"Demostración completada con éxito. Archivo exportado en: {xml_output_path}")
        return 0


if __name__ == "__main__":
    sys.exit(run_demo())