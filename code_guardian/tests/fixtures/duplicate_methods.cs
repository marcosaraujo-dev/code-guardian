using System;

namespace CodeGuardian.Tests.Fixtures
{
    public class PricingService
    {
        public decimal CalculateOrderTotal(decimal subtotal, decimal taxRate, decimal shipping)
        {
            var tax = subtotal * taxRate;
            var total = subtotal + tax + shipping;
            if (total < 0)
            {
                total = 0;
            }
            return total;
        }

        public decimal CalculateInvoiceTotal(decimal subtotal, decimal taxRate, decimal shipping)
        {
            var tax = subtotal * taxRate;
            var total = subtotal + tax + shipping;
            if (total < 0)
            {
                total = 0;
            }
            return total;
        }

        public int SumSmall(int a, int b)
        {
            return a + b;
        }
    }
}
