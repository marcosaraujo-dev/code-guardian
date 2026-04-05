using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class CacheService
    {
        // TODO: implementar cache distribuido com Redis
        public async Task<object> GetAsync(string key)
        {
            // FIXME: remover simulacao e usar cache real
            return await Task.FromResult<object>(null);
        }

        // HACK: solucao temporaria para contornar bug do provider
        public void InvalidateAll()
        {
        }
    }
}
