using System.ComponentModel.Composition;
using System.Threading.Tasks;
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
                // GetService pode retornar null se o package ainda não terminou InitializeAsync.
                // Com IsAsyncQueryable=true não causa deadlock — retorna null em vez de bloquear.
                var service = ServiceProvider.GetService(typeof(SGuardianAnalysisService))
                              as IGuardianAnalysisService;

                var tagger = new GuardianTagger(textView, buffer, service);

                // Serviço não disponível ainda: conectar de forma assíncrona sem bloquear a UI
                if (service == null)
                    _ = ConectarServicoAsync(tagger);

                return tagger;
            }) as ITagger<T>;
        }

        /// <summary>
        /// Aguarda o package terminar de carregar e conecta o serviço ao tagger já criado.
        /// Evita qualquer bloqueio na UI thread durante a abertura do primeiro arquivo .cs.
        /// </summary>
        private static async Task ConectarServicoAsync(GuardianTagger tagger)
        {
            // Aguardar a inicialização async do package sem bloquear nada
            await Task.Delay(2000).ConfigureAwait(false);

            var service = await AsyncServiceProvider.GlobalProvider
                .GetServiceAsync(typeof(SGuardianAnalysisService)) as IGuardianAnalysisService;

            tagger.ConectarServico(service);
        }
    }
}
