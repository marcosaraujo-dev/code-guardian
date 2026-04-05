using System;
using System.Collections.Generic;
using System.Linq;
using CodeGuardian.VS.Analysis;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Text;
using Microsoft.VisualStudio.Text.Adornments;
using Microsoft.VisualStudio.Text.Editor;
using Microsoft.VisualStudio.Text.Tagging;

namespace CodeGuardian.VS.Editor
{
    /// <summary>
    /// ITagger que produz squiggles coloridos nas linhas com issues do Code Guardian.
    /// critical/error = vermelho (SyntaxError), warning = verde (Warning), info = pontilhado (Suggestion).
    /// </summary>
    public sealed class GuardianTagger : ITagger<IErrorTag>, IDisposable
    {
        private readonly ITextView _textView;
        private readonly ITextBuffer _buffer;
        private readonly IGuardianAnalysisService? _analysisService;
        private List<ITagSpan<IErrorTag>> _tags = new List<ITagSpan<IErrorTag>>();

        public event EventHandler<SnapshotSpanEventArgs>? TagsChanged;

        public GuardianTagger(ITextView textView, ITextBuffer buffer, IGuardianAnalysisService? analysisService)
        {
            _textView = textView;
            _buffer = buffer;
            _analysisService = analysisService;

            if (_analysisService != null)
                _analysisService.AnalysisCompleted += AoAnaliseCompleta;
        }

        public IEnumerable<ITagSpan<IErrorTag>> GetTags(NormalizedSnapshotSpanCollection spans)
        {
            var snapshot = _buffer.CurrentSnapshot;

            foreach (var tag in _tags)
            {
                if (tag.Span.Snapshot != snapshot)
                {
                    // Traduzir para snapshot atual
                    var traduzido = tag.Span.TranslateTo(snapshot, SpanTrackingMode.EdgeInclusive);
                    if (spans.IntersectsWith(traduzido))
                        yield return new TagSpan<IErrorTag>(traduzido, tag.Tag);
                }
                else if (spans.IntersectsWith(tag.Span))
                {
                    yield return tag;
                }
            }
        }

        private void AoAnaliseCompleta(object sender, AnalysisCompletedEventArgs e)
        {
            var filePath = ObterCaminhoDoBuffer();
            if (filePath == null)
                return;

            // Verificar se o resultado se aplica a este buffer
            var issues = ObterIssuesParaArquivo(e.Result, filePath);
            var snapshot = _buffer.CurrentSnapshot;
            var novasTags = ConstruirTags(issues, snapshot);

            // TagsChanged deve ser disparado no UI thread
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
                _tags = novasTags;

                var spanCompleto = new SnapshotSpan(snapshot, 0, snapshot.Length);
                TagsChanged?.Invoke(this, new SnapshotSpanEventArgs(spanCompleto));
            });
        }

        private List<ITagSpan<IErrorTag>> ConstruirTags(
            IEnumerable<IssueResult> issues,
            ITextSnapshot snapshot)
        {
            var resultado = new List<ITagSpan<IErrorTag>>();

            foreach (var issue in issues)
            {
                var linhaNumerada = issue.Line - 1;  // 0-indexed
                if (linhaNumerada < 0 || linhaNumerada >= snapshot.LineCount)
                    continue;

                var linha = snapshot.GetLineFromLineNumber(linhaNumerada);
                var span = new SnapshotSpan(snapshot, linha.Start, linha.Length);
                var tipoErro = MapearTipoDeErro(issue.Severity);
                var tag = new ErrorTag(tipoErro, issue.Message);

                resultado.Add(new TagSpan<IErrorTag>(span, tag));
            }

            return resultado;
        }

        private static IEnumerable<IssueResult> ObterIssuesParaArquivo(
            GuardianResult resultado, string filePath)
        {
            foreach (var fileResult in resultado.Files)
            {
                if (string.Equals(fileResult.File, filePath, StringComparison.OrdinalIgnoreCase))
                    return fileResult.Issues;

                // Comparar apenas o nome do arquivo (caminhos relativos vs absolutos)
                if (string.Equals(
                    System.IO.Path.GetFullPath(fileResult.File),
                    System.IO.Path.GetFullPath(filePath),
                    StringComparison.OrdinalIgnoreCase))
                    return fileResult.Issues;
            }

            return Enumerable.Empty<IssueResult>();
        }

        private static string MapearTipoDeErro(string severity) =>
            severity?.ToLowerInvariant() switch
            {
                "critical" => PredefinedErrorTypeNames.SyntaxError,
                "error" => PredefinedErrorTypeNames.OtherError,
                "warning" => PredefinedErrorTypeNames.Warning,
                "info" => PredefinedErrorTypeNames.Suggestion,
                _ => PredefinedErrorTypeNames.Warning,
            };

        private string? ObterCaminhoDoBuffer()
        {
            _buffer.Properties.TryGetProperty(typeof(ITextDocument), out ITextDocument? doc);
            return doc?.FilePath;
        }

        public void Dispose()
        {
            if (_analysisService != null)
                _analysisService.AnalysisCompleted -= AoAnaliseCompleta;
        }
    }
}
