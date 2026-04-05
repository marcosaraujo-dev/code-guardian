using System.Collections.Generic;
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class OrderProcessor
    {
        public async Task<string> ProcessOrders(List<Order> orders)
        {
            if (orders != null)
            {
                foreach (var order in orders)
                {
                    if (order.IsValid)
                    {
                        if (order.Items.Count > 0)
                        {
                            foreach (var item in order.Items)
                            {
                                if (item.Quantity > 0)
                                {
                                    // Nesting nivel 6 — profundo demais
                                    await ProcessItemAsync(item);
                                }
                            }
                        }
                    }
                }
            }

            return "Concluido";
        }

        private async Task ProcessItemAsync(object item)
        {
            await Task.CompletedTask;
        }
    }

    public class Order
    {
        public bool IsValid { get; set; }
        public List<OrderItem> Items { get; set; } = new();
    }

    public class OrderItem
    {
        public int Quantity { get; set; }
    }
}
