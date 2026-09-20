"use client";

const MainError = ({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "16px",
        padding: "80px 40px",
        textAlign: "center",
        background: "var(--tv-surface, #1E222D)",
        border: "1px solid var(--tv-border, #2A2E39)",
        borderRadius: "6px",
        color: "var(--tv-text-1, #D1D4DC)",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          fontWeight: 500,
          letterSpacing: "0.4px",
          textTransform: "uppercase",
          color: "var(--tv-text-3, #787B86)",
        }}
      >
        ◆ Something went wrong
      </div>
      <div style={{ fontSize: "13px", color: "var(--tv-text-3, #787B86)" }}>
        This section failed to load. You can try again.
      </div>
      <button
        onClick={() => reset()}
        style={{
          padding: "8px 20px",
          fontSize: "13px",
          fontWeight: 600,
          color: "#FFFFFF",
          background: "var(--tv-accent, #2962FF)",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
        }}
      >
        Try again
      </button>
    </div>
  );
};

export default MainError;
