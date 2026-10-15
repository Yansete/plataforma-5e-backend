/**
 * Iconos de trazo: 1,5 px sobre rejilla de 20 px, extremos redondeados (sección 5).
 * Son decorativos (aria-hidden). Si un botón solo tiene icono, el botón lleva aria-label.
 */
const PATHS = {
  home: 'M3.5 9 10 3.5 16.5 9v7a1 1 0 0 1-1 1h-3.5v-5h-4v5H4.5a1 1 0 0 1-1-1Z',
  upload: 'M10 13V3.5M6.5 7 10 3.5 13.5 7M3.5 12.5v2.5a1.5 1.5 0 0 0 1.5 1.5h10a1.5 1.5 0 0 0 1.5-1.5v-2.5',
  sliders: 'M4 5.5h7M14.5 5.5H16M4 10h2.5M10 10h6M4 14.5h7M14.5 14.5H16M12.75 4v3M8.25 8.5v3M12.75 13v3',
  review: 'M4.5 3.5h8l3 3v10a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1v-12a1 1 0 0 1 1-1ZM7 11l2 2 4-4.5',
  export: 'M3.5 7.5 10 4l6.5 3.5v5L10 16l-6.5-3.5ZM3.5 7.5 10 11l6.5-3.5M10 11v5',
  chart: 'M3.5 16.5h13M5.5 13.5v-4M9 13.5v-8M12.5 13.5v-6M16 13.5v-2.5',
  file: 'M5.5 2.5h6l3.5 3.5v10.5a1 1 0 0 1-1 1h-8.5a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1ZM11.5 2.5V6h3.5M7.5 10h5M7.5 13h5',
  check: 'M4.5 10.5 8 14l7.5-8',
  x: 'M5.5 5.5l9 9M14.5 5.5l-9 9',
  edit: 'M12.5 4.5l3 3-8.5 8.5H4v-3ZM11 6l3 3',
  trash: 'M4 6h12M8 6V4.5h4V6M5.5 6l.75 10a1 1 0 0 0 1 .9h5.5a1 1 0 0 0 1-.9L14.5 6M8.5 9v5M11.5 9v5',
  alert: 'M10 3.5 17 16H3ZM10 8.5v3.5M10 14.25v.25',
  info: 'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14ZM10 9v4.5M10 6.5v.25',
  chevronRight: 'M8 5l5 5-5 5',
  chevronLeft: 'M12 5l-5 5 5 5',
  reset: 'M4 10a6 6 0 1 0 1.8-4.3M4 3.5v3h3',
  menu: 'M3.5 5.5h13M3.5 10h13M3.5 14.5h13',
  clock: 'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14ZM10 6v4l2.5 2',
  book: 'M3.5 4.5h4.5a2 2 0 0 1 2 2v10a1.5 1.5 0 0 0-1.5-1.5H3.5ZM16.5 4.5H12a2 2 0 0 0-2 2v10a1.5 1.5 0 0 1 1.5-1.5h5Z',
  download: 'M10 3.5V13M6.5 9.5 10 13l3.5-3.5M3.5 13.5v1.5a1.5 1.5 0 0 0 1.5 1.5h10a1.5 1.5 0 0 0 1.5-1.5v-1.5',
  layers: 'M10 3.5 17 7l-7 3.5L3 7ZM3 10.5 10 14l7-3.5M3 14l7 3.5 7-3.5',
  pending: 'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14ZM7 10h.25M10 10h.25M13 10h.25',
  undo: 'M6.5 7.5h6a3.5 3.5 0 0 1 0 7H9M6.5 7.5 9 5M6.5 7.5 9 10',
  arrowRight: 'M4 10h12M11.5 5.5 16 10l-4.5 4.5',
  quote: 'M6 3.5h8v13l-4-3-4 3Z',
  target: 'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14ZM10 13.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM10 10.25v-.5',
  table: 'M3.5 4.5h13v11h-13ZM3.5 8.5h13M3.5 12h13M8 8.5v7',
  plus: 'M10 4v12M4 10h12',
  search: 'M9 15a6 6 0 1 0 0-12 6 6 0 0 0 0 12ZM13.5 13.5 17 17',
  logout: 'M8 16.5H4.5a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1H8M13 13.5 16.5 10 13 6.5M16.5 10H8',
  refresh: 'M16 10a6 6 0 0 1-10.5 4M4 10a6 6 0 0 1 10.5-4M14.5 3v3h-3M5.5 17v-3h3',
  link: 'M8.5 11.5a3 3 0 0 0 4.24 0l2.5-2.5a3 3 0 0 0-4.24-4.24l-.75.75M11.5 8.5a3 3 0 0 0-4.24 0l-2.5 2.5a3 3 0 0 0 4.24 4.24l.75-.75',
  write: 'M4 16h12M12.5 3.5l3 3-7 7H5.5v-3Z',
} as const;

export type IconName = keyof typeof PATHS;

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
}

export function Icon({ name, size = 20, className }: IconProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
