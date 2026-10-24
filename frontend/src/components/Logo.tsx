/** The product's mark: three rising bars on an indigo tile. */
export function Logo({ size = 32 }: { size?: number }) {
  return (
    <span
      aria-hidden
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none",
        width: size,
        height: size,
        borderRadius: size * 0.28,
        background: "linear-gradient(135deg, #818cf8 0%, #6d28d9 100%)",
        boxShadow: "0 4px 12px rgba(79, 70, 229, 0.35)",
      }}
    >
      <svg width={size * 0.56} height={size * 0.56} viewBox="0 0 18 18">
        <rect x="1" y="10" width="4" height="7" rx="2" fill="#fff" fillOpacity="0.65" />
        <rect x="7" y="6" width="4" height="11" rx="2" fill="#fff" fillOpacity="0.82" />
        <rect x="13" y="1" width="4" height="16" rx="2" fill="#fff" />
      </svg>
    </span>
  );
}
