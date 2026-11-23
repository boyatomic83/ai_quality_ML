// Small building blocks shared by every section.

export function Card({ title, subtitle, children, className = "" }: {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`min-w-0 rounded-2xl border border-border bg-surface p-5 shadow-sm sm:p-6 ${className}`}>
      {title && <h2 className="text-lg font-semibold">{title}</h2>}
      {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      <div className={title || subtitle ? "mt-4" : ""}>{children}</div>
    </section>
  );
}

// Grey pulsing placeholder shown while data loads.
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-surface-2 ${className}`} />;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
      <p>
        <span className="font-semibold">Couldn&apos;t load data.</span> {message}
      </p>
      {onRetry && (
        <button onClick={onRetry} className="rounded-lg border border-current px-3 py-1 font-medium hover:bg-red-100 dark:hover:bg-red-900/40">
          Try again
        </button>
      )}
    </div>
  );
}
