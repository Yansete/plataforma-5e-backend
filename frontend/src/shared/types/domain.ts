/**
 * Modelos de datos del frontend. Coinciden con las respuestas del backend (docs/openapi.json).
 */

/** Etapas del modelo instruccional (Bybee et al., 2006). En pantalla se muestran como momentos de la clase. */
export type Stage5E = 'engage' | 'explore' | 'explain' | 'elaborate' | 'evaluate';

export interface LearningOutcome {
  id: string;
  code: string;
  text: string;
}

export interface Unit {
  id: string;
  courseId: string;
  number: number;
  title: string;
  outcomes: LearningOutcome[];
}

export interface Course {
  id: string;
  code: string;
  name: string;
  term: string;
  sumilla?: string;
  logro?: string;
  units: Unit[];
}

export type FileKind = 'pdf' | 'pptx' | 'txt';

/** `registrado`: guardado sin procesar · `procesado`: con fragmentos · `error`: no se pudo leer. */
export type DocumentStatus = 'registrado' | 'procesando' | 'procesado' | 'error';

export interface MaterialDocument {
  id: string;
  fileName: string;
  kind: FileKind;
  sizeBytes: number;
  unitId: string;
  outcomeIds: string[];
  documentType: string;
  status: DocumentStatus;
  registeredAt: string;
  processedAt: string | null;
  fragmentCount: number;
  pageCount: number | null;
  errorMessage: string | null;
  /** Material creado desde un tema: enlace y licencia de la fuente abierta. */
  origin?: { fuente: string; url: string; licencia: string; tema: string };
}

export interface Fragment {
  id: string;
  orden: number;
  location: string;
  text: string;
}

export type ResourceType =
  | 'pregunta_detonante'
  | 'sondeo_diagnostico'
  | 'guia_exploracion'
  | 'caso_indagacion'
  | 'explicacion'
  | 'glosario'
  | 'ejercicio_aplicacion'
  | 'item_opcion_multiple';

export interface Citation {
  claim: string;
  fragmentIds: string[];
}

export type DistractorDecision = 'pendiente' | 'aceptado' | 'descartado';

export type DiscardReason = 'sin_sentido' | 'tambien_correcto' | 'duplicado' | 'fuera_de_unidad' | 'otro' | 'regenerado';

export interface ItemOption {
  id: string;
  text: string;
  isCorrect: boolean;
  feedback: string;
  sourceFragmentIds: string[];
  /** Solo los distractores se deciden; la clave no. */
  decision: DistractorDecision;
  discardReason: DiscardReason | null;
  edited: boolean;
}

export type ReviewStatus = 'pendiente' | 'aprobado' | 'descartado';

/** Copia del fragmento citado, guardada con el recurso al generarlo. */
export interface Evidence {
  id: string;
  text: string;
  location: string;
  documentId: string;
  documentName: string;
  sourceUrl?: string | null;
  license?: string | null;
}

export type Difficulty = 'basica' | 'intermedia' | 'avanzada';

/** Parámetros con que se pidió el recurso: «Regenerar» repite el pedido con ellos. */
export interface GenerationParams {
  resourceType: ResourceType;
  stage: Stage5E;
  outcomeId: string | null;
  difficulty: Difficulty;
  optionCount: number;
  instructions: string;
  audience?: string;
  competency?: string;
  modalities?: string[];
}

export interface Resource {
  id: string;
  unitId: string;
  outcomeId: string;
  stage: Stage5E;
  type: ResourceType;
  title: string;
  /** Contenido. En preguntas es el enunciado. Párrafos separados por línea en blanco. */
  body: string;
  options: ItemOption[] | null;
  citations: Citation[];
  status: ReviewStatus;
  edited: boolean;
  discardReason: DiscardReason | null;
  createdAt: string;
  updatedAt: string;
  decidedAt: string | null;
  evidence: Evidence[];
  params?: GenerationParams;
  /** `ia`: redactado por el modelo de lenguaje · `respaldo`: generador por reglas. */
  generatorKind?: 'ia' | 'respaldo';
}

export interface GenerationInput {
  unitId: string;
  outcomeId: string | null;
  resourceType: ResourceType;
  quantity: number;
  difficulty: Difficulty;
  optionCount: number;
  instructions: string;
  audience: string;
  competency: string;
  modalities: string[];
}

export type DownloadFormat = 'moodle_xml' | 'qti21' | 'documento';

export interface Download {
  id: string;
  unitId: string;
  format: DownloadFormat;
  fileName: string;
  resourceCount: number;
  createdAt: string;
}

export interface Session {
  email: string;
  name: string;
  token: string;
}

/** Recursos aprobados y por revisar de una unidad (GET /api/v1/resumen). */
export interface UnitSummary {
  courseId: string;
  unitId: string;
  approved: number;
  pending: number;
}
