/** La aplicación real carga la API; las pruebas aisladas reciben este contrato explícito. */
import { beforeEach } from 'vitest';
import { installResourceCatalog } from '@/features/generation/model/resourceCatalog';
import { resourceCatalogFixture } from '@/test/resourceCatalogFixture';

beforeEach(() => installResourceCatalog(resourceCatalogFixture));
