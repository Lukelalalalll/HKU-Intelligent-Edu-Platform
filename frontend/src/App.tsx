/**
 * Root component wiring the React Query provider to the route tree.
 */
import { QueryClientProvider } from "@tanstack/react-query";
import AppRoutes from "./app/AppRoutes";
import { queryClient } from "./queryClient";

/**
 * Root component that provides the shared query client.
 */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRoutes />
    </QueryClientProvider>
  );
}
