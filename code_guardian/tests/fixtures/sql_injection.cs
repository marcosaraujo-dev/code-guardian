using System.Data.SqlClient;

namespace CodeGuardian.Tests.Fixtures
{
    public class UserRepository
    {
        private readonly string _connectionString = "Server=.;Database=App;";

        public object GetUserByName(string name)
        {
            // SQL Injection por concatenacao
            var query = "SELECT * FROM Users WHERE Name = '" + name + "'";
            using var conn = new SqlConnection(_connectionString);
            using var cmd = new SqlCommand(query, conn);
            conn.Open();
            return cmd.ExecuteScalar();
        }

        public object SearchByEmail(string email)
        {
            // SQL Injection por interpolacao
            var query = $"SELECT * FROM Users WHERE Email = '{email}'";
            using var conn = new SqlConnection(_connectionString);
            using var cmd = new SqlCommand(query, conn);
            conn.Open();
            return cmd.ExecuteScalar();
        }
    }
}
