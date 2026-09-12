using System;

namespace CodeGuardian.Tests.Fixtures
{
    public class DiscountService
    {
        public int ApplyDiscount(int basePrice, int tax)
        {
            // This function applies a discount to the total
            var discounted = basePrice - 10;

            // totalPrice equals basePrice plus tax
            var totalPrice = basePrice + tax;

            // Workaround: a API externa as vezes retorna negativo por bug de arredondamento -
            // forcamos o piso em zero ate o fornecedor corrigir (ver ticket INT-482)
            if (discounted < 0)
            {
                discounted = 0;
            }

            return discounted + totalPrice;
        }
    }
}
