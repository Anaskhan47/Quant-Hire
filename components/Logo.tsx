import React from 'react';

interface LogoProps {
  width?: number | string;
  height?: number | string;
  className?: string;
  showGlow?: boolean;
}

/**
 * QuantHire Premium AI Logo Component
 * Concept: 'Neural Bolt' - Symbolizing Speed, Intelligence, and Data Precision.
 */
const Logo: React.FC<LogoProps> = ({ 
  width = 240, 
  height = 60, 
  className = "", 
  showGlow = true 
}) => {
  return (
    <div className={`inline-flex items-center ${className} ${showGlow ? 'drop-shadow-[0_0_15px_rgba(16,185,129,0.3)]' : ''}`}>
      <svg 
        width={width} 
        height={height} 
        viewBox="0 0 240 60" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
        className="transition-all duration-300 transform hover:scale-[1.02]"
      >
        <defs>
          <linearGradient id="emeraldGradient" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#10B981" />
            <stop offset="100%" stopColor="#34D399" />
          </linearGradient>
          
          <filter id="logoGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Neural Bolt Container */}
        <rect 
          x="0" 
          y="10" 
          width="40" 
          height="40" 
          rx="10" 
          fill="url(#emeraldGradient)" 
          filter={showGlow ? "url(#logoGlow)" : "none"} 
        />
        
        {/* Bolt Icon */}
        <path 
          d="M24.5 18L15.5 31H21.5L18.5 42L27.5 29H21.5L24.5 18Z" 
          fill="white" 
        />

        {/* QuantHire Branding */}
        <text 
          x="52" 
          y="40" 
          style={{ 
            fontFamily: "'Inter', sans-serif", 
            fontWeight: 800, 
            fontSize: '32px', 
            letterSpacing: '-0.04em',
            WebkitUserSelect: 'none',
            userSelect: 'none'
          }}
        >
          <tspan fill="white">Quant</tspan><tspan fill="#34D399">Hire</tspan>
        </text>
      </svg>
    </div>
  );
};

export default Logo;
