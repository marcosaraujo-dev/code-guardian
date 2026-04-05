namespace CodeGuardian.Tests.Fixtures
{
    public class PaymentService
    {
        // Senha hardcoded
        private string password = "MinhaS3nh@Secreta123";

        // API Key hardcoded
        private string apiKey = "sk-abcdefghijklmnopqrstuvwxyz123456";

        // Token hardcoded
        private string token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature";

        public bool Authenticate()
        {
            return password != null && apiKey != null;
        }
    }
}
