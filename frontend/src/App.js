import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { useAuthStore } from './stores';

// Layout
import Layout from './components/Layout';

// Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import MappaPage from './pages/MappaPage';
import ImmobiliPage from './pages/ImmobiliPage';
import ImmobileFormPage from './pages/ImmobileFormPage';
import ContrattiPage from './pages/ContrattiPage';
import ContrattoWizardPage from './pages/ContrattoWizardPage';
import SoggettiPage from './pages/SoggettiPage';
import PagamentiPage from './pages/PagamentiPage';
import NotifichePage from './pages/NotifichePage';
import ImmobileDetailPage from './pages/ImmobileDetailPage';
import VerbaleFormPage from './pages/VerbaleFormPage';
import ApePage from './pages/ApePage';
import AiAssistantPage from './pages/AiAssistantPage';
import ImpostazioniPage from './pages/ImpostazioniPage';

// Protected Route component
function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <Layout>{children}</Layout>;
}

// Public Route (redirects to dashboard if already logged in)
function PublicRoute({ children }) {
  const { isAuthenticated } = useAuthStore();
  
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  
  return children;
}

// Placeholder page for routes not yet implemented
function PlaceholderPage({ title }) {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="text-center">
        <h1 className="text-2xl font-bold font-heading mb-2">{title}</h1>
        <p className="text-slate-500">Pagina in costruzione</p>
      </div>
    </div>
  );
}

function App() {
  return (
    <>
      <Toaster 
        position="top-right" 
        richColors 
        closeButton 
        toastOptions={{
          duration: 4000,
        }}
      />
      
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route 
            path="/login" 
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            } 
          />
          
          {/* Protected Routes */}
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/mappa" 
            element={
              <ProtectedRoute>
                <MappaPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Immobili */}
          <Route 
            path="/immobili" 
            element={
              <ProtectedRoute>
                <ImmobiliPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/immobili/nuovo" 
            element={
              <ProtectedRoute>
                <ImmobileFormPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/immobili/:id" 
            element={
              <ProtectedRoute>
                <ImmobileDetailPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/immobili/:id/modifica" 
            element={
              <ProtectedRoute>
                <ImmobileFormPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Contratti */}
          <Route 
            path="/contratti" 
            element={
              <ProtectedRoute>
                <ContrattiPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/contratti/nuovo" 
            element={
              <ProtectedRoute>
                <ContrattoWizardPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/contratti/:id" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Dettaglio Contratto" />
              </ProtectedRoute>
            } 
          />
          
          {/* Soggetti */}
          <Route 
            path="/soggetti" 
            element={
              <ProtectedRoute>
                <SoggettiPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/soggetti/nuovo" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Nuovo Soggetto" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/soggetti/:id" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Dettaglio Soggetto" />
              </ProtectedRoute>
            } 
          />
          
          {/* Pagamenti */}
          <Route 
            path="/pagamenti" 
            element={
              <ProtectedRoute>
                <PagamentiPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Eventi Critici */}
          <Route 
            path="/eventi-critici" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Eventi Critici" />
              </ProtectedRoute>
            } 
          />
          
          {/* Verbali */}
          <Route 
            path="/verbali" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Verbali" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/verbali/nuovo" 
            element={
              <ProtectedRoute>
                <VerbaleFormPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/verbali/nuovo/:contrattoId" 
            element={
              <ProtectedRoute>
                <VerbaleFormPage />
              </ProtectedRoute>
            } 
          />

          {/* APE */}
          <Route 
            path="/ape" 
            element={
              <ProtectedRoute>
                <ApePage />
              </ProtectedRoute>
            } 
          />

          {/* AI Assistant */}
          <Route 
            path="/ai" 
            element={
              <ProtectedRoute>
                <AiAssistantPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Documenti */}
          <Route 
            path="/documenti" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Documenti" />
              </ProtectedRoute>
            } 
          />
          
          {/* Manutenzione */}
          <Route 
            path="/manutenzione" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Interventi Manutenzione" />
              </ProtectedRoute>
            } 
          />
          
          {/* Report */}
          <Route 
            path="/report" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Report" />
              </ProtectedRoute>
            } 
          />
          
          {/* Audit */}
          <Route 
            path="/audit" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Audit Log" />
              </ProtectedRoute>
            } 
          />
          
          {/* Impostazioni */}
          <Route 
            path="/impostazioni" 
            element={
              <ProtectedRoute>
                <ImpostazioniPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Notifiche */}
          <Route 
            path="/notifiche" 
            element={
              <ProtectedRoute>
                <NotifichePage />
              </ProtectedRoute>
            } 
          />
          
          {/* Profile */}
          <Route 
            path="/profilo" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Profilo Utente" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/cambio-password" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Cambio Password" />
              </ProtectedRoute>
            } 
          />
          
          {/* Catch all - 404 */}
          <Route 
            path="*" 
            element={
              <ProtectedRoute>
                <PlaceholderPage title="Pagina non trovata (404)" />
              </ProtectedRoute>
            } 
          />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
