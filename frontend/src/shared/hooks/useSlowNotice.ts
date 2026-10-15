import { useEffect, useState } from 'react';

/** true si la operación lleva más de `ms` milisegundos: el servidor gratuito puede estar despertando. */
export function useSlowNotice(active: boolean, ms = 5000): boolean {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    setSlow(false);
    if (!active) return;
    const timer = setTimeout(() => setSlow(true), ms);
    return () => clearTimeout(timer);
  }, [active, ms]);
  return slow;
}
