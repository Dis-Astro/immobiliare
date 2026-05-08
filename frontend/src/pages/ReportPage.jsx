import React, { useState, useEffect } from 'react';
import api from '../stores';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import {
  FileText, Download, FileSpreadsheet, FileType, BarChart3,
  TrendingUp, TrendingDown, Wallet, Building2, Loader2, AlertCircle
} from 'lucide-react';

export default function ReportPage() {
  const { user, token } = useAuthStore();
  const isSupervisore = user?.ruolo === 'supervisore';
  const [periodoDa, setPeriodoDa] = useState('');
  const [periodoA, setPeriodoA] = useState('');
  const [anno, setAnno] = useState(new Date().getFullYear());
  const [executive, setExecutive] = useState(null);
  const [loadingExec, setLoadingExec] = useState(false);
  const [downloading, setDownloading] = useState(null);

  const fetchExecutive = async () => {
    if (!isSupervisore) return;
    setLoadingExec(true);
    try {
      const res = await api.get(`/reports/executive?anno=${anno}`);
      setExecutive(res.data);
    } catch (err) {
      if (err.response?.status !== 403) {
        toast.error('Errore caricamento report executive');
      }
    } finally {
      setLoadingExec(false);
    }
  };

  useEffect(() => { fetchExecutive(); }, [anno]);

  const downloadFile = async (url, filename, format) => {
    setDownloading(format);
    try {
      const res = await api.get(url, { responseType: 'blob' });
      const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
      toast.success(`Download ${format.toUpperCase()} completato`);
    } catch (err) {
      toast.error('Errore download: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDownloading(null);
    }
  };

  const buildQuery = () => {
    const p = new URLSearchParams();
    if (periodoDa) p.set('periodo_da', periodoDa);
    if (periodoA) p.set('periodo_a', periodoA);
    return p.toString();
  };

  const handleExportPagamenti = (formato) => {
    const q = buildQuery();
    const ext = formato === 'excel' ? 'xlsx' : formato;
    if (formato === 'pdf') {
      downloadFile(`/reports/pagamenti/pdf?${q}`, `report_pagamenti_${new Date().toISOString().slice(0,10)}.pdf`, 'pdf');
    } else {
      downloadFile(`/reports/pagamenti?${q}&formato=${formato}`, `report_pagamenti.${ext}`, formato);
    }
  };

  return (
    <div className="space-y-6" data-testid="report-page">
      <div>
        <h1 className="text-3xl font-bold font-heading">Report</h1>
        <p className="text-slate-500">Esporta dati ed analizza la performance del portafoglio</p>
      </div>

      <Tabs defaultValue="pagamenti">
        <TabsList>
          <TabsTrigger value="pagamenti" data-testid="tab-pagamenti">
            <Wallet className="w-4 h-4 mr-2" /> Pagamenti
          </TabsTrigger>
          {isSupervisore && (
            <TabsTrigger value="executive" data-testid="tab-executive">
              <BarChart3 className="w-4 h-4 mr-2" /> Executive
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="pagamenti">
          <Card>
            <CardHeader>
              <CardTitle>Report Pagamenti</CardTitle>
              <CardDescription>
                Esporta l'elenco rate filtrato per periodo in PDF, CSV o Excel.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="periodo-da">Da (YYYY-MM)</Label>
                  <Input
                    id="periodo-da"
                    placeholder="2026-01"
                    value={periodoDa}
                    onChange={e => setPeriodoDa(e.target.value)}
                    data-testid="input-periodo-da"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="periodo-a">A (YYYY-MM)</Label>
                  <Input
                    id="periodo-a"
                    placeholder="2026-12"
                    value={periodoA}
                    onChange={e => setPeriodoA(e.target.value)}
                    data-testid="input-periodo-a"
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-3 pt-2">
                <Button
                  onClick={() => handleExportPagamenti('pdf')}
                  disabled={downloading !== null}
                  data-testid="btn-export-pdf"
                >
                  {downloading === 'pdf' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileType className="w-4 h-4 mr-2" />}
                  Scarica PDF
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleExportPagamenti('csv')}
                  disabled={downloading !== null}
                  data-testid="btn-export-csv"
                >
                  {downloading === 'csv' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileText className="w-4 h-4 mr-2" />}
                  Scarica CSV
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleExportPagamenti('excel')}
                  disabled={downloading !== null}
                  data-testid="btn-export-excel"
                >
                  {downloading === 'excel' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-2" />}
                  Scarica Excel
                </Button>
              </div>

              <div className="text-xs text-slate-500 pt-2 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>Lascia i campi vuoti per esportare tutto il periodo. Formato data: <code>YYYY-MM</code> (es. 2026-03).</span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {isSupervisore && (
          <TabsContent value="executive">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Report Executive</CardTitle>
                  <CardDescription>
                    KPI annuali, occupazione, profit/loss mensile (solo supervisori).
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Label htmlFor="anno-input">Anno</Label>
                  <Input
                    id="anno-input"
                    type="number"
                    value={anno}
                    onChange={e => setAnno(parseInt(e.target.value) || new Date().getFullYear())}
                    className="w-24"
                    data-testid="input-anno"
                  />
                </div>
              </CardHeader>
              <CardContent>
                {loadingExec ? (
                  <div className="text-center py-8"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
                ) : executive ? (
                  <div className="space-y-6" data-testid="executive-data">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <KpiCard label="Immobili" value={executive.patrimonio.immobili} icon={Building2} />
                      <KpiCard label="Unità totali" value={executive.patrimonio.unita_totali} />
                      <KpiCard label="Tasso occupazione" value={`${executive.patrimonio.tasso_occupazione}%`} accent="emerald" />
                      <KpiCard label="Contratti attivi" value={executive.contratti.attivi} />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <KpiCard
                        label="Totale Incassi"
                        value={`€ ${(executive.finanze.totale_incassi || 0).toLocaleString('it-IT', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`}
                        icon={TrendingUp}
                        accent="emerald"
                      />
                      <KpiCard
                        label="Totale Spese"
                        value={`€ ${(executive.finanze.totale_spese || 0).toLocaleString('it-IT', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`}
                        icon={TrendingDown}
                        accent="red"
                      />
                      <KpiCard
                        label="Profit/Loss"
                        value={`€ ${(executive.finanze.profit_loss_totale || 0).toLocaleString('it-IT', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`}
                        accent={executive.finanze.profit_loss_totale >= 0 ? 'emerald' : 'red'}
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Card>
                        <CardHeader><CardTitle className="text-base">Pagamenti</CardTitle></CardHeader>
                        <CardContent className="space-y-2">
                          <div className="flex justify-between"><span className="text-slate-500">Rate in ritardo</span><Badge variant="destructive">{executive.pagamenti.rate_in_ritardo}</Badge></div>
                          <div className="flex justify-between"><span className="text-slate-500">% insoluti</span><Badge variant="secondary">{executive.pagamenti.percentuale_insoluti}%</Badge></div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardHeader><CardTitle className="text-base">Criticità</CardTitle></CardHeader>
                        <CardContent className="space-y-2">
                          <div className="flex justify-between"><span className="text-slate-500">Eventi critici</span><Badge variant="secondary">{executive.criticita.eventi_critici_totali}</Badge></div>
                          <div className="flex justify-between"><span className="text-slate-500">Alta gravità</span><Badge variant="destructive">{executive.criticita.eventi_alta_gravita}</Badge></div>
                        </CardContent>
                      </Card>
                    </div>

                    {executive.finanze.andamento_mensile?.length > 0 && (
                      <Card>
                        <CardHeader><CardTitle className="text-base">Andamento Mensile {executive.anno}</CardTitle></CardHeader>
                        <CardContent>
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b text-slate-500 text-left">
                                  <th className="py-2">Mese</th>
                                  <th className="py-2 text-right">Incassi</th>
                                  <th className="py-2 text-right">Spese</th>
                                  <th className="py-2 text-right">Profit</th>
                                </tr>
                              </thead>
                              <tbody>
                                {executive.finanze.andamento_mensile.map(row => (
                                  <tr key={row.mese} className="border-b hover:bg-slate-50 dark:hover:bg-slate-800">
                                    <td className="py-2 font-mono">{row.mese}</td>
                                    <td className="py-2 text-right text-emerald-600">€ {row.incassi.toLocaleString('it-IT', {minimumFractionDigits: 2})}</td>
                                    <td className="py-2 text-right text-red-600">€ {row.spese.toLocaleString('it-IT', {minimumFractionDigits: 2})}</td>
                                    <td className={`py-2 text-right font-medium ${row.profit >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>€ {row.profit.toLocaleString('it-IT', {minimumFractionDigits: 2})}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                ) : (
                  <p className="text-slate-500 text-center py-4">Nessun dato disponibile</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

function KpiCard({ label, value, icon: Icon, accent }) {
  const accentClass = {
    emerald: 'text-emerald-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
  }[accent] || 'text-slate-900 dark:text-slate-100';

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-slate-500">{label}</p>
            <p className={`text-2xl font-bold mt-1 ${accentClass}`}>{value}</p>
          </div>
          {Icon && <Icon className={`w-5 h-5 ${accentClass}`} />}
        </div>
      </CardContent>
    </Card>
  );
}
