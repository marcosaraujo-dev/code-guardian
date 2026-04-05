using System;
using System.Collections.Generic;
using System.Linq;
using CodeGuardian.VS.Analysis;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Shell.TableControl;
using Microsoft.VisualStudio.Shell.TableManager;

namespace CodeGuardian.VS.ErrorList
{
    /// <summary>
    /// Fonte de dados para a Error List do Visual Studio.
    /// Implementa ITableDataSource e recebe notificações via AnalysisCompleted.
    /// </summary>
    public sealed class GuardianErrorListService : ITableDataSource, IDisposable
    {
        private const string IdentificadorFonte = "CodeGuardian";
        private const string NomeFonte = "Code Guardian";

        private readonly ITableManager _tableManager;
        private readonly IGuardianAnalysisService _analysisService;
        private readonly List<ITableDataSink> _sinks = new List<ITableDataSink>();
        private readonly object _lock = new object();
        private List<GuardianTableEntry> _entradas = new List<GuardianTableEntry>();

        public string SourceTypeIdentifier => StandardTableDataSources.ErrorTableDataSource;
        public string Identifier => IdentificadorFonte;
        public string DisplayName => NomeFonte;

        public GuardianErrorListService(ITableManager tableManager, IGuardianAnalysisService analysisService)
        {
            _tableManager = tableManager;
            _analysisService = analysisService;
            _tableManager.AddSource(this, StandardTableColumnDefinitions.DetailsExpander,
                StandardTableColumnDefinitions.ErrorSeverity,
                StandardTableColumnDefinitions.ErrorCode,
                StandardTableColumnDefinitions.Text,
                StandardTableColumnDefinitions.DocumentName,
                StandardTableColumnDefinitions.Line,
                StandardTableColumnDefinitions.Column);

            _analysisService.AnalysisCompleted += AoAnaliseCompleta;
        }

        public IDisposable Subscribe(ITableDataSink sink)
        {
            lock (_lock)
            {
                _sinks.Add(sink);
                sink.AddEntries(_entradas.Cast<ITableEntry>().ToList());
            }

            return new UnsubscribeToken(() =>
            {
                lock (_lock) { _sinks.Remove(sink); }
            });
        }

        private void AoAnaliseCompleta(object sender, AnalysisCompletedEventArgs e)
        {
            var novasEntradas = ExtrairEntradas(e.Result, e.FilePath);

            lock (_lock)
            {
                if (e.IsFullScan)
                {
                    // Scan completo: limpar e repopular
                    _entradas = novasEntradas;
                    NotificarSinks(s =>
                    {
                        s.RemoveAllEntries();
                        s.AddEntries(novasEntradas.Cast<ITableEntry>().ToList(), false);
                    });
                }
                else
                {
                    // Arquivo único: substituir apenas entradas deste arquivo
                    _entradas.RemoveAll(ex =>
                        string.Equals(ex.Identity.ToString()?.Split(':')[0], e.FilePath, StringComparison.OrdinalIgnoreCase));
                    _entradas.AddRange(novasEntradas);
                    NotificarSinks(s => s.AddEntries(novasEntradas.Cast<ITableEntry>().ToList(), false));
                }
            }
        }

        private static List<GuardianTableEntry> ExtrairEntradas(GuardianResult resultado, string filtroArquivo)
        {
            var entradas = new List<GuardianTableEntry>();

            foreach (var fileResult in resultado.Files)
            {
                foreach (var issue in fileResult.Issues)
                {
                    entradas.Add(new GuardianTableEntry(issue));
                }
            }

            return entradas;
        }

        private void NotificarSinks(Action<ITableDataSink> acao)
        {
            List<ITableDataSink> copia;
            lock (_lock) { copia = new List<ITableDataSink>(_sinks); }

            foreach (var sink in copia)
            {
                try { acao(sink); } catch { /* sink pode ter sido desregistrado */ }
            }
        }

        /// <summary>
        /// Remove todos os issues do Code Guardian da Error List.
        /// </summary>
        public void Limpar()
        {
            lock (_lock)
            {
                _entradas.Clear();
                NotificarSinks(s => s.RemoveAllEntries());
            }
        }

        public void Dispose()
        {
            _analysisService.AnalysisCompleted -= AoAnaliseCompleta;
            _tableManager.RemoveSource(this);
        }

        private sealed class UnsubscribeToken : IDisposable
        {
            private readonly Action _acao;
            public UnsubscribeToken(Action acao) { _acao = acao; }
            public void Dispose() => _acao();
        }
    }
}
