import React from "react";

export function RadarIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx={12} cy={12} r={9} opacity={0.4} />
      <path d="M12 3a9 9 0 0 1 9 9" />
      <path d="M12 12l4 4" />
      <circle cx={12} cy={12} r={1.5} />
    </svg>
  );
}

export function PowerIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M12 2v10" />
      <path d="M6.2 6.2a8 8 0 1 0 11.3 0" />
    </svg>
  );
}

export function PulseIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M3 12h4l2-5 4 10 2-5h6" />
    </svg>
  );
}

export function RefreshIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M20 11a8.1 8.1 0 0 0-15.5-2m-.5-5v5h5" />
      <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 5v-5h-5" />
    </svg>
  );
}

export function HistoryIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M3 13a9 9 0 1 0 3.4-7" />
      <path d="M3 4v5h5" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

export function CompassIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx={12} cy={12} r={9} />
      <path d="M9.5 9.5 7 17l7.5-2.5L17 7z" />
    </svg>
  );
}

export function TerminalIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="m7 8 4 4-4 4" />
      <path d="M13 16h4" />
      <rect x={3} y={4} width={18} height={16} rx={2} />
    </svg>
  );
}
