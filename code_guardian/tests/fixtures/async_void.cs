using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class NotificationService
    {
        private readonly IEmailSender _emailSender;

        public NotificationService(IEmailSender emailSender)
        {
            _emailSender = emailSender;
        }

        // async void perde excecoes — nao deve ser usado fora de event handlers
        public async void SendWelcomeEmail(string email)
        {
            await _emailSender.SendAsync(email, "Bem-vindo!", "Conteudo do email");
        }

        // async void perde excecoes
        private async void ProcessQueueInternal()
        {
            await Task.Delay(1000);
        }
    }
}
