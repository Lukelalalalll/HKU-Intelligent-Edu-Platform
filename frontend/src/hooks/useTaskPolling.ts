import { useQuery } from "@tanstack/react-query";

export const TERMINAL_TASK_STATUSES = ["completed", "completed_with_errors", "failed", "cancelled"] as const;

export function isTerminalTaskStatus(status?: string | null): boolean {
  return Boolean(status && (TERMINAL_TASK_STATUSES as readonly string[]).includes(status));
}

export function useTaskPolling<T>(options: {
  queryKey: readonly unknown[];
  queryFn: () => Promise<T>;
  enabled?: boolean;
  getStatus?: (value: T) => string | null | undefined;
  intervalMs?: number;
}) {
  const { getStatus, intervalMs = 2_000 } = options;
  return useQuery({
    queryKey: options.queryKey,
    queryFn: options.queryFn,
    enabled: options.enabled,
    refetchInterval: (query) => {
      if (!getStatus || !query.state.data) return intervalMs;
      return isTerminalTaskStatus(getStatus(query.state.data)) ? false : intervalMs;
    },
  });
}
