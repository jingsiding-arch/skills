export type MockDelayOptions = {
  minMs?: number;
  maxMs?: number;
  failRate?: number; // 0..1
};

const defaultDelay: Required<MockDelayOptions> = {
  minMs: 120,
  maxMs: 420,
  failRate: 0,
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function withMockDelay<T>(
  fn: () => T,
  options: MockDelayOptions = {},
): Promise<T> {
  const { minMs, maxMs, failRate } = { ...defaultDelay, ...options };
  const ms = Math.floor(minMs + Math.random() * (maxMs - minMs));
  await sleep(ms);

  if (failRate > 0 && Math.random() < failRate) {
    throw new Error("Mock API error");
  }

  return fn();
}

export function createId(prefix = "id"): string {
  return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now()}`;
}
