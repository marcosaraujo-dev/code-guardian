using System;
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    // async void em event handlers e permitido — nao deve disparar ASYNC_VOID
    public class Form1
    {
        private async void Button_Click(object sender, EventArgs e)
        {
            await Task.Delay(100);
        }

        private async void Form_Load(object sender, EventArgs e)
        {
            await Task.Delay(100);
        }
    }
}
