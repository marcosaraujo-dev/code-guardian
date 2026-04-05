using System.Net.Http;
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class ApiClient
    {
        public async Task<string> GetDataAsync(string url)
        {
            // Socket exhaustion: HttpClient criado com new dentro de metodo
            var client = new HttpClient();
            var response = await client.GetStringAsync(url);
            return response;
        }
    }
}
