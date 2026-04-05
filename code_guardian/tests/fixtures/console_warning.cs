using System;

namespace CodeGuardian.Tests.Fixtures
{
    public class DebugHelper
    {
        public void PrintStatus(string message)
        {
            Console.WriteLine($"[STATUS] {message}");
            Console.Write("Processando... ");
        }
    }
}
