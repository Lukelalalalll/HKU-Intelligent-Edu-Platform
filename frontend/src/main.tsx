/**
 * Browser entry point: mounts the router, app shell and global toast host.
 */
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import App from "./App";
import { initLocale } from "./i18n";
import "./styles.css";

// Resolve the stored/browser language before the first paint so <html lang> and
// the whole UI start in the same locale.
initLocale();

ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><BrowserRouter><App /></BrowserRouter><Toaster position="top-right" /></React.StrictMode>);

