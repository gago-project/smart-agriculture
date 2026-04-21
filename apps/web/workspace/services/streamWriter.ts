interface StreamOptions {
  chunkSize?: number;
  intervalMs?: number;
  onChunk: (chunk: string) => void;
  onDone?: () => void;
}

interface StreamControl {
  cancel: () => void;
}

export function simulateStream(text: string, options: StreamOptions): StreamControl {
  const chunkSize = Math.max(1, options.chunkSize ?? 8);
  const intervalMs = Math.max(10, options.intervalMs ?? 24);
  let offset = 0;
  let cancelled = false;

  const timer = setInterval(() => {
    if (cancelled) {
      clearInterval(timer);
      return;
    }

    const next = text.slice(offset, offset + chunkSize);
    if (!next) {
      clearInterval(timer);
      options.onDone?.();
      return;
    }

    options.onChunk(next);
    offset += chunkSize;

    if (offset >= text.length) {
      clearInterval(timer);
      options.onDone?.();
    }
  }, intervalMs);

  return {
    cancel() {
      cancelled = true;
      clearInterval(timer);
    }
  };
}
