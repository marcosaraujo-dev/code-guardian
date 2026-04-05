using System.ComponentModel.Composition;
using CodeGuardian.VS.Analysis;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Text;
using Microsoft.VisualStudio.Text.Editor;
using Microsoft.VisualStudio.Text.Tagging;
using Microsoft.VisualStudio.Utilities;

namespace CodeGuardian.VS.Editor
{
    /// <summary>
    /// Provider MEF para squiggles inline do Code Guardian em arquivos C#.
    /// Exportado como IViewTaggerProvider para receber acesso ao ITextView (e ao file path).
    /// </summary>
    [Export(typeof(IViewTaggerProvider))]
    [ContentType("CSharp")]
    [TagType(typeof(IErrorTag))]
    public sealed class GuardianTaggerProvider : IViewTaggerProvider
    {
        /// <summary>
        /// Import via MEF: dá acesso aos serviços VS, incluindo o SGuardianAnalysisService.
        /// </summary>
        [Import]
        internal SVsServiceProvider ServiceProvider { get; set; } = null!;

        public ITagger<T>? CreateTagger<T>(ITextView textView, ITextBuffer buffer) where T : ITag
        {
            if (typeof(T) != typeof(IErrorTag))
                return null;

            // Singleton por buffer — evita criar múltiplos taggers para o mesmo arquivo
            return buffer.Properties.GetOrCreateSingletonProperty(() =>
            {
                var service = ServiceProvider.GetService(typeof(SGuardianAnalysisService))
                              as IGuardianAnalysisService;

                return new GuardianTagger(textView, buffer, service);
            }) as ITagger<T>;
        }
    }
}
