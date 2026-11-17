import { useEffect, type ReactNode } from 'react';

export function Sheet({ open, onClose, label, children }: { open: boolean; onClose: () => void; label: string; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div role="dialog" aria-modal="false" aria-label={label} className="fixed inset-x-0 bottom-16 z-30 mx-auto max-w-[560px] px-3 pb-3">
      <div className="rounded-lg border border-line bg-raised p-4">
        <div className="mb-2 flex justify-end">
          <button type="button" onClick={onClose} className="min-h-[44px] min-w-[44px] rounded-md text-muted hover:text-ink" aria-label="Close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
