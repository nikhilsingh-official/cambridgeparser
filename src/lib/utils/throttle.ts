export function throttle<T extends (...args: any[]) => void>(fn: T, limit = 30) {
  let last = 0;
  return (...args: Parameters<T>) => {
    const now = Date.now();
    if (now - last >= limit) {
      last = now;
      fn(...args);
    }
  };
}