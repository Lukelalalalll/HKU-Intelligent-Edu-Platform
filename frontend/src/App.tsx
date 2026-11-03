/**
 * Root component wiring the React Query provider to the route tree.
 */
import { QueryClientProvider } from "@tanstack/react-query";
import AppRoutes from "./app/AppRoutes";
import { I18nProvider } from "./i18n";
import { queryClient } from "./queryClient";

/**
 * Root component that provides the shared query client and the active locale.
 */
export default function App() {
  return (
    <I18nProvider>
      <QueryClientProvider client={queryClient}>
        <AppRoutes />
      </QueryClientProvider>
    </I18nProvider>
  );
}
