import { useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";

export const TERMINAL_TASK_STATUSES = ["completed", "completed_with_errors", "failed", "cancelled"] as const;

export function isTerminalTaskStatus(status?: string | null): boolean {
  return Boolean(status && (TERMINAL_TASK_STATUSES as readonly string[]).includes(status));
}

export function useTaskPolling<T>(options: {
  queryKey: QueryKey;
  queryFn: (signal?: AbortSignal) => Promise<T>;
  enabled?: boolean;
  getStatus?: (value: T) => string | null | undefined;
  intervalMs?: number;
}) {
  const { getStatus, intervalMs = 2_000, enabled = true } = options;
  const client = useQueryClient();
  const query = useQuery({
    queryKey: options.queryKey,
    queryFn: ({ signal }) => options.queryFn(signal),
    enabled: options.enabled ?? enabled,
    refetchInterval: (query) => {
      if (!getStatus || !query.state.data) return intervalMs;
      return isTerminalTaskStatus(getStatus(query.state.data)) ? false : intervalMs;
    },
  });
  const value = query.data;
  const status = value === undefined ? undefined : getStatus?.(value);
  return {
    ...query,
    taskStatus: status,
    isTerminal: isTerminalTaskStatus(status),
    progress: value && typeof value === "object" && value !== null && "progress" in value && typeof value.progress === "number" ? value.progress : undefined,
    cancel: () => client.cancelQueries({ queryKey: options.queryKey }),
    retry: () => query.refetch(),
  };
}
