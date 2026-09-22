import { QueryClientProvider } from "@tanstack/react-query";
import AppRoutes from "./app/AppRoutes";
import { queryClient } from "./queryClient";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRoutes />
    </QueryClientProvider>
  );
}
