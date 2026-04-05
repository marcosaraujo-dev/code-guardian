using System;
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class DataProcessor
    {
        public async Task<string> ProcessDataAsync(string input)
        {
            try
            {
                if (string.IsNullOrEmpty(input))
                    throw new ArgumentException("Input invalido");

                return await Task.FromResult(input.ToUpper());
            }
            catch { }

            return string.Empty;
        }

        public int ParseInt(string value)
        {
            try
            {
                return int.Parse(value);
            }
            catch (Exception ex) { }

            return 0;
        }
    }
}
