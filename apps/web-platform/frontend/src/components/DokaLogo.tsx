import React from "react";

interface DokaLogoProps {
  className?: string;
  size?: number;
  showText?: boolean;
}

export function DokaLogo({ className = "", size = 36, showText = true }: DokaLogoProps) {
  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* 3D Isometric Quantum Shield & Folded Document SVG */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 transition-transform hover:scale-105 duration-300"
      >
        <defs>
          <linearGradient id="doka-cyan-grad" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#22D3EE" />
            <stop offset="50%" stopColor="#0EA5E9" />
            <stop offset="100%" stopColor="#2563EB" />
          </linearGradient>
          <linearGradient id="doka-fold-grad" x1="28" y1="6" x2="40" y2="18" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38BDF8" />
            <stop offset="100%" stopColor="#0284C7" />
          </linearGradient>
          <linearGradient id="doka-laser-grad" x1="8" y1="24" x2="40" y2="24" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#10B981" stopOpacity="0" />
            <stop offset="50%" stopColor="#34D399" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Outer Hexagonal Shield Background */}
        <path
          d="M24 3L41 10V25C41 34.5 33.8 43 24 45C14.2 43 7 34.5 7 25V10L24 3Z"
          fill="#0B132B"
          stroke="url(#doka-cyan-grad)"
          strokeWidth="1.8"
        />

        {/* Isometric Document Silhouette with Folded Corner */}
        <path
          d="M16 14H30L36 20V34H16V14Z"
          fill="#0F172A"
          stroke="#38BDF8"
          strokeWidth="1.6"
        />
        {/* Folded Top-Right Corner */}
        <path
          d="M30 14V20H36"
          fill="url(#doka-fold-grad)"
          stroke="#38BDF8"
          strokeWidth="1.4"
        />

        {/* Stylized Modern "D" Cutout / Archway */}
        <path
          d="M21 21H25.5C27.5 21 29 22.5 29 24.5C29 26.5 27.5 28 25.5 28H21V21Z"
          stroke="url(#doka-cyan-grad)"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Horizontal Laser Scanning Beam */}
        <line x1="12" y1="28" x2="36" y2="28" stroke="url(#doka-laser-grad)" strokeWidth="1.8" />

        {/* Verification Checkpoint Pip (Emerald Green) */}
        <circle cx="36" cy="36" r="3" fill="#10B981" />
        <circle cx="36" cy="36" r="5" stroke="#10B981" strokeWidth="1" opacity="0.6" className="animate-ping" />
      </svg>

      {showText && (
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="block text-[17px] font-black tracking-tight text-white leading-none">
              DOKA<span className="text-cyan-400">.AI</span>
            </span>
            <span className="inline-block px-1.5 py-0.5 text-[9px] font-mono font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 rounded">
              DMS
            </span>
          </div>
          <span className="mt-1 block text-[9.5px] font-semibold uppercase tracking-[0.2em] text-slate-400 leading-none">
            Document Intelligence
          </span>
        </div>
      )}
    </div>
  );
}

export default DokaLogo;
