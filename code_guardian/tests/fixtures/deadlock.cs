using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class OrderService
    {
        private readonly IOrderRepository _orderRepository;

        public OrderService(IOrderRepository orderRepository)
        {
            _orderRepository = orderRepository;
        }

        public int GetTotalOrders(int userId)
        {
            // Deadlock: .Result bloqueia a thread
            var orders = _orderRepository.GetByUserAsync(userId).Result;
            return orders.Count;
        }

        public void ProcessOrder(int orderId)
        {
            // Deadlock: .Wait() bloqueia a thread
            _orderRepository.ProcessAsync(orderId).Wait();
        }
    }
}
