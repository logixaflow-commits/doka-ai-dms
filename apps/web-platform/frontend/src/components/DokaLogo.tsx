import React from 'react';

interface DokaLogoProps {
  className?: string;
  size?: number;
  showText?: boolean;
}

export function DokaLogo({
  className = '',
  size = 40,
  showText = true,
}: DokaLogoProps) {
  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* Clean Cyber Shield Tile */}
      <img
        src="/logo.svg"
        alt="Doka Icon"
        width={size}
        height={size}
        className="shrink-0 object-contain rounded-2xl drop-shadow-[0_0_12px_rgba(34,211,238,0.25)] transition-transform duration-200 hover:scale-105"
      />

      {showText && (
        <div className="flex flex-col leading-none">
          <span className="text-[16px] font-bold tracking-tight text-white">
            Doka
          </span>
          <span className="mt-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            Document Intelligence
          </span>
        </div>
      )}
    </div>
  );
}

export default DokaLogo;
