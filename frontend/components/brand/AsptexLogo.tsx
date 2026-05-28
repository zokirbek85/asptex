interface LogoProps {
  variant?: "full" | "mark" | "wordmark";
  size?: number;
  className?: string;
  onDark?: boolean;
}

export function AsptexLogo({
  variant = "full",
  size = 32,
  className = "",
  onDark = false,
}: LogoProps) {
  const textColor = onDark ? "#FFFFFF" : "#0D2240";
  const accentColor = "#1565C0";
  const threadColor = "#00A88E";

  if (variant === "mark") {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        className={className}
        aria-label="ASPTEX"
      >
        {/* Square base with rounded corners */}
        <rect width="40" height="40" rx="10" fill={accentColor} />
        {/* Thread arc — top-left quarter circle suggesting a spool */}
        <path
          d="M8 20 Q8 8 20 8"
          stroke={threadColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
        />
        {/* Thread arc — bottom-right */}
        <path
          d="M20 32 Q32 32 32 20"
          stroke={threadColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
        />
        {/* Center diagonal — weave line */}
        <line
          x1="12" y1="28"
          x2="28" y2="12"
          stroke="rgba(255,255,255,0.35)"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        {/* A letterform — strong white */}
        <text
          x="20"
          y="26"
          textAnchor="middle"
          fontSize="17"
          fontWeight="700"
          fontFamily="Inter, system-ui, sans-serif"
          fill="white"
          letterSpacing="-0.5"
        >
          A
        </text>
      </svg>
    );
  }

  if (variant === "wordmark") {
    return (
      <svg
        width={size * 4}
        height={size}
        viewBox="0 0 160 40"
        fill="none"
        className={className}
        aria-label="ASPTEX"
      >
        <text
          x="0"
          y="28"
          fontSize="22"
          fontWeight="800"
          fontFamily="Inter, system-ui, sans-serif"
          fill={textColor}
          letterSpacing="-1"
        >
          ASPTEX
        </text>
      </svg>
    );
  }

  // full: mark + wordmark
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <AsptexLogo variant="mark" size={size} />
      <span
        className="font-extrabold tracking-tight select-none"
        style={{
          fontSize: size * 0.55,
          color: textColor,
          letterSpacing: "-0.04em",
        }}
      >
        ASPTEX
      </span>
    </div>
  );
}

export function AsptexFavicon({ size = 32 }: { size?: number }) {
  return <AsptexLogo variant="mark" size={size} />;
}
